"""
Authentication and Multi-Tenancy Serializers

Handles user registration, practice creation, and invitation workflows.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.db import transaction
from .auth_models import User, PracticeMembership, PracticeInvitation
from claims.models import Practice


class PracticeRegistrationSerializer(serializers.Serializer):
    """
    Handles practice registration with initial admin user.
    """
    # Practice fields
    practice_name = serializers.CharField(max_length=200)
    tax_id = serializers.CharField(max_length=20)
    npi = serializers.CharField(max_length=10)
    
    # Practice address
    address = serializers.CharField(max_length=200)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=2)
    zip_code = serializers.CharField(max_length=10)
    
    # Admin user fields
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value
    
    def validate_tax_id(self, value):
        if Practice.objects.filter(tax_id=value).exists():
            raise serializers.ValidationError("Practice with this Tax ID already exists")
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        # Extract user data
        user_data = {
            'username': validated_data.pop('username'),
            'email': validated_data.pop('email'),
            'password': validated_data.pop('password'),
            'first_name': validated_data.pop('first_name'),
            'last_name': validated_data.pop('last_name'),
            'role': User.Role.ADMIN,
        }
        
        # Create practice
        practice = Practice.objects.create(
            name=validated_data['practice_name'],
            tax_id=validated_data['tax_id'],
            npi=validated_data['npi'],
            address_line1=validated_data['address'],
            city=validated_data['city'],
            state=validated_data['state'],
            zip_code=validated_data['zip_code']
        )
        
        # Create admin user
        user = User.objects.create_user(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            role=user_data['role'],
            active_practice=practice,
            is_verified=True
        )
        
        # Create practice membership
        PracticeMembership.objects.create(
            user=user,
            practice=practice,
            role=User.Role.ADMIN,
            is_owner=True,
            is_active=True
        )
        
        return {
            'practice': practice,
            'user': user
        }


class InvitationCreateSerializer(serializers.ModelSerializer):
    """
    Create invitations for new practice members.
    """
    class Meta:
        model = PracticeInvitation
        fields = ['email', 'role', 'message']
    
    def validate_role(self, value):
        if value == User.Role.ADMIN:
            # Check if user is owner
            user = self.context['request'].user
            membership = user.practice_memberships.filter(
                practice=user.active_practice,
                is_owner=True
            ).first()
            if not membership:
                raise serializers.ValidationError("Only practice owners can invite admins")
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        practice = user.active_practice
        
        if not practice:
            raise serializers.ValidationError("No active practice set")
        
        # Check for existing invitation
        existing = PracticeInvitation.objects.filter(
            practice=practice,
            email=validated_data['email'],
            status=PracticeInvitation.Status.PENDING
        ).first()
        
        if existing:
            raise serializers.ValidationError("Invitation already sent to this email")
        
        # Create invitation
        invitation = PracticeInvitation.objects.create(
            practice=practice,
            email=validated_data['email'],
            role=validated_data['role'],
            message=validated_data.get('message', ''),
            invited_by=user
        )
        
        return invitation


class InvitationAcceptSerializer(serializers.Serializer):
    """
    Accept a practice invitation.
    """
    token = serializers.CharField()
    
    # For new users
    username = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True, required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    
    def validate_token(self, value):
        try:
            self.invitation = PracticeInvitation.objects.get(
                token=value,
                status=PracticeInvitation.Status.PENDING
            )
        except PracticeInvitation.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired invitation")
        
        if self.invitation.is_expired():
            self.invitation.status = PracticeInvitation.Status.EXPIRED
            self.invitation.save()
            raise serializers.ValidationError("Invitation has expired")
        
        return value
    
    def validate(self, data):
        # Check if user exists
        user = self.context.get('request').user if self.context.get('request') else None
        
        if user and user.is_authenticated:
            # Existing user accepting invitation
            if self.invitation.email != user.email:
                raise serializers.ValidationError("Invitation was sent to a different email")
        else:
            # New user - require registration fields
            required_fields = ['username', 'password', 'first_name', 'last_name']
            missing_fields = [f for f in required_fields if not data.get(f)]
            if missing_fields:
                raise serializers.ValidationError(f"Missing fields for new user: {missing_fields}")
            
            # Validate username uniqueness
            if User.objects.filter(username=data['username']).exists():
                raise serializers.ValidationError("Username already exists")
        
        return data
    
    @transaction.atomic
    def save(self):
        user = self.context.get('request').user if self.context.get('request') else None
        
        if not user or not user.is_authenticated:
            # Create new user
            user = User.objects.create_user(
                username=self.validated_data['username'],
                email=self.invitation.email,
                password=self.validated_data['password'],
                first_name=self.validated_data['first_name'],
                last_name=self.validated_data['last_name'],
                role=self.invitation.role,
                is_verified=True
            )
        
        # Accept invitation and create membership
        membership = self.invitation.accept(user)
        
        return {
            'user': user,
            'membership': membership,
            'practice': self.invitation.practice
        }


class UserSerializer(serializers.ModelSerializer):
    """
    User details with practice information.
    """
    practices = serializers.SerializerMethodField()
    active_practice_name = serializers.CharField(source='active_practice.name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'is_verified', 'phi_training_completed',
            'active_practice', 'active_practice_name', 'practices'
        ]
        read_only_fields = ['id', 'is_verified']
    
    def get_practices(self, obj):
        memberships = obj.practice_memberships.filter(is_active=True)
        return [
            {
                'id': m.practice.id,
                'name': m.practice.name,
                'role': m.role,
                'is_owner': m.is_owner
            }
            for m in memberships
        ]


class LoginSerializer(serializers.Serializer):
    """
    User login with practice selection.
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    practice_id = serializers.UUIDField(required=False)
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled")
        
        # Handle practice selection
        if data.get('practice_id'):
            if not user.has_practice_access(data['practice_id']):
                raise serializers.ValidationError("You don't have access to this practice")
            user.active_practice_id = data['practice_id']
            user.save()
        elif not user.active_practice:
            # Set first available practice as active
            first_membership = user.practice_memberships.filter(is_active=True).first()
            if first_membership:
                user.active_practice = first_membership.practice
                user.save()
        
        data['user'] = user
        return data


class PracticeSwitchSerializer(serializers.Serializer):
    """
    Switch active practice for multi-practice users.
    """
    practice_id = serializers.UUIDField()
    
    def validate_practice_id(self, value):
        user = self.context['request'].user
        if not user.has_practice_access(value):
            raise serializers.ValidationError("You don't have access to this practice")
        return value
    
    def save(self):
        user = self.context['request'].user
        user.active_practice_id = self.validated_data['practice_id']
        user.save()
        return user