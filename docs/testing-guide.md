# ProGestock Testing Guide

This guide explains how to write and run tests for the ProGestock backend.

## Why Test?

- **Catch bugs before users do** - Tests find issues automatically
- **Confidence in changes** - Know your changes don't break existing features
- **Faster development** - Less time manually clicking through the app
- **Documentation** - Tests show how code should work

## What's Been Set Up

```
ProGestock/
├── tests/                      # All tests go here
│   ├── unit/                   # Fast, isolated tests
│   ├── integration/            # Tests with database/API
│   └── conftest.py            # Shared test fixtures
├── pytest.ini                  # Pytest configuration
└── requirements-dev.txt        # Testing dependencies
```

## Installation

Install testing dependencies:

```bash
cd C:\Users\Dell\Documents\ProGestock
pip install -r requirements-dev.txt
```

This installs:
- `pytest` - Test runner
- `pytest-django` - Django integration for pytest
- `pytest-cov` - Code coverage reports
- `factory-boy` - Test data generation

## Running Tests

### Run all tests
```bash
pytest
```

### Run with verbose output
```bash
pytest -v
```

### Run specific test file
```bash
pytest tests/unit/test_user_model.py
```

### Run specific test
```bash
pytest tests/unit/test_user_model.py::TestUserModel::test_create_user_with_email
```

### Run by markers
```bash
# Run only unit tests (fast)
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only smoke tests (critical paths)
pytest -m smoke

# Run everything except slow tests
pytest -m "not slow"
```

### Run with coverage report
```bash
pytest --cov=. --cov-report=html
# Then open htmlcov/index.html in browser
```

## Test Types

### Unit Tests
**Location:** `tests/unit/`
**Purpose:** Test individual functions/methods in isolation
**Speed:** Very fast (milliseconds)
**Example:** Testing User model creation

```python
@pytest.mark.unit
def test_create_user_with_email(self):
    user = User.objects.create_user(email='test@example.com', password='pass123')
    assert user.email == 'test@example.com'
```

### Integration Tests
**Location:** `tests/integration/`
**Purpose:** Test multiple components working together
**Speed:** Slower (uses database)
**Example:** Testing Product API endpoints

```python
@pytest.mark.integration
def test_create_product(self, authenticated_client, product_data):
    response = authenticated_client.post('/api/inventory/products/', product_data)
    assert response.status_code == 201
```

### Smoke Tests
**Marker:** `@pytest.mark.smoke`
**Purpose:** Test critical user journeys
**When to run:** Before every deployment
**Example:** Complete invoice creation flow

## Writing Your First Test

### 1. Choose the right location
- Simple function/model test? → `tests/unit/`
- API endpoint test? → `tests/integration/`

### 2. Create a test file
Name it `test_<feature>.py`, for example:
- `test_invoice_model.py`
- `test_quote_api.py`
- `test_stock_adjustment.py`

### 3. Write a test class

```python
import pytest
from inventory.models import Product

@pytest.mark.django_db  # Required for database access
@pytest.mark.unit       # Mark test type
class TestProduct:
    """Test Product model."""

    def test_product_creation(self):
        """Test creating a product."""
        product = Product.objects.create(
            name='Test Widget',
            sku='TEST-001',
            price='50.00'
        )

        assert product.name == 'Test Widget'
        assert product.sku == 'TEST-001'
        assert str(product.price) == '50.00'
```

### 4. Run your test

```bash
pytest tests/unit/test_product_model.py -v
```

## Using Fixtures

Fixtures provide reusable test data. They're defined in `tests/conftest.py`.

### Available Fixtures

| Fixture | Description | Usage |
|---------|-------------|-------|
| `api_client` | DRF API client | For API requests |
| `user` | Basic authenticated user | For tests needing a user |
| `authenticated_client` | API client + logged in user | For authenticated API tests |
| `admin_user` | Superuser | For admin-only tests |

### Example: Using Fixtures

```python
@pytest.mark.django_db
def test_list_products(authenticated_client):
    """Test that authenticated user can list products."""
    response = authenticated_client.get('/api/inventory/products/')
    assert response.status_code == 200
```

