# Quick Start: Testing Internationalized Error Messages

## What's New

Your backend now supports **user-friendly error messages in English and French** with standardized error codes!

## How It Works

1. **Language Detection:**
   - The backend automatically detects the user's language from their company settings
   - Falls back to `Accept-Language` HTTP header if no company language is set
   - Defaults to English if no language is detected

2. **Error Response Format:**
   - All errors now return a consistent format:
   ```json
   {
     "status": "error",
     "error": {
       "code": "USER_FRIENDLY_CODE",
       "message": "Clear, actionable error message in the user's language"
     }
   }
   ```

## Testing the Changes

### Option 1: Test via Company Settings (Recommended)

The frontend already saves the language preference to the backend company settings. When a user changes their language in the UI:

1. Frontend calls: `PATCH /api/company/settings/` with `{ "language": "fr" }`
2. This is stored in the company model
3. All subsequent API requests will return errors in French

**Example:**
```bash
# Login as a user
# Change language to French via the frontend UI
# Try an invalid action (e.g., wrong password)
# Error will be in French!
```

### Option 2: Test via HTTP Header

You can also test by sending the `Accept-Language` header:

```bash
# English (default)
curl -X POST http://localhost:8000/api/auth/verify-email/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "code": "wrong"}' \
  -i

# Response:
{
  "status": "error",
  "error": {
    "code": "INVALID_VERIFICATION_CODE",
    "message": "The verification code is invalid or has expired."
  }
}

# French
curl -X POST http://localhost:8000/api/auth/verify-email/ \
  -H "Content-Type: application/json" \
  -H "Accept-Language: fr" \
  -d '{"email": "test@example.com", "code": "wrong"}' \
  -i

# Response:
{
  "status": "error",
  "error": {
    "code": "INVALID_VERIFICATION_CODE",
    "message": "Le code de vérification est invalide ou a expiré."
  }
}
```

## Example Error Messages

### Authentication Errors

| Code | English | French |
|------|---------|--------|
| `INVALID_CREDENTIALS` | The email or password you entered is incorrect. | L'email ou le mot de passe que vous avez saisi est incorrect. |
| `EMAIL_NOT_VERIFIED` | Please verify your email address before logging in. | Veuillez vérifier votre adresse email avant de vous connecter. |
| `TOKEN_EXPIRED` | This link has expired. Please request a new one. | Ce lien a expiré. Veuillez en demander un nouveau. |
| `INVALID_VERIFICATION_CODE` | The verification code is invalid or has expired. | Le code de vérification est invalide ou a expiré. |

### User Management Errors

| Code | English | French |
|------|---------|--------|
| `EMAIL_ALREADY_EXISTS` | A user is already registered with this email address. | Un utilisateur est déjà enregistré avec cette adresse email. |
| `CANNOT_DELETE_SELF` | You cannot delete your own account. | Vous ne pouvez pas supprimer votre propre compte. |
| `ADMIN_PERMISSION_REQUIRED` | Only administrators can perform this action. | Seuls les administrateurs peuvent effectuer cette action. |

### Inventory Errors

| Code | English | French |
|------|---------|--------|
| `PRODUCT_NOT_FOUND` | Product not found. | Produit non trouvé. |
| `INSUFFICIENT_STOCK` | Insufficient stock available for this operation. | Stock insuffisant pour cette opération. |
| `CATEGORY_IN_USE` | Cannot delete category. It is being used by X product(s). | Impossible de supprimer la catégorie. Elle est utilisée par X produit(s). |

## Already Updated Files

The following files have been updated with internationalized error messages:

1. **user/views.py** (examples updated):
   - Email verification errors
   - Password reset errors
   - Token expiration errors

2. **progestock_backend/settings.py**:
   - Added LANGUAGES configuration
   - Added LOCALE_PATHS
   - Added custom exception handler
   - Added LanguageMiddleware

## Next Steps for Full Implementation

To complete the internationalization across the entire codebase, you need to update:

1. **Remaining views** - Replace all `Response({'error': '...'})` with `error_response(...)`
2. **All serializers** - Wrap validation messages with `_("message")`
3. **Frontend integration** - The frontend already saves language preference, so it should work automatically!

See `I18N_IMPLEMENTATION_GUIDE.md` for detailed instructions and examples.

## How to Add More Translations

1. Edit `locale/en/LC_MESSAGES/django.po` (English)
2. Edit `locale/fr/LC_MESSAGES/django.po` (French)
3. Run: `python compile_messages.py`
4. Restart the server

## Files Created

- `progestock_backend/exceptions.py` - Custom exception handler
- `progestock_backend/error_codes.py` - Error code constants (50 messages)
- `progestock_backend/error_utils.py` - Helper functions
- `progestock_backend/language_middleware.py` - Language detection
- `locale/en/LC_MESSAGES/django.po` - English translations
- `locale/fr/LC_MESSAGES/django.po` - French translations
- `compile_messages.py` - Translation compiler

## Benefits

1. **Better UX:** Users see errors in their preferred language
2. **Consistent Format:** All errors follow the same structure
3. **Error Codes:** Frontend can handle specific errors programmatically
4. **Proper HTTP Status Codes:** 401 for auth, 403 for permissions, 404 for not found, etc.
5. **Maintainable:** All error messages defined in one place

## Troubleshooting

**Q: Errors still showing in English even though I set French?**
- Check that the company language setting is saved correctly
- Verify the LanguageMiddleware is in the MIDDLEWARE list
- Check that the .mo files are compiled (run `python compile_messages.py`)
- Restart the Django server

**Q: Getting import errors?**
- Make sure all new files are in the `progestock_backend` directory
- Verify the paths in settings.py are correct

**Q: Want to add a new language (e.g., Spanish)?**
1. Add `('es', 'Español')` to `settings.LANGUAGES`
2. Create `locale/es/LC_MESSAGES/django.po`
3. Translate all messages
4. Run `python compile_messages.py`
