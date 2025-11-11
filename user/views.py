from dj_rest_auth.registration.views import RegisterView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from dj_rest_auth.views import LoginView
from allauth.socialaccount.providers.google import views as google_views
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.utils import jwt_encode
from dj_rest_auth.jwt_auth import set_jwt_cookies
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from datetime import timedelta as td
from rest_framework import serializers
# This is the NEW, correct path
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
import random
import string
import secrets # Import secrets for generating secure tokens
from allauth.account.models import EmailAddress
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import requests
import logging

# Import DRF's throttle classes
from rest_framework.throttling import AnonRateThrottle

# Import internationalization and error handling utilities
from django.utils.translation import gettext as _
from progestock_backend.error_utils import error_response, validation_error_response
from progestock_backend.error_codes import AuthErrors, UserErrors

# Import necessary generic views and models
from rest_framework.generics import GenericAPIView
from .models import User, Invitation
from .serializers import (
    VerificationCodeSerializer,
    ResendVerificationCodeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifyCodeSerializer, # Import the new serializer
    PasswordResetConfirmSerializer,
    TeamMemberSerializer,
    UpdateRoleSerializer,
    InvitationSerializer,
    CreateInvitationSerializer,
    AcceptInvitationSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer
)

logger = logging.getLogger(__name__)


def generate_verification_email_html(code, title, subtitle="Your one time code is below.", expiry_text="24 hours", logo_url=None):
    """
    Generate modern HTML email template for verification codes.
    """
    formatted_code = ' '.join(code)
    
    logo_html = f'<img src="{logo_url}" alt="Company Logo" style="width: 64px; height: 64px; border-radius: 50%;">' if logo_url else '''
                                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M20 12V22H4V12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M22 7H2V12H22V7Z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M12 22V7" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M12 7H7.5C6.83696 7 6.20107 6.73661 5.73223 6.26777C5.26339 5.79893 5 5.16304 5 4.5C5 3.83696 5.26339 3.20107 5.73223 2.73223C6.20107 2.26339 6.83696 2 7.5 2C11 2 12 7 12 7Z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M12 7H16.5C17.163 7 17.7989 6.73661 18.2678 6.26777C18.7366 5.79893 19 5.16304 19 4.5C19 3.83696 18.7366 3.20107 18.2678 2.73223C17.7989 2.26339 17.163 2 16.5 2C13 2 12 7 12 7Z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            '''

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="padding: 48px 40px; text-align: center;">
                            <div style="width: 64px; height: 64px; margin: 0 auto 24px; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;">
                                {logo_html}
                            </div>
                            <h1 style="margin: 0 0 16px; font-size: 28px; font-weight: 700; color: #111827; line-height: 1.2;">
                                {title}
                            </h1>
                            <p style="margin: 0; font-size: 16px; color: #6b7280; line-height: 1.5;">
                                {subtitle}
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 0 40px 48px;">
                            <div style="background-color: #f9fafb; border-radius: 8px; padding: 24px; text-align: center; border: 1px solid #e5e7eb;">
                                <div style="font-size: 32px; font-weight: 600; letter-spacing: 8px; color: #111827; font-family: 'Courier New', monospace;">
                                    {formatted_code}
                                </div>
                            </div>
                            <p style="margin: 24px 0 0; font-size: 14px; color: #6b7280; line-height: 1.5; text-align: center;">
                                If you did not request this email, please ignore it. For security reasons, this code will expire in {expiry_text}.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 32px 40px; background-color: #f9fafb; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0; font-size: 12px; color: #9ca3af; text-align: center; line-height: 1.5;">
                                Please do not reply to this automated message.
                            </p>
                            <p style="margin: 8px 0 0; font-size: 12px; color: #9ca3af; text-align: center;">
                                © {settings.FRONTEND_URL.replace('https://', '').replace('http://', '')} • ProGestock
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def send_invitation_email(recipient_email, invitation_token, company_name, invited_by_name, role):
    """
    Send team invitation email synchronously.
    """
    frontend_url = settings.FRONTEND_URL
    invitation_link = f"{frontend_url}/accept-invitation?token={invitation_token}"

    subject = f"You've been invited to join {company_name} on ProGestock"
    message = f"""Hello,

{invited_by_name} has invited you to join {company_name} on ProGestock as a {role}.

Click the link below to accept the invitation and set up your account:
{invitation_link}

This invitation will expire in 7 days.

If you believe you received this email in error, you can safely ignore it.

Best regards,
The ProGestock Team"""

    from django.core.mail import send_mail
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        logger.info(f"Invitation email sent to {recipient_email} for {company_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to send invitation email to {recipient_email}: {str(e)}")
        return False


