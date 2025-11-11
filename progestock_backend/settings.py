from pathlib import Path
import environ
import os
from datetime import timedelta # Import timedelta for token lifetimes


env = environ.Env(
    DEBUG=(bool, False)
)

BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file only if it exists (for local development)
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')

IS_PRODUCTION = not DEBUG 

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    # Add your production domains here
    # 'your-backend-domain.com',
]

# Add Railway domain if RAILWAY_PUBLIC_DOMAIN is set
if 'RAILWAY_PUBLIC_DOMAIN' in os.environ:
    ALLOWED_HOSTS.append(os.environ['RAILWAY_PUBLIC_DOMAIN'])

# Add Railway static URL if RAILWAY_STATIC_URL is set
if 'RAILWAY_STATIC_URL' in os.environ:
    railway_domain = os.environ['RAILWAY_STATIC_URL'].replace('https://', '').replace('http://', '')
    ALLOWED_HOSTS.append(railway_domain) 

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'inventory',
    'user.apps.UserConfig',  # Explicitly use UserConfig to enable ready() hook
    'auditing',
    'company',
    'dashboard',
    'sales',
    'purchasing',
    'notifications',
    'rest_framework',
    'corsheaders',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'rest_framework_simplejwt.token_blacklist',
    'storages',
]

AUTH_USER_MODEL = 'user.User'
SITE_ID = 1

MIDDLEWARE = [
    # CRITICAL: CorsMiddleware must be at the very top
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Language detection middleware (must be after AuthenticationMiddleware)
    'progestock_backend.language_middleware.LanguageMiddleware',
]

# CORS Configuration
# Custom domain for production (iOS cookie support)
CUSTOM_DOMAIN = 'yourdomain.com'  # Replace with your actual domain

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    # Add your production frontend URLs here
    # "https://yourdomain.com",
    # "https://www.yourdomain.com",
]

# Optional: Allow regex patterns for dynamic origins
# CORS_ALLOWED_ORIGIN_REGEXES = [
#     r"^https://.*\.yourdomain\.com$",
# ]

# REMOVE THIS LINE - it conflicts with CORS_ALLOWED_ORIGINS
# CORS_ALLOW_ALL_ORIGINS = True  # <-- DELETE THIS

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours

# CRITICAL: This must be True for cookie-based auth
CORS_ALLOW_CREDENTIALS = True

# Cookie settings - Using custom domain for iOS compatibility
SESSION_COOKIE_NAME = 'progestock-sessionid'
SESSION_COOKIE_SAMESITE = 'None'  # Must be None for iOS Safari cross-subdomain cookies
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_DOMAIN = f'.{CUSTOM_DOMAIN}' if IS_PRODUCTION else None  # Leading dot for subdomain sharing
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds

CSRF_COOKIE_NAME = 'progestock-csrftoken'
CSRF_COOKIE_SAMESITE = 'None'  # Must be None for iOS Safari cross-subdomain cookies
CSRF_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_HTTPONLY = False  # Must be False so JavaScript can read it if needed
CSRF_COOKIE_DOMAIN = f'.{CUSTOM_DOMAIN}' if IS_PRODUCTION else None  # Leading dot for subdomain sharing

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Add your production URLs here
    # "https://yourdomain.com",
    # "https://www.yourdomain.com",
    # "https://api.yourdomain.com",
]

# Add Railway domains dynamically
if 'RAILWAY_PUBLIC_DOMAIN' in os.environ:
    railway_url = f"https://{os.environ['RAILWAY_PUBLIC_DOMAIN']}"
    if railway_url not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(railway_url)

# Add Vercel preview URLs dynamically if needed
if IS_PRODUCTION:
    import re
    # This will trust all *.vercel.app subdomains for CSRF
    # Note: CSRF_TRUSTED_ORIGINS doesn't support regex, so add common ones manually
    pass

ROOT_URLCONF = 'progestock_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'progestock_backend.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'),
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Internationalization - Supported languages
LANGUAGES = [
    ('en', 'English'),
    ('fr', 'Français'),
]

# Path to locale files
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Whitenoise configuration for serving static files in production
USE_GCS = env('USE_GCS', default=False, cast=bool)

# Initialize GCS_ENABLED flag
GCS_ENABLED = False

if USE_GCS:
    import json
    import base64
    from google.oauth2 import service_account
    import logging

    logger = logging.getLogger(__name__)

    # GCS Settings
    try:
        GS_BUCKET_NAME = env('GS_BUCKET_NAME')
        GS_PROJECT_ID = env('GS_PROJECT_ID')

        # Parse GCS credentials from JSON string, base64, or file
        gcs_credentials_json = env('GS_CREDENTIALS', default=None)
        if gcs_credentials_json:
            try:
                # First, try to parse as base64-encoded JSON
                try:
                    decoded = base64.b64decode(gcs_credentials_json).decode('utf-8')
                    credentials_dict = json.loads(decoded)
                    GS_CREDENTIALS = service_account.Credentials.from_service_account_info(credentials_dict)
                    GCS_ENABLED = True
                    logger.info("✅ GCS credentials loaded successfully from base64")
                except Exception:
                    # If base64 fails, try to parse as JSON string directly
                    credentials_dict = json.loads(gcs_credentials_json)
                    GS_CREDENTIALS = service_account.Credentials.from_service_account_info(credentials_dict)
                    GCS_ENABLED = True
                    logger.info("✅ GCS credentials loaded successfully from JSON")
            except (json.JSONDecodeError, ValueError) as e:
                # If not JSON, assume it's a file path
                try:
                    GS_CREDENTIALS = service_account.Credentials.from_service_account_file(gcs_credentials_json)
                    GCS_ENABLED = True
                    logger.info("✅ GCS credentials loaded successfully from file")
                except Exception as file_err:
                    logger.warning(f"Failed to load GCS credentials: {file_err}. Falling back to local storage.")
                    GS_CREDENTIALS = None
        else:
            logger.warning("GS_CREDENTIALS not set. Falling back to local storage.")
            GS_CREDENTIALS = None
    except Exception as e:
        logger.error(f"Error configuring GCS: {e}. Falling back to local storage.")
        GCS_ENABLED = False

