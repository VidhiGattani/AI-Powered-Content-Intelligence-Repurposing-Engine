"""
Unit tests for error handling utilities
"""
import pytest
from src.utils.errors import (
    ErrorCode,
    ErrorResponse,
    PlatformError,
    ValidationError,
    AuthenticationError,
    NotFoundError,
    ExternalServiceError,
    RateLimitError,
    ProcessingError,
    get_http_status_code
)


class TestErrorResponse:
    """Test ErrorResponse dataclass"""
    
    def test_error_response_to_dict_minimal(self):
        """Test error response with minimal fields"""
        error = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test error message"
        )
        
        result = error.to_dict()
        
        assert result["error_code"] == "TEST_ERROR"
        assert result["message"] == "Test error message"
        assert "details" not in result
        assert "retry_after" not in result
        assert "request_id" not in result
    
    def test_error_response_to_dict_complete(self):
        """Test error response with all fields"""
        error = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test error message",
            details={"field": "value"},
            retry_after=60,
            request_id="req-123"
        )
        
        result = error.to_dict()
        
        assert result["error_code"] == "TEST_ERROR"
        assert result["message"] == "Test error message"
        assert result["details"] == {"field": "value"}
        assert result["retry_after"] == 60
        assert result["request_id"] == "req-123"


class TestPlatformError:
    """Test PlatformError exception"""
    
    def test_platform_error_creation(self):
        """Test creating platform error"""
        error = PlatformError(
            error_code=ErrorCode.INVALID_FILE_TYPE,
            message="Invalid file type",
            details={"file_type": "exe"}
        )
        
        assert error.error_code == ErrorCode.INVALID_FILE_TYPE
        assert error.message == "Invalid file type"
        assert error.details == {"file_type": "exe"}
        assert str(error) == "Invalid file type"
    
    def test_platform_error_to_error_response(self):
        """Test converting platform error to error response"""
        error = PlatformError(
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message="Rate limit exceeded",
            retry_after=120
        )
        
        response = error.to_error_response(request_id="req-456")
        
        assert response.error_code == "RATE_LIMIT_EXCEEDED"
        assert response.message == "Rate limit exceeded"
        assert response.retry_after == 120
        assert response.request_id == "req-456"


class TestErrorSubclasses:
    """Test error subclasses"""
    
    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError(
            error_code=ErrorCode.INVALID_FILE_TYPE,
            message="Invalid file"
        )
        assert isinstance(error, PlatformError)
    
    def test_authentication_error(self):
        """Test AuthenticationError"""
        error = AuthenticationError(
            error_code=ErrorCode.INVALID_CREDENTIALS,
            message="Invalid credentials"
        )
        assert isinstance(error, PlatformError)
    
    def test_not_found_error(self):
        """Test NotFoundError"""
        error = NotFoundError(
            error_code=ErrorCode.CONTENT_NOT_FOUND,
            message="Content not found"
        )
        assert isinstance(error, PlatformError)
    
    def test_external_service_error(self):
        """Test ExternalServiceError"""
        error = ExternalServiceError(
            error_code=ErrorCode.BEDROCK_UNAVAILABLE,
            message="Bedrock unavailable"
        )
        assert isinstance(error, PlatformError)
    
    def test_rate_limit_error(self):
        """Test RateLimitError"""
        error = RateLimitError(
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message="Rate limit exceeded"
        )
        assert isinstance(error, PlatformError)
    
    def test_processing_error(self):
        """Test ProcessingError"""
        error = ProcessingError(
            error_code=ErrorCode.TRANSCRIPTION_FAILED,
            message="Transcription failed"
        )
        assert isinstance(error, PlatformError)


class TestGetHttpStatusCode:
    """Test HTTP status code mapping"""
    
    def test_validation_errors_return_400(self):
        """Test validation errors map to 400"""
        assert get_http_status_code(ErrorCode.INVALID_FILE_TYPE) == 400
        assert get_http_status_code(ErrorCode.MISSING_REQUIRED_FIELD) == 400
        assert get_http_status_code(ErrorCode.CONTENT_EXCEEDS_LIMIT) == 400
    
    def test_auth_errors_return_401_or_403(self):
        """Test auth errors map to 401 or 403"""
        assert get_http_status_code(ErrorCode.INVALID_CREDENTIALS) == 401
        assert get_http_status_code(ErrorCode.EXPIRED_TOKEN) == 401
        assert get_http_status_code(ErrorCode.INSUFFICIENT_PERMISSIONS) == 403
    
    def test_not_found_errors_return_404(self):
        """Test not found errors map to 404"""
        assert get_http_status_code(ErrorCode.CONTENT_NOT_FOUND) == 404
        assert get_http_status_code(ErrorCode.USER_NOT_FOUND) == 404
    
    def test_rate_limit_errors_return_429(self):
        """Test rate limit errors map to 429"""
        assert get_http_status_code(ErrorCode.RATE_LIMIT_EXCEEDED) == 429
        assert get_http_status_code(ErrorCode.BEDROCK_THROTTLED) == 429
    
    def test_processing_errors_return_500(self):
        """Test processing errors map to 500"""
        assert get_http_status_code(ErrorCode.TRANSCRIPTION_FAILED) == 500
        assert get_http_status_code(ErrorCode.INTERNAL_ERROR) == 500
    
    def test_service_errors_return_502_or_503(self):
        """Test service errors map to 502 or 503"""
        assert get_http_status_code(ErrorCode.TRANSCRIBE_FAILURE) == 502
        assert get_http_status_code(ErrorCode.BEDROCK_UNAVAILABLE) == 503
        assert get_http_status_code(ErrorCode.S3_ACCESS_ERROR) == 503
