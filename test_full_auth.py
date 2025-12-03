#!/usr/bin/env python3
"""
Comprehensive test of all authentication endpoints
"""
import json
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_auth_flow():
    """Test complete authentication flow."""
    print("="*60)
    print("CLARA HEALTHCARE - AUTHENTICATION SYSTEM TEST")
    print("="*60)
    
    # 1. Register first practice
    print("\n1. REGISTER PRACTICE")
    print("-" * 40)
    
    timestamp = datetime.now().strftime("%H%M%S")
    practice_data = {
        "practice_name": f"Test Practice {timestamp}",
        "tax_id": f"99-{timestamp}",
        "npi": f"11{timestamp[:8]}",
        "address": "123 Test Street",
        "city": "San Francisco",
        "state": "CA",
        "zip_code": "94102",
        "username": f"admin_{timestamp}",
        "email": f"admin_{timestamp}@test.com",
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "Admin"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/register-practice/",
        json=practice_data
    )
    
    assert response.status_code == 201, f"Registration failed: {response.text}"
    data = response.json()
    token1 = data['token']
    practice1_id = data['practice']['id']
    user1_id = data['user']['id']
    
    print(f"✅ Practice registered: {data['practice']['name']}")
    print(f"✅ Admin user: {data['user']['username']}")
    print(f"✅ Token received: {token1[:20]}...")
    
    # 2. Test login
    print("\n2. TEST LOGIN")
    print("-" * 40)
    
    login_data = {
        "username": practice_data["username"],
        "password": practice_data["password"]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login/",
        json=login_data
    )
    
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert data['token'] == token1, "Token mismatch"
    print(f"✅ Login successful")
    print(f"✅ Active practice: {data['user']['active_practice_name']}")
    
    # 3. Get user profile
    print("\n3. USER PROFILE")
    print("-" * 40)
    
    headers = {"Authorization": f"Token {token1}"}
    response = requests.get(
        f"{BASE_URL}/api/v1/auth/profile/",
        headers=headers
    )
    
    assert response.status_code == 200, f"Profile fetch failed: {response.text}"
    profile = response.json()
    print(f"✅ User: {profile['first_name']} {profile['last_name']}")
    print(f"✅ Role: {profile['role']}")
    print(f"✅ Practices: {len(profile['practices'])}")
    
    # 4. Create invitation
    print("\n4. INVITATION SYSTEM")
    print("-" * 40)
    
    invitation_data = {
        "email": f"therapist_{timestamp}@test.com",
        "role": "therapist",
        "message": "Welcome to our practice!"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/invitations/",
        json=invitation_data,
        headers=headers
    )
    
    assert response.status_code == 201, f"Invitation failed: {response.text}"
    invitation = response.json()
    invitation_token = invitation['invitation']['token']
    print(f"✅ Invitation sent to: {invitation['invitation']['email']}")
    print(f"✅ Role: {invitation['invitation']['role']}")
    print(f"✅ Token: {invitation_token[:20]}...")
    
    # 5. Accept invitation (new user)
    print("\n5. ACCEPT INVITATION")
    print("-" * 40)
    
    accept_data = {
        "token": invitation_token,
        "username": f"therapist_{timestamp}",
        "password": "TherapistPass123!",
        "first_name": "Test",
        "last_name": "Therapist"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/invitations/accept/",
        json=accept_data
    )
    
    assert response.status_code == 200, f"Accept failed: {response.text}"
    data = response.json()
    therapist_token = data['token']
    print(f"✅ Therapist joined: {data['user']['username']}")
    print(f"✅ Practice: {data['practice']['name']}")
    
    # 6. View practice members (admin only)
    print("\n6. PRACTICE MEMBERS")
    print("-" * 40)
    
    response = requests.get(
        f"{BASE_URL}/api/v1/auth/practice-members/",
        headers=headers  # Admin token
    )
    
    assert response.status_code == 200, f"Members fetch failed: {response.text}"
    members_data = response.json()
    print(f"✅ Practice: {members_data['practice']['name']}")
    print(f"✅ Total members: {members_data['total']}")
    for member in members_data['members']:
        print(f"   - {member['name']} ({member['role']})")
    
    # 7. Test logout
    print("\n7. LOGOUT")
    print("-" * 40)
    
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/logout/",
        headers=headers
    )
    
    assert response.status_code == 200, f"Logout failed: {response.text}"
    print("✅ Logout successful")
    
    # 8. Test protected endpoint with therapist token
    print("\n8. CLAIMS API WITH AUTH")
    print("-" * 40)
    
    claim_data = {
        "practice_id": practice1_id,
        "therapist_id": "test_therapist",
        "patient_id": "test_patient",
        "session_date": "2024-01-20",
        "cpt_code": "90834",
        "icd10_code": "F41.1",
        "fee": 150.00,
        "copay": 25.00,
        "payer_id": "BCBS001"
    }
    
    # Without auth (should work since claims endpoint doesn't require auth yet)
    response = requests.post(
        f"{BASE_URL}/api/v1/claims/prepare",
        json=claim_data
    )
    
    assert response.status_code == 200, f"Claim preparation failed: {response.text}"
    claim = response.json()
    print(f"✅ Claim prepared: {claim['claim_id']}")
    print(f"✅ Status: {claim['status']}")
    
    print("\n" + "="*60)
    print("✅ ALL AUTHENTICATION TESTS PASSED!")
    print("="*60)
    print("\nAPI Endpoints Available:")
    print("  • POST /api/v1/auth/register-practice/ - Register new practice")
    print("  • POST /api/v1/auth/login/ - User login")
    print("  • POST /api/v1/auth/logout/ - User logout")
    print("  • GET  /api/v1/auth/profile/ - Get user profile")
    print("  • POST /api/v1/auth/invitations/ - Send invitation")
    print("  • POST /api/v1/auth/invitations/accept/ - Accept invitation")
    print("  • GET  /api/v1/auth/practice-members/ - List members")
    print("  • POST /api/v1/auth/switch-practice/ - Switch active practice")
    print("\nView API docs at: http://localhost:8000/api/docs/")

if __name__ == "__main__":
    test_auth_flow()