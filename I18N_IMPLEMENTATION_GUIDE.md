# Internationalization (i18n) Implementation Guide

## Overview

This guide explains how to use the new internationalized error handling system in ProGestock.

## What's Been Implemented

### 1. Custom Exception Handler
- Location: `progestock_backend/exceptions.py`
- Automatically formats all DRF exceptions into standardized responses
- Configured in `settings.py` under `REST_FRAMEWORK['EXCEPTION_HANDLER']`

### 2. Error Codes Module
- Location: `progestock_backend/error_codes.py`
- Contains all error codes and translatable messages
- Organized by category (Auth, User, Company, Inventory, Sales, etc.)

### 3. Error Utilities
- Location: `progestock_backend/error_utils.py`
- Helper functions for creating standardized error responses
- Simplifies error handling in views

### 4. Language Detection Middleware
- Location: `progestock_backend/language_middleware.py`
- Automatically detects language from:
  1. User's company language setting (priority)
  2. Accept-Language HTTP header (fallback)
  3. Default to English

### 5. Translation Files
- English: `locale/en/LC_MESSAGES/django.po` and `django.mo`
- French: `locale/fr/LC_MESSAGES/django.po` and `django.mo`
- Contains 50 translated error messages

### 6. Compilation Script
- Location: `compile_messages.py`
- Run after updating .po files: `python compile_messages.py`

## Standardized Error Response Format

All errors now follow this format:

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message in user's language",
    "field": "field_name",  // Optional: for validation errors
    "details": {}  // Optional: additional information
  }
}
```

## How to Use in Your Code

### In Serializers (Validation Errors)

```python
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

class MySerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                _("A user is already registered with this email address.")
            )
        return value
```

### In Views (Using Error Utilities)

```python
from django.utils.translation import gettext as _
from progestock_backend.error_utils import error_response, not_found_error_response
from progestock_backend.error_codes import UserErrors

class MyView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            # Option 1: Using error_response helper
            return error_response(
                message=UserErrors.USER_NOT_FOUND['message'],
                code=UserErrors.USER_NOT_FOUND['code'],
                status=404
            )

            # Option 2: Using specific helper
            return not_found_error_response('User')

        # ... rest of the logic
```

### In Views (Using Error Codes Module)

```python
from progestock_backend.error_codes import AuthErrors, InventoryErrors, create_error_response
from rest_framework.response import Response

# For simple errors
if not verification_code:
    error = create_error_response(AuthErrors.INVALID_VERIFICATION_CODE)
    return Response({
        'status': 'error',
        'error': error
    }, status=400)

# For errors with variable substitution
if category_in_use:
    count = Product.objects.filter(category=category).count()
    error = create_error_response(InventoryErrors.CATEGORY_IN_USE, count=count)
    return Response({
        'status': 'error',
        'error': error
    }, status=400)
```

### In Views (Raising Exceptions)

```python
from rest_framework.exceptions import PermissionDenied, NotFound
from django.utils.translation import gettext as _

# The custom exception handler will format these automatically
def delete_user(self, request, pk):
    user = self.get_object()

    if user == request.user:
        raise PermissionDenied(_("You cannot delete your own account."))

    user.delete()
    return Response(status=204)
```

## Migration Checklist

To update existing code to use internationalized errors:

### For Serializers:
1. Import: `from django.utils.translation import gettext_lazy as _`
2. Wrap all error messages with `_("message")`
3. Use error codes from `error_codes.py` when applicable

### For Views:
1. Import: `from django.utils.translation import gettext as _`
2. Import helpers: `from progestock_backend.error_utils import error_response`
3. Import error codes: `from progestock_backend.error_codes import AuthErrors, UserErrors, etc.`
4. Replace all `return Response({'error': '...'}, status=...)` with `error_response(...)`
5. Use proper HTTP status codes:
   - 400: Bad Request (validation errors, business logic errors)
   - 401: Unauthorized (authentication required)
   - 403: Forbidden (insufficient permissions)
   - 404: Not Found (resource doesn't exist)
   - 500: Internal Server Error (unexpected errors)

### Priority Files to Update:

1. **user/views.py** - Authentication and user management (HIGHEST PRIORITY)
   - Login, registration, password reset
   - Team management
   - Invitations

2. **user/serializers.py** - User validation
   - Email validation
   - Password validation

3. **inventory/views.py** - Inventory operations
   - Product CRUD
   - Stock operations
   - Category/location deletion checks

4. **sales/views.py** - Sales operations
   - Quote and invoice management
   - Payment processing

5. **purchasing/views.py** - Purchasing operations
   - PO management

6. **company/serializers.py** - Company settings validation
   - Logo size validation
   - Tax rate validation
   - Color format validation

## Examples of Common Patterns

### Pattern 1: Replace Simple Error Response

**Before:**
```python
return Response({'error': 'User not found'}, status=404)
```

**After:**
```python
from progestock_backend.error_utils import not_found_error_response
return not_found_error_response('User')
```

### Pattern 2: Replace Validation Error

**Before:**
```python
return Response({'error': 'Invalid email format'}, status=400)
```

**After:**
```python
from progestock_backend.error_utils import validation_error_response
from django.utils.translation import gettext as _
return validation_error_response(_('Please enter a valid email address.'), field='email')
```

### Pattern 3: Replace Permission Check

**Before:**
```python
if user.role != 'admin':
    return Response({'error': 'Admin permission required'}, status=400)  # Wrong status code!
