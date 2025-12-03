"""
Clara Claims Engine - Exception Handling

Custom exception handler for consistent API error responses.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler for Clara API.
    
    Ensures consistent error response format across all endpoints.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Customize the response format
        custom_response_data = {
            'error': response.status_text if hasattr(response, 'status_text') else 'Error',
            'detail': response.data,
            'code': response.status_code,
        }
        response.data = custom_response_data
    
    return response


class ClaimValidationError(Exception):
    """Raised when claim validation fails."""
    
    def __init__(self, errors: list):
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")


class EntityNotFoundError(Exception):
    """Raised when a required entity is not found."""
    
    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} not found: {entity_id}")