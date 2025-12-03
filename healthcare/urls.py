"""
URL configuration for healthcare project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from claims.views import (
    MemberViewSet, ProviderViewSet, ClaimViewSet, PaymentTransactionViewSet,
    PracticeViewSet, TherapistViewSet, PatientViewSet, SessionViewSet,
    prepare_claim_standalone
)
from healthcare.auth_views import (
    PracticeRegistrationView,
    LoginView,
    LogoutView,
    PracticeSwitchView,
    InvitationViewSet,
    UserProfileView,
    PracticeMembersView
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'members', MemberViewSet, basename='member')
router.register(r'providers', ProviderViewSet, basename='provider')
router.register(r'claims', ClaimViewSet, basename='claim')
router.register(r'payments', PaymentTransactionViewSet, basename='payment')

# Clara-specific endpoints
router.register(r'practices', PracticeViewSet, basename='practice')
router.register(r'therapists', TherapistViewSet, basename='therapist')
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'sessions', SessionViewSet, basename='session')

# Auth endpoints router
auth_router = DefaultRouter()
auth_router.register(r'invitations', InvitationViewSet, basename='invitation')

urlpatterns = [
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/', include(router.urls)),

    # Standalone claim preparation endpoint (Part 2)
    path('api/claims/prepare/', prepare_claim_standalone, name='prepare-claim'),
    
    # Authentication endpoints
    path('api/auth/register-practice/', PracticeRegistrationView.as_view(), name='register-practice'),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/switch-practice/', PracticeSwitchView.as_view(), name='switch-practice'),
    path('api/auth/profile/', UserProfileView.as_view(), name='user-profile'),
    path('api/auth/practice-members/', PracticeMembersView.as_view(), name='practice-members'),
    path('api/auth/', include(auth_router.urls)),

    # API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
