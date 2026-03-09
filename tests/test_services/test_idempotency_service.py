"""
Unit tests for IdempotencyService
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
import json
import hashlib

from src.services.idempotency_service import IdempotencyService, IdempotencyRecord
from src.utils.errors import ValidationError, ErrorCode


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB client"""
    mock = Mock()
    mock.exceptions = Mock()
    mock.exceptions.ConditionalCheckFailedException = type(
        "ConditionalCheckFailedException", (Exception,), {}
    )
    return mock


@pytest.fixture
def idempotency_service(mock_dynamodb):
    """Create IdempotencyService instance"""
    return IdempotencyService(mock_dynamodb, "test_idempotency_table")


def test_compute_request_hash_consistent(idempotency_service):
    """Test that request hash is consistent for same data"""
    request_data = {"user_id": "123", "content": "test", "platform": "linkedin"}
    
    hash1 = idempotency_service._compute_request_hash(request_data)
    hash2 = idempotency_service._compute_request_hash(request_data)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 produces 64 character hex string


def test_compute_request_hash_order_independent(idempotency_service):
    """Test that request hash is same regardless of key order"""
    request_data1 = {"user_id": "123", "content": "test", "platform": "linkedin"}
    request_data2 = {"platform": "linkedin", "user_id": "123", "content": "test"}
    
    hash1 = idempotency_service._compute_request_hash(request_data1)
    hash2 = idempotency_service._compute_request_hash(request_data2)
    
    assert hash1 == hash2


def test_compute_request_hash_different_for_different_data(idempotency_service):
    """Test that different data produces different hashes"""
    request_data1 = {"user_id": "123", "content": "test"}
    request_data2 = {"user_id": "456", "content": "test"}
    
    hash1 = idempotency_service._compute_request_hash(request_data1)
    hash2 = idempotency_service._compute_request_hash(request_data2)
    
    assert hash1 != hash2


def test_check_idempotency_no_existing_record(idempotency_service, mock_dynamodb):
    """Test check_idempotency when no record exists"""
    mock_dynamodb.get_item.return_value = {}
    
    result = idempotency_service.check_idempotency(
        "key123",
        "upload_content",
        {"user_id": "123"}
    )
    
    assert result is None
    mock_dynamodb.get_item.assert_called_once()


def test_check_idempotency_expired_record(idempotency_service, mock_dynamodb):
    """Test check_idempotency with expired record"""
    expired_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    
    mock_dynamodb.get_item.return_value = {
        "Item": {
            "idempotency_key": "key123",
            "operation": "upload_content",
            "status": "COMPLETED",
            "created_at": (datetime.utcnow() - timedelta(hours=25)).isoformat(),
            "expires_at": expired_time,
            "request_hash": "abc123"
        }
    }
    
    result = idempotency_service.check_idempotency(
        "key123",
        "upload_content",
        {"user_id": "123"}
    )
    
    assert result is None


def test_check_idempotency_valid_record(idempotency_service, mock_dynamodb):
    """Test check_idempotency with valid existing record"""
    request_data = {"user_id": "123"}
    request_hash = idempotency_service._compute_request_hash(request_data)
    
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=12)
    
    mock_dynamodb.get_item.return_value = {
        "Item": {
            "idempotency_key": "key123",
            "operation": "upload_content",
            "status": "COMPLETED",
            "result": json.dumps({"content_id": "content123"}),
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "request_hash": request_hash
        }
    }
    
    result = idempotency_service.check_idempotency(
        "key123",
        "upload_content",
        request_data
    )
    
    assert result is not None
    assert result.idempotency_key == "key123"
    assert result.operation == "upload_content"
    assert result.status == "COMPLETED"
    assert result.result == {"content_id": "content123"}


def test_check_idempotency_hash_mismatch(idempotency_service, mock_dynamodb):
    """Test check_idempotency raises error when request hash doesn't match"""
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=12)
    
    mock_dynamodb.get_item.return_value = {
        "Item": {
            "idempotency_key": "key123",
            "operation": "upload_content",
            "status": "COMPLETED",
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "request_hash": "different_hash"
        }
    }
    
    with pytest.raises(ValidationError) as exc_info:
        idempotency_service.check_idempotency(
            "key123",
            "upload_content",
            {"user_id": "123"}
        )
    
    assert exc_info.value.error_code == ErrorCode.INVALID_REQUEST
    assert "different request data" in exc_info.value.message


def test_start_operation_success(idempotency_service, mock_dynamodb):
    """Test starting a new operation"""
    mock_dynamodb.put_item.return_value = {}
    
    result = idempotency_service.start_operation(
        "key123",
        "upload_content",
        {"user_id": "123"}
    )
    
    assert result is True
    mock_dynamodb.put_item.assert_called_once()
    
    # Verify the item structure
    call_args = mock_dynamodb.put_item.call_args
    item = call_args.kwargs["Item"]
    assert item["idempotency_key"] == "key123"
    assert item["operation"] == "upload_content"
    assert item["status"] == "IN_PROGRESS"
    assert "created_at" in item
    assert "expires_at" in item
    assert "request_hash" in item
    assert "ttl" in item


def test_start_operation_already_in_progress(idempotency_service, mock_dynamodb):
    """Test starting operation that's already in progress"""
    mock_dynamodb.put_item.side_effect = (
        mock_dynamodb.exceptions.ConditionalCheckFailedException()
    )
    
    result = idempotency_service.start_operation(
        "key123",
        "upload_content",
        {"user_id": "123"}
    )
    
    assert result is False


