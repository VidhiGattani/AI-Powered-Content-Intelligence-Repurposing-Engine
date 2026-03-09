"""
Idempotency service for Content Repurposing Platform

Ensures operations can be safely retried without side effects.
Uses DynamoDB to track operation state with idempotency keys.
"""
from dataclasses import dataclass
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import json
import hashlib
from src.utils.errors import ValidationError, ErrorCode
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IdempotencyRecord:
    """Record of an idempotent operation"""
    idempotency_key: str
    operation: str
    status: str  # IN_PROGRESS, COMPLETED, FAILED
    result: Optional[Any]
    created_at: datetime
    expires_at: datetime
    request_hash: str


class IdempotencyService:
    """
    Service for managing idempotent operations
    
    Ensures that operations with the same idempotency key are executed only once,
    even if the request is retried multiple times.
    """
    
    def __init__(self, dynamodb_client, table_name: str = "idempotency_records"):
        """
        Initialize idempotency service
        
        Args:
            dynamodb_client: DynamoDB client instance
            table_name: Name of the idempotency records table
        """
        self.dynamodb = dynamodb_client
        self.table_name = table_name
        self.ttl_hours = 24  # Records expire after 24 hours
    
    def _compute_request_hash(self, request_data: Dict[str, Any]) -> str:
        """
        Compute hash of request data for validation
        
        Args:
            request_data: Request parameters
            
        Returns:
            SHA256 hash of request data
        """
        # Sort keys for consistent hashing
        sorted_data = json.dumps(request_data, sort_keys=True)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    def check_idempotency(
        self,
        idempotency_key: str,
        operation: str,
        request_data: Dict[str, Any]
    ) -> Optional[IdempotencyRecord]:
        """
        Check if operation with this idempotency key already exists
        
        Args:
            idempotency_key: Unique key for this operation
            operation: Operation name
            request_data: Request parameters for hash validation
            
        Returns:
            IdempotencyRecord if operation exists, None otherwise
            
        Raises:
            ValidationError: If idempotency key exists with different request data
        """
        try:
            response = self.dynamodb.get_item(
                TableName=self.table_name,
                Key={
                    "idempotency_key": idempotency_key,
                    "operation": operation
                }
            )
            
            if "Item" not in response:
                return None
            
            item = response["Item"]
            
            # Check if record has expired
            expires_at = datetime.fromisoformat(item["expires_at"])
            if datetime.utcnow() > expires_at:
                # Record expired, can proceed with new operation
                return None
            
            # Validate request hash matches
            request_hash = self._compute_request_hash(request_data)
            if item["request_hash"] != request_hash:
                raise ValidationError(
                    ErrorCode.INVALID_REQUEST,
                    f"Idempotency key '{idempotency_key}' already used with different request data"
                )
            
            # Return existing record
            return IdempotencyRecord(
                idempotency_key=item["idempotency_key"],
                operation=item["operation"],
                status=item["status"],
                result=json.loads(item["result"]) if item.get("result") else None,
                created_at=datetime.fromisoformat(item["created_at"]),
                expires_at=expires_at,
                request_hash=item["request_hash"]
            )
            
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            logger.log_error(
                operation="check_idempotency",
                error=e,
                idempotency_key=idempotency_key,
                operation_name=operation
            )
            # On error, allow operation to proceed
            return None
    
    def start_operation(
        self,
        idempotency_key: str,
        operation: str,
        request_data: Dict[str, Any]
    ) -> bool:
        """
        Mark operation as started
        
        Args:
            idempotency_key: Unique key for this operation
            operation: Operation name
            request_data: Request parameters
            
        Returns:
            True if operation started successfully, False if already in progress
        """
        try:
            now = datetime.utcnow()
            expires_at = now + timedelta(hours=self.ttl_hours)
            request_hash = self._compute_request_hash(request_data)
            
            # Use conditional write to prevent race conditions
            self.dynamodb.put_item(
                TableName=self.table_name,
                Item={
                    "idempotency_key": idempotency_key,
                    "operation": operation,
                    "status": "IN_PROGRESS",
                    "created_at": now.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "request_hash": request_hash,
                    "ttl": int(expires_at.timestamp())
                },
                ConditionExpression="attribute_not_exists(idempotency_key)"
            )
            
            logger.log_operation(
                operation="start_idempotent_operation",
                status="started",
                idempotency_key=idempotency_key,
                operation_name=operation
            )
            return True
            
        except self.dynamodb.exceptions.ConditionalCheckFailedException:
            # Operation already in progress
            logger.info(
                "Operation already in progress",
                idempotency_key=idempotency_key,
                operation=operation
            )
            return False
        except Exception as e:
            logger.log_error(
                operation="start_operation",
                error=e,
                idempotency_key=idempotency_key,
                operation_name=operation
            )
            # On error, allow operation to proceed
            return True
    
    def complete_operation(
        self,
        idempotency_key: str,
        operation: str,
        result: Any
    ) -> None:
        """
        Mark operation as completed with result
        
        Args:
            idempotency_key: Unique key for this operation
            operation: Operation name
            result: Operation result to store
        """
        try:
            self.dynamodb.update_item(
                TableName=self.table_name,
                Key={
                    "idempotency_key": idempotency_key,
                    "operation": operation
                },
                UpdateExpression="SET #status = :status, #result = :result",
                ExpressionAttributeNames={
                    "#status": "status",
                    "#result": "result"
                },
                ExpressionAttributeValues={
                    ":status": "COMPLETED",
                    ":result": json.dumps(result)
                }
            )
            
            logger.log_operation(
                operation="complete_idempotent_operation",
                status="completed",
                idempotency_key=idempotency_key,
                operation_name=operation
            )
            
        except Exception as e:
            logger.log_error(
                operation="complete_operation",
                error=e,
                idempotency_key=idempotency_key,
                operation_name=operation
            )
    
    def fail_operation(
        self,
        idempotency_key: str,
        operation: str,
        error_message: str
    ) -> None:
        """
        Mark operation as failed
        
        Args:
            idempotency_key: Unique key for this operation
            operation: Operation name
            error_message: Error message
        """
        try:
            self.dynamodb.update_item(
                TableName=self.table_name,
                Key={
                    "idempotency_key": idempotency_key,
                    "operation": operation
                },
                UpdateExpression="SET #status = :status, #result = :result",
                ExpressionAttributeNames={
                    "#status": "status",
                    "#result": "result"
                },
                ExpressionAttributeValues={
                    ":status": "FAILED",
                    ":result": json.dumps({"error": error_message})
                }
            )
            
            logger.log_operation(
                operation="fail_idempotent_operation",
                status="failed",
                idempotency_key=idempotency_key,
                operation_name=operation,
                error=error_message
            )
            
        except Exception as e:
            logger.log_error(
                operation="fail_operation",
                error=e,
                idempotency_key=idempotency_key,
                operation_name=operation
            )
