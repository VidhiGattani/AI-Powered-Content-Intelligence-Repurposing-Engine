"""
Logging utilities for Content Repurposing Platform
"""
import logging
import json
import os
from typing import Any, Dict, Optional
from datetime import datetime


class StructuredLogger:
    """Structured logger for CloudWatch with JSON formatting"""
    
    def __init__(self, name: str, level: Optional[str] = None):
        self.logger = logging.getLogger(name)
        
        # Set log level from environment or default to INFO
        log_level = level or os.environ.get("LOG_LEVEL", "INFO")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create console handler with JSON formatter
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JsonFormatter())
            self.logger.addHandler(handler)
    
    def _log(
        self,
        level: str,
        message: str,
        **kwargs: Any
    ) -> None:
        """Internal log method with structured data"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            **kwargs
        }
        
        log_method = getattr(self.logger, level.lower())
        log_method(json.dumps(log_data))
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message"""
        self._log("INFO", message, **kwargs)
    
    def error(
        self,
        message: str,
        error: Optional[Exception] = None,
        **kwargs: Any
    ) -> None:
        """Log error message with optional exception"""
        error_data = kwargs.copy()
        if error:
            error_data["error_type"] = type(error).__name__
            error_data["error_message"] = str(error)
        self._log("ERROR", message, **error_data)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message"""
        self._log("WARNING", message, **kwargs)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message"""
        self._log("DEBUG", message, **kwargs)
    
    def log_operation(
        self,
        operation: str,
        user_id: Optional[str] = None,
        content_id: Optional[str] = None,
        status: str = "started",
        **kwargs: Any
    ) -> None:
        """Log operation with standard fields"""
        self.info(
            f"Operation: {operation}",
            operation=operation,
            user_id=user_id,
            content_id=content_id,
            status=status,
            **kwargs
        )
    
    def log_error(
        self,
        operation: str,
        error: Exception,
        user_id: Optional[str] = None,
        content_id: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Log error with standard fields"""
        self.error(
            f"Operation failed: {operation}",
            error=error,
            operation=operation,
            user_id=user_id,
            content_id=content_id,
            **kwargs
        )


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # If the message is already JSON, return it as-is
        try:
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, ValueError):
            # Otherwise, wrap it in JSON
            log_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage()
            }
            return json.dumps(log_data)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)
