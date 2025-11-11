# ProGestock Tests

This directory contains all tests for the ProGestock backend API.

## Quick Start

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=term
```

## Directory Structure

```
tests/
├── README.md              # This file
├── conftest.py           # Shared fixtures (user, api_client, etc.)
├── unit/                 # Fast, isolated tests
│   └── test_user_model.py
└── integration/          # Database & API tests
    ├── test_product_api.py
    └── test_authentication_flow.py
```

## Test Types

### Unit Tests (`tests/unit/`)
- Test individual functions/methods
- Very fast (milliseconds)
- No external dependencies
- Example: Testing model creation, utility functions

**Run only unit tests:**
```bash
pytest -m unit
```

### Integration Tests (`tests/integration/`)
- Test multiple components together
- Use database and API
- Slower but more realistic
- Example: Testing complete API endpoints

**Run only integration tests:**
```bash
pytest -m integration
```

### Smoke Tests (marker `@pytest.mark.smoke`)
- Test critical user journeys
- Run before every deployment
- Example: Can user login? Can invoice be created?

**Run only smoke tests:**
```bash
pytest -m smoke
```

## Adding New Tests

### 1. Create test file
```bash
# For model tests
touch tests/unit/test_invoice_model.py

# For API tests
touch tests/integration/test_invoice_api.py
```

### 2. Write test
```python
import pytest
from inventory.models import Product

@pytest.mark.django_db
@pytest.mark.unit
class TestProduct:
    def test_product_creation(self):
        product = Product.objects.create(name="Widget", price="50.00")
        assert product.name == "Widget"
```

### 3. Run test
```bash
pytest tests/unit/test_invoice_model.py -v
```

## Available Fixtures

Defined in `conftest.py`:

| Fixture | Description |
|---------|-------------|
| `api_client` | DRF API test client |
| `user` | Basic authenticated user |
| `authenticated_client` | API client with logged-in user |
| `admin_user` | Superuser for admin tests |

**Usage example:**
```python
def test_list_products(authenticated_client):
    response = authenticated_client.get('/api/inventory/products/')
    assert response.status_code == 200
```

## Common Commands

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Stop at first failure
pytest -x

# Run specific file
pytest tests/unit/test_user_model.py

# Run specific test
pytest tests/unit/test_user_model.py::TestUserModel::test_create_user_with_email

# Run tests matching pattern
pytest -k "product"

# Coverage report
pytest --cov=. --cov-report=html

# Run only fast tests
pytest -m unit

# Run critical tests
pytest -m smoke
```

## Before Committing Code

Always run tests:
```bash
pytest -m "unit or smoke" --maxfail=1
```

## Before Deploying to Railway

Run full test suite:
```bash
pytest -v
pytest --cov=. --cov-report=term-missing
```

All green? Safe to deploy! ✅

## Documentation

- **Complete guide:** `../docs/testing-guide.md`
- **Quick commands:** `../TEST_COMMANDS.md`
- **Setup summary:** `../TESTING_SETUP_SUMMARY.md`

## Need Help?

1. Read `docs/testing-guide.md`
2. Look at example tests in this directory
3. Check [Pytest docs](https://docs.pytest.org/)
4. Check [DRF testing docs](https://www.django-rest-framework.org/api-guide/testing/)
