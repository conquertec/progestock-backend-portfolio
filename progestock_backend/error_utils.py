"""
Utility functions for creating standardized error responses.
"""
from rest_framework.response import Response
from rest_framework import status as http_status
from django.utils.translation import gettext as _


def error_response(message, code='ERROR', status=http_status.HTTP_400_BAD_REQUEST, details=None, field=None):
    """
    Create a standardized error response.

    Args:
        message: The error message (can be translatable string)
        code: Error code (default: 'ERROR')
        status: HTTP status code (default: 400)
        details: Optional additional details (dict)
        field: Optional field name for validation errors

    Returns:
        Response object with standardized error format

    Example:
        return error_response(
            message=_('User not found'),
            code='USER_NOT_FOUND',
            status=404
        )
    """
    error_data = {
        'status': 'error',
        'error': {
            'code': code,
            'message': str(message),
        }
    }

    if details:
        error_data['error']['details'] = details

    if field:
        error_data['error']['field'] = field

    return Response(error_data, status=status)


def validation_error_response(message, field=None, details=None):
    """
    Create a validation error response.

    Args:
        message: The validation error message
        field: Optional field name
        details: Optional additional validation details

    Returns:
        Response object with validation error format
    """
    return error_response(
        message=message,
        code='VALIDATION_ERROR',
        status=http_status.HTTP_400_BAD_REQUEST,
        field=field,
        details=details
    )


def authentication_error_response(message=None):
    """
    Create an authentication error response.

    Args:
        message: Optional custom message (defaults to standard auth message)

    Returns:
        Response object with authentication error
    """
    if message is None:
        message = _('Authentication credentials were not provided or are invalid.')

    return error_response(
        message=message,
        code='AUTHENTICATION_REQUIRED',
        status=http_status.HTTP_401_UNAUTHORIZED
    )


def permission_error_response(message=None):
    """
    Create a permission denied error response.

    Args:
        message: Optional custom message

    Returns:
        Response object with permission error
    """
    if message is None:
        message = _('You do not have permission to perform this action.')

    return error_response(
        message=message,
        code='PERMISSION_DENIED',
        status=http_status.HTTP_403_FORBIDDEN
    )


def not_found_error_response(resource_name=None):
    """
    Create a not found error response.

    Args:
        resource_name: Optional name of the resource that wasn't found

    Returns:
        Response object with not found error
    """
    if resource_name:
        message = _('{} not found.').format(resource_name)
    else:
        message = _('The requested resource was not found.')

    return error_response(
        message=message,
        code='NOT_FOUND',
        status=http_status.HTTP_404_NOT_FOUND
    )


def success_response(data, message=None, status=http_status.HTTP_200_OK):
    """
    Create a standardized success response.

    Args:
        data: Response data
        message: Optional success message
        status: HTTP status code (default: 200)

    Returns:
        Response object with success format
    """
    response_data = {
        'status': 'success',
        'data': data
    }

    if message:
        response_data['message'] = str(message)

    return Response(response_data, status=status)