def set_jwt_cookies_with_ios_support(response, access_token, refresh_token, remember_me=True):
    """
    Custom cookie setter with iOS compatibility using custom domain
    Uses SameSite=Lax since we're on same root domain (progestock.com)

    Args:
        response: Django Response object
        access_token: JWT access token
        refresh_token: JWT refresh token
        remember_me: If True, sets long-lived cookies (30 days). If False, session cookies. Default True for OAuth.
    """
    from django.conf import settings

    is_production = not settings.DEBUG
    cookie_settings = getattr(settings, 'REST_AUTH', {})
    custom_domain = getattr(settings, 'CUSTOM_DOMAIN', None)

    # Cookie domain - exact match without leading dot (progestock.com)
    # Note: Removed leading dot to fix cookie persistence issues
    cookie_domain = custom_domain if (is_production and custom_domain) else None

    # Determine cookie lifetime based on remember_me
    if remember_me:
        # Persistent cookies for 30 days
        cookie_max_age = int(td(days=30).total_seconds())
        logger.info("Setting persistent cookies (30 days) for OAuth login")
    else:
        # Session cookies (deleted when browser closes)
        cookie_max_age = None
        logger.info("Setting session cookies for OAuth login")

    # Access token cookie
    auth_cookie_name = cookie_settings.get('JWT_AUTH_COOKIE', 'progestock-auth')

    response.set_cookie(
        key=auth_cookie_name,
        value=access_token,
        max_age=cookie_max_age,
        path='/',
        domain=cookie_domain,
        secure=is_production,
        httponly=True,
        samesite='Lax',  # Can use Lax with custom domain (more secure!)
    )

    # Refresh token cookie
    refresh_cookie_name = cookie_settings.get('JWT_AUTH_REFRESH_COOKIE', 'progestock-refresh')

    response.set_cookie(
        key=refresh_cookie_name,
        value=refresh_token,
        max_age=cookie_max_age,
        path='/',
        domain=cookie_domain,
        secure=is_production,
        httponly=True,
        samesite='Lax',  # Can use Lax with custom domain (more secure!)
    )

    logger.info(f"Set cookies with SameSite=Lax, Secure={is_production}, Domain={cookie_domain}, max_age={cookie_max_age}")


