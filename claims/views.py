"""
Clara Claims Engine - API Views

REST API endpoints for claim preparation and management.
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import (
    SessionClaimInputSerializer,
    PreparedClaimOutputSerializer,
    ValidationErrorResponseSerializer,
)
from .services import ClaimPreparationService, ClaimStatus


class PrepareClaimView(APIView):
    """
    Endpoint to prepare a therapy session for claim submission.
    
    Accepts session data, validates against business rules, and returns
    a structured claim object ready for 837P transformation.
    """
    # TODO: Re-enable after fixing auth setup
    # permission_classes = [IsAuthenticated, CanSubmitClaims]
    permission_classes = []  # Temporarily disabled for MVP
    
    @extend_schema(
        request=SessionClaimInputSerializer,
        responses={
            200: PreparedClaimOutputSerializer,
            400: ValidationErrorResponseSerializer,
            422: OpenApiResponse(description="Validation failed"),
        },
        summary="Prepare a claim from session data",
        description="""
        Validates session data and prepares it for claim submission.
        
        Business rules enforced:
        - Fee must be greater than $0
        - Copay cannot exceed fee
        - CPT code must be from allowed list
        - ICD-10 code must have valid format
        - Session date cannot be in the future
        
        Returns a prepared claim object with status:
        - READY_FOR_SUBMISSION: All validations passed
        - INVALID: One or more validation errors
        """,
        tags=["Claims"],
    )
    def post(self, request):
        """
        Prepare a claim from session data.
        
        POST /api/v1/claims/prepare
        """
        # Deserialize and validate input format
        serializer = SessionClaimInputSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    "status": "INVALID",
                    "validation_errors": self._format_serializer_errors(serializer.errors),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Convert to payload and process
        payload = serializer.to_payload()
        
        # Add practice context from user (if authenticated)
        if hasattr(request, 'practice_id'):
            payload['practice_id'] = request.practice_id
        elif hasattr(request.user, 'active_practice') and request.user.active_practice:
            payload['practice_id'] = request.user.active_practice.id
        
        # Prepare claim using service layer
        service = ClaimPreparationService()
        prepared_claim = service.prepare_claim(payload)
        
        # Serialize output
        output_serializer = PreparedClaimOutputSerializer(prepared_claim.to_dict())
        
        # Return with appropriate status code
        if prepared_claim.status == ClaimStatus.INVALID:
            return Response(
                output_serializer.data,
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        
        return Response(output_serializer.data, status=status.HTTP_200_OK)
    
    def _format_serializer_errors(self, errors: dict) -> list:
        """Convert DRF serializer errors to flat list of strings."""
        formatted = []
        for field, messages in errors.items():
            if isinstance(messages, list):
                for msg in messages:
                    formatted.append(f"{field}: {msg}")
            else:
                formatted.append(f"{field}: {messages}")
        return formatted


# Alternative function-based view (for simpler implementation)
@extend_schema(
    request=SessionClaimInputSerializer,
    responses={
        200: PreparedClaimOutputSerializer,
        400: ValidationErrorResponseSerializer,
    },
    summary="Prepare a claim (function-based)",
    tags=["Claims"],
)
@api_view(['POST'])
def prepare_claim(request):
    """
    Function-based alternative for claim preparation.
    
    POST /api/v1/claims/prepare-simple
    """
    serializer = SessionClaimInputSerializer(data=request.data)
    
    if not serializer.is_valid():
        errors = []
        for field, messages in serializer.errors.items():
            for msg in messages:
                errors.append(f"{field}: {msg}")
        return Response(
            {"status": "INVALID", "validation_errors": errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    payload = serializer.to_payload()
    service = ClaimPreparationService()
    prepared_claim = service.prepare_claim(payload)
    
    output = PreparedClaimOutputSerializer(prepared_claim.to_dict())
    
    if prepared_claim.status == ClaimStatus.INVALID:
        return Response(output.data, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    return Response(output.data, status=status.HTTP_200_OK)


class HealthCheckView(APIView):
    """Simple health check endpoint."""
    
    @extend_schema(
        responses={200: OpenApiResponse(description="Service is healthy")},
        summary="Health check",
        tags=["System"],
    )
    def get(self, request):
        return Response({"status": "healthy", "service": "clara-claims-api"})