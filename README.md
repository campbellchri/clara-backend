# Clara Healthcare Backend Demo - Claims Processing API

## Founding Engineer Technical Assessment

A therapy practice management system with intelligent claims processing, built with Django REST Framework. This implementation demonstrates production-ready patterns for a HIPAA-compliant, multi-tenant healthcare SaaS platform.

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 14+ (for production) or SQLite (for development)
- Poetry (recommended) or pip

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/campbellchri/clara-backend.git
cd clara-healthcare-backend
```

2. **Install dependencies**

**Option A: Using Poetry (Recommended)**
```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Runserver
python3 manage.py runserver
```

## Core Features

### Authentication & Authorization System ✅

Complete multi-tenant authentication with role-based access control.

#### Practice Registration
```bash
# Register a new practice with admin user
POST /api/v1/auth/register-practice/
{
  "practice_name": "Mindful Therapy Group",
  "tax_id": "12-3456789",
  "npi": "1234567890",
  "address_line1": "123 Main St",
  "city": "San Francisco",
  "state": "CA",
  "zip_code": "94102",
  "username": "admin",
  "email": "admin@mindful.com",
  "password": "SecurePass123!",
  "first_name": "Sarah",
  "last_name": "Johnson"
}
```

#### User Login
```bash
# Login to get authentication token
POST /api/v1/auth/login/
{
  "username": "admin",
  "password": "SecurePass123!"
}

# Response includes token for API access
{
  "token": "9b1d2c3e4f5a6b7c8d9e0f1a2b3c4d5e",
  "user": {...},
  "active_practice": {...}
}
```

#### Invite Team Members
```bash
# Admin can invite team members
POST /api/v1/auth/invitations/
Authorization: Token <admin_token>
{
  "email": "therapist@mindful.com",
  "role": "therapist",
  "message": "Welcome to our practice!"
}
```

### Permission Roles
- **Admin**: Full practice management
- **Therapist**: Manage own patients and sessions
- **Billing**: Submit and manage claims
- **Front Desk**: View schedules, manage appointments

### Part 2: Claims Preparation API ✅

The main endpoint transforms therapy session data into structured claims ready for 837P EDI generation.

#### Endpoint: `POST /api/v1/claims/prepare`

**Request:**
```json
{
  "practice_id": "practice_123",
  "therapist_id": "therapist_456",
  "patient_id": "patient_789",
  "session_date": "2025-11-20",
  "cpt_code": "90837",
  "icd10_code": "F33.1",
  "fee": 175.00,
  "copay_collected": 25.00,
  "payer_id": "BCBSMA"
}
```

**Success Response (200):**
```json
{
  "claim_id": "CLM-A1B2C3D4",
  "patient_id": "patient_789",
  "provider_id": "therapist_456",
  "practice_id": "practice_123",
  "payer_id": "BCBSMA",
  "service_date": "2025-11-20",
  "cpt_code": "90837",
  "icd10_code": "F33.1",
  "charge_amount": 175.00,
  "copay_amount": 25.00,
  "status": "READY_FOR_SUBMISSION",
  "validation_errors": []
}
```

**Validation Error Response (422):**
```json
{
  "status": "INVALID",
  "validation_errors": [
    "Copay ($200.00) cannot exceed total fee ($175.00).",
    "CPT code '99999' is not in the allowed list."
  ]
}
```

### Business Rules Validated

1. **Fee Validation**: Must be greater than $0
2. **Copay Validation**: Cannot exceed total fee, must be non-negative
3. **CPT Code Validation**: Must be from allowed psychotherapy codes list
4. **ICD-10 Format**: Validates proper format (letter + digits)
5. **Date Validation**: Session date cannot be in the future
6. **Payer Validation**: Checks against known payer registry
7. **Practice Access**: User must have active practice membership
8. **Role Permissions**: User must have claims submission permission

### API Documentation

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## Architecture Highlights

### Service Layer Pattern
```python
# Clean separation of concerns
ClaimPreparationService
├── Validates session payload
├── Generates unique claim ID
├── Enriches with entity data
└── Returns PreparedClaim object
```

### Chain of Responsibility for Validation
```python
# Extensible validator chain
ClaimValidatorChain
├── FeeValidator
├── CopayValidator
├── CPTCodeValidator
├── ICD10CodeValidator
└── SessionDateValidator
```

### Multi-Tenancy (Row-Level Security)
- Every model includes `practice_id` foreign key
- PostgreSQL RLS policies enforce tenant isolation
- Middleware sets tenant context per request

## Testing

### Run All Tests
```bash
# With Poetry
poetry run python manage.py test
```

### Test Authentication Flow
```bash
# Test complete registration and login flow
poetry run python test_full_auth.py
```

### Test Claims Workflow
```bash
# Test end-to-end claims submission
poetry run python test_workflow.py
```

### Run Specific Test Suites
```bash
# Authentication tests
poetry run python manage.py test healthcare.tests

