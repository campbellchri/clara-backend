"""
Multi-Tenant Middleware

Implements tenant context isolation and audit logging.
Ensures all database queries are automatically scoped to the correct tenant.
"""
import logging
import uuid
import json
from django.db import connection
from django.utils import timezone
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import AnonymousUser
from threading import local


# Thread-local storage for tenant context
_thread_locals = local()

logger = logging.getLogger(__name__)


def get_current_practice_id():
    """Get the current practice ID from thread-local storage."""
    return getattr(_thread_locals, 'practice_id', None)


class TenantMiddleware:
    """
    Sets tenant context for each request based on user's practice.
    Ensures all queries are automatically filtered by practice.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Initialize tenant context
        self.set_tenant_context(request)
        
        try:
            # Process request with tenant context
            response = self.get_response(request)
        finally:
            # Clear tenant context after request
            self.clear_tenant_context()
        
        return response
    
    def set_tenant_context(self, request):
        """Set the tenant context for the current request."""
        # Clear any existing context
        self.clear_tenant_context()
        
        # Skip for anonymous users
        if isinstance(request.user, AnonymousUser):
            return
        
        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return
        
        # Get practice from user's active practice
        practice_id = None
        if hasattr(request.user, 'active_practice_id'):
            practice_id = request.user.active_practice_id
        elif hasattr(request.user, 'active_practice'):
            if request.user.active_practice:
                practice_id = request.user.active_practice.id
        
        if practice_id:
            # Store in thread locals
            _thread_locals.practice_id = practice_id
            
            # Set PostgreSQL session variable for Row-Level Security
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.current_practice_id = %s",
                    [str(practice_id)]
                )
            
            # Add to request for easy access
            request.practice_id = practice_id
    
    def clear_tenant_context(self):
        """Clear the tenant context."""
        if hasattr(_thread_locals, 'practice_id'):
            del _thread_locals.practice_id


class AuditLoggingMiddleware:
    """
    Logs all data access for HIPAA compliance.
    Tracks who accessed what data and when.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.sensitive_models = [
            'Patient', 'Session', 'Claim', 'MemberCoverage',
            'PatientOutcome', 'EligibilityCheck'
        ]
    
    def __call__(self, request):
        # Generate unique request ID for tracking
        request.audit_id = str(uuid.uuid4())
        
        # Log request start
        self.log_request_start(request)
        
        # Process request
        response = self.get_response(request)
        
        # Log request completion
        self.log_request_end(request, response)
        
        return response
    
    def log_request_start(self, request):
        """Log the start of a request."""
        if self.should_audit(request):
            audit_data = {
                'audit_id': request.audit_id,
                'timestamp': timezone.now().isoformat(),
                'user': self.get_user_info(request),
                'method': request.method,
                'path': request.path,
                'ip_address': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            }
            
            logger.info(f"AUDIT_START: {json.dumps(audit_data)}")
    
    def log_request_end(self, request, response):
        """Log the completion of a request."""
        if self.should_audit(request):
            audit_data = {
                'audit_id': request.audit_id,
                'timestamp': timezone.now().isoformat(),
                'status_code': response.status_code,
                'accessed_records': getattr(request, 'accessed_records', []),
            }
            
            logger.info(f"AUDIT_END: {json.dumps(audit_data)}")
    
    def should_audit(self, request):
        """Determine if request should be audited."""
        # Audit all authenticated requests to sensitive endpoints
        if not request.user.is_authenticated:
            return False
        
        # Check if accessing sensitive data
        path_parts = request.path.split('/')
        for model in self.sensitive_models:
            if model.lower() in [part.lower() for part in path_parts]:
                return True
        
        return False
    
    def get_user_info(self, request):
        """Extract user information for audit log."""
        if request.user.is_authenticated:
            return {
                'id': str(request.user.id),
                'username': request.user.username,
                'email': getattr(request.user, 'email', ''),
                'role': getattr(request.user, 'role', 'unknown'),
                'practice_id': str(getattr(request, 'practice_id', '')),
            }
        return {'anonymous': True}
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RateLimitMiddleware:
    """
    Implements rate limiting to prevent abuse and ensure fair usage.
    Different limits for different user roles.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limits = {
            'anonymous': {'requests': 100, 'period': 3600},  # 100/hour
            'patient': {'requests': 500, 'period': 3600},     # 500/hour
            'therapist': {'requests': 1000, 'period': 3600},  # 1000/hour
            'admin': {'requests': 5000, 'period': 3600},      # 5000/hour
            'api': {'requests': 10000, 'period': 3600},       # 10000/hour for API users
        }
        # In production, use Redis for distributed rate limiting
        self.request_counts = {}
    
    def __call__(self, request):
        # Check rate limit
        if not self.check_rate_limit(request):
            return JsonResponse(
                {'error': 'Rate limit exceeded. Please try again later.'},
                status=429
            )
        
        # Process request
        response = self.get_response(request)
        
        # Add rate limit headers
        self.add_rate_limit_headers(request, response)
        
        return response
    
    def check_rate_limit(self, request):
        """Check if request is within rate limits."""
        user_key = self.get_user_key(request)
        user_type = self.get_user_type(request)
        
        limits = self.rate_limits.get(user_type, self.rate_limits['anonymous'])
        
        # Get current count
        current_count = self.request_counts.get(user_key, 0)
        
        # Check limit
        if current_count >= limits['requests']:
            return False
        
        # Increment counter
        self.request_counts[user_key] = current_count + 1
        
        # In production, use Redis with expiration
        # redis_client.incr(user_key)
        # redis_client.expire(user_key, limits['period'])
        
        return True
    
    def get_user_key(self, request):
        """Generate unique key for rate limiting."""
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        else:
            ip = self.get_client_ip(request)
            return f"ip:{ip}"
    
    def get_user_type(self, request):
        """Determine user type for rate limiting."""
        if not request.user.is_authenticated:
            return 'anonymous'
        
        role = getattr(request.user, 'role', 'patient')
        return role if role in self.rate_limits else 'patient'
    
    def add_rate_limit_headers(self, request, response):
        """Add rate limit information to response headers."""
        user_type = self.get_user_type(request)
        limits = self.rate_limits.get(user_type, self.rate_limits['anonymous'])
        
        response['X-RateLimit-Limit'] = str(limits['requests'])
        response['X-RateLimit-Remaining'] = str(
            limits['requests'] - self.request_counts.get(self.get_user_key(request), 0)
        )
        response['X-RateLimit-Reset'] = str(
            int(timezone.now().timestamp()) + limits['period']
        )
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware:
    """
    Adds security headers for HIPAA and SOC 2 compliance.
    Implements defense in depth strategy.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy
        csp = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response['Content-Security-Policy'] = '; '.join(csp)
        
        # Strict Transport Security (HSTS)
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Feature Policy
        feature_policy = [
            "camera 'none'",
            "microphone 'none'",
            "geolocation 'none'",
            "payment 'none'",
        ]
        response['Feature-Policy'] = '; '.join(feature_policy)
        
        return response


