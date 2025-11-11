# ProGestock Backend - Code Portfolio Sample

> **Note:** This is a code sample extracted from a private full-stack inventory management system. It showcases Django REST Framework architecture, authentication patterns, and multi-tenancy implementation.

## Overview

ProGestock is a Django REST Framework-based inventory management system designed for multi-tenant SaaS architecture. This backend API demonstrates production-ready patterns for authentication, data isolation, and scalable system design.

## Key Features & Technical Highlights

### 🔐 Advanced Authentication System
- **JWT Cookie-Based Auth**: Secure HTTP-only cookies with refresh token rotation
- **Google OAuth Integration**: Supports both Google Button and One Tap flows
- **Email Verification**: 6-digit code verification with async email sending via Celery
- **Password Reset Flow**: Secure 3-step password reset with token verification
- **Custom User Model**: Email-based authentication without username field

### 🏢 Multi-Tenancy Architecture
- **Row-Level Tenant Isolation**: Each company's data is completely isolated at the database level
- **Automatic Tenant Filtering**: All queries automatically filter by authenticated user's company
- **Scalable Design**: Ready for thousands of tenants without performance degradation

### 📊 Core Business Features
- **Inventory Management**: Products, stock levels, locations, and categories
- **Client Management**: Customer database with company-level isolation
- **Audit Logging**: Comprehensive action tracking for compliance
- **AI Profile Generation**: Google Gemini integration for business profile creation

### 🛠️ Technical Architecture

#### Stack
- **Framework**: Django 5.2.6 + Django REST Framework 3.16.1
- **Authentication**: dj-rest-auth + django-allauth (JWT via HTTP-only cookies)
- **Database**: PostgreSQL (production) / SQLite (development)
- **Task Queue**: Celery 5.5.3 + Redis for async operations
- **Storage**: Google Cloud Storage support with local fallback
- **AI**: Google Generative AI (Gemini) integration

#### Design Patterns Demonstrated
- Repository pattern with Django ORM
- Service layer for business logic
- Custom authentication adapters
- Async task processing with Celery
- RESTful API design
- Rate limiting and throttling
- CORS configuration for SPA integration
- Environment-based configuration

## Project Structure

```
progestock_backend/
├── user/                    # Authentication & user management
│   ├── models.py           # Custom user model
│   ├── views.py            # Auth endpoints (login, register, OAuth)
│   ├── serializers.py      # User data serialization
│   └── tasks.py            # Async email tasks
├── company/                # Company (tenant) management
│   ├── models.py           # Company model with AI profile
│   ├── views.py            # Onboarding & profile generation
│   └── serializers.py      # Company data serialization
├── inventory/              # Inventory management
│   ├── models.py           # Product, Stock, Location, Category
│   └── views.py            # Inventory CRUD operations
├── auditing/               # Audit logging system
│   ├── models.py           # LogEntry model
│   └── signals.py          # Auto-logging signals
├── progestock_backend/     # Project configuration
│   ├── settings.py         # Django settings
│   ├── celery.py           # Celery configuration
│   └── urls.py             # URL routing
└── manage.py
```

## Key Code Highlights

### Multi-Tenant Query Filtering
All views automatically filter data by the authenticated user's company:

```python
class ProductListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Automatic tenant isolation
        return Product.objects.filter(company=self.request.user.company)
```

### JWT Cookie Authentication
Secure token storage without localStorage vulnerabilities:

```python
REST_AUTH = {
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'progestock-auth',
    'JWT_AUTH_REFRESH_COOKIE': 'progestock-refresh',
    'JWT_AUTH_HTTPONLY': True,
    'JWT_AUTH_SAMESITE': 'None',
    'JWT_AUTH_SECURE': IS_PRODUCTION,
}
```

### Async Email Processing
Non-blocking email sending with Celery:

```python
@shared_task
def send_verification_email_task(email, subject, message):
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
```

### Google OAuth Integration
Unified handler for multiple Google authentication methods:

```python
class GoogleLoginView(APIView):
    def post(self, request):
        auth_type = request.data.get('auth_type')  # 'button' or 'one_tap'
        token = request.data.get('access_token') or request.data.get('id_token')
        # Verify token with Google APIs...
```

