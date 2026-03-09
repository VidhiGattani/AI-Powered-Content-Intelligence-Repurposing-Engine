"""
Unit tests for ContentUploadHandler
"""
import pytest
from io import BytesIO
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from src.services.content_upload_handler import ContentUploadHandler
from src.models.content import ContentMetadata
from src.models.enums import ProcessingStatus
from src.utils.errors import ValidationError, ErrorCode


class TestContentUploadHandler:
    """Test suite for ContentUploadHandler"""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client"""
        client = Mock()
        client.upload_file = Mock(return_value="s3://bucket/user123/content-id.mp4")
        return client
    
    @pytest.fixture
    def mock_dynamodb_client(self):
        """Mock DynamoDB client"""
        client = Mock()
        client.put_item = Mock()
        return client
    
    @pytest.fixture
    def handler(self, mock_s3_client, mock_dynamodb_client):
        """Create ContentUploadHandler with mocked clients"""
        return ContentUploadHandler(
            s3_client=mock_s3_client,
            dynamodb_client=mock_dynamodb_client
        )
    
    def test_upload_video_file_success(self, handler, mock_s3_client, mock_dynamodb_client):
        """Test successful video file upload"""
        # Arrange
        user_id = "user123"
        filename = "test_video.mp4"
        file_content = b"fake video content"
        file = BytesIO(file_content)
        
        # Act
        with patch('src.services.content_upload_handler.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = MagicMock(
                __str__=lambda x: "test-content-id"
            )
            metadata = handler.upload_content(
                user_id=user_id,
                file=file,
                filename=filename
            )
        
        # Assert
        assert metadata.user_id == user_id
        assert metadata.filename == filename
        assert metadata.content_type == "video/mp4"
        assert metadata.processing_status == ProcessingStatus.UPLOADED
        assert metadata.content_id == "test-content-id"
        
        # Verify S3 upload was called
        mock_s3_client.upload_file.assert_called_once()
        call_args = mock_s3_client.upload_file.call_args
        assert call_args.kwargs['file_content'] == file_content
        assert call_args.kwargs['content_type'] == "video/mp4"
        
        # Verify DynamoDB put was called
        mock_dynamodb_client.put_item.assert_called_once()
    
    def test_upload_audio_file_success(self, handler, mock_s3_client):
        """Test successful audio file upload"""
        # Arrange
        user_id = "user456"
        filename = "podcast.mp3"
        file = BytesIO(b"fake audio content")
        
        # Act
        metadata = handler.upload_content(
            user_id=user_id,
            file=file,
            filename=filename
        )
        
        # Assert
        assert metadata.content_type == "audio/mpeg"
        assert metadata.processing_status == ProcessingStatus.UPLOADED
    
    def test_upload_text_file_success(self, handler):
        """Test successful text file upload"""
        # Arrange
        user_id = "user789"
        filename = "article.txt"
        file = BytesIO(b"This is article content")
        
        # Act
        metadata = handler.upload_content(
            user_id=user_id,
            file=file,
            filename=filename
        )
        
        # Assert
        assert metadata.content_type == "text/plain"
        assert metadata.processing_status == ProcessingStatus.UPLOADED
    
    def test_upload_markdown_file_success(self, handler):
        """Test successful markdown file upload"""
        # Arrange
        filename = "notes.md"
        file = BytesIO(b"# Markdown content")
        
        # Act
        metadata = handler.upload_content(
            user_id="user123",
            file=file,
            filename=filename
        )
        
        # Assert
        assert metadata.content_type == "text/markdown"
    
    def test_upload_pdf_file_success(self, handler):
        """Test successful PDF file upload"""
        # Arrange
        filename = "document.pdf"
        file = BytesIO(b"%PDF-1.4 fake pdf content")
        
        # Act
        metadata = handler.upload_content(
            user_id="user123",
            file=file,
            filename=filename
        )
        
        # Assert
        assert metadata.content_type == "application/pdf"
    
    def test_upload_all_supported_video_formats(self, handler):
        """Test all supported video formats"""
        video_formats = ['.mp4', '.mov', '.avi']
        
        for ext in video_formats:
            filename = f"video{ext}"
            file = BytesIO(b"video content")
            
            metadata = handler.upload_content(
                user_id="user123",
                file=file,
                filename=filename
            )
            
            assert metadata.processing_status == ProcessingStatus.UPLOADED
    
    def test_upload_all_supported_audio_formats(self, handler):
        """Test all supported audio formats"""
        audio_formats = ['.mp3', '.wav']
        
        for ext in audio_formats:
            filename = f"audio{ext}"
            file = BytesIO(b"audio content")
            
            metadata = handler.upload_content(
                user_id="user123",
                file=file,
                filename=filename
            )
            
            assert metadata.processing_status == ProcessingStatus.UPLOADED
    
    def test_upload_unsupported_file_type_raises_error(self, handler):
        """Test that unsupported file types raise ValidationError"""
        # Arrange
        filename = "document.docx"
        file = BytesIO(b"unsupported content")
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            handler.upload_content(
                user_id="user123",
                file=file,
                filename=filename
            )
        
        assert exc_info.value.error_code == ErrorCode.INVALID_FILE_TYPE
        assert ".docx" in exc_info.value.message
        assert "supported_formats" in exc_info.value.details
    
    def test_upload_file_without_extension_raises_error(self, handler):
        """Test that files without extension raise ValidationError"""
        # Arrange
        filename = "noextension"
        file = BytesIO(b"content")
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            handler.upload_content(
                user_id="user123",
                file=file,
                filename=filename
            )
        
        assert exc_info.value.error_code == ErrorCode.INVALID_FILE_TYPE
    
    def test_upload_with_custom_content_type(self, handler, mock_s3_client):
        """Test upload with custom content type"""
        # Arrange
        filename = "video.mp4"
        file = BytesIO(b"video content")
        custom_content_type = "video/custom"
        
        # Act
        metadata = handler.upload_content(
            user_id="user123",
            file=file,
            filename=filename,
            content_type=custom_content_type
        )
        
        # Assert
        assert metadata.content_type == custom_content_type
        
        # Verify S3 was called with custom content type
        call_args = mock_s3_client.upload_file.call_args
        assert call_args.kwargs['content_type'] == custom_content_type
    
    def test_upload_generates_unique_content_id(self, handler):
        """Test that each upload generates a unique content ID"""
        # Arrange
        file1 = BytesIO(b"content 1")
        file2 = BytesIO(b"content 2")
        
        # Act
        metadata1 = handler.upload_content(
            user_id="user123",
            file=file1,
            filename="file1.mp4"
        )
        metadata2 = handler.upload_content(
            user_id="user123",
            file=file2,
            filename="file2.mp4"
        )
        
        # Assert
        assert metadata1.content_id != metadata2.content_id
    
    def test_upload_stores_correct_s3_key_structure(self, handler, mock_s3_client):
        """Test that S3 key follows user_id/content_id.ext pattern"""
        # Arrange
        user_id = "user123"
        filename = "video.mp4"
        file = BytesIO(b"content")
        
        # Act
        with patch('src.services.content_upload_handler.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = MagicMock(
                __str__=lambda x: "content-id-123"
            )
            handler.upload_content(
                user_id=user_id,
                file=file,
                filename=filename
            )
        
        # Assert
        call_args = mock_s3_client.upload_file.call_args
        assert call_args.kwargs['key'] == "user123/content-id-123.mp4"
    
    def test_upload_case_insensitive_extension(self, handler):
        """Test that file extensions are case-insensitive"""
        # Arrange
        filenames = ["video.MP4", "video.Mp4", "video.mP4"]
        
        for filename in filenames:
            file = BytesIO(b"content")
            
            # Act
            metadata = handler.upload_content(
                user_id="user123",
                file=file,
                filename=filename
            )
            
            # Assert
            assert metadata.content_type == "video/mp4"
    
    def test_get_upload_status(self, handler):
        """Test getting upload status"""
        # Arrange
        content_id = "test-content-id"
        
        # Act
        status = handler.get_upload_status(content_id)
        
        # Assert
        assert status["content_id"] == content_id
        assert "stage" in status
        assert "progress_percentage" in status
        assert isinstance(status["progress_percentage"], int)
    
    def test_metadata_contains_required_fields(self, handler):
        """Test that metadata contains all required fields per Requirement 10.2"""
        # Arrange
        file = BytesIO(b"content")
        
        # Act
        metadata = handler.upload_content(
            user_id="user123",
            file=file,
            filename="test.mp4"
        )
        
        # Assert - Property 38: Metadata completeness
        assert metadata.user_id is not None
        assert metadata.content_id is not None
        assert metadata.uploaded_at is not None
        assert isinstance(metadata.uploaded_at, datetime)
        assert metadata.processing_status is not None
    
    def test_s3_uri_stored_in_metadata(self, handler, mock_s3_client):
        """Test that S3 URI is stored in metadata"""
        # Arrange
        expected_uri = "s3://bucket/user123/content-id.mp4"
        mock_s3_client.upload_file.return_value = expected_uri
        file = BytesIO(b"content")
        
        # Act
        metadata = handler.upload_content(
            user_id="user123",
            file=file,
            filename="test.mp4"
        )
        
        # Assert
        assert metadata.s3_uri == expected_uri
    
    def test_dynamodb_item_format(self, handler, mock_dynamodb_client):
        """Test that DynamoDB item has correct format"""
        # Arrange
        file = BytesIO(b"content")
        
        # Act
        handler.upload_content(
            user_id="user123",
            file=file,
            filename="test.mp4"
        )
        
        # Assert
        call_args = mock_dynamodb_client.put_item.call_args
        item = call_args.kwargs['item']
        
        assert 'content_id' in item
        assert 'user_id' in item
        assert 'filename' in item
        assert 's3_uri' in item
        assert 'content_type' in item
        assert 'uploaded_at' in item
        assert 'processing_status' in item
