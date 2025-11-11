"""
Error codes and messages for ProGestock API.
All error messages support internationalization.
"""
from django.utils.translation import gettext_lazy as _


# Authentication & Authorization Error Codes
class AuthErrors:
    INVALID_CREDENTIALS = {
        'code': 'INVALID_CREDENTIALS',
        'message': _('The email or password you entered is incorrect.')
    }

    EMAIL_NOT_VERIFIED = {
        'code': 'EMAIL_NOT_VERIFIED',
        'message': _('Please verify your email address before logging in.')
    }

    ACCOUNT_DISABLED = {
        'code': 'ACCOUNT_DISABLED',
        'message': _('Your account has been disabled. Please contact support.')
    }

    TOKEN_EXPIRED = {
        'code': 'TOKEN_EXPIRED',
        'message': _('This link has expired. Please request a new one.')
    }

    INVALID_TOKEN = {
        'code': 'INVALID_TOKEN',
        'message': _('This link is invalid or has already been used.')
    }

    INVALID_VERIFICATION_CODE = {
        'code': 'INVALID_VERIFICATION_CODE',
        'message': _('The verification code is invalid or has expired.')
    }

    EMAIL_ALREADY_VERIFIED = {
        'code': 'EMAIL_ALREADY_VERIFIED',
        'message': _('This email address has already been verified.')
    }

    GOOGLE_AUTH_FAILED = {
        'code': 'GOOGLE_AUTH_FAILED',
        'message': _('Google authentication failed. Please try again.')
    }


# User & Team Management Error Codes
class UserErrors:
    EMAIL_ALREADY_EXISTS = {
        'code': 'EMAIL_ALREADY_EXISTS',
        'message': _('A user is already registered with this email address.')
    }

    USER_NOT_FOUND = {
        'code': 'USER_NOT_FOUND',
        'message': _('User not found.')
    }

    CANNOT_DELETE_SELF = {
        'code': 'CANNOT_DELETE_SELF',
        'message': _('You cannot delete your own account.')
    }

    CANNOT_CHANGE_OWN_ROLE = {
        'code': 'CANNOT_CHANGE_OWN_ROLE',
        'message': _('You cannot change your own role.')
    }

    ADMIN_PERMISSION_REQUIRED = {
        'code': 'ADMIN_PERMISSION_REQUIRED',
        'message': _('Only administrators can perform this action.')
    }

    INVITATION_NOT_FOUND = {
        'code': 'INVITATION_NOT_FOUND',
        'message': _('Invitation not found or has expired.')
    }

    INVITATION_ALREADY_ACCEPTED = {
        'code': 'INVITATION_ALREADY_ACCEPTED',
        'message': _('This invitation has already been accepted.')
    }

    PASSWORD_TOO_WEAK = {
        'code': 'PASSWORD_TOO_WEAK',
        'message': _('Password must be at least 8 characters long.')
    }


# Company & Settings Error Codes
class CompanyErrors:
    NO_COMPANY_ASSOCIATION = {
        'code': 'NO_COMPANY_ASSOCIATION',
        'message': _('User is not associated with any company.')
    }

    LOGO_TOO_LARGE = {
        'code': 'LOGO_TOO_LARGE',
        'message': _('Logo file size must not exceed 2MB.')
    }

    INVALID_TAX_RATE = {
        'code': 'INVALID_TAX_RATE',
        'message': _('Sales tax rate must be between 0 and 100.')
    }

    INVALID_COLOR_FORMAT = {
        'code': 'INVALID_COLOR_FORMAT',
        'message': _('Brand color must be a valid hexadecimal color code (e.g., #FF5733).')
    }