## API Endpoints

### Authentication
- `POST /api/auth/login/` - Email/password login with "Remember Me"
- `POST /api/auth/registration/` - User registration
- `POST /api/auth/logout/` - Logout (clears JWT cookies)
- `POST /api/auth/google/` - Google OAuth (Button + One Tap)
- `POST /api/auth/password/reset/` - Request password reset code

### User Management
- `POST /api/user/verify-code/` - Verify email with 6-digit code
- `POST /api/user/resend-verification-code/` - Resend verification code
- `POST /api/user/password-reset-verify-code/` - Verify password reset code
- `POST /api/user/password-reset-confirm/` - Set new password

### Company (Tenant)
- `POST /api/company/onboarding/` - Create company (tenant)
- `PATCH /api/company/complete-onboarding/` - Complete onboarding wizard
- `POST /api/company/generate-profile/` - AI-generate business profile

### Inventory
- `GET /api/inventory/products/` - List products (filtered by company)
- `POST /api/inventory/products/create/` - Create product
- `GET /api/inventory/locations/` - List locations
- `GET /api/inventory/categories/` - List categories
- `GET /api/inventory/dashboard-stats/` - Dashboard statistics

## Setup & Installation

### Prerequisites
- Python 3.10+
- Redis (for Celery tasks)
- PostgreSQL (production) or SQLite (development)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/progestock-portfolio.git
   cd progestock-portfolio
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your SECRET_KEY and other configuration
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

8. **Run Celery worker** (in separate terminal)
   ```bash
   celery -A progestock_backend worker --loglevel=info
   ```

### Testing

```bash
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test user
python manage.py test inventory
```

## Configuration

### Environment Variables
See `.env.example` for all available configuration options. Key variables:

- `SECRET_KEY`: Django secret key (required)
- `DEBUG`: Debug mode (default: False)
- `DATABASE_URL`: PostgreSQL connection string (optional, defaults to SQLite)
- `GOOGLE_OAUTH_CLIENT_ID`: Google OAuth client ID (optional)
- `GEMINI_API_KEY`: Google Gemini API key for AI features (optional)
- `CELERY_BROKER`: Redis URL for Celery (default: redis://localhost:6379/0)

### CORS Configuration
Configure allowed origins in `settings.py`:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Local frontend
    "http://localhost:3000",
    # Add your production frontend URLs
]
```

## Security Features

- ✅ JWT tokens in HTTP-only cookies (no XSS vulnerability)
- ✅ CSRF protection with SameSite cookies
- ✅ Rate limiting on all endpoints
- ✅ Password validation with Django validators
- ✅ Secure password reset flow with tokens
- ✅ Email verification required for account activation
- ✅ Row-level multi-tenancy (complete data isolation)

## Code Quality & Best Practices

- **Type Safety**: Serializers validate all incoming data
- **Error Handling**: Custom exception handler for consistent API responses
- **Code Organization**: Separation of concerns (models, views, serializers, services)
- **Documentation**: Comprehensive inline comments
- **Environment Management**: django-environ for configuration
- **Database Optimization**: Efficient querysets with select_related/prefetch_related
- **Async Processing**: Celery for long-running tasks

## Learning Resources

This project demonstrates solutions to common backend challenges:

1. **Multi-Tenancy**: How to implement secure tenant isolation
2. **JWT Auth**: Cookie-based JWT vs. localStorage approach
3. **OAuth Integration**: Google OAuth with multiple flow types
4. **Email Verification**: Async email sending with verification codes
5. **API Design**: RESTful patterns and consistent response formats
6. **Task Queues**: Celery integration for background jobs
7. **Cloud Storage**: GCS integration with local fallback

## Contact

This is a code sample from a larger private project. For questions or to discuss the architecture:

- **GitHub**: github.com/conquertec
- **LinkedIn**: linkedin.com/in/losogelet
- **Email**: ogeletlevy@gmail.com

---

**Note**: This is a demonstration project extracted from a production codebase. Some features have been simplified for portfolio purposes. The full private version includes additional modules for sales, purchasing, notifications, and advanced reporting.
