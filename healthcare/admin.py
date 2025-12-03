from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PracticeMembership, PracticeInvitation, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'active_practice', 'is_verified')
    list_filter = ('role', 'is_verified', 'phi_training_completed', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Healthcare', {
            'fields': ('role', 'phone', 'is_verified', 'phi_training_completed', 
                      'phi_training_date', 'active_practice')
        }),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')


@admin.register(PracticeMembership)
class PracticeMembershipAdmin(admin.ModelAdmin):
    """Admin interface for PracticeMembership model."""
    list_display = ('user', 'practice', 'role', 'is_active', 'is_owner', 'joined_at')
    list_filter = ('role', 'is_active', 'is_owner')
    search_fields = ('user__username', 'user__email', 'practice__name')
    date_hierarchy = 'joined_at'


@admin.register(PracticeInvitation)
class PracticeInvitationAdmin(admin.ModelAdmin):
    """Admin interface for PracticeInvitation model."""
    list_display = ('email', 'practice', 'role', 'status', 'invited_by', 'created_at', 'expires_at')
    list_filter = ('status', 'role')
    search_fields = ('email', 'practice__name')
    date_hierarchy = 'created_at'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model."""
    list_display = ('user', 'practice', 'action', 'resource_type', 'accessed_phi', 'created_at')
    list_filter = ('action', 'resource_type', 'accessed_phi')
    search_fields = ('user__username', 'resource_type', 'resource_id')
    date_hierarchy = 'created_at'
    readonly_fields = ('user', 'practice', 'action', 'resource_type', 'resource_id', 
                      'ip_address', 'user_agent', 'request_path', 'old_values', 
                      'new_values', 'accessed_phi', 'created_at')