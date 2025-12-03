"""
Providers Module - Future Enhancement Placeholder

Simple placeholder for future provider network management.
Demonstrates awareness of provider credentialing needs without over-engineering.
"""
from django.db import models
from claims.models import BaseModel, Practice, Therapist


class NetworkStatus(BaseModel):
    """
    Simplified tracking of therapist insurance network participation.
    MVP placeholder for future credentialing and network management.
    """
    practice = models.ForeignKey(
        Practice,
        on_delete=models.CASCADE,
        related_name='network_statuses'
    )
    therapist = models.ForeignKey(
        Therapist,
        on_delete=models.CASCADE,
        related_name='network_status'
    )
    
    # Basic network info
    payer_name = models.CharField(max_length=100)
    is_in_network = models.BooleanField(default=False)
    provider_id = models.CharField(max_length=50, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Future: Will expand with credentialing workflow
    # Future: Will add reimbursement rate management
    # Future: Will add contract tracking
    
    class Meta:
        unique_together = [['therapist', 'payer_name']]
    
    def __str__(self):
        return f"{self.therapist} - {self.payer_name} ({'In' if self.is_in_network else 'Out'} Network)"