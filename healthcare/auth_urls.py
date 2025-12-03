"""
Healthcare Authentication URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .auth_views import (
    PracticeRegistrationView,
    LoginView,
    LogoutView,
    PracticeSwitchView,
    InvitationViewSet,
    UserProfileView,
    PracticeMembersView
)

# Router for viewsets
router = DefaultRouter()
router.register(r'invitations', InvitationViewSet, basename='invitation')

app_name = 'healthcare_auth'

urlpatterns = [
    # Authentication
    path('register-practice/', PracticeRegistrationView.as_view(), name='register-practice'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Practice Management
    path('switch-practice/', PracticeSwitchView.as_view(), name='switch-practice'),
    path('practice-members/', PracticeMembersView.as_view(), name='practice-members'),
    
    # User Management
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    
    # Include router URLs for invitations
    path('', include(router.urls)),
]