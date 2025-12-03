"""
Authentication and Multi-Tenancy API Views

Handles practice registration, user authentication, and invitation workflows.
"""
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.db import transaction
from django.shortcuts import get_object_or_404
from .auth_models import User, PracticeMembership, PracticeInvitation, AuditLog
from .auth_serializers import (
    PracticeRegistrationSerializer,
    InvitationCreateSerializer,
    InvitationAcceptSerializer,
    UserSerializer,
    LoginSerializer,
    PracticeSwitchSerializer
)
from .permissions import IsPracticeAdmin, IsPracticeMember
from claims.models import Practice


class PracticeRegistrationView(APIView):
    """
    Register a new practice with admin user.
    
    POST /api/auth/register-practice/
    """
    permission_classes = [permissions.AllowAny]
    
    @transaction.atomic
    def post(self, request):
        serializer = PracticeRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            
            # Create auth token
            token, created = Token.objects.get_or_create(user=result['user'])
            
            # Log registration
            AuditLog.objects.create(
                user=result['user'],
                practice=result['practice'],
                action=AuditLog.Action.CREATE,
                resource_type='Practice',
                resource_id=str(result['practice'].id),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                request_path=request.path
            )
            
            return Response({
                'message': 'Practice registered successfully',
                'token': token.key,
                'user': UserSerializer(result['user']).data,
                'practice': {
                    'id': result['practice'].id,
                    'name': result['practice'].name
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    User login with optional practice selection.
    
    POST /api/auth/login/
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Create or get token
            token, created = Token.objects.get_or_create(user=user)
            
            # Log login
            if user.active_practice:
                AuditLog.objects.create(
                    user=user,
                    practice=user.active_practice,
                    action=AuditLog.Action.VIEW,
                    resource_type='Login',
                    resource_id=str(user.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    request_path=request.path
                )
            
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    User logout - deletes auth token.
    
    POST /api/auth/logout/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Delete token
        try:
            request.user.auth_token.delete()
        except:
            pass
        
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


class PracticeSwitchView(APIView):
    """
    Switch active practice for multi-practice users.
    
    POST /api/auth/switch-practice/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PracticeSwitchSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            
            # Log practice switch
            AuditLog.objects.create(
                user=user,
                practice=user.active_practice,
                action=AuditLog.Action.UPDATE,
                resource_type='PracticeSwitch',
                resource_id=str(user.active_practice.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                request_path=request.path
            )
            
            return Response({
                'message': 'Practice switched successfully',
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InvitationViewSet(viewsets.ModelViewSet):
    """
    Manage practice invitations.
    
    GET /api/auth/invitations/ - List practice invitations
    POST /api/auth/invitations/ - Create new invitation
    POST /api/auth/invitations/accept/ - Accept invitation
    """
    serializer_class = InvitationCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsPracticeMember]
    
    def get_queryset(self):
        user = self.request.user
        if not user.active_practice:
            return PracticeInvitation.objects.none()
        
        # Admins see all practice invitations
        membership = user.practice_memberships.filter(
            practice=user.active_practice,
            is_active=True
        ).first()
        
        if membership and membership.role == User.Role.ADMIN:
            return PracticeInvitation.objects.filter(
                practice=user.active_practice
            ).order_by('-created_at')
        
        # Others only see their own invitations
        return PracticeInvitation.objects.filter(
            practice=user.active_practice,
            invited_by=user
        ).order_by('-created_at')
    
    def create(self, request):
        # Check admin permission
        if not self.has_admin_permission(request.user):
            return Response(
                {'error': 'Only admins can send invitations'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            invitation = serializer.save()
            
            # Log invitation
            AuditLog.objects.create(
                user=request.user,
                practice=request.user.active_practice,
                action=AuditLog.Action.CREATE,
                resource_type='Invitation',
                resource_id=str(invitation.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                request_path=request.path
            )
            
            return Response({
                'message': 'Invitation sent successfully',
                'invitation': {
                    'id': invitation.id,
                    'email': invitation.email,
                    'role': invitation.role,
                    'token': invitation.token,
                    'expires_at': invitation.expires_at
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def accept(self, request):
        """
        Accept a practice invitation.
        Can be called by existing users (authenticated) or new users (unauthenticated).
        """
        serializer = InvitationAcceptSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            result = serializer.save()
            
            # Create or get token
            token, created = Token.objects.get_or_create(user=result['user'])
            
            # Log acceptance
            AuditLog.objects.create(
                user=result['user'],
                practice=result['practice'],
                action=AuditLog.Action.CREATE,
                resource_type='Membership',
                resource_id=str(result['membership'].id),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                request_path=request.path
            )
            
            return Response({
                'message': 'Invitation accepted successfully',
                'token': token.key,
                'user': UserSerializer(result['user']).data,
                'practice': {
                    'id': result['practice'].id,
                    'name': result['practice'].name
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """
        Resend an invitation email.
        """
        invitation = self.get_object()
        
        if invitation.status != PracticeInvitation.Status.PENDING:
            return Response(
                {'error': 'Can only resend pending invitations'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # In production, this would trigger an email
        # For now, just return the token
        return Response({
            'message': 'Invitation resent',
            'token': invitation.token
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a pending invitation.
        """
        invitation = self.get_object()
        
        if invitation.status != PracticeInvitation.Status.PENDING:
            return Response(
                {'error': 'Can only cancel pending invitations'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invitation.status = PracticeInvitation.Status.DECLINED
        invitation.save()
        
        return Response({
            'message': 'Invitation cancelled'
        }, status=status.HTTP_200_OK)
    
    def has_admin_permission(self, user):
        """Check if user is admin of active practice."""
        if not user.active_practice:
            return False
        
        membership = user.practice_memberships.filter(
            practice=user.active_practice,
            role=User.Role.ADMIN,
            is_active=True
        ).exists()
        
        return membership


class UserProfileView(APIView):
    """
    Get and update user profile.
    
    GET /api/auth/profile/
    PUT /api/auth/profile/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            
            # Log profile update
            if request.user.active_practice:
                AuditLog.objects.create(
                    user=request.user,
                    practice=request.user.active_practice,
                    action=AuditLog.Action.UPDATE,
                    resource_type='UserProfile',
                    resource_id=str(request.user.id),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    request_path=request.path
                )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PracticeMembersView(APIView):
    """
    List practice members (admin only).
    
    GET /api/auth/practice-members/
    """
    permission_classes = [permissions.IsAuthenticated, IsPracticeAdmin]
    
    def get(self, request):
        if not request.user.active_practice:
            return Response(
                {'error': 'No active practice set'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        memberships = PracticeMembership.objects.filter(
            practice=request.user.active_practice,
            is_active=True
        ).select_related('user', 'therapist')
        
        members = []
        for membership in memberships:
            members.append({
                'id': membership.user.id,
                'username': membership.user.username,
                'email': membership.user.email,
                'name': f"{membership.user.first_name} {membership.user.last_name}",
                'role': membership.role,
                'is_owner': membership.is_owner,
                'joined_at': membership.joined_at,
                'therapist_id': membership.therapist.id if membership.therapist else None
            })
        
        return Response({
            'practice': {
                'id': request.user.active_practice.id,
                'name': request.user.active_practice.name
            },
            'members': members,
            'total': len(members)
        }, status=status.HTTP_200_OK)