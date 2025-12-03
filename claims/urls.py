"""
Clara Claims Engine - URL Configuration

API routes for the claims module.
"""
from django.urls import path
from .views import PrepareClaimView, prepare_claim, HealthCheckView

app_name = 'claims'

urlpatterns = [
    # Primary endpoint (class-based)
    path('prepare', PrepareClaimView.as_view(), name='prepare-claim'),
    
    # Alternative endpoint (function-based, for reference)
    path('prepare-simple', prepare_claim, name='prepare-claim-simple'),
    
    # Health check
    path('health', HealthCheckView.as_view(), name='health-check'),
]