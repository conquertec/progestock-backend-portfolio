"""
Integration tests for Product API endpoints.
These tests interact with the database and API views.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from inventory.models import Product, Category, Location
from company.models import Company


@pytest.mark.django_db
@pytest.mark.integration
class TestProductAPI:
    """Test Product CRUD operations via API."""

    @pytest.fixture
    def company(self, user):
        """Create a test company."""
        company = Company.objects.create(
            name='Test Company',
            industry='Technology',
            currency='USD'
        )
        # Link user to company
        user.company = company
        user.save()
        return company

    @pytest.fixture
    def category(self, company):
        """Create a test category."""
        return Category.objects.create(
            name='Electronics',
            company=company
        )

    @pytest.fixture
    def product_data(self, company, category):
        """Return valid product data for API requests."""
        return {
            'name': 'Test Product',
            'sku': 'TEST-001',
            'description_en': 'A test product',
            'price': '99.99',
            'purchase_price': '50.00',
            'reorder_threshold': 10,
            'category': category.id,
            'company': company.id
        }

    def test_list_products(self, authenticated_client, company, category):
        """Test listing products via API."""
        # Create a test product
        Product.objects.create(
            name='Product 1',
            sku='PROD-001',
            price='100.00',
            company=company,
            category=category
        )

        url = reverse('product-list')  # Adjust based on your URL name
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Response might be paginated, adjust accordingly
        assert len(response.data) > 0 or 'results' in response.data

    def test_create_product(self, authenticated_client, product_data):
        """Test creating a product via API."""
        url = reverse('product-list')
        response = authenticated_client.post(url, product_data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Test Product'
        assert response.data['sku'] == 'TEST-001'

        # Verify product was created in database
        assert Product.objects.filter(sku='TEST-001').exists()

    def test_retrieve_product(self, authenticated_client, company, category):
        """Test retrieving a single product via API."""
        product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price='100.00',
            company=company,
            category=category
        )

        url = reverse('product-detail', kwargs={'pk': product.pk})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Test Product'
        assert response.data['sku'] == 'TEST-001'

    def test_update_product(self, authenticated_client, company, category):
        """Test updating a product via API."""
        product = Product.objects.create(
            name='Old Name',
            sku='TEST-001',
            price='100.00',
            company=company,
            category=category
        )

        url = reverse('product-detail', kwargs={'pk': product.pk})
        updated_data = {
            'name': 'New Name',
            'sku': 'TEST-001',
            'price': '150.00',
            'purchase_price': '75.00',
            'company': company.id,
            'category': category.id
        }

        response = authenticated_client.put(url, updated_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'New Name'

        # Verify database was updated
        product.refresh_from_db()
        assert product.name == 'New Name'

    def test_delete_product(self, authenticated_client, company, category):
        """Test deleting a product via API."""
        product = Product.objects.create(
            name='Test Product',
            sku='TEST-001',
            price='100.00',
            company=company,
            category=category
        )

        url = reverse('product-detail', kwargs={'pk': product.pk})
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify product was deleted
        assert not Product.objects.filter(pk=product.pk).exists()

    def test_unauthenticated_access_denied(self, api_client):
        """Test that unauthenticated users cannot access product API."""
        url = reverse('product-list')
        response = api_client.get(url)

        # Should return 401 Unauthorized or 403 Forbidden
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]
