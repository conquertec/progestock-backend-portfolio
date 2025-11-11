"""
Pytest configuration and shared fixtures.
This file is automatically loaded by pytest.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    """Returns a DRF API client for testing API endpoints."""
    return APIClient()


@pytest.fixture
def user(db):
    """Creates and returns a basic test user."""
    user = User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )
    # Set user as active so they can log in
    user.is_active = True
    user.save()
    return user


@pytest.fixture
def authenticated_client(api_client, user):
    """Returns an API client authenticated with a test user."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_user(db):
    """Creates and returns an admin user."""
    return User.objects.create_superuser(
        email='admin@example.com',
        password='adminpass123',
        first_name='Admin',
        last_name='User'
    )


# Add more shared fixtures here as needed
# Example:
# @pytest.fixture
# def sample_product(db, user):
#     """Creates and returns a sample product."""
#     from inventory.models import Product
#     return Product.objects.create(
#         name="Test Product",
#         sku="TEST-001",
#         price=100.00,
#         created_by=user
#     )
