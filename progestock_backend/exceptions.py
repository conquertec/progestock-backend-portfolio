"""
Custom exception handler for ProGestock API.
Provides standardized error responses with internationalization support.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns standardized error responses.

    All errors will follow this format:
    {
        "status": "error",
        "error": {
            "code": "ERROR_CODE",
            "message": "Human-readable error message (internationalized)",
            "details": {...},  # Optional: additional error details
            "field": "field_name"  # Optional: for validation errors
        }
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # If DRF couldn't handle it, create a generic 500 response
    if response is None:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return Response({
            'status': 'error',
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': str(_('An unexpected error occurred. Please try again later.')),
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Standardize the error response format
    error_response = {
        'status': 'error',
        'error': {}
    }

    # Extract error code from exception if available
    error_code = getattr(exc, 'default_code', None) or getattr(exc, 'code', 'ERROR')
    error_response['error']['code'] = error_code.upper()

    # Handle validation errors (field-specific errors)
    if isinstance(exc, (DRFValidationError, DjangoValidationError)):
        if isinstance(response.data, dict):
            # Check for login-specific errors and provide user-friendly message
            non_field_errors = response.data.get('non_field_errors', [])
            if non_field_errors:
                # Check if it's a login credential error
                first_error = non_field_errors[0] if isinstance(non_field_errors, list) else str(non_field_errors)
                if 'credentials' in str(first_error).lower() or 'log in' in str(first_error).lower():
                    error_response['error']['code'] = 'INVALID_CREDENTIALS'
                    error_response['error']['message'] = str(_('Invalid email or password. Please check your credentials and try again.'))
                    error_response['error']['details'] = response.data
                    response.data = error_response
                    return response

            # Check if it's a single field error or multiple field errors
            if len(response.data) == 1 and 'non_field_errors' not in response.data:
                # Single field error
                field_name = list(response.data.keys())[0]
                error_message = response.data[field_name]
                if isinstance(error_message, list):
                    error_message = error_message[0]

                error_response['error']['code'] = 'VALIDATION_ERROR'
                error_response['error']['message'] = str(error_message)
                error_response['error']['field'] = field_name
            else:
                # Multiple field errors or non-field errors
                error_response['error']['code'] = 'VALIDATION_ERROR'
                error_response['error']['message'] = str(_('Validation failed. Please check your input.'))
                error_response['error']['details'] = response.data
        elif isinstance(response.data, list):
            # List of errors
            error_response['error']['message'] = response.data[0] if response.data else str(_('Validation error'))
        else:
            error_response['error']['message'] = str(response.data)

    # Handle authentication errors
    elif response.status_code == status.HTTP_401_UNAUTHORIZED:
        error_response['error']['code'] = 'AUTHENTICATION_REQUIRED'
        if 'detail' in response.data:
            error_response['error']['message'] = str(response.data['detail'])
        else:
            error_response['error']['message'] = str(_('Authentication credentials were not provided or are invalid.'))

    # Handle permission errors
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        error_response['error']['code'] = 'PERMISSION_DENIED'
        if 'detail' in response.data:
            error_response['error']['message'] = str(response.data['detail'])
        else:
            error_response['error']['message'] = str(_('You do not have permission to perform this action.'))

    # Handle not found errors
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        error_response['error']['code'] = 'NOT_FOUND'
        if 'detail' in response.data:
            error_response['error']['message'] = str(response.data['detail'])
        else:
            error_response['error']['message'] = str(_('The requested resource was not found.'))

    # Handle method not allowed
    elif response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        error_response['error']['code'] = 'METHOD_NOT_ALLOWED'
        error_response['error']['message'] = str(_('This HTTP method is not allowed for this endpoint.'))

    # Handle throttling (rate limiting)
    elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        error_response['error']['code'] = 'RATE_LIMIT_EXCEEDED'
        error_response['error']['message'] = str(_('Too many requests. Please slow down and try again later.'))
        if 'detail' in response.data:
            error_response['error']['details'] = {'retry_after': response.data.get('retry_after')}

    # Handle all other errors
    else:
        if 'detail' in response.data:
            error_response['error']['message'] = str(response.data['detail'])
        elif 'error' in response.data:
            error_response['error']['message'] = str(response.data['error'])
        else:
            error_response['error']['message'] = str(response.data) if response.data else str(_('An error occurred'))

    response.data = error_response
    return response


class CustomAPIException(Exception):
    """
    Base class for custom API exceptions with internationalization support.
    """
    def __init__(self, message, code='ERROR', status_code=status.HTTP_400_BAD_REQUEST, details=None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

    def to_response(self):
        """Convert exception to API response format"""
        error_response = {
            'status': 'error',
            'error': {
                'code': self.code,
                'message': str(self.message),
            }
        }
        if self.details:
            error_response['error']['details'] = self.details

        return Response(error_response, status=self.status_code)
