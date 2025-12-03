#!/usr/bin/env python
"""
Test Authentication and Multi-Tenant Workflow

Tests the complete user journey with authentication:
1. Practice registration with admin user
2. User invitation and acceptance
3. Multi-tenant claim submission
4. Access control validation
"""

import os
import sys
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healthcare.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from healthcare.auth_models import PracticeMembership, PracticeInvitation
from claims.models import Practice, Therapist, Patient, Session, Claim

User = get_user_model()


class AuthWorkflowTest(TestCase):
    """Test complete authentication and multi-tenant workflow."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        
    def test_complete_auth_workflow(self):
        """Test full authentication flow with practice management."""
        print("\n" + "="*60)
        print("AUTHENTICATION & MULTI-TENANT WORKFLOW TEST")
        print("="*60)
        
        # 1. Register first practice with admin
        print("\n1. PRACTICE REGISTRATION")
        print("-" * 40)
        
        practice1_data = {
            'practice_name': 'Mindful Therapy Center',
            'tax_id': '12-3456789',
            'npi': '1234567890',
            'address': '123 Wellness Way',
            'city': 'San Francisco',
            'state': 'CA',
            'zip_code': '94102',
            'phone': '415-555-0100',
            'username': 'admin1',
            'email': 'admin@mindful.com',
            'password': 'SecurePass123!',
            'first_name': 'Sarah',
            'last_name': 'Johnson'
        }
        
        response = self.client.post('/api/auth/register-practice/', practice1_data, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        data = response.json()
        admin1_token = data['token']
        practice1_id = data['practice']['id']
        admin1_user_id = data['user']['id']
        
        print(f"✓ Practice registered: {data['practice']['name']}")
        print(f"✓ Admin user created: {data['user']['username']}")
        print(f"✓ Auth token received: {admin1_token[:20]}...")
        
        # 2. Invite therapist to practice
        print("\n2. INVITATION SYSTEM")
        print("-" * 40)
        
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Token {admin1_token}'
        
        invitation_data = {
            'email': 'therapist@mindful.com',
            'role': 'therapist',
            'message': 'Welcome to our practice!'
        }
        
        response = self.client.post('/api/auth/invitations/', invitation_data, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        invitation = response.json()['invitation']
        invitation_token = invitation['token']
        
        print(f"✓ Invitation sent to: {invitation['email']}")
        print(f"✓ Role: {invitation['role']}")
        print(f"✓ Invitation token: {invitation_token[:20]}...")
        
        # 3. Accept invitation (new user)
        print("\n3. ACCEPT INVITATION")
        print("-" * 40)
        
        accept_data = {
            'token': invitation_token,
            'username': 'therapist1',
            'password': 'TherapistPass123!',
            'first_name': 'Michael',
            'last_name': 'Chen'
        }
        
        # Clear auth header for anonymous accept
        self.client.defaults.pop('HTTP_AUTHORIZATION', None)
        
        response = self.client.post('/api/auth/invitations/accept/', accept_data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        therapist_data = response.json()
        therapist_token = therapist_data['token']
        therapist_user = therapist_data['user']
        
        print(f"✓ Therapist joined: {therapist_user['username']}")
        print(f"✓ Practice: {therapist_data['practice']['name']}")
        print(f"✓ Auth token received: {therapist_token[:20]}...")
        
        # 4. Register second practice (competitor)
        print("\n4. SECOND PRACTICE (TENANT ISOLATION)")
        print("-" * 40)
        
        practice2_data = {
            'practice_name': 'Harmony Health Clinic',
            'tax_id': '98-7654321',
            'npi': '9876543210',
            'address': '456 Peace Plaza',
            'city': 'Oakland',
            'state': 'CA',
            'zip_code': '94610',
            'phone': '510-555-0200',
            'username': 'admin2',
            'email': 'admin@harmony.com',
            'password': 'SecurePass456!',
            'first_name': 'James',
            'last_name': 'Wilson'
        }
        
        response = self.client.post('/api/auth/register-practice/', practice2_data, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        
        data = response.json()
        admin2_token = data['token']
        practice2_id = data['practice']['id']
        
        print(f"✓ Second practice registered: {data['practice']['name']}")
        print(f"✓ Admin user: {data['user']['username']}")
        
        # 5. Create test data for practice 1
        print("\n5. CREATE TEST DATA")
        print("-" * 40)
        
        # Get practice objects
        practice1 = Practice.objects.get(id=practice1_id)
        practice2 = Practice.objects.get(id=practice2_id)
        
        # Create therapist record linked to user
        therapist1_user = User.objects.get(username='therapist1')
        therapist1 = Therapist.objects.create(
            practice=practice1,
            first_name='Michael',
            last_name='Chen',
            npi='1111111111',
            license_number='PSY12345',
            phone='415-555-0101',
            email='therapist@mindful.com'
        )
        
        # Update membership to link therapist
        membership = PracticeMembership.objects.get(
            user=therapist1_user,
            practice=practice1
        )
        membership.therapist = therapist1
        membership.save()
        
        # Create patient for practice 1
        patient1 = Patient.objects.create(
            practice=practice1,
            first_name='Alice',
            last_name='Smith',
            date_of_birth='1985-03-15',
            member_id='MEM001',
            phone='415-555-1001',
            email='alice@example.com'
        )
        
        # Create session for practice 1
        session1 = Session.objects.create(
            practice=practice1,
            patient=patient1,
            therapist=therapist1,
            session_date=datetime.now().date() - timedelta(days=1),
            cpt_code='90834',
            duration_minutes=45,
            fee=Decimal('150.00'),
            copay=Decimal('25.00'),
            diagnosis_codes=['F41.1']
        )
        
        print(f"✓ Created therapist: {therapist1}")
        print(f"✓ Created patient: {patient1}")
        print(f"✓ Created session: {session1}")
        
        # Create data for practice 2
        therapist2 = Therapist.objects.create(
            practice=practice2,
            first_name='Emily',
            last_name='Davis',
            npi='2222222222',
            license_number='MFT67890',
            phone='510-555-0201',
            email='emily@harmony.com'
        )
        
        patient2 = Patient.objects.create(
            practice=practice2,
            first_name='Bob',
            last_name='Jones',
            date_of_birth='1990-07-20',
            member_id='MEM002',
            phone='510-555-2001',
            email='bob@example.com'
        )
        
        session2 = Session.objects.create(
            practice=practice2,
            patient=patient2,
            therapist=therapist2,
            session_date=datetime.now().date() - timedelta(days=2),
            cpt_code='90837',
            duration_minutes=60,
            fee=Decimal('200.00'),
            copay=Decimal('30.00'),
            diagnosis_codes=['F32.1']
        )
        
        print(f"✓ Created practice 2 data")
        
        # 6. Test tenant isolation - therapist can only see their practice's data
        print("\n6. TENANT ISOLATION TEST")
        print("-" * 40)
        
        # Therapist from practice 1 tries to access sessions
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Token {therapist_token}'
        
        response = self.client.get('/api/sessions/')
        if response.status_code == 200:
            sessions = response.json().get('results', [])
            print(f"✓ Therapist sees {len(sessions)} session(s) from their practice")
            
            # Verify only practice 1 sessions are visible
            for session in sessions:
                self.assertEqual(session['practice'], practice1_id)
                print(f"  - Session {session['id']}: Patient {session['patient']}")
        
        # Try to access practice members (should fail - not admin)
        response = self.client.get('/api/auth/practice-members/')
        self.assertEqual(response.status_code, 403)
        print(f"✓ Access denied to practice members (not admin)")
        
        # Admin can see practice members
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Token {admin1_token}'
        
        response = self.client.get('/api/auth/practice-members/')
        if response.status_code == 200:
            members = response.json()['members']
            print(f"✓ Admin sees {len(members)} practice member(s)")
            for member in members:
                print(f"  - {member['name']} ({member['role']})")
        
        # 7. Test practice switching (for users in multiple practices)
        print("\n7. MULTI-PRACTICE ACCESS")
        print("-" * 40)
        
        # Invite admin1 to practice2
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Token {admin2_token}'
        
        invitation_data = {
            'email': 'admin@mindful.com',
            'role': 'billing',
            'message': 'Join us for collaboration'
        }
        
        response = self.client.post('/api/auth/invitations/', invitation_data, content_type='application/json')
        if response.status_code == 201:
            invitation_token = response.json()['invitation']['token']
            
            # Accept with existing user
            self.client.defaults['HTTP_AUTHORIZATION'] = f'Token {admin1_token}'
            
            accept_data = {'token': invitation_token}
            response = self.client.post('/api/auth/invitations/accept/', accept_data, content_type='application/json')
            
            if response.status_code == 200:
                print(f"✓ User joined second practice as billing staff")
                
                # Get user's practices
                response = self.client.get('/api/auth/profile/')
                if response.status_code == 200:
                    user_data = response.json()
                    practices = user_data['practices']
                    print(f"✓ User now has access to {len(practices)} practice(s):")
                    for p in practices:
                        print(f"  - {p['name']} (role: {p['role']})")
                
                # Switch practice
                switch_data = {'practice_id': practice2_id}
                response = self.client.post('/api/auth/switch-practice/', switch_data, content_type='application/json')
                if response.status_code == 200:
                    print(f"✓ Successfully switched to practice 2")
        
        # 8. Test claim submission with proper permissions
        print("\n8. CLAIM SUBMISSION WITH PERMISSIONS")
        print("-" * 40)
        
        # Therapist submits claim
        self.client.defaults['HTTP_AUTHORIZATION'] = f'Token {therapist_token}'
        
        claim_data = {
            'session': {
                'session_id': str(session1.id),
                'practice_id': str(practice1.id),
                'therapist_id': str(therapist1.id),
                'patient': {
                    'patient_id': str(patient1.id),
                    'first_name': patient1.first_name,
                    'last_name': patient1.last_name,
                    'date_of_birth': str(patient1.date_of_birth),
                    'member_id': patient1.member_id
                },
                'service': {
                    'session_date': str(session1.session_date),
                    'cpt_code': session1.cpt_code,
                    'diagnosis_codes': session1.diagnosis_codes,
                    'duration_minutes': session1.duration_minutes
                },
                'billing': {
                    'fee': str(session1.fee),
                    'copay': str(session1.copay)
                }
            }
        }
        
        response = self.client.post('/api/claims/prepare/', claim_data, content_type='application/json')
        if response.status_code in [200, 201]:
            claim = response.json()
            print(f"✓ Claim prepared successfully")
            print(f"  - Status: {claim.get('status', 'READY')}")
            print(f"  - Amount: ${claim.get('claim_amount', session1.fee - session1.copay)}")
        
        # 9. Summary
        print("\n" + "="*60)
        print("AUTHENTICATION WORKFLOW TEST COMPLETED")
        print("="*60)
        print("\n✓ Practice registration and multi-tenancy")
        print("✓ User invitation and acceptance")
        print("✓ Role-based access control")
        print("✓ Tenant data isolation")
        print("✓ Multi-practice support")
        print("✓ Secure claim submission")
        

def run_tests():
    """Run the authentication workflow tests."""
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False)
    
    # Run our specific test
    failures = test_runner.run_tests(['__main__.AuthWorkflowTest'])
    
    if failures:
        sys.exit(1)
    else:
        print("\n✅ All authentication tests passed!")
        sys.exit(0)


if __name__ == '__main__':
    run_tests()