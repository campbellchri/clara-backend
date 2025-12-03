"""
Custom Permission Classes for Multi-Tenant Access Control

Enforces practice-based data isolation and role-based permissions.
"""
from rest_framework import permissions
from .auth_models import User, PracticeMembership


class IsPracticeMember(permissions.BasePermission):
    """
    Ensures user is an active member of a practice.
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Must have an active practice set
        if not request.user.active_practice:
            return False
        
        # Must be an active member of that practice
        return request.user.practice_memberships.filter(
            practice=request.user.active_practice,
            is_active=True
        ).exists()
    
    def has_object_permission(self, request, view, obj):
        # Check if object has practice attribute
        if hasattr(obj, 'practice'):
            return obj.practice == request.user.active_practice
        
        # Check if object has practice_id attribute
        if hasattr(obj, 'practice_id'):
            return obj.practice_id == request.user.active_practice_id
        
        return True


class IsPracticeAdmin(permissions.BasePermission):
    """
    Ensures user is an admin of their active practice.
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Must have an active practice set
        if not request.user.active_practice:
            return False
        
        # Must be an admin of that practice
        return request.user.practice_memberships.filter(
            practice=request.user.active_practice,
            role=User.Role.ADMIN,
            is_active=True
        ).exists()


class IsPracticeOwner(permissions.BasePermission):
    """
    Ensures user is the owner of their active practice.
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Must have an active practice set
        if not request.user.active_practice:
            return False
        
        # Must be the owner of that practice
        return request.user.practice_memberships.filter(
            practice=request.user.active_practice,
            is_owner=True,
            is_active=True
        ).exists()


class IsTherapist(permissions.BasePermission):
    """
    Ensures user is a therapist in their active practice.
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Must have an active practice set
        if not request.user.active_practice:
            return False
        
        # Must be a therapist in that practice
        return request.user.practice_memberships.filter(
            practice=request.user.active_practice,
            role=User.Role.THERAPIST,
            is_active=True
        ).exists()
    
    def has_object_permission(self, request, view, obj):
        # For session/claim objects, check if user is the therapist
        if hasattr(obj, 'therapist'):
            membership = request.user.practice_memberships.filter(
                practice=request.user.active_practice,
                role=User.Role.THERAPIST,
                is_active=True
            ).first()
            
            if membership and membership.therapist:
                return obj.therapist == membership.therapist
        
        return True


class IsBillingStaff(permissions.BasePermission):
    """
    Ensures user is billing staff in their active practice.
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Must have an active practice set
        if not request.user.active_practice:
            return False
        
        # Must be billing staff or admin
        return request.user.practice_memberships.filter(
            practice=request.user.active_practice,
            role__in=[User.Role.BILLING, User.Role.ADMIN],
            is_active=True
        ).exists()


class CanSubmitClaims(permissions.BasePermission):
    """
    Ensures user can submit claims (therapist, billing, or admin).
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Must have an active practice set
        if not request.user.active_practice:
            return False
        
        # Must have appropriate role
        return request.user.practice_memberships.filter(
            practice=request.user.active_practice,
            role__in=[User.Role.THERAPIST, User.Role.BILLING, User.Role.ADMIN],
            is_active=True
        ).exists()


class ReadOnlyOrAdmin(permissions.BasePermission):
    """
    Read-only access for all practice members, write access for admins only.
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Must have an active practice set
        if not request.user.active_practice:
            return False
        
        # Read permissions for any practice member
        if request.method in permissions.SAFE_METHODS:
            return request.user.practice_memberships.filter(
                practice=request.user.active_practice,
                is_active=True
            ).exists()
        
        # Write permissions for admins only
        return request.user.practice_memberships.filter(
            practice=request.user.active_practice,
            role=User.Role.ADMIN,
            is_active=True
        ).exists()


class HasPHITraining(permissions.BasePermission):
    """
    Ensures user has completed PHI training before accessing sensitive data.
    """
    
    def has_permission(self, request, view):
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Must have completed PHI training
        return request.user.phi_training_completed
    
    def has_object_permission(self, request, view, obj):
        # Additional check for patient-specific data
        return request.user.phi_training_completed