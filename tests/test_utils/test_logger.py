"""
Unit tests for logging utilities
"""
import pytest
import json
import logging
from src.utils.logger import StructuredLogger, JsonFormatter, get_logger


class TestStructuredLogger:
    """Test StructuredLogger class"""
    
    def test_logger_creation(self):
        """Test creating a structured logger"""
        logger = StructuredLogger("test_logger")
        assert logger.logger.name == "test_logger"
        assert logger.logger.level == logging.INFO
    
    def test_logger_with_custom_level(self):
        """Test creating logger with custom level"""
        logger = StructuredLogger("test_logger", level="DEBUG")
        assert logger.logger.level == logging.DEBUG
    
    def test_info_logging(self, caplog):
        """Test info level logging"""
        logger = StructuredLogger("test_logger")
        
        with caplog.at_level(logging.INFO):
            logger.info("Test message", user_id="user-123")
        
        # Check that log was created
        assert len(caplog.records) > 0
        
        # Parse JSON log
        log_data = json.loads(caplog.records[0].message)
        assert log_data["message"] == "Test message"
        assert log_data["user_id"] == "user-123"
        assert "timestamp" in log_data
    
    def test_error_logging(self, caplog):
        """Test error level logging"""
        logger = StructuredLogger("test_logger")
        test_error = ValueError("Test error")
        
        with caplog.at_level(logging.ERROR):
            logger.error("Error occurred", error=test_error, context="test")
        
        # Parse JSON log
        log_data = json.loads(caplog.records[0].message)
        assert log_data["message"] == "Error occurred"
        assert log_data["error_type"] == "ValueError"
        assert log_data["error_message"] == "Test error"
        assert log_data["context"] == "test"
    
    def test_log_operation(self, caplog):
        """Test operation logging"""
        logger = StructuredLogger("test_logger")
        
        with caplog.at_level(logging.INFO):
            logger.log_operation(
                operation="upload_content",
                user_id="user-123",
                content_id="content-456",
                status="completed"
            )
        
        log_data = json.loads(caplog.records[0].message)
        assert log_data["operation"] == "upload_content"
        assert log_data["user_id"] == "user-123"
        assert log_data["content_id"] == "content-456"
        assert log_data["status"] == "completed"
    
    def test_log_error_method(self, caplog):
        """Test error logging method"""
        logger = StructuredLogger("test_logger")
        test_error = RuntimeError("Operation failed")
        
        with caplog.at_level(logging.ERROR):
            logger.log_error(
                operation="generate_content",
                error=test_error,
                user_id="user-789"
            )
        
        log_data = json.loads(caplog.records[0].message)
        assert "Operation failed: generate_content" in log_data["message"]
        assert log_data["operation"] == "generate_content"
        assert log_data["user_id"] == "user-789"
        assert log_data["error_type"] == "RuntimeError"


class TestJsonFormatter:
    """Test JsonFormatter class"""
    
    def test_format_plain_message(self):
        """Test formatting plain text message"""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Plain message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        log_data = json.loads(result)
        
        assert log_data["message"] == "Plain message"
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test"
        assert "timestamp" in log_data
    
    def test_format_json_message(self):
        """Test formatting already-JSON message"""
        formatter = JsonFormatter()
        json_msg = json.dumps({"key": "value", "number": 42})
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=json_msg,
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        # Should return the JSON as-is
        assert result == json_msg


class TestGetLogger:
    """Test get_logger function"""
    
    def test_get_logger_returns_structured_logger(self):
        """Test that get_logger returns StructuredLogger instance"""
        logger = get_logger("test_module")
        assert isinstance(logger, StructuredLogger)
        assert logger.logger.name == "test_module"
