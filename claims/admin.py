"""
Django Admin configuration for Claims app
"""
from django.contrib import admin
from .models import (
    Practice, Therapist, Patient, Session, Claim
)


@admin.register(Practice)
class PracticeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'npi', 'state', 'created_at']
    list_filter = ['state', 'created_at']
    search_fields = ['name', 'npi', 'id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Therapist)
class TherapistAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'practice', 'npi', 'is_active']
    list_filter = ['practice', 'is_active', 'license_state']
    search_fields = ['first_name', 'last_name', 'npi', 'id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'practice', 'payer_id', 'is_active']
    list_filter = ['practice', 'is_active', 'payer_id']
    search_fields = ['first_name', 'last_name', 'id', 'member_id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_date', 'patient', 'therapist', 'cpt_code', 'status', 'fee']
    list_filter = ['practice', 'status', 'session_date']
    search_fields = ['id', 'patient__first_name', 'patient__last_name', 'therapist__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'session_date'


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ['claim_number', 'session', 'status', 'charge_amount', 'paid_amount', 'created_at']
    list_filter = ['status', 'submitted_at', 'created_at']
    search_fields = ['claim_number', 'id', 'payer_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'