class SessionTimeoutMiddleware:
    """
    Implements session timeout for security.
    Required for HIPAA compliance.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout_minutes = 15  # 15 minutes of inactivity
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Check last activity
            last_activity = request.session.get('last_activity')
            
            if last_activity:
                time_since_activity = timezone.now() - timezone.datetime.fromisoformat(last_activity)
                
                if time_since_activity.total_seconds() > (self.timeout_minutes * 60):
                    # Session timeout - logout user
                    request.session.flush()
                    return JsonResponse(
                        {'error': 'Session timeout. Please login again.'},
                        status=401
                    )
            
            # Update last activity
            request.session['last_activity'] = timezone.now().isoformat()
        
        response = self.get_response(request)
        return response


class DataMaskingMiddleware:
    """
    Masks sensitive data in responses for non-privileged users.
    Implements data minimization principle.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.sensitive_fields = [
            'ssn', 'social_security_number',
            'date_of_birth', 'dob',
            'member_id', 'insurance_id',
            'credit_card', 'account_number',
        ]
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Only mask for non-admin users
        if hasattr(request.user, 'role') and request.user.role != 'admin':
            self.mask_response_data(response)
        
        return response
    
    def mask_response_data(self, response):
        """Mask sensitive fields in response data."""
        if hasattr(response, 'data') and isinstance(response.data, dict):
            self._mask_dict(response.data)
    
    def _mask_dict(self, data):
        """Recursively mask sensitive fields in dictionary."""
        for key, value in data.items():
            if key.lower() in self.sensitive_fields:
                # Mask the value
                if isinstance(value, str) and len(value) > 4:
                    data[key] = '*' * (len(value) - 4) + value[-4:]
                else:
                    data[key] = '****'
            elif isinstance(value, dict):
                self._mask_dict(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._mask_dict(item)


def get_current_practice():
    """Helper function to get current practice from thread locals."""
    return getattr(_thread_locals, 'practice_id', None)