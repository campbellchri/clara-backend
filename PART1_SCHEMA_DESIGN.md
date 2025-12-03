# Part 1: Data Modeling & Schema Design

## Overview
Relational database schema for a multi-tenant therapy practice claims system using Django ORM with PostgreSQL.

## Core Entities

### 1. Practice (Tenant Root)
```python
claims_practice:
  - id (UUID, PK)
  - name, npi, tax_id
  - address_line1, city, state, zip_code
  - created_at, updated_at
```
**Purpose**: All data is scoped to a practice for multi-tenancy

### 2. Therapist (Provider)
```python
claims_therapist:
  - id (UUID, PK)
  - practice_id (FK → Practice)
  - first_name, last_name, npi
  - license_number, license_state
  - email, phone, is_active
```
**Indexes**: practice_id, unique(practice_id + npi)

### 3. Patient
```python
claims_patient:
  - id (UUID, PK)
  - practice_id (FK → Practice)
  - first_name, last_name, date_of_birth
  - member_id, phone, email
  - is_active
```
**Indexes**: practice_id, (practice_id + date_of_birth)

### 4. Session (Therapy Appointment)
```python
claims_session:
  - id (UUID, PK)
  - practice_id (FK → Practice)
  - therapist_id (FK → Therapist)
  - patient_id (FK → Patient)
  - session_date, cpt_code, duration_minutes
  - fee, copay, diagnosis_codes (JSON)
  - status (scheduled/completed/cancelled)
```
**Indexes**: practice_id, session_date, patient_id, therapist_id

### 5. Claim
```python
claims_claim:
  - id (UUID, PK)
  - practice_id (FK → Practice)
  - session_id (FK → Session)
  - claim_number (unique), payer_id
  - status (draft/ready/submitted/paid/denied)
  - charge_amount, copay_amount, paid_amount
  - submitted_at, validation_errors (JSON)
```
**Indexes**: practice_id, status, session_id

## Authentication & Access Control

### 6. User (Extended Django User)
```python
healthcare_user:
  - Standard Django user fields
  - role (admin/therapist/billing/front_desk)
  - active_practice_id (FK → Practice)
  - is_verified, phi_training_completed
```

### 7. Practice Membership
```python
healthcare_practicemembership:
  - user_id (FK → User)
  - practice_id (FK → Practice)
  - role, is_owner, is_active
  - therapist_id (FK → Therapist, optional)
```
**Unique**: (user_id, practice_id)

### 8. Audit Log (HIPAA Compliance)
```python
healthcare_auditlog:
  - user_id, practice_id
  - action (view/create/update/delete)
  - resource_type, resource_id
  - accessed_phi, ip_address, created_at
```

## Supporting Models

- **members_insurancecoverage**: Patient insurance details
- **providers_networkstatus**: Therapist-payer network status  
- **analytics_practicesummary**: Daily practice metrics

## Key Design Decisions

### Multi-Tenancy
- **Row-level isolation**: Every table has practice_id
- **Middleware enforcement**: Automatic filtering by active practice
- **No shared data**: Complete isolation between practices

### Data Flow
```
Session (completed) → Validation → Claim Generation → Payer Submission
```

### Security
- UUID primary keys (no enumeration)
- Audit logging for PHI access
- Role-based permissions
- Token authentication

## Scalability Path
1. **Indexes** on foreign keys and common queries
2. **JSONB** for flexible fields (diagnosis codes)
3. **Partitioning** by practice_id when needed
4. **Read replicas** for analytics
5. **Archive old claims** to cold storage