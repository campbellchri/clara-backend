"""
Authentication and Multi-Tenancy Models

Handles user-practice associations, invitations, and role-based access.
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    """
    Extended user model with practice associations and roles.
    """
    
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Practice Admin'
        THERAPIST = 'therapist', 'Therapist'
        BILLING = 'billing', 'Billing Staff'
        FRONT_DESK = 'front_desk', 'Front Desk'
        
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        null=True,
        blank=True
    )
    phone = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)
    phi_training_completed = models.BooleanField(default=False)
    phi_training_date = models.DateField(null=True, blank=True)
    
    # Current active practice (for users in multiple practices)
    active_practice = models.ForeignKey(
        'claims.Practice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_users'
    )
    
    class Meta:
        pass
    
    def get_practices(self):
        """Get all practices this user belongs to."""
        return self.practice_memberships.filter(is_active=True).values_list('practice', flat=True)
    
    def has_practice_access(self, practice_id):
        """Check if user has access to a specific practice."""
        return self.practice_memberships.filter(
            practice_id=practice_id,
            is_active=True
        ).exists()


class PracticeMembership(models.Model):
    """
    Many-to-many relationship between users and practices with additional metadata.
    Handles multi-tenancy at the database level.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='practice_memberships'
    )
    practice = models.ForeignKey(
        'claims.Practice',
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=User.Role.choices
    )
    
    # Therapist association (if role is therapist)
    therapist = models.ForeignKey(
        'claims.Therapist',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_membership'
    )
    
    # Membership details
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invitations_sent'
    )
    is_active = models.BooleanField(default=True)
    is_owner = models.BooleanField(default=False)
    
    # Permissions override (optional)
    custom_permissions = models.JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = [['user', 'practice']]
        indexes = [
            models.Index(fields=['practice', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.practice.name} ({self.role})"


class PracticeInvitation(models.Model):
    """
    Invitations for users to join a practice.
    Supports both email invites for new users and invites to existing users.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'
        EXPIRED = 'expired', 'Expired'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    practice = models.ForeignKey(
        'claims.Practice',
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    
    # Either email (for new users) or existing user
    email = models.EmailField()
    invited_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='practice_invitations'
    )
    
    # Invitation details
    role = models.CharField(
        max_length=20,
        choices=User.Role.choices
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations'
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    token = models.CharField(max_length=100, unique=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    # Optional message
    message = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['email', 'status']),
            models.Index(fields=['practice', 'status']),
        ]
    
    def __str__(self):
        return f"Invitation to {self.email} for {self.practice.name}"
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = str(uuid.uuid4())
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if invitation has expired."""
        return timezone.now() > self.expires_at
    
    def accept(self, user=None):
        """Accept the invitation and create practice membership."""
        if self.status != self.Status.PENDING:
            raise ValueError("Invitation is not pending")
        
        if self.is_expired():
            self.status = self.Status.EXPIRED
            self.save()
            raise ValueError("Invitation has expired")
        
        # Use provided user or the invited_user
        membership_user = user or self.invited_user
        if not membership_user:
            raise ValueError("No user provided for membership")
        
        # Create practice membership
        membership, created = PracticeMembership.objects.get_or_create(
            user=membership_user,
            practice=self.practice,
            defaults={
                'role': self.role,
                'invited_by': self.invited_by,
            }
        )
        
        # Update invitation status
        self.status = self.Status.ACCEPTED
        self.accepted_at = timezone.now()
        self.invited_user = membership_user
        self.save()
        
        # Set as active practice if user doesn't have one
        if not membership_user.active_practice:
            membership_user.active_practice = self.practice
            membership_user.save()
        
        return membership


class AuditLog(models.Model):
    """
    HIPAA-compliant audit logging for all data access.
    """
    
    class Action(models.TextChoices):
        VIEW = 'view', 'View'
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        EXPORT = 'export', 'Export'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    practice = models.ForeignKey(
        'claims.Practice',
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    
    # Action details
    action = models.CharField(
        max_length=20,
        choices=Action.choices
    )
    resource_type = models.CharField(max_length=50)
    resource_id = models.CharField(max_length=100, blank=True)
    
    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    
    # Data changes (for updates)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    
    # PHI access flag
    accessed_phi = models.BooleanField(default=False)
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['practice', '-created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['accessed_phi', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} {self.resource_type}"