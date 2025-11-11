from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from datetime import timedelta
from company.models import Company
import uuid
import secrets

class UserManager(BaseUserManager):
    """
    Custom manager for the User model.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # Ensure new superusers are active by default
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for ProGestock.
    """
    # Role choices for team management
    ROLE_ADMIN = 'admin'
    ROLE_MEMBER = 'member'
    ROLE_VIEWER = 'viewer'

    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MEMBER, 'Member'),
        (ROLE_VIEWER, 'Viewer'),
    ]

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    profile_picture = models.URLField(max_length=500, blank=True, null=True, help_text="URL to user's profile picture (e.g., from Google)")

    # Fields for email verification
    verification_code = models.CharField(max_length=6, blank=True, null=True)

    # Fields for password reset flow
    password_reset_code = models.CharField(max_length=6, blank=True, null=True)
    password_reset_code_created_at = models.DateTimeField(blank=True, null=True)
    password_reset_token = models.CharField(max_length=100, blank=True, null=True, unique=True)
    password_reset_token_created_at = models.DateTimeField(blank=True, null=True)

    # --- 2. Add the relationship to the Company model ---
    # This links a user to their company. `null=True` allows users to exist
    # before they complete the company onboarding step.
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='users')
    # ----------------------------------------------------

    # Role field for team permissions
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_ADMIN,
        help_text="User's role within the company"
    )

    # Track last activity for team management
    last_active = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def is_password_reset_code_expired(self):
        """Checks if the password reset code is older than 15 minutes."""
        if not self.password_reset_code_created_at:
            return True
        return timezone.now() > self.password_reset_code_created_at + timedelta(minutes=15)

    def get_full_name(self):
        """Returns the full name of the user."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email

    def update_last_active(self):
        """Updates the last_active timestamp to now."""
        self.last_active = timezone.now()
        self.save(update_fields=['last_active'])


class Invitation(models.Model):
    """
    Model to handle secure team member invitations.
    """
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_EXPIRED = 'expired'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(help_text="Email address of the invited user")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invitations')
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_invitations')
    role = models.CharField(
        max_length=20,
        choices=User.ROLE_CHOICES,
        default=User.ROLE_MEMBER,
        help_text="Role to assign to the invited user"
    )
    token = models.CharField(max_length=100, unique=True, help_text="Unique invitation token")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Expiration time for the invitation")

    class Meta:
        ordering = ['-created_at']
        unique_together = [['email', 'company', 'status']]

    def __str__(self):
        return f"Invitation for {self.email} to {self.company.name}"

    def save(self, *args, **kwargs):
        """Generate token and set expiration if not already set."""
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def is_expired(self):
        """Check if the invitation has expired."""
        return timezone.now() > self.expires_at or self.status == self.STATUS_EXPIRED

    def is_valid(self):
        """Check if the invitation is still valid."""
        return self.status == self.STATUS_PENDING and not self.is_expired()