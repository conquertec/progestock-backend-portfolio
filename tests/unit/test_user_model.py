"""
Unit tests for User model.
These are fast tests that don't require complex setup.
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestUserModel:
    """Test User model creation and methods."""

    def test_create_user_with_email(self):
        """Test creating a user with email and password."""
        email = 'testuser@example.com'
        password = 'testpass123'

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name='Test',
            last_name='User'
        )

        assert user.email == email
        assert user.first_name == 'Test'
        assert user.last_name == 'User'
        assert user.check_password(password)
        assert not user.is_superuser
        assert not user.is_staff

    def test_create_superuser(self):
        """Test creating a superuser."""
        email = 'admin@example.com'
        password = 'adminpass123'

        admin = User.objects.create_superuser(
            email=email,
            password=password
        )

        assert admin.email == email
        assert admin.is_superuser
        assert admin.is_staff
        assert admin.is_active
        assert admin.check_password(password)

    def test_create_user_without_email_raises_error(self):
        """Test that creating a user without email raises ValueError."""
        with pytest.raises(ValueError, match='The Email field must be set'):
            User.objects.create_user(email='', password='testpass123')

    def test_user_email_is_normalized(self):
        """Test that email is normalized (lowercase domain)."""
        email = 'test@EXAMPLE.COM'
        user = User.objects.create_user(email=email, password='testpass123')

        assert user.email == 'test@example.com'

    def test_user_string_representation(self):
        """Test the __str__ method of User."""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )

        # Adjust this assertion based on your actual __str__ implementation
        assert str(user) == 'test@example.com' or 'John' in str(user)