# Claims processing tests
poetry run python manage.py test claims.tests

# Validator tests
poetry run pytest claims/tests.py -k "test_validator"
```

### Test Coverage Goals
- Unit Tests: 90%+ coverage
- Integration Tests: All API endpoints
- Validator Tests: All business rules

## Project Structure

```
clara-healthcare-backend/
├── config/                # Django configuration
│   ├── settings.py       # Main settings file
│   ├── urls.py          # Root URL configuration
│   └── wsgi.py          # WSGI application
├── claims/               # Claims processing module
│   ├── models.py        # Practice, Therapist, Patient, Session, Claim
│   ├── serializers.py   # DRF serializers
│   ├── views.py         # Claims API endpoints
│   ├── services.py      # Business logic layer
│   ├── validators.py    # Validation chain
│   └── tests.py         # Claims test suite
├── healthcare/          # Authentication & core
│   ├── auth_models.py   # User, PracticeMembership, AuditLog
│   ├── auth_serializers.py # Auth serializers
│   ├── auth_views.py    # Registration, login, invitations
│   ├── permissions.py   # RBAC implementation
│   ├── middleware.py    # Tenant context middleware
│   └── tests.py         # Auth test suite
├── members/             # Patient insurance module
│   └── models.py        # InsuranceCoverage
├── providers/           # Provider network module
│   └── models.py        # NetworkStatus
├── analytics/           # Practice metrics module
│   └── models.py        # PracticeSummary
├── pyproject.toml       # Poetry configuration
├── poetry.lock          # Locked dependencies
├── requirements.txt     # pip dependencies
├── PART1_SCHEMA_DESIGN.md # Database schema
├── PART3_ARCHITECTURE_ANSWERS.md # Architecture decisions
└── README.md            # This file
```

## Technology Stack

- **Framework**: Django 4.2.7 + Django REST Framework 3.14.0
- **Database**: PostgreSQL 14+ (production), SQLite (development)
- **API Documentation**: DRF Spectacular (OpenAPI 3.0)
- **Testing**: pytest + pytest-django
- **Code Quality**: black, isort, flake8, mypy
- **Deployment**: Docker, Gunicorn, Nginx

## Development Workflow

### Code Formatting
```bash
# With Poetry
poetry run black claims/ healthcare/
poetry run isort claims/ healthcare/
poetry run flake8 claims/ healthcare/
poetry run mypy claims/ healthcare/
```

### Database Operations
```bash
# Create new migration after model changes
poetry run python manage.py makemigrations

# Apply migrations
poetry run python manage.py migrate

# Create sample data for testing
poetry run python manage.py shell
>>> from claims.models import Practice
>>> practice = Practice.objects.create(
...     name="Test Practice",
...     npi="1234567890",
...     tax_id="12-3456789"
... )

# Reset database (development only)
poetry run python manage.py flush
```

## Deployment

### Environment Variables
```bash
# .env.production
DEBUG=False
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://user:password@host:5432/clara_db
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=api.clara.health
CORS_ALLOWED_ORIGINS=https://app.clara.health
```

### Docker Deployment
```bash
# Build production image
docker build -t clara-backend:latest .

# Run with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Health Check
```bash
curl http://localhost:8000/api/v1/claims/health
# Response: {"status": "healthy", "service": "clara-claims-api"}
```

## Security & Compliance

### HIPAA Compliance Features
- ✅ Audit logging for all PHI access (AuditLog model)
- ✅ Encryption at rest and in transit
- ✅ Role-based access control (Admin, Therapist, Billing, Front Desk)
- ✅ Patient data soft deletes (deleted_at field)
- ✅ PHI training tracking (phi_training_completed flag)
- ✅ Session timeout support
- ✅ Token-based authentication

### SOC 2 Readiness
- ✅ Comprehensive logging
- ✅ Security headers (HSTS, CSP, etc.)
- ✅ Rate limiting and DDoS protection
- ✅ Automated vulnerability scanning
- ✅ Incident response procedures

## Performance Optimizations

- Database connection pooling
- Redis caching for frequently accessed data
- Indexed queries on practice_id, dates, status
- Async task processing with Celery
- API response pagination