# Only use GCS if credentials are properly configured
if GCS_ENABLED and GS_CREDENTIALS:
    # Use signed URLs instead of public URLs for better security
    GS_QUERYSTRING_AUTH = True  # Use signed URLs
    GS_EXPIRATION = timedelta(days=7)  # Set expiration for signed URLs to 7 days

    # Set ACL to None to avoid errors if public access prevention is enabled
    # Files will inherit bucket permissions
    GS_DEFAULT_ACL = None  # Let files inherit bucket-level permissions
    GS_FILE_OVERWRITE = False  # Don't overwrite files with same name
    GS_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB max memory for file upload

    # Media files will be uploaded to GCS
    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/'

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    # Local development settings or fallback when GCS is not available
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }


 

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'dj_rest_auth.jwt_auth.JWTCookieAuthentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/minute',
        'user': '1000/minute',
    },
    'EXCEPTION_HANDLER': 'progestock_backend.exceptions.custom_exception_handler',
}

# Django-allauth 65.x configuration
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*']
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_ADAPTER = 'user.adapters.CustomEmailAdapter'

# Force allauth to send confirmation emails
ACCOUNT_EMAIL_CONFIRMATION_HMAC = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False

# Email Backend Configuration
if DEBUG:
    # Development: Print emails to console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # Production: Use custom SendGrid backend
    EMAIL_BACKEND = 'progestock_backend.sendgrid_backend.SendGridBackend'

# SendGrid Configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')

# Frontend URL for email links
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173')

DEFAULT_FROM_EMAIL = 'YourApp <no-reply@yourdomain.com>'
SERVER_EMAIL = DEFAULT_FROM_EMAIL  # For error emails

# REST_AUTH Configuration
REST_AUTH = {
    'REGISTER_SERIALIZER': 'user.serializers.CustomRegisterSerializer',
    'USER_DETAILS_SERIALIZER': 'user.serializers.UserDetailsSerializer',
    'TOKEN_MODEL': None,
    'USE_JWT': True,
    'JWT_AUTH_COOKIE': 'progestock-auth',
    'JWT_AUTH_REFRESH_COOKIE': 'progestock-refresh',
    'JWT_AUTH_HTTPONLY': True,
    'JWT_AUTH_SAMESITE': 'None',  # Must be None for iOS Safari cross-subdomain cookies
    'JWT_AUTH_SECURE': IS_PRODUCTION,
    'JWT_AUTH_COOKIE_DOMAIN': f'.{CUSTOM_DOMAIN}' if IS_PRODUCTION else None,  # Leading dot for subdomain sharing
    'JWT_AUTH_COOKIE_USE_CSRF': False,
    'JWT_AUTH_COOKIE_ENFORCE_CSRF_ON_UNAUTHENTICATED': False,

    # Default cookie lifetime - will be overridden by CustomLoginView based on remember_me flag
    # This is just a fallback
    'JWT_AUTH_COOKIE_MAX_AGE': None,  # None = session cookie by default

    # Note: max_age is handled dynamically in CustomLoginView based on remember_me flag
    # - remember_me=True: 30 days (persistent cookies)
    # - remember_me=False: None (session cookies, deleted when browser closes)
}

# Google OAuth Configuration
# Make Google OAuth optional - set empty values if not configured
GOOGLE_OAUTH_CLIENT_ID = env('GOOGLE_OAUTH_CLIENT_ID', default='')
GOOGLE_OAUTH_CLIENT_SECRET = env('GOOGLE_OAUTH_CLIENT_SECRET', default='')

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': GOOGLE_OAUTH_CLIENT_ID,
            'secret': GOOGLE_OAUTH_CLIENT_SECRET,
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'VERIFIED_EMAIL': True,
    }
}

SOCIALACCOUNT_ADAPTER = 'user.adapters.CustomSocialAccountAdapter'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    # Cookie settings (these mirror REST_AUTH settings)
    'AUTH_COOKIE': 'progestock-auth',
    'AUTH_COOKIE_REFRESH': 'progestock-refresh',
    'AUTH_COOKIE_SECURE': IS_PRODUCTION,
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_PATH': '/',
    'AUTH_COOKIE_SAMESITE': 'None',  # Must be None for iOS Safari cross-subdomain cookies
    'AUTH_COOKIE_DOMAIN': f'.{CUSTOM_DOMAIN}' if IS_PRODUCTION else None,  # Leading dot for subdomain sharing
}

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_BROKER", "redis://localhost:6379/0")

# Logging for debugging CORS in production
if IS_PRODUCTION:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'loggers': {
            'corsheaders': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
    }