class CustomLoginView(LoginView):
    """
    Custom login view to handle the 'Remember Me' functionality and provide user-friendly error messages.
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        import sys
        sys.stderr.write("=== LOGIN VIEW DEBUG ===\n")
        sys.stderr.write(f"Response status: {response.status_code}\n")
        sys.stderr.flush()
        logger.info("=== LOGIN VIEW DEBUG ===")
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response data keys: {response.data.keys() if isinstance(response.data, dict) else 'Not a dict'}")
        logger.info(f"Full response data: {response.data}")
        logger.info("========================")

        # Handle failed login attempts with user-friendly messages
        if response.status_code == 400:
            # Override the default error message with a clearer one
            if isinstance(response.data, dict):
                # Check for common error patterns from dj-rest-auth
                error_msg = None
                if 'non_field_errors' in response.data:
                    error_msg = "Invalid email or password. Please check your credentials and try again."
                elif 'email' in response.data or 'password' in response.data:
                    error_msg = "Invalid email or password. Please check your credentials and try again."
                elif 'detail' in response.data:
                    # Keep the detail message if it's already user-friendly
                    detail = response.data['detail']
                    if 'credentials' in detail.lower() or 'password' in detail.lower():
                        error_msg = "Invalid email or password. Please check your credentials and try again."
                    else:
                        error_msg = detail

                if error_msg:
                    response.data = {
                        'detail': error_msg,
                        'error': error_msg  # Add both for compatibility
                    }
            return response

        if response.status_code == 200:
            user = request.user
            has_company = user.company is not None
            is_new_user = not has_company

            if isinstance(response.data, dict):
                if 'user' not in response.data:
                    response.data['user'] = {}

                response.data['user']['has_company'] = has_company
                response.data['user']['is_new_user'] = is_new_user
                response.data['user']['fullname'] = f"{user.first_name} {user.last_name}".strip()
                response.data['redirect_to'] = 'company-setup' if is_new_user else 'dashboard'

            # Add debug headers
            response['X-Auth-Status'] = 'success'
            response['X-Cookies-Set'] = 'progestock-auth,progestock-refresh'

        # Handle cookie settings based on remember_me flag
        if response.status_code == 200:
            auth_cookie_name = getattr(settings, 'JWT_AUTH_COOKIE', 'progestock-auth')
            refresh_cookie_name = getattr(settings, 'JWT_AUTH_REFRESH_COOKIE', 'progestock-refresh')
            is_production = not settings.DEBUG
            remember_me = request.data.get('remember_me', False)

            logger.info(f"=== REMEMBER ME DEBUG ===")
            logger.info(f"remember_me value from request: {remember_me}")
            logger.info(f"remember_me type: {type(remember_me)}")
            logger.info(f"Request data: {request.data}")
            logger.info(f"Cookies in response before update: {list(response.cookies.keys())}")

            if remember_me:
                # User checked "Remember Me" - set long-lived cookies (30 days)
                logger.info("'Remember Me' was checked. Setting persistent cookies for 30 days.")
                cookie_lifetime = timedelta(days=30)
                cookie_max_age = int(cookie_lifetime.total_seconds())
            else:
                # User did NOT check "Remember Me" - set session cookies (deleted when browser closes)
                logger.info("'Remember Me' was NOT checked. Setting session cookies.")
                cookie_max_age = None  # None = session cookie (deleted when browser closes)

            # Update both cookies with the appropriate settings
            # Check both possible locations for cookies
            if auth_cookie_name in response.cookies:
                logger.info(f"Found {auth_cookie_name} in response.cookies")
                cookie = response.cookies[auth_cookie_name]
                response.set_cookie(
                    key=auth_cookie_name,
                    value=cookie.value,
                    max_age=cookie_max_age,
                    httponly=True,
                    samesite='None',  # Must be None for iOS Safari cross-subdomain cookies
                    secure=is_production,
                    domain=f'.{settings.CUSTOM_DOMAIN}' if is_production else None  # Leading dot for subdomain sharing
                )
                logger.info(f"Updated auth cookie - max_age={cookie_max_age}, secure={is_production}, domain={f'.{settings.CUSTOM_DOMAIN}' if is_production else None}")
            else:
                logger.warning(f"{auth_cookie_name} not found in response.cookies")

            if refresh_cookie_name in response.cookies:
                logger.info(f"Found {refresh_cookie_name} in response.cookies")
                cookie = response.cookies[refresh_cookie_name]
                response.set_cookie(
                    key=refresh_cookie_name,
                    value=cookie.value,
                    max_age=cookie_max_age,
                    httponly=True,
                    samesite='None',  # Must be None for iOS Safari cross-subdomain cookies
                    secure=is_production,
                    domain=f'.{settings.CUSTOM_DOMAIN}' if is_production else None  # Leading dot for subdomain sharing
                )
                logger.info(f"Updated refresh cookie - max_age={cookie_max_age}, secure={is_production}, domain={f'.{settings.CUSTOM_DOMAIN}' if is_production else None}")
            else:
                logger.warning(f"{refresh_cookie_name} not found in response.cookies")

            logger.info(f"Final cookies in response: {list(response.cookies.keys())}")
            logger.info(f"=========================")

        return response

class UserProfileView(APIView):
    """
    A protected view that only returns data for an authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # The `request.user` object is automatically populated by Django
        # after it verifies the JWT from the Authorization header.
        user_data = {
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name
        }
        return Response(user_data, status=status.HTTP_200_OK)


