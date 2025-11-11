from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from allauth.account.models import EmailAddress
from .models import User, Invitation
from company.serializers import CompanySerializer 

User = get_user_model()

class UserDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer for the user details endpoint.
    Includes nested company information to check onboarding status.
    """
    # 2. Nest the CompanySerializer to include company details
    company = CompanySerializer(read_only=True)

    # Add computed fields for frontend routing logic
    has_company = serializers.SerializerMethodField()
    is_new_user = serializers.SerializerMethodField()
    fullname = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('pk', 'email', 'first_name', 'last_name', 'fullname', 'profile_picture', 'role', 'company', 'has_company', 'is_new_user')

    def get_has_company(self, obj):
        return obj.company is not None

    def get_is_new_user(self, obj):
        return obj.company is None

    def get_fullname(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

class CustomRegisterSerializer(RegisterSerializer):
    username = None
    fullname = serializers.CharField(max_length=150, write_only=True, required=True)
    
    # This field accepts the single password from the frontend.
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    def run_validation(self, data):
        """
        This is the key to the solution. We intercept the data before the parent
        serializer's validation runs.
        """
        # Get the single password from the incoming data.
        password = data.get('password')
        
        # Create the 'password1' and 'password2' fields that the parent class expects.
        data['password1'] = password
        data['password2'] = password
        
        # Now, call the parent class's validation with the corrected data.
        # This will no longer fail.
        return super().run_validation(data)

    def validate_email(self, email):
        email = super().validate_email(email)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(_("A user is already registered with this email address."))
        return email

    def get_cleaned_data(self):
        # We still need this to pass the fullname to the save method.
        data = super().get_cleaned_data()
        data.update({
            'fullname': self.validated_data.get('fullname', ''),
        })
        return data

    def save(self, request):
        import logging
        logger = logging.getLogger(__name__)

        # Set cleaned_data on the serializer instance
        self.cleaned_data = self.get_cleaned_data()

        user = super().save(request)

        # Set user's full name BEFORE sending confirmation email
        fullname = self.cleaned_data.get('fullname')
        if fullname:
            parts = fullname.strip().split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
            user.save(update_fields=['first_name', 'last_name'])

        # Send email confirmation with 6-digit code
        email = self.cleaned_data.get('email')
        if email:
            email_address_obj, created = EmailAddress.objects.get_or_create(
                user=user,
                email__iexact=email,
                defaults={'email': email, 'primary': True, 'verified': False}
            )

            # Send confirmation email if not verified
            if not email_address_obj.verified:
                try:
                    email_address_obj.send_confirmation(request, signup=True)
                    logger.info(f"Verification code sent to {email}")
                except Exception as e:
                    logger.error(f"Failed to send verification code to {email}: {str(e)}")
                    # Don't raise - log the error but allow registration to complete
                    # The user is already created, and they can request a new code later
                    logger.warning(f"Registration completed for {email} but email verification failed - user can resend code")

        return user



class VerificationCodeSerializer(serializers.Serializer):
    """
    Serializer for the verification code endpoint.
    Validates that email and a 6-digit code are provided.
    """
    email = serializers.EmailField()
    code = serializers.CharField(
        required=True,
        max_length=6,
        min_length=6,
        write_only=True
    )

class ResendVerificationCodeSerializer(serializers.Serializer):
    """
    Serializer for the resend verification code endpoint.
    Validates that an email is provided.
    """
    email = serializers.EmailField()


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset.
    It validates that an email is provided.
    """
    email = serializers.EmailField()

class PasswordResetVerifyCodeSerializer(serializers.Serializer):
    """
    Serializer for the second step of password reset: verifying the reset code.
    """
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6, write_only=True)

class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for the final step of password reset: setting a new password.
    It now uses the secure token and validates the new password.
    """
    token = serializers.CharField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )


# Team Management Serializers

class TeamMemberSerializer(serializers.ModelSerializer):
    """
    Serializer for team member information.
    """
    full_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role', 'last_active', 'date_joined', 'is_active', 'status']
        read_only_fields = ['id', 'email', 'date_joined', 'is_active', 'last_active']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_status(self, obj):
        """Return the status of the user (Active or Inactive)."""
        return 'Active' if obj.is_active else 'Inactive'


class UpdateRoleSerializer(serializers.Serializer):
    """
    Serializer for updating a user's role.
    """
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)

    def validate_role(self, value):
        """Ensure the role is valid."""
        if value not in dict(User.ROLE_CHOICES).keys():
            raise serializers.ValidationError("Invalid role.")
        return value


class InvitationSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and viewing invitations.
    """
    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)
    invited_by_name = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = ['id', 'email', 'role', 'status', 'created_at', 'expires_at', 'invited_by_email', 'invited_by_name', 'is_expired']
        read_only_fields = ['id', 'status', 'created_at', 'expires_at', 'invited_by_email', 'invited_by_name', 'is_expired']

    def get_invited_by_name(self, obj):
        if obj.invited_by:
            return obj.invited_by.get_full_name()
        return None

    def get_is_expired(self, obj):
        return obj.is_expired()

    def validate_email(self, value):
        """Validate that the email doesn't already belong to a user in this company."""
        request = self.context.get('request')
        if request and request.user.company:
            if User.objects.filter(email__iexact=value, company=request.user.company).exists():
                raise serializers.ValidationError("A user with this email is already a member of your company.")

            # Check for pending invitations
            if Invitation.objects.filter(
                email__iexact=value,
                company=request.user.company,
                status=Invitation.STATUS_PENDING
            ).exists():
                raise serializers.ValidationError("An invitation has already been sent to this email address.")

        return value


class CreateInvitationSerializer(serializers.Serializer):
    """
    Serializer for creating new invitations (supports multiple emails).
    """
    emails = serializers.ListField(
        child=serializers.EmailField(),
        min_length=1,
        max_length=10,
        help_text="List of email addresses to invite"
    )
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default=User.ROLE_MEMBER)

    def validate_emails(self, value):
        """Validate that emails are unique in the list."""
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate email addresses are not allowed.")
        return value


class AcceptInvitationSerializer(serializers.Serializer):
    """
    Serializer for accepting an invitation and setting up the account.
    """
    token = serializers.CharField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)


# Settings Serializers

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile updates (name, email - read only).
    Does not include role to prevent users from changing their own role.
    """
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'profile_picture', 'role', 'date_joined']
        read_only_fields = ['id', 'email', 'role', 'date_joined']

    def get_full_name(self, obj):
        return obj.get_full_name()


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing password.
    """
    current_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate_current_password(self, value):
        """Validate that the current password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        """Validate that new passwords match."""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "Password fields didn't match."
            })
        return attrs

    def save(self, **kwargs):
        """Update the user's password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