### Creating Your Own Fixtures

Add to `tests/conftest.py`:

```python
@pytest.fixture
def sample_product(db, user):
    """Creates a sample product for testing."""
    from inventory.models import Product
    return Product.objects.create(
        name='Sample Product',
        sku='SAMPLE-001',
        price='100.00'
    )
```

Then use it:

```python
def test_product_update(authenticated_client, sample_product):
    response = authenticated_client.patch(
        f'/api/inventory/products/{sample_product.id}/',
        {'price': '150.00'}
    )
    assert response.status_code == 200
```

## Common Patterns

### Testing API Endpoints

```python
@pytest.mark.django_db
@pytest.mark.integration
def test_create_invoice(authenticated_client, sample_product, sample_client):
    invoice_data = {
        'client': sample_client.id,
        'items': [
            {
                'product': sample_product.id,
                'quantity': 5,
                'unit_price': '50.00'
            }
        ]
    }

    response = authenticated_client.post('/api/sales/invoices/', invoice_data)

    assert response.status_code == 201
    assert response.data['total'] == '250.00'
```

### Testing Permissions

```python
def test_viewer_cannot_delete_product(api_client, viewer_user, sample_product):
    """Test that viewer role cannot delete products."""
    api_client.force_authenticate(user=viewer_user)

    response = api_client.delete(f'/api/inventory/products/{sample_product.id}/')

    assert response.status_code == 403  # Forbidden
```

### Testing Error Cases

```python
def test_create_product_without_name_fails(authenticated_client):
    """Test that creating product without name returns validation error."""
    invalid_data = {
        'sku': 'TEST-001',
        'price': '50.00'
        # name is missing
    }

    response = authenticated_client.post('/api/inventory/products/', invalid_data)

    assert response.status_code == 400
    assert 'name' in response.data  # Error message for name field
```

## Test Markers Reference

Add markers to categorize tests:

```python
@pytest.mark.unit           # Fast, isolated tests
@pytest.mark.integration    # Tests with database/external systems
@pytest.mark.smoke          # Critical path tests
@pytest.mark.slow           # Tests that take >5 seconds
```

## Before Railway Migration: Critical Tests

Run these tests before deploying to Railway:

```bash
# 1. Run smoke tests (critical paths)
pytest -m smoke -v

# 2. Run all tests
pytest

# 3. Check test coverage
pytest --cov=. --cov-report=term-missing

# All tests passing? ✅ Safe to deploy!
```

## Debugging Failed Tests

### View full output
```bash
pytest -vv
```

### Stop at first failure
```bash
pytest -x
```

### Enter debugger on failure
```bash
pytest --pdb
```

### Run only failed tests from last run
```bash
pytest --lf
```

### See print statements
```bash
pytest -s
```

## Next Steps

### Immediate (Before Railway Migration)
- [ ] Install test dependencies: `pip install -r requirements-dev.txt`
- [ ] Run existing tests: `pytest`
- [ ] Fix any failures
- [ ] Run smoke tests: `pytest -m smoke`

### Short Term (This Week)
- [ ] Write 5 more tests for critical features:
  - [ ] Invoice creation
  - [ ] Quote to invoice conversion
  - [ ] Stock adjustment
  - [ ] User permissions
  - [ ] Report generation

### Long Term (When You Have Time)
- [ ] Add CI/CD with GitHub Actions (run tests automatically)
- [ ] Set coverage goal (aim for 80%+)
- [ ] Add test data factories with factory-boy
- [ ] Set up test artifacts storage

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- [DRF Testing](https://www.django-rest-framework.org/api-guide/testing/)

## Questions?

Common issues and solutions:

**Q: Tests fail with "no such table" error**
A: Run `python manage.py migrate` to create test database tables

**Q: Tests are slow**
A: Use `pytest -m unit` to run only fast unit tests during development

**Q: Import errors in tests**
A: Make sure you're running pytest from the project root directory

**Q: How many tests do I need?**
A: Start with smoke tests for critical features, then expand. Aim for 80% coverage eventually.

---

**Remember:** Writing tests takes time upfront but saves MUCH more time debugging production issues later. Start small and build up gradually.
