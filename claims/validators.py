"""
Clara Claims Engine - Validators

Business rule validators for claim preparation. Each validator is a single-responsibility
class that can be composed into validation chains. This design supports:
- Easy testing of individual rules
- Payer-specific rule overrides
- Clear error messaging
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional


@dataclass
class SessionPayload:
    """Input payload for claim preparation."""
    practice_id: str
    therapist_id: str
    patient_id: str
    session_date: date
    cpt_code: str
    icd10_code: str
    fee: Decimal
    copay_collected: Decimal
    payer_id: str


class ClaimValidator(ABC):
    """Base class for claim validators."""
    
    @abstractmethod
    def validate(self, payload: SessionPayload) -> List[str]:
        """
        Validate the payload and return a list of error messages.
        Empty list means validation passed.
        """
        pass


class FeeValidator(ClaimValidator):
    """Validates that fee is positive."""
    
    def validate(self, payload: SessionPayload) -> List[str]:
        errors = []
        if payload.fee <= Decimal('0'):
            errors.append("Fee must be greater than $0.00.")
        return errors


class CopayValidator(ClaimValidator):
    """Validates that copay does not exceed total fee."""
    
    def validate(self, payload: SessionPayload) -> List[str]:
        errors = []
        if payload.copay_collected > payload.fee:
            errors.append(
                f"Copay (${payload.copay_collected}) cannot exceed total fee (${payload.fee})."
            )
        return errors


class CopayNonNegativeValidator(ClaimValidator):
    """Validates that copay is non-negative."""
    
    def validate(self, payload: SessionPayload) -> List[str]:
        errors = []
        if payload.copay_collected < Decimal('0'):
            errors.append("Copay cannot be negative.")
        return errors


class CPTCodeValidator(ClaimValidator):
    """
    Validates CPT code against allowed list.
    
    In production, this would likely pull from a database table
    or external service. For MVP, we use a hardcoded list of common
    psychotherapy CPT codes.
    """
    
    # Common psychotherapy CPT codes
    ALLOWED_CPT_CODES = {
        # Psychotherapy
        '90832': 'Psychotherapy, 30 min',
        '90834': 'Psychotherapy, 45 min',
        '90837': 'Psychotherapy, 60 min',
        '90839': 'Psychotherapy for crisis, first 60 min',
        '90840': 'Psychotherapy for crisis, each additional 30 min',
        # Evaluation
        '90791': 'Psychiatric diagnostic evaluation',
        '90792': 'Psychiatric diagnostic evaluation with medical services',
        # Group therapy
        '90853': 'Group psychotherapy',
        # Family therapy
        '90846': 'Family psychotherapy without patient',
        '90847': 'Family psychotherapy with patient',
        # Add-on codes
        '90785': 'Interactive complexity add-on',
    }
    
    def validate(self, payload: SessionPayload) -> List[str]:
        errors = []
        if payload.cpt_code not in self.ALLOWED_CPT_CODES:
            allowed_list = ', '.join(sorted(self.ALLOWED_CPT_CODES.keys()))
            errors.append(
                f"CPT code '{payload.cpt_code}' is not in the allowed list. "
                f"Allowed codes: {allowed_list}"
            )
        return errors


class ICD10CodeValidator(ClaimValidator):
    """
    Validates ICD-10 code format.
    
    Full ICD-10 validation would require a comprehensive database.
    For MVP, we validate the format is correct.
    """
    
    # Common mental health ICD-10 prefixes
    MENTAL_HEALTH_PREFIXES = {'F', 'Z'}
    
    def validate(self, payload: SessionPayload) -> List[str]:
        errors = []
        code = payload.icd10_code.upper()
        
        # Basic format validation: letter + 2 digits + optional decimal + more digits
        if not code:
            errors.append("ICD-10 code is required.")
        elif len(code) < 3:
            errors.append(f"ICD-10 code '{code}' is too short (minimum 3 characters).")
        elif not code[0].isalpha():
            errors.append(f"ICD-10 code '{code}' must start with a letter.")
        elif not code[1:3].replace('.', '').isdigit():
            errors.append(f"ICD-10 code '{code}' has invalid format.")
        
        return errors


class SessionDateValidator(ClaimValidator):
    """Validates session date is not in the future."""
    
    def validate(self, payload: SessionPayload) -> List[str]:
        errors = []
        today = date.today()
        if payload.session_date > today:
            errors.append(
                f"Session date ({payload.session_date}) cannot be in the future."
            )
        return errors


class PayerIdValidator(ClaimValidator):
    """
    Validates payer ID is recognized.
    
    In production, this would check against a payer directory or
    clearinghouse-supported payer list.
    """
    
    # Common payer IDs (subset for demo)
    KNOWN_PAYERS = {
        'BCBSMA': 'Blue Cross Blue Shield Massachusetts',
        'BCBSCA': 'Blue Cross Blue Shield California',
        'AETNA': 'Aetna',
        'CIGNA': 'Cigna',
        'UHC': 'United Healthcare',
        'HUMANA': 'Humana',
        'ANTHEM': 'Anthem',
        'KAISER': 'Kaiser Permanente',
        'MEDICAID': 'Medicaid',
        'MEDICARE': 'Medicare',
    }
    
    def validate(self, payload: SessionPayload) -> List[str]:
        errors = []
        if payload.payer_id.upper() not in self.KNOWN_PAYERS:
            # Warning rather than error - allow unknown payers for flexibility
            # In production, might want configurable behavior
            pass
        return errors


class ClaimValidatorChain:
    """
    Orchestrates multiple validators and aggregates results.
    
    This pattern allows easy addition of new validators and supports
    payer-specific validation chains.
    """
    
    def __init__(self, validators: Optional[List[ClaimValidator]] = None):
        self.validators = validators or self._default_validators()
    
    def _default_validators(self) -> List[ClaimValidator]:
        """Returns the standard validator chain."""
        return [
            FeeValidator(),
            CopayNonNegativeValidator(),
            CopayValidator(),
            CPTCodeValidator(),
            ICD10CodeValidator(),
            SessionDateValidator(),
        ]
    
    def validate(self, payload: SessionPayload) -> List[str]:
        """
        Run all validators and return aggregated errors.
        Returns empty list if all validations pass.
        """
        all_errors = []
        for validator in self.validators:
            errors = validator.validate(payload)
            all_errors.extend(errors)
        return all_errors
    
    def add_validator(self, validator: ClaimValidator) -> 'ClaimValidatorChain':
        """Add a validator to the chain. Returns self for chaining."""
        self.validators.append(validator)
        return self


# Convenience function for quick validation
def validate_session_payload(payload: SessionPayload) -> List[str]:
    """Validate a session payload using the default validator chain."""
    chain = ClaimValidatorChain()
    return chain.validate(payload)