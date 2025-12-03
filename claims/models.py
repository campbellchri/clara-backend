"""
Clara Claims Engine - Models

These models represent the core domain entities for the Clara healthcare
claims platform. For the MVP/technical assessment, we use simplified
in-memory representations alongside Django models.
"""
import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator


class BaseModel(models.Model):
    """Abstract base model with common fields for all entities."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Practice(BaseModel):
    """
    Tenant model - represents a therapy practice.
    All other entities are scoped to a practice for multi-tenancy.
    """
    name = models.CharField(max_length=255)
    npi = models.CharField(max_length=10, unique=True, blank=True, null=True)
    tax_id = models.CharField(max_length=20, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.name


class Therapist(BaseModel):
    """Provider/therapist within a practice."""
    
    practice = models.ForeignKey(
        Practice, 
        on_delete=models.CASCADE, 
        related_name='therapists'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    npi = models.CharField(max_length=10, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    license_state = models.CharField(max_length=2, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['practice']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['practice', 'npi'],
                name='unique_therapist_npi_per_practice'
            )
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Patient(BaseModel):
    """Patient within a practice."""
    
    practice = models.ForeignKey(
        Practice, 
        on_delete=models.CASCADE, 
        related_name='patients'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    member_id = models.CharField(max_length=50, blank=True)
    payer_id = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)  # Soft delete

    class Meta:
        indexes = [
            models.Index(fields=['practice']),
            models.Index(fields=['practice', 'date_of_birth']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Session(BaseModel):
    """Therapy session/appointment."""
    
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'

    practice = models.ForeignKey(
        Practice, 
        on_delete=models.CASCADE, 
        related_name='sessions'
    )
    therapist = models.ForeignKey(
        Therapist, 
        on_delete=models.PROTECT, 
        related_name='sessions'
    )
    patient = models.ForeignKey(
        Patient, 
        on_delete=models.PROTECT, 
        related_name='sessions'
    )
    session_date = models.DateField()
    cpt_code = models.CharField(max_length=10)
    icd10_code = models.CharField(max_length=10)  # Primary diagnosis
    fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    copay_collected = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    payer_id = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.COMPLETED
    )
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['practice']),
            models.Index(fields=['practice', 'session_date']),
            models.Index(fields=['patient']),
            models.Index(fields=['therapist']),
        ]

    def __str__(self):
        return f"Session {self.id} - {self.patient} on {self.session_date}"


class Claim(BaseModel):
    """
    Insurance claim generated from a session.
    Supports multiple claims per session (for resubmissions/corrections).
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        READY_FOR_SUBMISSION = 'ready', 'Ready for Submission'
        SUBMITTED = 'submitted', 'Submitted'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        PAID = 'paid', 'Paid'
        DENIED = 'denied', 'Denied'

    practice = models.ForeignKey(
        Practice, 
        on_delete=models.CASCADE, 
        related_name='claims'
    )
    session = models.ForeignKey(
        Session, 
        on_delete=models.PROTECT, 
        related_name='claims'
    )
    claim_number = models.CharField(max_length=50, unique=True)
    payer_id = models.CharField(max_length=20)
    status = models.CharField(
        max_length=30, 
        choices=Status.choices, 
        default=Status.DRAFT
    )
    charge_amount = models.DecimalField(max_digits=10, decimal_places=2)
    copay_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    allowed_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    paid_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    response_at = models.DateTimeField(null=True, blank=True)
    denial_reason = models.CharField(max_length=500, blank=True)
    edi_payload = models.JSONField(null=True, blank=True)
    validation_errors = models.JSONField(default=list)

    class Meta:
        indexes = [
            models.Index(fields=['practice']),
            models.Index(fields=['status']),
            models.Index(fields=['practice', 'status']),
            models.Index(fields=['session']),
        ]

    def __str__(self):
        return f"Claim {self.claim_number} - {self.status}"