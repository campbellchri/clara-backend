"""
Claims API Tests - Therapy Practice Domain
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from claims.models import Practice, Therapist, Patient, Session, Claim
from claims.services import ClaimPreparationService, ClaimStatus
from claims.validators import (
    SessionPayload,
    ClaimValidatorChain,
    FeeValidator,
    CopayValidator,
    CPTCodeValidator,
    ICD10CodeValidator,
    SessionDateValidator,
)


class ValidatorTestCase(TestCase):
    """Test individual validators"""
    
    def setUp(self):
        self.valid_payload = SessionPayload(
            practice_id="practice_123",
            therapist_id="therapist_456",
            patient_id="patient_789",
            session_date=date.today(),
            cpt_code="90837",
            icd10_code="F33.1",
            fee=Decimal("175.00"),
            copay_collected=Decimal("25.00"),
            payer_id="BCBSMA"
        )
    
    def test_fee_validator_positive(self):
        validator = FeeValidator()
        errors = validator.validate(self.valid_payload)
        self.assertEqual(len(errors), 0)
    
    def test_fee_validator_zero(self):
        validator = FeeValidator()
        payload = SessionPayload(
            practice_id="practice_123",
            therapist_id="therapist_456",
            patient_id="patient_789",
            session_date=date.today(),
            cpt_code="90837",
            icd10_code="F33.1",
            fee=Decimal("0.00"),
            copay_collected=Decimal("0.00"),
            payer_id="BCBSMA"
        )
        errors = validator.validate(payload)
        self.assertEqual(len(errors), 1)
        self.assertIn("greater than $0", errors[0])
    
    def test_copay_validator_valid(self):
        validator = CopayValidator()
        errors = validator.validate(self.valid_payload)
        self.assertEqual(len(errors), 0)
    
    def test_copay_validator_exceeds_fee(self):
        validator = CopayValidator()
        payload = SessionPayload(
            practice_id="practice_123",
            therapist_id="therapist_456",
            patient_id="patient_789",
            session_date=date.today(),
            cpt_code="90837",
            icd10_code="F33.1",
            fee=Decimal("175.00"),
            copay_collected=Decimal("200.00"),
            payer_id="BCBSMA"
        )
        errors = validator.validate(payload)
        self.assertEqual(len(errors), 1)
        self.assertIn("cannot exceed", errors[0])
    
    def test_cpt_code_validator_valid(self):
        validator = CPTCodeValidator()
        errors = validator.validate(self.valid_payload)
        self.assertEqual(len(errors), 0)
    
    def test_cpt_code_validator_invalid(self):
        validator = CPTCodeValidator()
        payload = SessionPayload(
            practice_id="practice_123",
            therapist_id="therapist_456",
            patient_id="patient_789",
            session_date=date.today(),
            cpt_code="99999",
            icd10_code="F33.1",
            fee=Decimal("175.00"),
            copay_collected=Decimal("25.00"),
            payer_id="BCBSMA"
        )
        errors = validator.validate(payload)
        self.assertEqual(len(errors), 1)
        self.assertIn("not in the allowed list", errors[0])
    
    def test_icd10_validator_valid(self):
        validator = ICD10CodeValidator()
        errors = validator.validate(self.valid_payload)
        self.assertEqual(len(errors), 0)
    
    def test_icd10_validator_invalid_format(self):
        validator = ICD10CodeValidator()
        payload = SessionPayload(
            practice_id="practice_123",
            therapist_id="therapist_456",
            patient_id="patient_789",
            session_date=date.today(),
            cpt_code="90837",
            icd10_code="123",  # Invalid - starts with number
            fee=Decimal("175.00"),
            copay_collected=Decimal("25.00"),
            payer_id="BCBSMA"
        )
        errors = validator.validate(payload)
        self.assertGreater(len(errors), 0)
    
    def test_session_date_validator_past(self):
        validator = SessionDateValidator()
        payload = SessionPayload(
            practice_id="practice_123",
            therapist_id="therapist_456",
            patient_id="patient_789",
            session_date=date.today() - timedelta(days=1),
            cpt_code="90837",
            icd10_code="F33.1",
            fee=Decimal("175.00"),
            copay_collected=Decimal("25.00"),
            payer_id="BCBSMA"
        )
        errors = validator.validate(payload)
        self.assertEqual(len(errors), 0)
    
    def test_session_date_validator_future(self):
        validator = SessionDateValidator()
        payload = SessionPayload(
            practice_id="practice_123",
            therapist_id="therapist_456",
            patient_id="patient_789",
            session_date=date.today() + timedelta(days=1),
            cpt_code="90837",
            icd10_code="F33.1",
            fee=Decimal("175.00"),
            copay_collected=Decimal("25.00"),
            payer_id="BCBSMA"
        )
        errors = validator.validate(payload)
        self.assertEqual(len(errors), 1)
        self.assertIn("cannot be in the future", errors[0])


class ClaimPreparationServiceTestCase(TestCase):
    """Test the claim preparation service"""
    
    def setUp(self):
        self.service = ClaimPreparationService()
        self.valid_payload = SessionPayload(
            practice_id="practice_123",
            therapist_id="therapist_456",
            patient_id="patient_789",
            session_date=date.today(),
            cpt_code="90837",
            icd10_code="F33.1",
            fee=Decimal("175.00"),
            copay_collected=Decimal("25.00"),
            payer_id="BCBSMA"
        )
    
    def test_prepare_valid_claim(self):
        claim = self.service.prepare_claim(self.valid_payload)
        
        self.assertEqual(claim.status, ClaimStatus.READY_FOR_SUBMISSION)
        self.assertEqual(len(claim.validation_errors), 0)
        self.assertEqual(claim.patient_id, "patient_789")
        self.assertEqual(claim.provider_id, "therapist_456")
        self.assertEqual(claim.practice_id, "practice_123")
        self.assertEqual(claim.charge_amount, 175.00)
        self.assertEqual(claim.copay_amount, 25.00)
        self.assertIsNotNone(claim.claim_id)
        self.assertTrue(claim.claim_id.startswith("CLM-"))
    
    def test_prepare_invalid_claim(self):
        invalid_payload = SessionPayload(
            practice_id="practice_123",
            therapist_id="therapist_456",
            patient_id="patient_789",
            session_date=date.today(),
            cpt_code="99999",  # Invalid CPT code
            icd10_code="F33.1",
            fee=Decimal("0.00"),  # Invalid fee
            copay_collected=Decimal("25.00"),
            payer_id="BCBSMA"
        )
        
        claim = self.service.prepare_claim(invalid_payload)
        
        self.assertEqual(claim.status, ClaimStatus.INVALID)
        self.assertGreater(len(claim.validation_errors), 0)
        self.assertFalse(claim.is_valid())
    
    def test_claim_enrichment(self):
        claim = self.service.prepare_claim(self.valid_payload)
        
        # Check that enrichment fields are populated
        self.assertIsNotNone(claim.patient_name)
        self.assertIsNotNone(claim.provider_npi)
        self.assertIsNotNone(claim.practice_npi)
        self.assertIsNotNone(claim.practice_tax_id)


class ClaimAPITestCase(APITestCase):
    """Test the claim preparation API endpoints"""
    
    def setUp(self):
        # Create test data
        self.practice = Practice.objects.create(
            id="practice_123",
            name="Test Therapy Practice",
            npi="1234567890",
            tax_id="XX-XXXXXXX",
            address_line1="123 Main St",
            city="Boston",
            state="MA",
            zip_code="02101"
        )
        
        self.therapist = Therapist.objects.create(
            id="therapist_456",
            practice=self.practice,
            first_name="Jane",
            last_name="Smith",
            npi="0987654321",
            license_number="PSY12345",
            license_state="MA",
            email="jane.smith@therapy.com"
        )
        
        self.patient = Patient.objects.create(
            id="patient_789",
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1990, 1, 1),
            member_id="MEM123456",
            payer_id="BCBSMA"
        )
    
    def test_prepare_claim_success(self):
        """Test successful claim preparation"""
        url = '/api/v1/claims/prepare'
        data = {
            "practice_id": "practice_123",
            "therapist_id": "therapist_456",
            "patient_id": "patient_789",
            "session_date": str(date.today()),
            "cpt_code": "90837",
            "icd10_code": "F33.1",
            "fee": 175.00,
            "copay_collected": 25.00,
            "payer_id": "BCBSMA"
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'READY_FOR_SUBMISSION')
        self.assertIn('claim_id', response.data)
        self.assertEqual(response.data['charge_amount'], 175.00)
        self.assertEqual(response.data['copay_amount'], 25.00)
        self.assertEqual(len(response.data['validation_errors']), 0)
    
    def test_prepare_claim_validation_error(self):
        """Test claim preparation with validation errors"""
        url = '/api/v1/claims/prepare'
        data = {
            "practice_id": "practice_123",
            "therapist_id": "therapist_456",
            "patient_id": "patient_789",
            "session_date": str(date.today()),
            "cpt_code": "99999",  # Invalid CPT code
            "icd10_code": "F33.1",
            "fee": 175.00,
            "copay_collected": 200.00,  # Exceeds fee
            "payer_id": "BCBSMA"
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data['status'], 'INVALID')
        self.assertGreater(len(response.data['validation_errors']), 0)
    
    def test_prepare_claim_missing_fields(self):
        """Test claim preparation with missing required fields"""
        url = '/api/v1/claims/prepare'
        data = {
            "practice_id": "practice_123",
            # Missing required fields
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'INVALID')
        self.assertIn('validation_errors', response.data)
    
    def test_health_check(self):
        """Test health check endpoint"""
        url = '/api/v1/claims/health'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
        self.assertEqual(response.data['service'], 'clara-claims-api')


class ModelTestCase(TestCase):
    """Test Django models for therapy practice domain"""
    
    def setUp(self):
        self.practice = Practice.objects.create(
            name="Test Practice",
            npi="1234567890",
            tax_id="XX-XXXXXXX",
            address_line1="123 Main St",
            city="Boston",
            state="MA",
            zip_code="02101"
        )
    
    def test_create_therapist(self):
        therapist = Therapist.objects.create(
            practice=self.practice,
            first_name="Jane",
            last_name="Smith",
            npi="0987654321",
            license_number="PSY12345",
            license_state="MA",
            email="jane@therapy.com"
        )
        
        self.assertEqual(str(therapist), "Jane Smith")
        self.assertEqual(therapist.practice, self.practice)
        self.assertTrue(therapist.is_active)
    
    def test_create_patient(self):
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1990, 1, 1),
            member_id="MEM123456",
            payer_id="BCBSMA"
        )
        
        self.assertEqual(str(patient), "John Doe")
        self.assertEqual(patient.practice, self.practice)
        self.assertTrue(patient.is_active)
        self.assertIsNone(patient.deleted_at)
    
    def test_create_session(self):
        therapist = Therapist.objects.create(
            practice=self.practice,
            first_name="Jane",
            last_name="Smith",
            npi="0987654321",
            license_number="PSY12345",
            license_state="MA"
        )
        
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1990, 1, 1)
        )
        
        session = Session.objects.create(
            practice=self.practice,
            therapist=therapist,
            patient=patient,
            session_date=date.today(),
            cpt_code="90837",
            icd10_code="F33.1",
            fee=Decimal("175.00"),
            copay_collected=Decimal("25.00"),
            payer_id="BCBSMA",
            status=Session.Status.COMPLETED
        )
        
        self.assertEqual(session.practice, self.practice)
        self.assertEqual(session.therapist, therapist)
        self.assertEqual(session.patient, patient)
        self.assertEqual(session.status, Session.Status.COMPLETED)
    
    def test_create_claim(self):
        therapist = Therapist.objects.create(
            practice=self.practice,
            first_name="Jane",
            last_name="Smith",
            npi="0987654321",
            license_number="PSY12345",
            license_state="MA"
        )
        
        patient = Patient.objects.create(
            practice=self.practice,
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1990, 1, 1)
        )
        
        session = Session.objects.create(
            practice=self.practice,
            therapist=therapist,
            patient=patient,
            session_date=date.today(),
            cpt_code="90837",
            icd10_code="F33.1",
            fee=Decimal("175.00"),
            copay_collected=Decimal("25.00"),
            payer_id="BCBSMA"
        )
        
        claim = Claim.objects.create(
            practice=self.practice,
            session=session,
            claim_number="CLM-12345678",
            payer_id="BCBSMA",
            status=Claim.Status.READY_FOR_SUBMISSION,
            charge_amount=Decimal("175.00"),
            copay_amount=Decimal("25.00")
        )
        
        self.assertEqual(claim.practice, self.practice)
        self.assertEqual(claim.session, session)
        self.assertEqual(str(claim), "Claim CLM-12345678 - ready")
        self.assertEqual(claim.status, Claim.Status.READY_FOR_SUBMISSION)