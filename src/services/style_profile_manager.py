"""
Style Profile Manager Service

Manages user style content uploads and style profile creation.
"""
import os
import uuid
from datetime import datetime
from typing import BinaryIO, Optional
from io import BytesIO

from src.models import StyleContentMetadata, StyleProfile, StyleProfileStatus, EmbeddingStatus, EmbeddingResult
from src.utils.aws_clients import S3Client, DynamoDBClient, BedrockClient
from src.utils.errors import ValidationError, NotFoundError, ErrorCode, ProcessingError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StyleProfileManager:
    """Manages style profile content and profile status"""
    
    # Supported file types for style content
    SUPPORTED_FILE_TYPES = {'.txt', '.md', '.pdf', '.doc', '.docx'}
    
    def __init__(
        self,
        s3_client: Optional[S3Client] = None,
        dynamodb_client: Optional[DynamoDBClient] = None,
        bedrock_client: Optional[BedrockClient] = None
    ):
        """
        Initialize StyleProfileManager
        
        Args:
            s3_client: S3 client for file storage
            dynamodb_client: DynamoDB client for metadata storage
            bedrock_client: Bedrock client for embedding generation
        """
        self.s3_client = s3_client or S3Client()
        self.dynamodb_client = dynamodb_client or DynamoDBClient()
        self.bedrock_client = bedrock_client or BedrockClient()
        
        # Get table and bucket names from environment
        self.style_content_table = os.environ.get(
            "DYNAMODB_TABLE_STYLE_CONTENT",
            "style_content"
        )
        self.users_table = os.environ.get(
            "DYNAMODB_TABLE_USERS",
            "users"
        )
        self.style_vault_bucket = os.environ.get(
            "S3_BUCKET_STYLE_VAULT",
            "style-vault"
        )
        self.knowledge_base_id = os.environ.get("KNOWLEDGE_BASE_ID")
    
    def upload_style_content(
        self,
        user_id: str,
        file: BinaryIO,
        filename: str,
        content_type: str
    ) -> StyleContentMetadata:
        """
        Upload style content to Style Vault
        
        Args:
            user_id: User identifier
            file: File object to upload
            filename: Original filename
            content_type: MIME type of the file
        
        Returns:
            StyleContentMetadata with content_id and status
        
        Raises:
            ValidationError: If file type is unsupported
        """
        # Validate file type
        file_extension = self._get_file_extension(filename)
        if file_extension not in self.SUPPORTED_FILE_TYPES:
            raise ValidationError(
                error_code=ErrorCode.INVALID_FILE_TYPE,
                message=f"Unsupported file type: {file_extension}. "
                        f"Supported types: {', '.join(self.SUPPORTED_FILE_TYPES)}",
                details={
                    "filename": filename,
                    "file_extension": file_extension,
                    "supported_types": list(self.SUPPORTED_FILE_TYPES)
                }
            )
        
        # Generate unique content ID
        content_id = str(uuid.uuid4())
        
        # Read file content
        file_content = file.read()
        
        # Upload to S3
        s3_key = f"{user_id}/{content_id}{file_extension}"
        s3_uri = self.s3_client.upload_file(
            file_content=file_content,
            bucket=self.style_vault_bucket,
            key=s3_key,
            content_type=content_type
        )
        
        # Create metadata
        metadata = StyleContentMetadata(
            content_id=content_id,
            user_id=user_id,
            filename=filename,
            s3_uri=s3_uri,
            content_type=content_type,
            uploaded_at=datetime.utcnow(),
            embedding_status=EmbeddingStatus.PENDING
        )
        
        # Store metadata in DynamoDB
        self.dynamodb_client.put_item(
            table_name=self.style_content_table,
            item=metadata.to_dict()
        )
        
        # Update user's style content count
        self._increment_style_content_count(user_id)
        
        logger.info(
            "Style content uploaded",
            user_id=user_id,
            content_id=content_id,
            filename=filename,
            size=len(file_content)
        )
        
        return metadata
    
    def generate_embeddings(self, user_id: str, content_id: str) -> EmbeddingResult:
        """
        Generate embeddings for style content using Amazon Titan Embeddings G1
        
        Args:
            user_id: User identifier
            content_id: Style content identifier
        
        Returns:
            EmbeddingResult with embedding_id and vector dimensions
        
        Raises:
            NotFoundError: If content doesn't exist
            ProcessingError: If embedding generation fails
        """
        try:
            # Get content metadata
            metadata_item = self.dynamodb_client.get_item(
                table_name=self.style_content_table,
                key={"user_id": user_id, "content_id": content_id}
            )
            
            if not metadata_item:
                raise NotFoundError(
                    error_code=ErrorCode.CONTENT_NOT_FOUND,
                    message=f"Style content not found: {content_id}",
                    details={"user_id": user_id, "content_id": content_id}
                )
            
            # Download content from S3
            s3_uri = metadata_item['s3_uri']
            bucket = s3_uri.split('/')[2]
            key = '/'.join(s3_uri.split('/')[3:])
            
            content_bytes = self.s3_client.download_file(bucket, key)
            content_text = content_bytes.decode('utf-8')
            
            # Generate embeddings using Titan Embeddings G1
            model_id = "amazon.titan-embed-text-v1"
            
            response = self.bedrock_client.invoke_model(
                model_id=model_id,
                body={
                    "inputText": content_text
                }
            )
            
            # Extract embedding vector from response
            embedding_vector = response.get('embedding', [])
            
            if not embedding_vector:
                raise ProcessingError(
                    error_code=ErrorCode.EMBEDDING_GENERATION_FAILED,
                    message="Embedding generation returned empty vector",
                    details={"content_id": content_id, "user_id": user_id}
                )
            
            # Generate embedding ID
            embedding_id = str(uuid.uuid4())
            
            # Create embedding result
            embedding_result = EmbeddingResult(
                embedding_id=embedding_id,
                content_id=content_id,
                user_id=user_id,
                vector_dimensions=len(embedding_vector),
                embedding_vector=embedding_vector,
                model_id=model_id
            )
            
            # Store embedding in Bedrock Knowledge Base
            # Note: In a real implementation, this would use the Bedrock Agent Runtime
            # to ingest documents into the Knowledge Base. For now, we'll update the status.
            # The actual ingestion would be handled by a separate data source sync process.
            
            # Update embedding status in DynamoDB
            self.dynamodb_client.update_item(
                table_name=self.style_content_table,
                key={"user_id": user_id, "content_id": content_id},
                update_expression="SET embedding_status = :status, embedding_id = :embedding_id",
                expression_attribute_values={
                    ":status": EmbeddingStatus.COMPLETED.value,
                    ":embedding_id": embedding_id
                }
            )
            
            logger.info(
                "Embeddings generated successfully",
                user_id=user_id,
                content_id=content_id,
                embedding_id=embedding_id,
                vector_dimensions=len(embedding_vector)
            )
            
            return embedding_result
            
        except (NotFoundError, ProcessingError):
            # Re-raise known errors
            raise
            
        except Exception as e:
            # Log and wrap unexpected errors
            logger.log_error(
                operation="generate_embeddings",
                error=e,
                user_id=user_id,
                content_id=content_id
            )
            
            # Update status to FAILED
            try:
                self.dynamodb_client.update_item(
                    table_name=self.style_content_table,
                    key={"user_id": user_id, "content_id": content_id},
                    update_expression="SET embedding_status = :status",
                    expression_attribute_values={
                        ":status": EmbeddingStatus.FAILED.value
                    }
                )
            except Exception as update_error:
                logger.log_error(
                    operation="update_embedding_status_to_failed",
                    error=update_error,
                    user_id=user_id,
                    content_id=content_id
                )
            
            raise ProcessingError(
                error_code=ErrorCode.EMBEDDING_GENERATION_FAILED,
                message=f"Failed to generate embeddings: {str(e)}",
                details={"user_id": user_id, "content_id": content_id}
            )
    
    def get_style_profile(self, user_id: str) -> StyleProfile:
        """
        Retrieve user's style profile
        
        Args:
            user_id: User identifier
        
        Returns:
            StyleProfile with status and content count
        
        Raises:
            NotFoundError: If profile doesn't exist
        """
        # Get user profile from DynamoDB
        user_data = self.dynamodb_client.get_item(
            table_name=self.users_table,
            key={"user_id": user_id}
        )
        
        if not user_data:
            raise NotFoundError(
                error_code=ErrorCode.USER_NOT_FOUND,
                message=f"User not found: {user_id}",
                details={"user_id": user_id}
            )
        
        # Count style content pieces
        from boto3.dynamodb.conditions import Key
        style_content_items = self.dynamodb_client.resource.Table(
            self.style_content_table
        ).query(
            KeyConditionExpression=Key('user_id').eq(user_id)
        ).get('Items', [])
        
        content_count = len(style_content_items)
        
        # Determine status based on content count
        status = (
            StyleProfileStatus.READY if content_count >= 3
            else StyleProfileStatus.INCOMPLETE
        )
        
        # Create style profile
        profile = StyleProfile(
            user_id=user_id,
            status=status,
            content_count=content_count,
            last_updated=datetime.utcnow(),
            knowledge_base_id=os.environ.get("KNOWLEDGE_BASE_ID")
        )
        
        logger.info(
            "Style profile retrieved",
            user_id=user_id,
            status=status.value,
            content_count=content_count
        )
        
        return profile
    
    def is_profile_ready(self, user_id: str) -> bool:
        """
        Check if style profile has sufficient content (>= 3 pieces)
        
        Args:
            user_id: User identifier
        
        Returns:
            True if ready (>= 3 pieces), False otherwise
        """
        try:
            profile = self.get_style_profile(user_id)
            is_ready = profile.content_count >= 3
            
            logger.info(
                "Style profile readiness checked",
                user_id=user_id,
                is_ready=is_ready,
                content_count=profile.content_count
            )
            
            return is_ready
            
        except NotFoundError:
            logger.info(
                "Style profile readiness checked - user not found",
                user_id=user_id,
                is_ready=False
            )
            return False
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        if '.' not in filename:
            return ''
        return '.' + filename.rsplit('.', 1)[1].lower()
    
    def _increment_style_content_count(self, user_id: str) -> None:
        """Increment the style content count for a user"""
        try:
            self.dynamodb_client.update_item(
                table_name=self.users_table,
                key={"user_id": user_id},
                update_expression="SET style_content_count = style_content_count + :inc",
                expression_attribute_values={":inc": 1}
            )
            
            logger.info(
                "Style content count incremented",
                user_id=user_id
            )
            
        except Exception as e:
            # Log error but don't fail the upload
            logger.log_error(
                operation="increment_style_content_count",
                error=e,
                user_id=user_id
            )
