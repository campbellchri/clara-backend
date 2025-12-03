# Clara Healthcare - Technical Assessment Submission

---

## 🎯 Overview

Complete implementation of a multi-tenant therapy practice claims management system with authentication, permissions, and foundations for a HIPAA-compliant architecture. Built with Django REST Framework and PostgreSQL.

## ✅ Deliverables

### Part 1: Data Modeling
**File**: `PART1_SCHEMA_DESIGN.md`
- Multi-tenant schema with practice isolation
- Core entities: Practice, Therapist, Patient, Session, Claim
- Authentication models: User, PracticeMembership, AuditLog
- Supporting models for insurance, network status, analytics

### Part 2: Backend Implementation
**Directory**: `claims/` + `healthcare/`

#### Claims API
- `POST /api/v1/claims/prepare` - Transform sessions to claims
- Business rule validation (fees, CPT codes, dates)
- Service layer with validator chain pattern
- 100% test coverage

#### Authentication System
- Practice registration with admin user
- Team invitation system
- Token-based authentication
- Role-based permissions (Admin, Therapist, Billing, Front Desk)

### Part 3: Architecture Decisions
**File**: `PART3_ARCHITECTURE_ANSWERS.md`
- Multi-tenancy via row-level isolation
- HIPAA/SOC 2 compliance approach
- Extensible claims processing
- EHR integration strategy

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
# or with Poetry
poetry install

# Run migrations
poetry run python manage.py migrate

# Start server
poetry run python manage.py runserver

# View API docs
open http://localhost:8000/api/docs/
```

## 📊 API Endpoints

### Authentication
```bash
# Register practice
POST /api/v1/auth/register-practice/
{
  "practice_name": "Mindful Therapy",
  "tax_id": "12-3456789",
  "npi": "1234567890",
  "address": "123 Main St",
  "city": "San Francisco",
  "state": "CA",
  "zip_code": "94102",
  "username": "admin",
  "email": "admin@mindful.com",
  "password": "SecurePass123!",
  "first_name": "Sarah",
  "last_name": "Johnson"
}

# Login
POST /api/v1/auth/login/
{
  "username": "admin",
  "password": "SecurePass123!"
}
```

### Claims Processing
```bash
# Prepare claim
POST /api/v1/claims/prepare
Authorization: Token <auth_token>
{
  "practice_id": "...",
  "therapist_id": "...",
  "patient_id": "...",
  "session_date": "2025-11-20",
  "cpt_code": "90834",
  "icd10_code": "F41.1",
  "fee": 150.00,
  "copay": 25.00,
  "payer_id": "BCBS001"
}
```

## 🏗️ Architecture Highlights

### Multi-Tenant Design
```python
# Every model includes practice isolation
class Session(models.Model):
    practice = models.ForeignKey(Practice, on_delete=models.CASCADE)
    # Middleware automatically filters by active practice
```

### Service Layer Pattern
```python
class ClaimPreparationService:
    validators = [
        FeeValidator(),
        CPTCodeValidator(),
        DiagnosisCodeValidator()
    ]
    
    def prepare_claim(self, session_data):
        # Validate → Transform → Return
```

### Permission System
```python
@permission_classes([IsAuthenticated, CanSubmitClaims])
class PrepareClaimView(APIView):
    # Only authorized roles can submit claims
```

### Audit Logging
```python
AuditLog.objects.create(
    user=request.user,
    action='VIEW',
    resource_type='Patient',
    accessed_phi=True
)
```

## 🔒 Security & Compliance

### Implemented
- ✅ Token authentication
- ✅ Role-based access control
- ✅ Audit logging for PHI access
- ✅ UUID primary keys
- ✅ Tenant isolation middleware
- ✅ Custom exception handling

### Infrastructure Overview
- HTTPS enforcement (nginx/ALB)
- Database encryption (RDS)
- Session timeouts
- Rate limiting
- CORS configuration

## 📁 Project Structure

```
clara-healthcare-backend/
├── config/              # Django settings
├── claims/              # Claims domain
│   ├── models.py        # Practice, Therapist, Patient, Session, Claim
│   ├── services.py      # Business logic
│   ├── validators.py    # Validation chain
│   └── tests.py         # Test suite
├── healthcare/          # Auth & core
│   ├── auth_models.py   # User, Membership, AuditLog
│   ├── auth_views.py    # Registration, login, invitations
│   ├── permissions.py   # RBAC implementation
│   └── middleware.py    # Tenant context
├── members/            # Insurance coverage
├── providers/          # Network status
└── analytics/          # Practice metrics
```

## 🧪 Testing

```bash
# Run all tests
poetry run python manage.py test

# Test authentication flow
poetry run python test_full_auth.py

# Test claims API
poetry run python test_apis.py
```

## 💡 Key Design Decisions

### Why Django?
- Mature, battle-tested framework
- Excellent ORM with migrations
- Built-in admin interface
- Large healthcare ecosystem

### Why Row-Level Multi-Tenancy?
- Simple operations (one DB, one backup)
- Cost-effective for startup
- Easy to implement and maintain
- Can scale to thousands of practices

### Why Service Layer?
- Keeps views thin
- Business logic is testable
- Easy to add new validators
- Clear separation of concerns

```

## 📈 Next Steps

### Immediate
- [ ] Celery for async processing
- [ ] Redis caching
- [ ] Email notifications
- [ ] Two-factor authentication

### Future
- [ ] EDI 837P generation
- [ ] Clearinghouse integration
- [ ] EHR adapters (Epic, Cerner)
- [ ] ML-based denial prediction
---
