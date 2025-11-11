from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
import logging
import random

logger = logging.getLogger(__name__)

class CustomEmailAdapter(DefaultAccountAdapter):
    """
    Custom adapter that sends 6-digit verification codes instead of links.
    """

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """
        Override to send 6-digit code instead of link.
        This is called by allauth during email verification.
        """
        user = emailconfirmation.email_address.user
        email = emailconfirmation.email_address.email

        # Generate 6-digit verification code
        verification_code = str(random.randint(100000, 999999))

        # Store code in user model
        user.verification_code = verification_code
        user.save(update_fields=['verification_code'])

        logger.info(f"Generated verification code for {email}: {verification_code}")

        # Format code with spaces (e.g., "1 2 3 4 5 6")
        formatted_code = ' '.join(verification_code)

        # Send email with modern HTML design
        subject = "Verify Your ProGestock Account"

        html_message = f"""
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
                    <!-- Header with logo/icon -->
                    <tr>
                        <td style="padding: 48px 40px; text-align: center;">
                            <div style="width: 64px; height: 64px; margin: 0 auto 24px; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M20 12V22H4V12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M22 7H2V12H22V7Z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M12 22V7" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M12 7H7.5C6.83696 7 6.20107 6.73661 5.73223 6.26777C5.26339 5.79893 5 5.16304 5 4.5C5 3.83696 5.26339 3.20107 5.73223 2.73223C6.20107 2.26339 6.83696 2 7.5 2C11 2 12 7 12 7Z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M12 7H16.5C17.163 7 17.7989 6.73661 18.2678 6.26777C18.7366 5.79893 19 5.16304 19 4.5C19 3.83696 18.7366 3.20107 18.2678 2.73223C17.7989 2.26339 17.163 2 16.5 2C13 2 12 7 12 7Z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            </div>
                            <h1 style="margin: 0 0 16px; font-size: 28px; font-weight: 700; color: #111827; line-height: 1.2;">
                                Verify your email to continue
                            </h1>
                            <p style="margin: 0; font-size: 16px; color: #6b7280; line-height: 1.5;">
                                Your one time code is below.
                            </p>
                        </td>
                    </tr>

                    <!-- Verification code box -->
                    <tr>
                        <td style="padding: 0 40px 48px;">
                            <div style="background-color: #f9fafb; border-radius: 8px; padding: 24px; text-align: center; border: 1px solid #e5e7eb;">
                                <div style="font-size: 32px; font-weight: 600; letter-spacing: 8px; color: #111827; font-family: 'Courier New', monospace;">
                                    {formatted_code}
                                </div>
                            </div>

                            <p style="margin: 24px 0 0; font-size: 14px; color: #6b7280; line-height: 1.5; text-align: center;">
                                If you did not request this email, please ignore it. For security reasons, this code will expire in 24 hours.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
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

        # Plain text fallback
        plain_message = f"""
Verify Your ProGestock Account

Your verification code is: {verification_code}

This code will expire in 24 hours.

If you didn't create an account with ProGestock, please ignore this email.

Please do not reply to this automated message.

© ProGestock
"""

        from django.core.mail import EmailMultiAlternatives

        try:
            email_msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email]
            )
            email_msg.attach_alternative(html_message, "text/html")
            email_msg.send(fail_silently=False)

            logger.info(f"Verification email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            raise

    def save_user(self, request, user, form, commit=True):
        """
        For regular email registration, keep users inactive until email verified.
        """
        user = super().save_user(request, user, form, commit=False)
        user.is_active = False
        if commit:
            user.save()
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adapter for social account authentication (Google OAuth).
    Handles both new signups and existing user logins.
    """

    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a social provider.
        This handles EXISTING users logging in again with Google.
        """
        if sociallogin.is_existing:
            user = sociallogin.user
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active'])

    def save_user(self, request, sociallogin, form=None):
        """
        Saves a NEW user instance using information from the social provider.
        This only runs for FIRST-TIME Google signups.
        """
        user = super().save_user(request, sociallogin, form)

        # Activate the user since Google has verified their email
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])

        logger.info(f"New user {user.email} signed up via Google")
        return user

    def populate_user(self, request, sociallogin, data):
        """
        Hook for populating user instance with data from social provider.
        Ensures is_active is set to True for new social users.
        """
        user = super().populate_user(request, sociallogin, data)
        user.is_active = True
        return user

    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Return True to allow automatic signup without additional form.
        This enables seamless Google login for both new and existing users.
        """
        return True