def test_start_operation_handles_errors_gracefully(idempotency_service, mock_dynamodb):
    """Test that start_operation allows operation to proceed on errors"""
    mock_dynamodb.put_item.side_effect = Exception("DynamoDB error")
    
    result = idempotency_service.start_operation(
        "key123",
        "upload_content",
        {"user_id": "123"}
    )
    
    # Should return True to allow operation to proceed
    assert result is True


def test_complete_operation(idempotency_service, mock_dynamodb):
    """Test completing an operation"""
    mock_dynamodb.update_item.return_value = {}
    
    result_data = {"content_id": "content123", "status": "uploaded"}
    
    idempotency_service.complete_operation(
        "key123",
        "upload_content",
        result_data
    )
    
    mock_dynamodb.update_item.assert_called_once()
    
    # Verify the update
    call_args = mock_dynamodb.update_item.call_args
    assert call_args.kwargs["Key"]["idempotency_key"] == "key123"
    assert call_args.kwargs["Key"]["operation"] == "upload_content"
    assert call_args.kwargs["ExpressionAttributeValues"][":status"] == "COMPLETED"
    assert json.loads(call_args.kwargs["ExpressionAttributeValues"][":result"]) == result_data


def test_complete_operation_handles_errors(idempotency_service, mock_dynamodb):
    """Test that complete_operation handles errors gracefully"""
    mock_dynamodb.update_item.side_effect = Exception("DynamoDB error")
    
    # Should not raise exception
    idempotency_service.complete_operation(
        "key123",
        "upload_content",
        {"content_id": "content123"}
    )


def test_fail_operation(idempotency_service, mock_dynamodb):
    """Test failing an operation"""
    mock_dynamodb.update_item.return_value = {}
    
    error_message = "Upload failed due to network error"
    
    idempotency_service.fail_operation(
        "key123",
        "upload_content",
        error_message
    )
    
    mock_dynamodb.update_item.assert_called_once()
    
    # Verify the update
    call_args = mock_dynamodb.update_item.call_args
    assert call_args.kwargs["Key"]["idempotency_key"] == "key123"
    assert call_args.kwargs["Key"]["operation"] == "upload_content"
    assert call_args.kwargs["ExpressionAttributeValues"][":status"] == "FAILED"
    result = json.loads(call_args.kwargs["ExpressionAttributeValues"][":result"])
    assert result["error"] == error_message


def test_fail_operation_handles_errors(idempotency_service, mock_dynamodb):
    """Test that fail_operation handles errors gracefully"""
    mock_dynamodb.update_item.side_effect = Exception("DynamoDB error")
    
    # Should not raise exception
    idempotency_service.fail_operation(
        "key123",
        "upload_content",
        "Upload failed"
    )


def test_idempotency_workflow_complete_flow(idempotency_service, mock_dynamodb):
    """Test complete idempotency workflow"""
    # 1. Check idempotency - no existing record
    mock_dynamodb.get_item.return_value = {}
    existing = idempotency_service.check_idempotency(
        "key123",
        "upload_content",
        {"user_id": "123"}
    )
    assert existing is None
    
    # 2. Start operation
    mock_dynamodb.put_item.return_value = {}
    started = idempotency_service.start_operation(
        "key123",
        "upload_content",
        {"user_id": "123"}
    )
    assert started is True
    
    # 3. Complete operation
    mock_dynamodb.update_item.return_value = {}
    idempotency_service.complete_operation(
        "key123",
        "upload_content",
        {"content_id": "content123"}
    )
    
    # Verify all operations were called
    assert mock_dynamodb.get_item.called
    assert mock_dynamodb.put_item.called
    assert mock_dynamodb.update_item.called


def test_idempotency_workflow_retry_completed_operation(idempotency_service, mock_dynamodb):
    """Test retrying an already completed operation returns cached result"""
    request_data = {"user_id": "123"}
    request_hash = idempotency_service._compute_request_hash(request_data)
    
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=12)
    
    # Simulate existing completed operation
    mock_dynamodb.get_item.return_value = {
        "Item": {
            "idempotency_key": "key123",
            "operation": "upload_content",
            "status": "COMPLETED",
            "result": json.dumps({"content_id": "content123"}),
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "request_hash": request_hash
        }
    }
    
    # Check idempotency
    existing = idempotency_service.check_idempotency(
        "key123",
        "upload_content",
        request_data
    )
    
    # Should return the cached result
    assert existing is not None
    assert existing.status == "COMPLETED"
    assert existing.result == {"content_id": "content123"}
    
    # Should not attempt to start a new operation
    mock_dynamodb.put_item.assert_not_called()


def test_ttl_configuration(idempotency_service):
    """Test that TTL is properly configured"""
    assert idempotency_service.ttl_hours == 24


def test_idempotency_record_dataclass():
    """Test IdempotencyRecord dataclass"""
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=24)
    
    record = IdempotencyRecord(
        idempotency_key="key123",
        operation="upload_content",
        status="COMPLETED",
        result={"content_id": "content123"},
        created_at=now,
        expires_at=expires_at,
        request_hash="abc123"
    )
    
    assert record.idempotency_key == "key123"
    assert record.operation == "upload_content"
    assert record.status == "COMPLETED"
    assert record.result == {"content_id": "content123"}
    assert record.created_at == now
    assert record.expires_at == expires_at
    assert record.request_hash == "abc123"
