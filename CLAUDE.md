# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ProGestock** is a Django REST Framework-based inventory management system with multi-tenant support. The backend provides REST APIs for user authentication (including Google OAuth), company onboarding, inventory management, client management, and audit logging. The frontend is expected to run on `http://localhost:5173` (likely React/Vite).

## Tech Stack

- **Backend**: Django 5.2.6 + Django REST Framework 3.16.1
- **Authentication**: dj-rest-auth + django-allauth (JWT via HTTP-only cookies)
- **Database**: SQLite (development), PostgreSQL support via psycopg (production-ready)
- **Task Queue**: Celery 5.5.3 + Redis (for async email sending)
- **AI Integration**: Google Generative AI (Gemini) for business profile generation

## Common Commands

### Development Server
```bash
# Activate virtual environment (Windows)
venv\Scripts\activate

# Run Django development server
python manage.py runserver

# Run Celery worker (for async tasks like email)
celery -A progestock_backend worker --loglevel=info
```

### Database Operations
```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser
```

### Testing
```bash
# Run all tests
python manage.py test

# Run tests for a specific app
python manage.py test user
python manage.py test inventory
```

## Architecture

### Multi-Tenancy Model

The system implements **row-level multi-tenancy** where each company's data is isolated:

1. **Company Model** (`company/models.py`): Central tenant model containing company info, settings, and AI-generated business profiles
2. **User-Company Relationship**: Each `User` has a `ForeignKey` to `Company` (nullable during registration)
3. **Data Isolation**: All major models (Product, Stock, Location, Category, Client) have a `company` foreign key

### App Structure

- **user/**: Custom user model (email-based auth), registration, email verification, password reset, Google OAuth
- **company/**: Company onboarding, settings management, AI profile generation
- **inventory/**: Products, stock levels, locations, categories, clients
- **auditing/**: System-wide audit logging (`LogEntry` model tracks all significant actions)

### Authentication Flow

The project uses **JWT tokens stored in HTTP-only cookies** (secure, no localStorage):

1. **Registration**: User registers → receives 6-digit verification code via Celery task → verifies email → auto-login with JWT cookies set
2. **Login**: Standard email/password → JWT cookies set with optional "Remember Me" (extends refresh token expiry)
3. **Google OAuth**: Supports both Google Button (`access_token`) and Google One Tap (`id_token`) → verifies with Google APIs → creates/gets user → sets JWT cookies
4. **Password Reset**: 3-step flow (request code → verify code → set new password with secure token)

**Key Files:**
- `user/views.py`: All auth views (login, register, Google OAuth, password reset)
- `user/adapters.py`: Custom adapters for django-allauth
- `progestock_backend/settings.py`: JWT configuration in `REST_AUTH` and `SIMPLE_JWT` settings

### API Design Patterns

**All protected endpoints require authentication via JWT cookies.**

Common patterns:
- Views use `permission_classes = [IsAuthenticated]`
- Rate limiting via `throttle_classes = [UserRateThrottle]`
- Queryset filtering by `request.user.company` for multi-tenancy
- `perform_create()` auto-assigns `company=request.user.company`

### Celery & Async Tasks

- **Configuration**: `progestock_backend/celery.py` + Redis broker
- **Tasks**: `user/tasks.py` contains `send_verification_email_task` (more tasks can be added here)
- **Usage**: Import task and call `.delay()` to run asynchronously

Example:
```python
from user.tasks import send_verification_email_task
send_verification_email_task.delay(user.email, subject, message)
```

### Environment Variables

Required in `.env` file:
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `GOOGLE_OAUTH_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_OAUTH_CLIENT_SECRET`: Google OAuth client secret
- `GEMINI_API_KEY`: Google Gemini AI API key (optional, falls back to mock)
- `CELERY_BROKER`: Redis URL (defaults to `redis://localhost:6379/0`)

## Important Design Decisions

### Custom User Model
- Email-based authentication (no username)
- `is_active=False` by default until email verification
- Custom `UserManager` handles user creation
- Defined in `user/models.py` as `AUTH_USER_MODEL = 'user.User'`

### JWT Cookie Authentication
- Cookies: `progestock-auth` (access token), `progestock-refresh` (refresh token)
- HttpOnly, SameSite=Lax for security
- Access token: 1 hour lifetime
- Refresh token: 7 days lifetime (rotated on use)

### Audit Logging
- `auditing/models.py` defines `LogEntry` with predefined `ACTION_TYPES`
- Manually created in views (e.g., `company/views.py:27` logs company creation)
- Signals in `auditing/signals.py` are commented out (manual logging preferred)

### AI Profile Generation
- `company/views.py:48-91` contains `GenerateProfileView`
- Uses Google Gemini API to generate company business profiles
- Falls back to mock profile if `GEMINI_API_KEY` not set

## URL Structure

```
/admin/                                  - Django admin
/api/auth/login/                         - Login (custom view with Remember Me)
/api/auth/logout/                        - Logout
/api/auth/registration/                  - Register
/api/auth/google/                        - Google OAuth (Button + One Tap)
/api/auth/password/reset/                - Request password reset code
/api/user/verify-code/                   - Verify email with 6-digit code
/api/user/resend-verification-code/      - Resend verification code
/api/user/password-reset-verify-code/    - Verify password reset code
/api/user/password-reset-confirm/        - Set new password with token
/api/company/onboarding/                 - Company onboarding (create company)
/api/company/complete-onboarding/        - Mark onboarding as complete
/api/company/generate-profile/           - AI-generate business profile
/api/inventory/locations/                - List/create locations
/api/inventory/categories/               - List/create categories
/api/inventory/products/create/          - Create product
/api/inventory/clients/create/           - Create client
/api/inventory/dashboard-stats/          - Dashboard statistics
```

## Model Relationships

```
Company (central tenant)
├── users (User.company FK)
├── locations (Location.company FK)
├── categories (Category.company FK)
├── products (Product.company FK)
├── clients (Client.company FK)
└── audit_log_entries (LogEntry.company FK)

Product
├── category (FK to Category)
└── stock_levels (Stock.product FK)

Stock (unique together: product + location)
├── product (FK to Product)
└── location (FK to Location)
```

## Frontend Integration Notes

- CORS configured for `http://localhost:5173`
- JWT cookies sent automatically with credentials
- Frontend should check `has_company` and `is_new_user` flags in auth responses to redirect appropriately:
  - New users without company → redirect to company onboarding
  - Users with company but `onboarding_complete=False` → redirect to onboarding wizard
  - Users with complete onboarding → redirect to dashboard

## When Adding New Features

1. **New Models**: Always add `company = ForeignKey(Company)` for multi-tenancy
2. **New Views**: Use `permission_classes = [IsAuthenticated]` and filter by `request.user.company`
3. **New Actions**: Add to `ACTION_TYPES` in `auditing/models.py` and create `LogEntry` in views
4. **New Async Tasks**: Add to `user/tasks.py` (or create `inventory/tasks.py` for inventory-related tasks)
5. **New URLs**: Register in appropriate app's `urls.py`, then include in `progestock_backend/urls.py`

## Database Migration Notes

- User model has a FK to Company, but Company is in a separate app
- Migration `user/migrations/0005_user_company.py` establishes this relationship
- When making model changes, always run `makemigrations` for ALL affected apps
