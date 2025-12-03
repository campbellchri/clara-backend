"""
Clara Claims Engine - Services

Service layer that orchestrates business logic for claim preparation.
Keeps views thin and business logic testable.
"""
import uuid
from dataclasses import dataclass, asdict
from datetime import date
from decimal import Decimal
from typing import List, Optional

from .validators import SessionPayload, ClaimValidatorChain


@dataclass
class PreparedClaim:
    """
    Internal representation of a claim ready for EDI transformation.
    
    This structure maps to the 837P professional claim format while
    remaining framework-agnostic. The actual EDI generation would
    transform this into X12 837P segments.
    """
    claim_id: str
    patient_id: str
    provider_id: str          # Rendering provider (therapist)
    practice_id: str          # Billing provider (practice)
    payer_id: str
    service_date: str         # ISO format YYYY-MM-DD
    cpt_code: str
    icd10_code: str           # Primary diagnosis
    charge_amount: float
    copay_amount: float
    status: str
    validation_errors: List[str]
    
    # Optional 837P-relevant fields (would be populated from entity lookups)
    patient_name: Optional[str] = None
    provider_npi: Optional[str] = None
    practice_npi: Optional[str] = None
    practice_tax_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def is_valid(self) -> bool:
        """Check if claim is ready for submission."""
        return self.status == ClaimStatus.READY_FOR_SUBMISSION


class ClaimStatus:
    """Claim status constants."""
    READY_FOR_SUBMISSION = "READY_FOR_SUBMISSION"
    INVALID = "INVALID"
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"


class ClaimPreparationService:
    """
    Service for preparing therapy session data into claim format.
    
    This service:
    1. Validates the session payload
    2. Enriches with entity data (mock for now)
    3. Generates a claim ID
    4. Returns a structured PreparedClaim object
    
    In production, this would integrate with:
    - Entity repositories for patient/provider/payer lookups
    - Payer-specific rule engines
    - Claim number generation service
    """
    
    def __init__(self, validator_chain: Optional[ClaimValidatorChain] = None):
        self.validator_chain = validator_chain or ClaimValidatorChain()
    
    def prepare_claim(self, payload: SessionPayload) -> PreparedClaim:
        """
        Prepare a claim from session data.
        
        Args:
            payload: Validated session input data
            
        Returns:
            PreparedClaim object with status indicating validity
        """
        # Run validation
        validation_errors = self.validator_chain.validate(payload)
        
        # Determine status based on validation
        if validation_errors:
            status = ClaimStatus.INVALID
        else:
            status = ClaimStatus.READY_FOR_SUBMISSION
        
        # Generate claim ID (in production: use a sequence or external service)
        claim_id = self._generate_claim_id()
        
        # Build prepared claim
        prepared_claim = PreparedClaim(
            claim_id=claim_id,
            patient_id=payload.patient_id,
            provider_id=payload.therapist_id,
            practice_id=payload.practice_id,
            payer_id=payload.payer_id,
            service_date=payload.session_date.isoformat(),
            cpt_code=payload.cpt_code,
            icd10_code=payload.icd10_code,
            charge_amount=float(payload.fee),
            copay_amount=float(payload.copay_collected),
            status=status,
            validation_errors=validation_errors,
        )
        
        # Enrich with entity data (would be real lookups in production)
        self._enrich_claim(prepared_claim, payload)
        
        return prepared_claim
    
    def _generate_claim_id(self) -> str:
        """
        Generate a unique claim identifier.
        
        Format: CLM-{short_uuid}
        In production, might use a database sequence or external service.
        """
        short_uuid = str(uuid.uuid4())[:8].upper()
        return f"CLM-{short_uuid}"
    
    def _enrich_claim(self, claim: PreparedClaim, payload: SessionPayload) -> None:
        """
        Enrich claim with data from related entities.
        
        In production, this would:
        - Look up patient demographics
        - Look up provider NPI and credentials
        - Look up practice billing info
        - Look up payer-specific requirements
        
        For MVP, we use mock data.
        """
        # Mock enrichment - in production these would be database lookups
        claim.patient_name = f"Patient {payload.patient_id}"
        claim.provider_npi = "1234567890"  # Mock NPI
        claim.practice_npi = "0987654321"  # Mock Practice NPI
        claim.practice_tax_id = "XX-XXXXXXX"  # Mock Tax ID


class ClaimSubmissionService:
    """
    Service for submitting prepared claims to clearinghouse.
    
    Stub for future implementation - would handle:
    - EDI 837P generation
    - Clearinghouse API integration
    - Submission tracking
    - Acknowledgment processing
    """
    
    def submit(self, claim: PreparedClaim) -> dict:
        """Submit a prepared claim to the clearinghouse."""
        if not claim.is_valid():
            raise ValueError("Cannot submit invalid claim")
        
        # TODO: Implement EDI generation and submission
        # This would:
        # 1. Transform PreparedClaim to 837P format
        # 2. Submit to clearinghouse API
        # 3. Track submission status
        # 4. Return confirmation
        
        return {
            "submission_id": str(uuid.uuid4()),
            "claim_id": claim.claim_id,
            "status": "SUBMITTED",
            "message": "Claim submitted successfully (mock)",
        }