```

**After:**
```python
from progestock_backend.error_utils import permission_error_response
from progestock_backend.error_codes import UserErrors

if user.role != 'admin':
    return Response({
        'status': 'error',
        'error': {
            'code': UserErrors.ADMIN_PERMISSION_REQUIRED['code'],
            'message': str(UserErrors.ADMIN_PERMISSION_REQUIRED['message'])
        }
    }, status=403)  # Correct status code
```

### Pattern 4: Replace Exception Handling

**Before:**
```python
try:
    product = Product.objects.get(id=product_id)
except Product.DoesNotExist:
    return Response({'error': 'Product not found'}, status=404)
```

**After:**
```python
from rest_framework.exceptions import NotFound
from django.utils.translation import gettext as _

try:
    product = Product.objects.get(id=product_id)
except Product.DoesNotExist:
    raise NotFound(_('Product not found.'))
    # The custom exception handler will format this automatically
```

## Adding New Translations

### Step 1: Add to error_codes.py

```python
class MyErrors:
    NEW_ERROR = {
        'code': 'NEW_ERROR_CODE',
        'message': _('This is a new error message.')
    }
```

### Step 2: Add to Translation Files

Edit both `locale/en/LC_MESSAGES/django.po` and `locale/fr/LC_MESSAGES/django.po`:

**English:**
```po
msgid "This is a new error message."
msgstr "This is a new error message."
```

**French:**
```po
msgid "This is a new error message."
msgstr "Ceci est un nouveau message d'erreur."
```

### Step 3: Compile Translations

```bash
python compile_messages.py
```

### Step 4: Restart Server

The server needs to be restarted to load the new compiled .mo files.

## Testing

### Test Different Languages

1. **Via Company Settings:**
   ```bash
   # Set company language to French
   PATCH /api/company/settings/
   { "language": "fr" }
   ```

2. **Via HTTP Header:**
   ```bash
   curl -H "Accept-Language: fr" http://localhost:8000/api/...
   ```

### Expected Behavior

**English (default):**
```json
{
  "status": "error",
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "User not found."
  }
}
```

**French (when language=fr):**
```json
{
  "status": "error",
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "Utilisateur non trouvé."
  }
}
```

## Important Notes

1. **gettext vs gettext_lazy:**
   - Use `gettext_lazy` (`_`) in serializers and model fields
   - Use `gettext` (`_`) in views and functions
   - Both are imported as `_` for convenience

2. **Variable Substitution:**
   ```python
   # Use .format() or % formatting
   message = _('Cannot delete category. It is being used by {count} product(s).').format(count=5)
   ```

3. **HTTP Status Codes:**
   - Always use the correct HTTP status code
   - 403 for permission errors (not 400!)
   - 401 for authentication errors
   - 404 for not found
   - 400 for validation/business logic errors

4. **DRF Exception Handler:**
   - The custom handler catches all DRF exceptions automatically
   - You can raise standard DRF exceptions and they'll be formatted correctly
   - Manual error responses should still use the error_response helpers

## Summary of Files Modified

### Created Files:
- `progestock_backend/exceptions.py` - Custom exception handler
- `progestock_backend/error_codes.py` - Error code constants
- `progestock_backend/error_utils.py` - Error response helpers
- `progestock_backend/language_middleware.py` - Language detection
- `locale/en/LC_MESSAGES/django.po` - English translations
- `locale/fr/LC_MESSAGES/django.po` - French translations
- `compile_messages.py` - Translation compiler script

### Modified Files:
- `progestock_backend/settings.py`:
  - Added LANGUAGES configuration
  - Added LOCALE_PATHS configuration
  - Added custom exception handler to REST_FRAMEWORK
  - Added LanguageMiddleware to MIDDLEWARE

## Next Steps

1. Update views and serializers to use the new error handling system
2. Test error responses in both English and French
3. Add more translations as needed
4. Consider adding more languages in the future
