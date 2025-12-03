"""
Clara Claims Engine - Serializers

Django REST Framework serializers for the claims API.
Handles input validation and output formatting.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from rest_framework import serializers

from .validators import SessionPayload


class SessionClaimInputSerializer(serializers.Serializer):
    """
    Input serializer for the claim preparation endpoint.
    
    Handles field-level validation and type conversion.
    Business rule validation happens in the validator layer.
    """
    practice_id = serializers.CharField(
        max_length=100,
        help_text="Unique identifier for the practice (tenant)"
    )
    therapist_id = serializers.CharField(
        max_length=100,
        help_text="Unique identifier for the rendering provider"
    )
    patient_id = serializers.CharField(
        max_length=100,
        help_text="Unique identifier for the patient"
    )
    session_date = serializers.DateField(
        help_text="Date of service (YYYY-MM-DD)"
    )
    cpt_code = serializers.CharField(
        max_length=10,
        help_text="CPT procedure code (e.g., 90837)"
    )
    icd10_code = serializers.CharField(
        max_length=10,
        help_text="Primary ICD-10 diagnosis code (e.g., F33.1)"
    )
    fee = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Session fee amount"
    )
    copay_collected = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=Decimal('0.00'),
        help_text="Copay amount collected from patient"
    )
    payer_id = serializers.CharField(
        max_length=20,
        help_text="Payer identifier (e.g., BCBSMA)"
    )
    
    def validate_fee(self, value):
        """Ensure fee is a valid decimal."""
        if value is None:
            raise serializers.ValidationError("Fee is required.")
        return value
    
    def validate_cpt_code(self, value):
        """Normalize CPT code."""
        return value.strip().upper() if value else value
    
    def validate_icd10_code(self, value):
        """Normalize ICD-10 code."""
        return value.strip().upper() if value else value
    
    def validate_payer_id(self, value):
        """Normalize payer ID."""
        return value.strip().upper() if value else value
    
    def to_payload(self) -> SessionPayload:
        """
        Convert validated data to a SessionPayload for processing.
        Must be called after is_valid().
        """
        data = self.validated_data
        return SessionPayload(
            practice_id=data['practice_id'],
            therapist_id=data['therapist_id'],
            patient_id=data['patient_id'],
            session_date=data['session_date'],
            cpt_code=data['cpt_code'],
            icd10_code=data['icd10_code'],
            fee=data['fee'],
            copay_collected=data.get('copay_collected', Decimal('0.00')),
            payer_id=data['payer_id'],
        )


class PreparedClaimOutputSerializer(serializers.Serializer):
    """
    Output serializer for prepared claim response.
    
    Maps the PreparedClaim dataclass to JSON response format.
    """
    claim_id = serializers.CharField(
        help_text="Unique identifier for this claim"
    )
    patient_id = serializers.CharField()
    provider_id = serializers.CharField(
        help_text="Rendering provider (therapist) ID"
    )
    practice_id = serializers.CharField(
        help_text="Billing provider (practice) ID"
    )
    payer_id = serializers.CharField()
    service_date = serializers.CharField(
        help_text="Date of service (ISO format)"
    )
    cpt_code = serializers.CharField()
    icd10_code = serializers.CharField(
        help_text="Primary diagnosis code"
    )
    charge_amount = serializers.FloatField()
    copay_amount = serializers.FloatField()
    status = serializers.CharField(
        help_text="READY_FOR_SUBMISSION or INVALID"
    )
    validation_errors = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of validation errors (empty if valid)"
    )


class ValidationErrorResponseSerializer(serializers.Serializer):
    """Serializer for validation error responses."""
    status = serializers.CharField(default="INVALID")
    validation_errors = serializers.ListField(
        child=serializers.CharField()
    )


class APIErrorSerializer(serializers.Serializer):
    """Standard API error response format."""
    error = serializers.CharField()
    detail = serializers.CharField(required=False)
    code = serializers.CharField(required=False)