# This is the view for your working Google Login
class GoogleLoginView(APIView):
    """
    Handle both Google Button (access_token) and Google One Tap (id_token)
    WITHOUT using django-allauth to avoid MultipleObjectsReturned
    """
    permission_classes = []
    
    def post(self, request, *args, **kwargs):
        access_token = request.data.get('access_token')
        id_token = request.data.get('id_token')
        
        logger.info(f"Google auth - access_token: {bool(access_token)}, id_token: {bool(id_token)}")
        
        if not access_token and not id_token:
            return Response(
                {'error': 'Either access_token or id_token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_info = None
            
            # Handle id_token (Google One Tap)
            if id_token:
                logger.info("Processing id_token from Google One Tap")
                
                # Verify id_token with Google
                verification_url = "https://oauth2.googleapis.com/tokeninfo"
                verify_response = requests.get(verification_url, params={'id_token': id_token})
                
                if verify_response.status_code != 200:
                    logger.error(f"Token verification failed: {verify_response.text}")
                    return Response(
                        {'error': 'Invalid id_token'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                user_info = verify_response.json()
                
                # Verify the token belongs to our app
                client_id = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']
                if user_info.get('aud') != client_id:
                    logger.error(f"Token audience mismatch")
                    return Response(
                        {'error': 'Token verification failed'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                logger.info(f"id_token verified for: {user_info.get('email')}")
            
            # Handle access_token (Google Button)
            elif access_token:
                logger.info("Processing access_token from Google Button")
                
                # Get user info from Google using access_token
                userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
                headers = {'Authorization': f'Bearer {access_token}'}
                userinfo_response = requests.get(userinfo_url, headers=headers)
                
                if userinfo_response.status_code != 200:
                    logger.error(f"Failed to get user info: {userinfo_response.text}")
                    return Response(
                        {'error': 'Failed to fetch user information'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                user_info = userinfo_response.json()
                logger.info(f"access_token verified for: {user_info.get('email')}")
            
            # Extract user data
            email = user_info.get('email')
            given_name = user_info.get('given_name', '')
            family_name = user_info.get('family_name', '')
            profile_picture = user_info.get('picture', '')  # Get Google profile picture

            if not email:
                return Response(
                    {'error': 'Email not provided by Google'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get or create user
            from django.contrib.auth import get_user_model
            from allauth.account.models import EmailAddress

            User = get_user_model()

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    # 'username': email,
                    'first_name': given_name,
                    'last_name': family_name,
                    'profile_picture': profile_picture,
                    'is_active': True,
                }
            )

            # Update name and profile picture if user exists
            if not created:
                updated = False
                if not user.first_name or not user.last_name:
                    user.first_name = given_name or user.first_name
                    user.last_name = family_name or user.last_name
                    updated = True
                # Always update profile picture from Google
                if profile_picture and user.profile_picture != profile_picture:
                    user.profile_picture = profile_picture
                    updated = True
                if updated:
                    user.save()
            
            # Mark email as verified
            email_obj, _ = EmailAddress.objects.get_or_create(
                user=user,
                email=email,
                defaults={'verified': True, 'primary': True}
            )
            if not email_obj.verified:
                email_obj.verified = True
                email_obj.save()
            
            # Generate JWT tokens
            from dj_rest_auth.utils import jwt_encode
            from dj_rest_auth.jwt_auth import set_jwt_cookies
            
            access_token_jwt, refresh_token_jwt = jwt_encode(user)
            
            # Check if user has company
            has_company = user.company is not None
            is_new_user = not has_company
            
            response_data = {
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'fullname': f"{user.first_name} {user.last_name}".strip(),
                    'is_new_user': is_new_user,
                    'has_company': has_company,
                },
                'redirect_to': 'company-setup' if is_new_user else 'dashboard',
            }

            response = Response(response_data, status=status.HTTP_200_OK)
            # Use custom cookie setter for iOS compatibility
            set_jwt_cookies_with_ios_support(response, access_token_jwt, refresh_token_jwt)

            # Add headers to help with debugging and iOS compatibility
            response['X-Auth-Status'] = 'success'
            response['X-Cookies-Set'] = 'progestock-auth,progestock-refresh'

            # Ensure CORS headers are explicitly set for cookie acceptance
            origin = request.META.get('HTTP_ORIGIN')
            if origin:
                response['Access-Control-Allow-Origin'] = origin
                response['Access-Control-Allow-Credentials'] = 'true'
                response['Vary'] = 'Origin'

            logger.info(f"Google login successful for {email} (new_user={is_new_user})")
            logger.info(f"Cookies set: {list(response.cookies.keys())}")
            logger.info(f"Cookie details: {[(k, v.value[:20]+'...', v.get('samesite'), v.get('secure'), v.get('httponly')) for k, v in response.cookies.items()]}")
            logger.info(f"Origin: {request.META.get('HTTP_ORIGIN', 'No origin header')}")
            logger.info(f"User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')[:100]}")
            return response
            
        except requests.RequestException as e:
            logger.exception(f"Network error during Google auth: {str(e)}")
            return Response(
                {'error': 'Failed to communicate with Google', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(f"Google login error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': 'Google authentication failed', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VerifyCodeView(GenericAPIView):
    """
    Handles email verification.
    On success, it activates the user AND performs a login by setting
    secure, HttpOnly JWT cookies in the user's browser.
    """
    serializer_class = VerificationCodeSerializer
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        user = User.objects.filter(email__iexact=email).first()

        if not user:
            logger.warning(f"Verification failed: User not found for email {email}")
            return error_response(
                message=AuthErrors.INVALID_VERIFICATION_CODE['message'],
                code=AuthErrors.INVALID_VERIFICATION_CODE['code'],
                status=status.HTTP_400_BAD_REQUEST
            )

        # Debug logging
        logger.info(f"Verification attempt - Email: {email}, Code received: {code}, Code in DB: {user.verification_code}")

        if user.verification_code != code:
            logger.warning(f"Verification failed: Code mismatch for {email}")
            return error_response(
                message=AuthErrors.INVALID_VERIFICATION_CODE['message'],
                code=AuthErrors.INVALID_VERIFICATION_CODE['code'],
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_active:
             return error_response(
                message=AuthErrors.EMAIL_ALREADY_VERIFIED['message'],
                code=AuthErrors.EMAIL_ALREADY_VERIFIED['code'],
                status=status.HTTP_400_BAD_REQUEST
            )

        # Activate user and email address
        email_address, _ = EmailAddress.objects.get_or_create(user=user, email=user.email, primary=True)
        email_address.verified = True
        email_address.save()
        user.is_active = True
        user.verification_code = None
        user.save()

        # --- THE FIX: Perform a login by generating tokens and setting cookies ---
        # 2. Generate the access and refresh tokens
        access_token, refresh_token = jwt_encode(user)

        # Check if user has company
        has_company = user.company is not None
        is_new_user = not has_company

        # 3. Create a response object with user data and flags
        response_data = {
            "detail": "Verification successful. User is now logged in.",
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "fullname": f"{user.first_name} {user.last_name}".strip(),
                "is_new_user": is_new_user,
                "has_company": has_company,
            },
            "redirect_to": "company-setup" if is_new_user else "dashboard",
        }
        response = Response(response_data, status=status.HTTP_200_OK)

        # 4. Use dj-rest-auth's utility to set the HttpOnly cookies on the response
        set_jwt_cookies(response, access_token, refresh_token)

        # 5. Return the response with the cookies
        return response

class ResendVerificationCodeView(GenericAPIView):
    """
    Resend a new 6-digit verification code to an unverified user.
    """
    throttle_classes = [AnonRateThrottle]
    serializer_class = ResendVerificationCodeSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=False)
        except User.DoesNotExist:
            # Return success message even if user doesn't exist (security best practice)
            return Response({
                "message": "If an account with that email exists and is not verified, a new code has been sent."
            }, status=status.HTTP_200_OK)

        # Generate new 6-digit verification code
        code = str(random.randint(100000, 999999))
        user.verification_code = code
        user.save(update_fields=['verification_code'])

        # Send email with modern HTML design
        subject = "Your New ProGestock Verification Code"

        logo_url = None
        if user.company and user.company.logo:
            logo_url = user.company.logo.url

        html_message = generate_verification_email_html(
            code=code,
            title="Verify your email to continue",
            subtitle="Your new one time code is below.",
            expiry_text="24 hours",
            logo_url=logo_url
        )

        plain_message = f"""
Verify Your ProGestock Account

Your new verification code is: {code}

This code will expire in 24 hours.

If you didn't request this code, please ignore this email.

Please do not reply to this automated message.

© ProGestock
"""

        from django.core.mail import EmailMultiAlternatives
        try:
            email_msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email_msg.attach_alternative(html_message, "text/html")
            email_msg.send(fail_silently=False)

            logger.info(f"Resent verification code to {email}")
        except Exception as e:
            logger.error(f"Failed to resend verification code to {email}: {str(e)}")

        return Response({
            "message": "If an account with that email exists and is not verified, a new code has been sent."
        }, status=status.HTTP_200_OK)

class PasswordResetRequestView(GenericAPIView):
    """
    Request a password reset by sending a 6-digit code to the user's email.
    """
    throttle_classes = [AnonRateThrottle]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            # Return success message even if user doesn't exist (security best practice)
            return Response({
                "message": "If an account with that email exists, a password reset code has been sent."
            }, status=status.HTTP_200_OK)

        # Generate 6-digit password reset code
        code = str(random.randint(100000, 999999))
        user.password_reset_code = code
        user.password_reset_code_created_at = timezone.now()
        user.save(update_fields=['password_reset_code', 'password_reset_code_created_at'])

        # Send email with modern HTML design
        subject = "Reset Your ProGestock Password"

        logo_url = None
        if user.company and user.company.logo:
            logo_url = user.company.logo.url

        html_message = generate_verification_email_html(
            code=code,
            title="Reset your password",
            subtitle="Your one time password reset code is below.",
            expiry_text="15 minutes",
            logo_url=logo_url
        )

        plain_message = f"""
Reset Your ProGestock Password

Your password reset code is: {code}

This code will expire in 15 minutes.

If you didn't request this password reset, please ignore this email and your password will remain unchanged.

Please do not reply to this automated message.

© ProGestock
"""

        from django.core.mail import EmailMultiAlternatives
        try:
            email_msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email_msg.attach_alternative(html_message, "text/html")
            email_msg.send(fail_silently=False)

            logger.info(f"Sent password reset code to {email}")
        except Exception as e:
            logger.error(f"Failed to send password reset code to {email}: {str(e)}")

        return Response({
            "message": "If an account with that email exists, a password reset code has been sent."
        }, status=status.HTTP_200_OK)

# --- New View to Verify the Password Reset Code ---
class PasswordResetVerifyCodeView(GenericAPIView):
    """
    Step 2 of password reset: Verify the code sent to the user's email.
    If successful, it returns a secure, single-use token.
    """
    throttle_classes = [AnonRateThrottle]
    serializer_class = PasswordResetVerifyCodeSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        try:
            user = User.objects.get(email=email, password_reset_code=code)
            if user.is_password_reset_code_expired():
                return error_response(
                    message=AuthErrors.TOKEN_EXPIRED['message'],
                    code=AuthErrors.TOKEN_EXPIRED['code'],
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Generate a secure, single-use token for the final step
            token = secrets.token_urlsafe(32)
            user.password_reset_token = token
            user.password_reset_token_created_at = timezone.now()
            # Clear the reset code now that it's been used
            user.password_reset_code = None
            user.save()

            # Return the token to the frontend
            return Response({"token": token}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return error_response(
                message=AuthErrors.INVALID_TOKEN['message'],
                code=AuthErrors.INVALID_TOKEN['code'],
                status=status.HTTP_400_BAD_REQUEST
            )


# --- Modified View to Confirm Password Reset using the Token ---
class PasswordResetConfirmView(GenericAPIView):
    """
    Step 3 of password reset: Set the new password using the secure token.
    """
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(password_reset_token=token)

            # Check if the token has expired (e.g., 5 minutes after verification)
            if timezone.now() > user.password_reset_token_created_at + timezone.timedelta(minutes=5):
                return error_response(
                    message=AuthErrors.TOKEN_EXPIRED['message'],
                    code=AuthErrors.TOKEN_EXPIRED['code'],
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Set the new password and clear all reset-related fields
            user.set_password(password)
            user.password_reset_token = None
            user.password_reset_token_created_at = None
            user.save()

            return Response({"message": "Password has been successfully reset."}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return error_response(
                message=AuthErrors.INVALID_TOKEN['message'],
                code=AuthErrors.INVALID_TOKEN['code'],
                status=status.HTTP_400_BAD_REQUEST
            )


class CustomRegisterView(RegisterView):
    """
    Custom registration view that sends 6-digit verification codes.
    """
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        if response.status_code == status.HTTP_201_CREATED:
            logger.info(f"User registered successfully: {request.data.get('email')}")
        else:
            logger.warning(f"Registration failed for: {request.data.get('email')}")

        return response


# ===========================
# TEAM MANAGEMENT VIEWS
# ===========================

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from django.db.models import Q, Count, Max
from django.utils import timezone


class IsAdminRole(permissions.BasePermission):
    """
    Permission class to check if user has Admin role.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.ROLE_ADMIN


class TeamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing team members.
    """
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only users from the current user's company."""
        if self.request.user.company:
            return User.objects.filter(company=self.request.user.company).order_by('-date_joined')
        return User.objects.none()

    def get_permissions(self):
        """Only admins can perform write operations."""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'update_role', 'deactivate', 'remove']:
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get team statistics for the KPI cards."""
        if not request.user.company:
            return Response({
                'total_seats': 0,
                'active_users': 0,
                'pending_invitations': 0
            })

        company = request.user.company

        # Total seats
        total_seats = User.objects.filter(company=company).count()

        # Active users (logged in within last 30 days)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        active_users = User.objects.filter(
            company=company,
            is_active=True,
            last_active__gte=thirty_days_ago
        ).count()

        # Pending invitations
        pending_invitations = Invitation.objects.filter(
            company=company,
            status=Invitation.STATUS_PENDING
        ).count()

        return Response({
            'total_seats': total_seats,
            'active_users': active_users,
            'pending_invitations': pending_invitations
        })

    @action(detail=True, methods=['patch'])
    def update_role(self, request, pk=None):
        """Update a team member's role."""
        user = self.get_object()

        # Prevent users from changing their own role
        if user == request.user:
            return Response(
                {'error': 'You cannot change your own role.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UpdateRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.role = serializer.validated_data['role']
        user.save(update_fields=['role'])

        return Response(TeamMemberSerializer(user).data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a team member."""
        user = self.get_object()

        # Prevent users from deactivating themselves
        if user == request.user:
            return Response(
                {'error': 'You cannot deactivate yourself.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_active = False
        user.save(update_fields=['is_active'])

        return Response({'message': 'User has been deactivated.'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Reactivate a team member."""
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])

        return Response({'message': 'User has been activated.'})

    @action(detail=True, methods=['delete'])
    def remove(self, request, pk=None):
        """Remove a team member from the company."""
        user = self.get_object()

        # Prevent users from removing themselves
        if user == request.user:
            return Response(
                {'error': 'You cannot remove yourself. Transfer ownership first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Instead of deleting, we'll just remove them from the company
        user.company = None
        user.is_active = False
        user.save(update_fields=['company', 'is_active'])

        return Response({'message': 'User has been removed from the company.'})


class InviteView(GenericAPIView):
    """
    Handle sending team invitations.
    """
    serializer_class = CreateInvitationSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        """Send invitations to one or more email addresses."""
        if not request.user.company:
            return Response(
                {'error': 'You must be part of a company to invite members.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        emails = serializer.validated_data['emails']
        role = serializer.validated_data['role']
        company = request.user.company

        created_invitations = []
        errors = []

        for email in emails:
            # Check if user already exists in company
            if User.objects.filter(email__iexact=email, company=company).exists():
                errors.append({
                    'email': email,
                    'error': 'User is already a member of your company.'
                })
                continue

            # Check for existing pending invitations
            existing_invitation = Invitation.objects.filter(
                email__iexact=email,
                company=company,
                status=Invitation.STATUS_PENDING
            ).first()

            if existing_invitation:
                errors.append({
                    'email': email,
                    'error': 'A pending invitation already exists for this email.'
                })
                continue

            # Create new invitation
            try:
                invitation = Invitation.objects.create(
                    email=email,
                    company=company,
                    invited_by=request.user,
                    role=role
                )

                # Send invitation email
                send_invitation_email(
                    recipient_email=email,
                    invitation_token=invitation.token,
                    company_name=company.name,
                    invited_by_name=request.user.get_full_name(),
                    role=dict(User.ROLE_CHOICES)[role]
                )

                created_invitations.append(InvitationSerializer(invitation).data)

            except Exception as e:
                errors.append({
                    'email': email,
                    'error': str(e)
                })

        response_data = {
            'created': created_invitations,
            'errors': errors
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    def get(self, request):
        """List all pending invitations for the company."""
        if not request.user.company:
            return Response([])

        invitations = Invitation.objects.filter(
            company=request.user.company,
            status=Invitation.STATUS_PENDING
        )

        serializer = InvitationSerializer(invitations, many=True)
        return Response(serializer.data)


class ResendInvitationView(GenericAPIView):
    """
    Resend an invitation email.
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request, invitation_id):
        """Resend an invitation."""
        try:
            invitation = Invitation.objects.get(
                id=invitation_id,
                company=request.user.company,
                status=Invitation.STATUS_PENDING
            )
        except Invitation.DoesNotExist:
            return Response(
                {'error': 'Invitation not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if invitation.is_expired():
            # Create a new invitation
            old_invitation = invitation
            old_invitation.status = Invitation.STATUS_EXPIRED
            old_invitation.save()

            invitation = Invitation.objects.create(
                email=old_invitation.email,
                company=old_invitation.company,
                invited_by=request.user,
                role=old_invitation.role
            )

        # Send invitation email
        send_invitation_email(
            recipient_email=invitation.email,
            invitation_token=invitation.token,
            company_name=invitation.company.name,
            invited_by_name=request.user.get_full_name(),
            role=dict(User.ROLE_CHOICES)[invitation.role]
        )

        return Response({
            'message': 'Invitation has been resent.',
            'invitation': InvitationSerializer(invitation).data
        })


class AcceptInvitationView(GenericAPIView):
    """
    Handle accepting an invitation and setting up the account.
    """
    serializer_class = AcceptInvitationSerializer
    permission_classes = []

    def post(self, request):
        """Accept an invitation and create the user account."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        password = serializer.validated_data['password']
        first_name = serializer.validated_data['first_name']
        last_name = serializer.validated_data.get('last_name', '')

        try:
            invitation = Invitation.objects.get(token=token)
        except Invitation.DoesNotExist:
            return Response(
                {'error': 'Invalid invitation token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not invitation.is_valid():
            return Response(
                {'error': 'This invitation has expired or is no longer valid.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user already exists
        if User.objects.filter(email__iexact=invitation.email).exists():
            return Response(
                {'error': 'An account with this email already exists. Please log in instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create the user
        user = User.objects.create_user(
            email=invitation.email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            company=invitation.company,
            role=invitation.role,
            is_active=True
        )

        # Mark email as verified
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=True
        )

        # Update invitation status
        invitation.status = Invitation.STATUS_ACCEPTED
        invitation.save()

        # Log the user in by generating JWT tokens
        access_token, refresh_token = jwt_encode(user)

        response_data = {
            'message': 'Account created successfully.',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'fullname': user.get_full_name(),
                'role': user.role,
                'company': {
                    'id': user.company.id,
                    'name': user.company.name
                }
            },
            'redirect_to': 'dashboard'
        }

        response = Response(response_data, status=status.HTTP_201_CREATED)
        set_jwt_cookies(response, access_token, refresh_token)

        return response


class ValidateInvitationView(GenericAPIView):
    """
    Validate an invitation token and return invitation details.
    """
    permission_classes = []

    def get(self, request):
        """Validate invitation token from query params."""
        token = request.query_params.get('token')

        if not token:
            return Response(
                {'error': 'Token is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invitation = Invitation.objects.get(token=token)
        except Invitation.DoesNotExist:
            return Response(
                {'error': 'Invalid invitation token.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not invitation.is_valid():
            return Response(
                {'error': 'This invitation has expired or is no longer valid.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'email': invitation.email,
            'company_name': invitation.company.name,
            'role': dict(User.ROLE_CHOICES)[invitation.role],
            'invited_by': invitation.invited_by.get_full_name() if invitation.invited_by else None,
            'expires_at': invitation.expires_at
        })


# ===========================
# SETTINGS VIEWS
# ===========================

from rest_framework.generics import RetrieveUpdateAPIView


class UserProfileDetailView(RetrieveUpdateAPIView):
    """
    Retrieve and update the current user's profile.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Return the current user."""
        return self.request.user


class ChangePasswordAPIView(GenericAPIView):
    """
    Change the current user's password.
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Change password."""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'message': 'Password changed successfully. Please log in with your new password.'
        }, status=status.HTTP_200_OK)


class DebugCookieSettingsView(APIView):
    """Debug endpoint to check cookie domain settings."""
    permission_classes = []  # Allow anyone to access for debugging

    def get(self, request):
        """Return current cookie domain settings."""
        from django.conf import settings

        return Response({
            'CUSTOM_DOMAIN': getattr(settings, 'CUSTOM_DOMAIN', 'Not set'),
            'IS_PRODUCTION': getattr(settings, 'IS_PRODUCTION', 'Not set'),
            'DEBUG': settings.DEBUG,
            'SESSION_COOKIE_DOMAIN': getattr(settings, 'SESSION_COOKIE_DOMAIN', 'Not set'),
            'CSRF_COOKIE_DOMAIN': getattr(settings, 'CSRF_COOKIE_DOMAIN', 'Not set'),
            'REST_AUTH_JWT_COOKIE_DOMAIN': settings.REST_AUTH.get('JWT_AUTH_COOKIE_DOMAIN', 'Not set'),
            'SIMPLE_JWT_AUTH_COOKIE_DOMAIN': settings.SIMPLE_JWT.get('AUTH_COOKIE_DOMAIN', 'Not set'),
        }, status=status.HTTP_200_OK)
