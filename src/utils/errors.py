"""
Error handling utilities for Content Repurposing Platform
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(Enum):
    """Standard error codes for the platform"""
    # Validation errors (4xx)
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    CONTENT_EXCEEDS_LIMIT = "CONTENT_EXCEEDS_LIMIT"
    INVALID_SCHEDULE_TIME = "INVALID_SCHEDULE_TIME"
    INSUFFICIENT_CONTENT = "INSUFFICIENT_CONTENT"
    UNSUPPORTED_PLATFORM = "UNSUPPORTED_PLATFORM"
    INVALID_REQUEST = "INVALID_REQUEST"
    
    # Authentication errors (401, 403)
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    EXPIRED_TOKEN = "EXPIRED_TOKEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # Resource not found (404)
    CONTENT_NOT_FOUND = "CONTENT_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    STYLE_PROFILE_NOT_FOUND = "STYLE_PROFILE_NOT_FOUND"
    SCHEDULE_NOT_FOUND = "SCHEDULE_NOT_FOUND"
    NO_STYLE_PROFILE = "NO_STYLE_PROFILE"
    
    # External service errors (502, 503)
    TRANSCRIBE_FAILURE = "TRANSCRIBE_FAILURE"
    BEDROCK_UNAVAILABLE = "BEDROCK_UNAVAILABLE"
    S3_ACCESS_ERROR = "S3_ACCESS_ERROR"
    DYNAMODB_ERROR = "DYNAMODB_ERROR"
    
    # Rate limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    BEDROCK_THROTTLED = "BEDROCK_THROTTLED"
    
    # Processing errors (500)
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"
    TRANSCRIPTION_IN_PROGRESS = "TRANSCRIPTION_IN_PROGRESS"
    TRANSCRIPTION_TIMEOUT = "TRANSCRIPTION_TIMEOUT"
    TOPIC_EXTRACTION_FAILED = "TOPIC_EXTRACTION_FAILED"
    CONTENT_GENERATION_FAILED = "CONTENT_GENERATION_FAILED"
    GENERATION_FAILED = "GENERATION_FAILED"
    EMBEDDING_GENERATION_FAILED = "EMBEDDING_GENERATION_FAILED"
    STYLE_RETRIEVAL_FAILED = "STYLE_RETRIEVAL_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class ErrorResponse:
    """Standardized error response format"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error response to dictionary"""
        result = {
            "error_code": self.error_code,
            "message": self.message
        }
        if self.details:
            result["details"] = self.details
        if self.retry_after:
            result["retry_after"] = self.retry_after
        if self.request_id:
            result["request_id"] = self.request_id
        return result


class PlatformError(Exception):
    """Base exception for platform errors"""
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None
    ):
        self.error_code = error_code
        self.message = message
        self.details = details
        self.retry_after = retry_after
        super().__init__(message)
    
    def to_error_response(self, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert exception to error response"""
        return ErrorResponse(
            error_code=self.error_code.value,
            message=self.message,
            details=self.details,
            retry_after=self.retry_after,
            request_id=request_id
        )


class ValidationError(PlatformError):
    """Validation error (4xx)"""
    pass


class AuthenticationError(PlatformError):
    """Authentication error (401, 403)"""
    pass


class NotFoundError(PlatformError):
    """Resource not found error (404)"""
    pass


class ExternalServiceError(PlatformError):
    """External service error (502, 503)"""
    pass


class RateLimitError(PlatformError):
    """Rate limit error (429)"""
    pass


class ProcessingError(PlatformError):
    """Processing error (500)"""
    pass


class TranscriptionError(ProcessingError):
    """Transcription-specific error"""
    pass


def get_http_status_code(error_code: ErrorCode) -> int:
    """Map error code to HTTP status code"""
    status_map = {
        # 400 Bad Request
        ErrorCode.INVALID_FILE_TYPE: 400,
        ErrorCode.MISSING_REQUIRED_FIELD: 400,
        ErrorCode.CONTENT_EXCEEDS_LIMIT: 400,
        ErrorCode.INVALID_SCHEDULE_TIME: 400,
        ErrorCode.INSUFFICIENT_CONTENT: 400,
        ErrorCode.UNSUPPORTED_PLATFORM: 400,
        ErrorCode.INVALID_REQUEST: 400,
        
        # 401 Unauthorized
        ErrorCode.INVALID_CREDENTIALS: 401,
        ErrorCode.EXPIRED_TOKEN: 401,
        
        # 403 Forbidden
        ErrorCode.INSUFFICIENT_PERMISSIONS: 403,
        
        # 404 Not Found
        ErrorCode.CONTENT_NOT_FOUND: 404,
        ErrorCode.USER_NOT_FOUND: 404,
        ErrorCode.STYLE_PROFILE_NOT_FOUND: 404,
        ErrorCode.SCHEDULE_NOT_FOUND: 404,
        ErrorCode.NO_STYLE_PROFILE: 404,
        
        # 429 Too Many Requests
        ErrorCode.RATE_LIMIT_EXCEEDED: 429,
        ErrorCode.BEDROCK_THROTTLED: 429,
        
        # 500 Internal Server Error
        ErrorCode.TRANSCRIPTION_FAILED: 500,
        ErrorCode.TRANSCRIPTION_IN_PROGRESS: 202,  # Accepted - still processing
        ErrorCode.TRANSCRIPTION_TIMEOUT: 504,  # Gateway Timeout
        ErrorCode.TOPIC_EXTRACTION_FAILED: 500,
        ErrorCode.CONTENT_GENERATION_FAILED: 500,
        ErrorCode.GENERATION_FAILED: 500,
        ErrorCode.EMBEDDING_GENERATION_FAILED: 500,
        ErrorCode.STYLE_RETRIEVAL_FAILED: 500,
        ErrorCode.INTERNAL_ERROR: 500,
        
        # 502 Bad Gateway
        ErrorCode.TRANSCRIBE_FAILURE: 502,
        
        # 503 Service Unavailable
        ErrorCode.BEDROCK_UNAVAILABLE: 503,
        ErrorCode.S3_ACCESS_ERROR: 503,
        ErrorCode.DYNAMODB_ERROR: 503,
    }
    return status_map.get(error_code, 500)


# Alias for backward compatibility with Lambda handlers
AppError = PlatformError
