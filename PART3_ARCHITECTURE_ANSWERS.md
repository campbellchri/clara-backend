# Part 3: Architecture Questions

## 1. Multi-Tenancy Approach

**Decision: Single Database with Row-Level Isolation**

Every table includes `practice_id` or foreignKey to practice for tenant isolation:
- ✅ Simple operations (one backup, one migration)
- ✅ Cost-effective for startup
- ✅ Django-friendly pattern
- ⚠️ Requires careful query filtering at application level

**Implementation:**
```python
# Middleware sets tenant context
class TenantMiddleware:
    def __call__(self, request):
        if request.user.active_practice:
            _thread_locals.practice_id = request.user.active_practice_id

# All models filtered by practice
class Session(models.Model):
    practice = models.ForeignKey(Practice, on_delete=models.CASCADE)
```

For additional security, can add PostgreSQL RLS policies.

## 2. HIPAA/SOC 2 Compliance

**Implemented Technical Controls:**

### Access Control
```python
# Role-based permissions
@permission_classes([IsAuthenticated, CanSubmitClaims])
def submit_claim(request): ...
```

### Audit Logging
```python
AuditLog.objects.create(
    user=request.user,
    action='VIEW',
    resource_type='Patient',
    accessed_phi=True,
    ip_address=request.META['REMOTE_ADDR']
)
```

### Encryption
- **Transit**: HTTPS only (enforce at load balancer)
- **Rest**: AWS RDS (or other provider) encryption
- **Tokens**: No passwords in logs, utilize hashes in database, JWT for user tokens

### Additional Measures
- Session timeout (2 hours)
- PHI training flag on users
- Soft deletes for patients
- No PHI in URLs

## 3. Claims Engine Extensibility

**Current: Validator Chain Pattern**

```python
class ClaimPreparationService:
    def __init__(self):
        self.validators = [
            FeeValidator(),
            CPTCodeValidator(), 
            DiagnosisCodeValidator()
        ]
    
    def add_payer_rules(self, payer_id):
        if payer_id == "AETNA":
            self.validators.append(AetnaAuthValidator())
```

**Adding New Payer:**
1. Create payer-specific validator
2. Register in service
3. No core code changes needed

**Future: Rules Engine** (if needed)
```yaml
# External configuration
payer: BCBS
rules:
  - field: cpt_code
    value: "90837"
    requires: prior_auth
```

## 4. EHR Integration Strategy

**Recommended: FHIR API with Adapter Pattern**

```python
class EHRAdapter(ABC):
    @abstractmethod
    def get_patient(self, id): pass

class EpicAdapter(EHRAdapter):
    def get_patient(self, id):
        response = requests.get(f"{self.base_url}/Patient/{id}")
        return self.map_to_internal(response.json())

# Factory pattern for multiple EHRs
def get_ehr_adapter(ehr_type):
    return {"epic": EpicAdapter, "cerner": CernerAdapter}[ehr_type]()
```

**Integration Points:**
- **Pull**: Nightly patient demographics sync
- **Push**: Real-time claim status updates
- **Webhooks**: Patient change notifications

## Key Implementation Details

### Authentication (Implemented)
- Token-based auth
- Practice registration flow
- Team invitation system
- Multi-practice support

### Permission System (Implemented)
```python
# Granular role-based access
IsPracticeAdmin     # Full access
IsTherapist        # Own patients only
IsBillingStaff     # Claims management
HasPHITraining     # Required for patient data
```

### Database Schema
- Django default naming (`app_model`)
- Automatic indexes on FKs from django ORM
- JSONB for flexible fields
- UUID primary keys


- Flexible audit log retention, can be improved with observability tool like datadog, telemetry, etc.