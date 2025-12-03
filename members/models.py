"""
Members Module - Future Enhancement Placeholder

Simple placeholder for future insurance eligibility and member management features.
Demonstrates awareness of future needs without over-engineering the MVP.
"""
from django.db import models
from claims.models import BaseModel, Practice, Patient


class InsuranceCoverage(BaseModel):
    """
    Simplified insurance coverage tracking for future eligibility checks.
    MVP placeholder for insurance verification features.
    """
    practice = models.ForeignKey(
        Practice,
        on_delete=models.CASCADE,
        related_name='insurance_coverages'
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='insurance_coverage'
    )
    
    # Basic insurance info
    payer_name = models.CharField(max_length=100)
    member_id = models.CharField(max_length=50)
    group_number = models.CharField(max_length=50, blank=True)
    
    # Simple coverage details
    copay_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    
    # Future: Will expand with eligibility API integration
    # Future: Will add deductible tracking
    # Future: Will add authorization management
    
    def __str__(self):
        return f"{self.patient} - {self.payer_name}"