# Inventory Error Codes
class InventoryErrors:
    PRODUCT_NOT_FOUND = {
        'code': 'PRODUCT_NOT_FOUND',
        'message': _('Product not found.')
    }

    CATEGORY_IN_USE = {
        'code': 'CATEGORY_IN_USE',
        'message': _('Cannot delete category. It is being used by {count} product(s).')
    }

    LOCATION_IN_USE = {
        'code': 'LOCATION_IN_USE',
        'message': _('Cannot delete location. It contains {count} product(s).')
    }

    INSUFFICIENT_STOCK = {
        'code': 'INSUFFICIENT_STOCK',
        'message': _('Insufficient stock available for this operation.')
    }

    INVALID_STOCK_QUANTITY = {
        'code': 'INVALID_STOCK_QUANTITY',
        'message': _('Stock quantity must be a positive number.')
    }

    PRODUCT_ALREADY_EXISTS = {
        'code': 'PRODUCT_ALREADY_EXISTS',
        'message': _('A product with this SKU already exists.')
    }


# Sales Error Codes
class SalesErrors:
    QUOTE_NOT_FOUND = {
        'code': 'QUOTE_NOT_FOUND',
        'message': _('Quote not found.')
    }

    INVOICE_NOT_FOUND = {
        'code': 'INVOICE_NOT_FOUND',
        'message': _('Invoice not found.')
    }

    CLIENT_NOT_FOUND = {
        'code': 'CLIENT_NOT_FOUND',
        'message': _('Client not found.')
    }

    INVALID_PAYMENT_AMOUNT = {
        'code': 'INVALID_PAYMENT_AMOUNT',
        'message': _('Payment amount cannot exceed the outstanding balance.')
    }

    QUOTE_ALREADY_CONVERTED = {
        'code': 'QUOTE_ALREADY_CONVERTED',
        'message': _('This quote has already been converted to an invoice.')
    }

    INVOICE_ALREADY_PAID = {
        'code': 'INVOICE_ALREADY_PAID',
        'message': _('This invoice has already been fully paid.')
    }


# Purchasing Error Codes
class PurchasingErrors:
    PURCHASE_ORDER_NOT_FOUND = {
        'code': 'PURCHASE_ORDER_NOT_FOUND',
        'message': _('Purchase order not found.')
    }

    SUPPLIER_NOT_FOUND = {
        'code': 'SUPPLIER_NOT_FOUND',
        'message': _('Supplier not found.')
    }

    PO_ALREADY_RECEIVED = {
        'code': 'PO_ALREADY_RECEIVED',
        'message': _('This purchase order has already been received.')
    }


# Validation Error Codes
class ValidationErrors:
    REQUIRED_FIELD = {
        'code': 'REQUIRED_FIELD',
        'message': _('This field is required.')
    }

    INVALID_EMAIL = {
        'code': 'INVALID_EMAIL',
        'message': _('Please enter a valid email address.')
    }

    INVALID_DATE = {
        'code': 'INVALID_DATE',
        'message': _('Please enter a valid date.')
    }

    INVALID_NUMBER = {
        'code': 'INVALID_NUMBER',
        'message': _('Please enter a valid number.')
    }

    VALUE_TOO_LONG = {
        'code': 'VALUE_TOO_LONG',
        'message': _('This value is too long.')
    }


# System Error Codes
class SystemErrors:
    INTERNAL_ERROR = {
        'code': 'INTERNAL_SERVER_ERROR',
        'message': _('An unexpected error occurred. Please try again later.')
    }

    EMAIL_SEND_FAILED = {
        'code': 'EMAIL_SEND_FAILED',
        'message': _('Failed to send email. Please try again later.')
    }

    DATABASE_ERROR = {
        'code': 'DATABASE_ERROR',
        'message': _('A database error occurred. Please try again.')
    }

    RATE_LIMIT_EXCEEDED = {
        'code': 'RATE_LIMIT_EXCEEDED',
        'message': _('Too many requests. Please slow down and try again later.')
    }


# Helper function to create error response
def create_error_response(error_dict, **kwargs):
    """
    Create an error response with optional variable substitution.

    Usage:
        create_error_response(InventoryErrors.CATEGORY_IN_USE, count=5)
    """
    message = str(error_dict['message'])
    if kwargs:
        message = message.format(**kwargs)

    return {
        'code': error_dict['code'],
        'message': message
    }
