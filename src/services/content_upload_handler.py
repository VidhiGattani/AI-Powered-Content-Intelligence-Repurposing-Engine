"""
Content Upload Handler for Content Repurposing Platform
Handles upload of original content (video, audio, text) and initiates processing
"""
import os
import uuid
from datetime import datetime, timezone
from typing import BinaryIO, Optional
from io import BytesIO

from ..models.content import ContentMetadata
from ..models.enums import ProcessingStatus as ProcessingStatusEnum
from ..utils.aws_clients import S3Client, DynamoDBClient
from ..utils.errors import ValidationError, ErrorCode
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ContentUploadHandler:
    """Handles content upload and storage"""
    
    # Supported file types as per Requirements 2.1
    SUPPORTED_VIDEO_FORMATS = {'.mp4', '.mov', '.avi'}
    SUPPORTED_AUDIO_FORMATS = {'.mp3', '.wav'}
    SUPPORTED_TEXT_FORMATS = {'.txt', '.md', '.pdf'}
    
    SUPPORTED_FORMATS = (
        SUPPORTED_VIDEO_FORMATS | 
        SUPPORTED_AUDIO_FORMATS | 
        SUPPORTED_TEXT_FORMATS
    )
    
    # Content type mappings
    CONTENT_TYPE_MAP = {
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.pdf': 'application/pdf'
    }
    
    def __init__(
        self,
        s3_client: Optional[S3Client] = None,
        dynamodb_client: Optional[DynamoDBClient] = None
    ):
        """Initialize ContentUploadHandler with AWS clients"""
        self.s3_client = s3_client or S3Client()
        self.dynamodb_client = dynamodb_client or DynamoDBClient()
        
        # Get configuration from environment
        self.content_bucket = os.environ.get(
            'S3_BUCKET_ORIGINAL_CONTENT',
            'original-content-bucket'
        )
        self.content_table = os.environ.get(
            'DYNAMODB_TABLE_ORIGINAL_CONTENT',
            'original_content'
        )
    
    def upload_content(
        self,
        user_id: str,
        file: BinaryIO,
        filename: str,
        content_type: Optional[str] = None
    ) -> ContentMetadata:
        """
        Upload original content and initiate processing
        
        Args:
            user_id: User ID uploading the content
            file: File object to upload
            filename: Original filename
            content_type: Optional content type (auto-detected if not provided)
        
        Returns:
            ContentMetadata with content_id and processing status
        
        Raises:
            ValidationError: If file type is unsupported
        
        Validates: Requirements 2.1, 2.2, 10.1, 10.2
        """
        # Validate file type
        file_extension = self._get_file_extension(filename)
        if file_extension not in self.SUPPORTED_FORMATS:
            logger.warning(
                "Unsupported file type",
                filename=filename,
                extension=file_extension
            )
            raise ValidationError(
                error_code=ErrorCode.INVALID_FILE_TYPE,
                message=f"Unsupported file type: {file_extension}. "
                        f"Supported formats: {', '.join(sorted(self.SUPPORTED_FORMATS))}",
                details={
                    "filename": filename,
                    "extension": file_extension,
                    "supported_formats": list(self.SUPPORTED_FORMATS)
                }
            )
        
        # Generate unique content ID
        content_id = str(uuid.uuid4())
        
        # Determine content type
        if not content_type:
            content_type = self.CONTENT_TYPE_MAP.get(
                file_extension,
                'application/octet-stream'
            )
        
        # Read file content
        file_content = file.read()
        
        # Upload to S3 with user-specific prefix
        s3_key = f"{user_id}/{content_id}{file_extension}"
        s3_uri = self.s3_client.upload_file(
            file_content=file_content,
            bucket=self.content_bucket,
            key=s3_key,
            content_type=content_type
        )
        
        # Extract text from PDF if applicable
        content_text = None
        if file_extension == '.pdf':
            try:
                import PyPDF2
                from io import BytesIO
                
                pdf_file = BytesIO(file_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                extracted_text = ""
                for page in pdf_reader.pages:
                    extracted_text += page.extract_text() + "\n"
                
                if extracted_text.strip():
                    content_text = extracted_text.strip()
                    logger.info(f"Extracted {len(content_text)} characters from PDF")
            except Exception as e:
                logger.warning(f"Failed to extract PDF text during upload: {str(e)}")
        elif file_extension in {'.txt', '.md'}:
            try:
                content_text = file_content.decode('utf-8')
            except Exception as e:
                logger.warning(f"Failed to decode text file: {str(e)}")
        
        # Create metadata
        metadata = ContentMetadata(
            content_id=content_id,
            user_id=user_id,
            filename=filename,
            s3_uri=s3_uri,
            content_type=content_type,
            uploaded_at=datetime.now(timezone.utc),
            processing_status=ProcessingStatusEnum.UPLOADED,
            content_text=content_text  # Store extracted text
        )
        
        # Store metadata in DynamoDB
        self.dynamodb_client.put_item(
            table_name=self.content_table,
            item=metadata.to_dynamodb_item()
        )
        
        logger.info(
            "Content uploaded successfully",
            content_id=content_id,
            user_id=user_id,
            filename=filename,
            size=len(file_content)
        )
        
        return metadata
    
    def get_upload_status(self, content_id: str) -> dict:
        """
        Get current processing status of uploaded content
        
        Args:
            content_id: Content ID to check status for
        
        Returns:
            Dictionary with stage and progress percentage
        
        Validates: Requirements 2.7
        """
        # Retrieve metadata from DynamoDB
        # Note: We need user_id as partition key, but for this method
        # we'll query by content_id using a GSI or scan (simplified for now)
        # In production, this would use a GSI on content_id
        
        # For now, we'll return a simplified status structure
        # This will be enhanced when implementing the full processing pipeline
        
        logger.info(
            "Retrieving upload status",
            content_id=content_id
        )
        
        return {
            "content_id": content_id,
            "stage": "uploaded",
            "progress_percentage": 0,
            "message": "Content uploaded, awaiting processing"
        }
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        if '.' not in filename:
            return ''
        return '.' + filename.rsplit('.', 1)[1].lower()
    
    def _is_media_file(self, file_extension: str) -> bool:
        """Check if file is video or audio (requires transcription)"""
        return (
            file_extension in self.SUPPORTED_VIDEO_FORMATS or
            file_extension in self.SUPPORTED_AUDIO_FORMATS
        )
    
    def _is_text_file(self, file_extension: str) -> bool:
        """Check if file is text (no transcription needed)"""
        return file_extension in self.SUPPORTED_TEXT_FORMATS
