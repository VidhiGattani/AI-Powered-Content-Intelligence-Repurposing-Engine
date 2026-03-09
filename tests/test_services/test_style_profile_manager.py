"""
Unit tests for StyleProfileManager
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from io import BytesIO
from botocore.exceptions import ClientError

from src.services.style_profile_manager import StyleProfileManager
from src.models import StyleContentMetadata, StyleProfile, StyleProfileStatus, EmbeddingStatus, EmbeddingResult
from src.utils.errors import ValidationError, NotFoundError, ErrorCode, ProcessingError


class TestStyleProfileManager:
    """Test suite for StyleProfileManager"""
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client"""
        return Mock()
    
    @pytest.fixture
    def mock_dynamodb_client(self):
        """Mock DynamoDB client"""
        mock_client = Mock()
        # Mock the resource attribute for query operations
        mock_resource = Mock()
        mock_table = Mock()
        mock_resource.Table.return_value = mock_table
        mock_client.resource = mock_resource
        return mock_client
    
    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock Bedrock client"""
        return Mock()
    
    @pytest.fixture
    def style_manager(self, mock_s3_client, mock_dynamodb_client, mock_bedrock_client):
        """Create StyleProfileManager with mocked dependencies"""
        manager = StyleProfileManager(
            s3_client=mock_s3_client,
            dynamodb_client=mock_dynamodb_client,
            bedrock_client=mock_bedrock_client
        )
        manager.style_content_table = "test-style-content-table"
        manager.users_table = "test-users-table"
        manager.style_vault_bucket = "test-style-vault-bucket"
        manager.knowledge_base_id = "test-kb-id"
        return manager
    
    # Tests for upload_style_content()
    
    def test_upload_style_content_success_txt(
        self,
        style_manager,
        mock_s3_client,
        mock_dynamodb_client
    ):
        """Test successful upload of .txt file"""
        # Arrange
        user_id = "test-user-123"
        filename = "style_sample.txt"
        content = b"This is my writing style sample."
        file = BytesIO(content)
        content_type = "text/plain"
        
        mock_s3_client.upload_file.return_value = f"s3://test-style-vault-bucket/{user_id}/test-content-id.txt"
        
        # Act
        with patch('uuid.uuid4', return_value=Mock(hex='test-content-id')):
            result = style_manager.upload_style_content(
                user_id=user_id,
                file=file,
                filename=filename,
                content_type=content_type
            )
        
        # Assert
        assert isinstance(result, StyleContentMetadata)
        assert result.user_id == user_id
        assert result.filename == filename
        assert result.content_type == content_type
        assert result.embedding_status == EmbeddingStatus.PENDING
        
        # Verify S3 upload was called
        mock_s3_client.upload_file.assert_called_once()
        s3_call_args = mock_s3_client.upload_file.call_args[1]
        assert s3_call_args["bucket"] == "test-style-vault-bucket"
        assert s3_call_args["content_type"] == content_type
        assert s3_call_args["file_content"] == content
        
        # Verify DynamoDB put_item was called
        mock_dynamodb_client.put_item.assert_called_once()
        db_call_args = mock_dynamodb_client.put_item.call_args[1]
        assert db_call_args["table_name"] == "test-style-content-table"
        
        # Verify update_item was called to increment count
        mock_dynamodb_client.update_item.assert_called_once()
    
    def test_upload_style_content_success_all_supported_types(
        self,
        style_manager,
        mock_s3_client,
        mock_dynamodb_client
    ):
        """Test upload with all supported file types"""
        user_id = "test-user-123"
        supported_files = [
            ("sample.txt", "text/plain"),
            ("sample.md", "text/markdown"),
            ("sample.pdf", "application/pdf"),
            ("sample.doc", "application/msword"),
            ("sample.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        ]
        
        for filename, content_type in supported_files:
            # Arrange
            content = b"Sample content"
            file = BytesIO(content)
            mock_s3_client.upload_file.return_value = f"s3://bucket/{user_id}/id"
            
            # Act
            result = style_manager.upload_style_content(
                user_id=user_id,
                file=file,
                filename=filename,
                content_type=content_type
            )
            
            # Assert
            assert isinstance(result, StyleContentMetadata)
            assert result.filename == filename
    
    def test_upload_style_content_invalid_file_type(self, style_manager):
        """Test upload with unsupported file type"""
        # Arrange
        user_id = "test-user-123"
        invalid_files = [
            "video.mp4",
            "audio.mp3",
            "image.jpg",
            "script.py",
            "data.json"
        ]
        
        for filename in invalid_files:
            # Arrange
            file = BytesIO(b"content")
            
            # Act & Assert
            with pytest.raises(ValidationError) as exc_info:
                style_manager.upload_style_content(
                    user_id=user_id,
                    file=file,
                    filename=filename,
                    content_type="application/octet-stream"
                )
            
            assert exc_info.value.error_code == ErrorCode.INVALID_FILE_TYPE
            assert "unsupported" in exc_info.value.message.lower()
            assert filename.split('.')[-1] in exc_info.value.message.lower() or \
                   f".{filename.split('.')[-1]}" in exc_info.value.message.lower()
    
    def test_upload_style_content_no_extension(self, style_manager):
        """Test upload with filename without extension"""
        # Arrange
        user_id = "test-user-123"
        filename = "noextension"
        file = BytesIO(b"content")
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            style_manager.upload_style_content(
                user_id=user_id,
                file=file,
                filename=filename,
                content_type="text/plain"
            )
        
        assert exc_info.value.error_code == ErrorCode.INVALID_FILE_TYPE
    
    def test_upload_style_content_case_insensitive_extension(
        self,
        style_manager,
        mock_s3_client,
        mock_dynamodb_client
    ):
        """Test that file extensions are case-insensitive"""
        # Arrange
        user_id = "test-user-123"
        filenames = ["sample.TXT", "sample.Md", "sample.PDF", "sample.DOCX"]
        
        for filename in filenames:
            # Arrange
            file = BytesIO(b"content")
            mock_s3_client.upload_file.return_value = f"s3://bucket/{user_id}/id"
            
            # Act
            result = style_manager.upload_style_content(
                user_id=user_id,
                file=file,
                filename=filename,
                content_type="text/plain"
            )
            
            # Assert
            assert isinstance(result, StyleContentMetadata)
    
    def test_upload_style_content_s3_error(
        self,
        style_manager,
        mock_s3_client
    ):
        """Test handling of S3 upload errors"""
        # Arrange
        user_id = "test-user-123"
        filename = "sample.txt"
        file = BytesIO(b"content")
        
        error_response = {
            'Error': {
                'Code': 'ServiceUnavailable',
                'Message': 'S3 service unavailable'
            }
        }
        mock_s3_client.upload_file.side_effect = ClientError(
            error_response,
            'PutObject'
        )
        
        # Act & Assert
        with pytest.raises(Exception):  # Should raise ExternalServiceError
            style_manager.upload_style_content(
                user_id=user_id,
                file=file,
                filename=filename,
                content_type="text/plain"
            )
    
    # Tests for get_style_profile()
    
    def test_get_style_profile_ready(
        self,
        style_manager,
        mock_dynamodb_client
    ):
        """Test getting style profile with >= 3 content pieces (READY)"""
        # Arrange
        user_id = "test-user-123"
        
        # Mock user data
        user_data = {
            'user_id': user_id,
            'email': 'test@example.com',
            'created_at': datetime.utcnow().isoformat(),
            'style_profile_status': 'incomplete',
            'style_content_count': 3
        }
        mock_dynamodb_client.get_item.return_value = user_data
        
        # Mock style content query
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {
            'Items': [
                {'content_id': '1', 'user_id': user_id},
                {'content_id': '2', 'user_id': user_id},
                {'content_id': '3', 'user_id': user_id}
            ]
        }
        
        # Act
        result = style_manager.get_style_profile(user_id)
        
        # Assert
        assert isinstance(result, StyleProfile)
        assert result.user_id == user_id
        assert result.status == StyleProfileStatus.READY
        assert result.content_count == 3
        
        # Verify DynamoDB was called
        mock_dynamodb_client.get_item.assert_called_once()
        mock_table.query.assert_called_once()
    
    def test_get_style_profile_incomplete(
        self,
        style_manager,
        mock_dynamodb_client
    ):
        """Test getting style profile with < 3 content pieces (INCOMPLETE)"""
        # Arrange
        user_id = "test-user-123"
        
        # Mock user data
        user_data = {
            'user_id': user_id,
            'email': 'test@example.com',
            'created_at': datetime.utcnow().isoformat(),
            'style_profile_status': 'incomplete',
            'style_content_count': 1
        }
        mock_dynamodb_client.get_item.return_value = user_data
        
        # Mock style content query with only 1 item
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {
            'Items': [
                {'content_id': '1', 'user_id': user_id}
            ]
        }
        
        # Act
        result = style_manager.get_style_profile(user_id)
        
        # Assert
        assert isinstance(result, StyleProfile)
        assert result.user_id == user_id
        assert result.status == StyleProfileStatus.INCOMPLETE
        assert result.content_count == 1
    
    def test_get_style_profile_no_content(
        self,
        style_manager,
        mock_dynamodb_client
    ):
        """Test getting style profile with 0 content pieces"""
        # Arrange
        user_id = "test-user-123"
        
        # Mock user data
        user_data = {
            'user_id': user_id,
            'email': 'test@example.com',
            'created_at': datetime.utcnow().isoformat(),
            'style_profile_status': 'incomplete',
            'style_content_count': 0
        }
        mock_dynamodb_client.get_item.return_value = user_data
        
        # Mock style content query with no items
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {'Items': []}
        
        # Act
        result = style_manager.get_style_profile(user_id)
        
        # Assert
        assert isinstance(result, StyleProfile)
        assert result.status == StyleProfileStatus.INCOMPLETE
        assert result.content_count == 0
    
    def test_get_style_profile_user_not_found(
        self,
        style_manager,
        mock_dynamodb_client
    ):
        """Test getting style profile when user doesn't exist"""
        # Arrange
        user_id = "nonexistent-user"
        mock_dynamodb_client.get_item.return_value = None
        
        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            style_manager.get_style_profile(user_id)
        
        assert exc_info.value.error_code == ErrorCode.USER_NOT_FOUND
        assert user_id in exc_info.value.message
    
    def test_get_style_profile_exactly_three_pieces(
        self,
        style_manager,
        mock_dynamodb_client
    ):
        """Test boundary condition: exactly 3 pieces should be READY"""
        # Arrange
        user_id = "test-user-123"
        
        user_data = {
            'user_id': user_id,
            'email': 'test@example.com',
            'created_at': datetime.utcnow().isoformat(),
            'style_profile_status': 'incomplete',
            'style_content_count': 3
        }
        mock_dynamodb_client.get_item.return_value = user_data
        
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {
            'Items': [{'content_id': str(i), 'user_id': user_id} for i in range(3)]
        }
        
        # Act
        result = style_manager.get_style_profile(user_id)
        
        # Assert
        assert result.status == StyleProfileStatus.READY
        assert result.content_count == 3
    
    # Tests for is_profile_ready()
    
    def test_is_profile_ready_true(
        self,
        style_manager,
        mock_dynamodb_client
    ):
        """Test is_profile_ready returns True when >= 3 pieces"""
        # Arrange
        user_id = "test-user-123"
        
        user_data = {
            'user_id': user_id,
            'email': 'test@example.com',
            'created_at': datetime.utcnow().isoformat(),
            'style_profile_status': 'ready',
            'style_content_count': 5
        }
        mock_dynamodb_client.get_item.return_value = user_data
        
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {
            'Items': [{'content_id': str(i), 'user_id': user_id} for i in range(5)]
        }
        
        # Act
        result = style_manager.is_profile_ready(user_id)
        
        # Assert
        assert result is True
    
    def test_is_profile_ready_false(
        self,
        style_manager,
        mock_dynamodb_client
    ):
        """Test is_profile_ready returns False when < 3 pieces"""
        # Arrange
        user_id = "test-user-123"
        
        user_data = {
            'user_id': user_id,
            'email': 'test@example.com',
            'created_at': datetime.utcnow().isoformat(),
            'style_profile_status': 'incomplete',
            'style_content_count': 2
        }
        mock_dynamodb_client.get_item.return_value = user_data
        
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {
            'Items': [{'content_id': str(i), 'user_id': user_id} for i in range(2)]
        }
        
        # Act
        result = style_manager.is_profile_ready(user_id)
        
        # Assert
        assert result is False
    
    def test_is_profile_ready_user_not_found(
        self,
        style_manager,
        mock_dynamodb_client
    ):
        """Test is_profile_ready returns False when user doesn't exist"""
        # Arrange
        user_id = "nonexistent-user"
        mock_dynamodb_client.get_item.return_value = None
        
        # Act
        result = style_manager.is_profile_ready(user_id)
        
        # Assert
        assert result is False
    
    def test_is_profile_ready_boundary_exactly_three(
        self,
        style_manager,
        mock_dynamodb_client
    ):
        """Test boundary: exactly 3 pieces should return True"""
        # Arrange
        user_id = "test-user-123"
        
        user_data = {
            'user_id': user_id,
            'email': 'test@example.com',
            'created_at': datetime.utcnow().isoformat(),
            'style_profile_status': 'ready',
            'style_content_count': 3
        }
        mock_dynamodb_client.get_item.return_value = user_data
        
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {
            'Items': [{'content_id': str(i), 'user_id': user_id} for i in range(3)]
        }
        
        # Act
        result = style_manager.is_profile_ready(user_id)
        
        # Assert
        assert result is True
    
    # Tests for helper methods
    
    def test_get_file_extension(self, style_manager):
        """Test file extension extraction"""
        # Test valid extensions
        assert style_manager._get_file_extension("file.txt") == ".txt"
        assert style_manager._get_file_extension("file.PDF") == ".pdf"
        assert style_manager._get_file_extension("my.file.docx") == ".docx"
        
        # Test no extension
        assert style_manager._get_file_extension("noextension") == ""
        
        # Test edge cases
        assert style_manager._get_file_extension(".hidden") == ".hidden"
        assert style_manager._get_file_extension("file.") == "."
    
    def test_increment_style_content_count(
        self,
        style_manager,
        mock_dynamodb_client
    ):
        """Test incrementing style content count"""
        # Arrange
        user_id = "test-user-123"
        
        # Act
        style_manager._increment_style_content_count(user_id)
        
        # Assert
        mock_dynamodb_client.update_item.assert_called_once()
        call_args = mock_dynamodb_client.update_item.call_args[1]
        assert call_args["table_name"] == "test-users-table"
        assert call_args["key"]["user_id"] == user_id
        assert "style_content_count" in call_args["update_expression"]
    
    def test_increment_style_content_count_error_handling(
        self,
        style_manager,
        mock_dynamodb_client
    ):
        """Test that increment errors don't fail the upload"""
        # Arrange
        user_id = "test-user-123"
        mock_dynamodb_client.update_item.side_effect = Exception("DynamoDB error")
        
        # Act - should not raise exception
        style_manager._increment_style_content_count(user_id)
        
        # Assert - method should complete without raising
        mock_dynamodb_client.update_item.assert_called_once()

    # Tests for generate_embeddings()
    
    def test_generate_embeddings_success(
        self,
        style_manager,
        mock_s3_client,
        mock_dynamodb_client,
        mock_bedrock_client
    ):
        """Test successful embedding generation"""
        # Arrange
        user_id = "test-user-123"
        content_id = "test-content-456"
        
        # Mock metadata retrieval
        metadata = {
            'user_id': user_id,
            'content_id': content_id,
            's3_uri': 's3://test-style-vault-bucket/test-user-123/test-content-456.txt',
            'embedding_status': 'PENDING'
        }
        mock_dynamodb_client.get_item.return_value = metadata
        
        # Mock S3 download
        content_text = "This is my unique writing style."
        mock_s3_client.download_file.return_value = content_text.encode('utf-8')
        
        # Mock Bedrock response with embedding vector
        embedding_vector = [0.1] * 1536  # Titan G1 produces 1536-dimensional vectors
        mock_bedrock_client.invoke_model.return_value = {
            'embedding': embedding_vector
        }
        
        # Act
        with patch('uuid.uuid4', return_value=Mock(hex='test-embedding-id')):
            result = style_manager.generate_embeddings(user_id, content_id)
        
        # Assert
        assert isinstance(result, EmbeddingResult)
        assert result.user_id == user_id
        assert result.content_id == content_id
        assert result.vector_dimensions == 1536
        assert result.model_id == "amazon.titan-embed-text-v1"
        assert len(result.embedding_vector) == 1536
        
        # Verify S3 download was called
        mock_s3_client.download_file.assert_called_once_with(
            "test-style-vault-bucket",
            "test-user-123/test-content-456.txt"
        )
        
        # Verify Bedrock was called with correct parameters
        mock_bedrock_client.invoke_model.assert_called_once()
        bedrock_call = mock_bedrock_client.invoke_model.call_args[1]
        assert bedrock_call['model_id'] == "amazon.titan-embed-text-v1"
        assert bedrock_call['body']['inputText'] == content_text
        
        # Verify DynamoDB update to COMPLETED status
        mock_dynamodb_client.update_item.assert_called_once()
        update_call = mock_dynamodb_client.update_item.call_args[1]
        assert update_call['table_name'] == "test-style-content-table"
        assert EmbeddingStatus.COMPLETED.value in str(update_call['expression_attribute_values'])
    
    def test_generate_embeddings_content_not_found(
        self,
        style_manager,
        mock_dynamodb_client
    ):
        """Test embedding generation when content doesn't exist"""
        # Arrange
        user_id = "test-user-123"
        content_id = "nonexistent-content"
        
        mock_dynamodb_client.get_item.return_value = None
        
        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            style_manager.generate_embeddings(user_id, content_id)
        
        assert exc_info.value.error_code == ErrorCode.CONTENT_NOT_FOUND
        assert content_id in exc_info.value.message
    
    def test_generate_embeddings_empty_vector(
        self,
        style_manager,
        mock_s3_client,
        mock_dynamodb_client,
        mock_bedrock_client
    ):
        """Test handling of empty embedding vector from Bedrock"""
        # Arrange
        user_id = "test-user-123"
        content_id = "test-content-456"
        
        metadata = {
            'user_id': user_id,
            'content_id': content_id,
            's3_uri': 's3://test-style-vault-bucket/test-user-123/test-content-456.txt',
            'embedding_status': 'PENDING'
        }
        mock_dynamodb_client.get_item.return_value = metadata
        mock_s3_client.download_file.return_value = b"Content"
        
        # Mock Bedrock returning empty embedding
        mock_bedrock_client.invoke_model.return_value = {'embedding': []}
        
        # Act & Assert
        with pytest.raises(ProcessingError) as exc_info:
            style_manager.generate_embeddings(user_id, content_id)
        
        assert exc_info.value.error_code == ErrorCode.EMBEDDING_GENERATION_FAILED
        assert "empty vector" in exc_info.value.message.lower()
    
    def test_generate_embeddings_bedrock_error(
        self,
        style_manager,
        mock_s3_client,
        mock_dynamodb_client,
        mock_bedrock_client
    ):
        """Test handling of Bedrock API errors"""
        # Arrange
        user_id = "test-user-123"
        content_id = "test-content-456"
        
        metadata = {
            'user_id': user_id,
            'content_id': content_id,
            's3_uri': 's3://test-style-vault-bucket/test-user-123/test-content-456.txt',
            'embedding_status': 'PENDING'
        }
        mock_dynamodb_client.get_item.return_value = metadata
        mock_s3_client.download_file.return_value = b"Content"
        
        # Mock Bedrock error
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate limit exceeded'
            }
        }
        mock_bedrock_client.invoke_model.side_effect = ClientError(
            error_response,
            'InvokeModel'
        )
        
        # Act & Assert
        with pytest.raises(ProcessingError) as exc_info:
            style_manager.generate_embeddings(user_id, content_id)
        
        assert exc_info.value.error_code == ErrorCode.EMBEDDING_GENERATION_FAILED
        
        # Verify status was updated to FAILED
        # The update_item should be called twice: once for the error, once for status update
        assert mock_dynamodb_client.update_item.call_count >= 1
    
    def test_generate_embeddings_s3_download_error(
        self,
        style_manager,
        mock_s3_client,
        mock_dynamodb_client
    ):
        """Test handling of S3 download errors"""
        # Arrange
        user_id = "test-user-123"
        content_id = "test-content-456"
        
        metadata = {
            'user_id': user_id,
            'content_id': content_id,
            's3_uri': 's3://test-style-vault-bucket/test-user-123/test-content-456.txt',
            'embedding_status': 'PENDING'
        }
        mock_dynamodb_client.get_item.return_value = metadata
        
        # Mock S3 error
        error_response = {
            'Error': {
                'Code': 'NoSuchKey',
                'Message': 'The specified key does not exist'
            }
        }
        mock_s3_client.download_file.side_effect = ClientError(
            error_response,
            'GetObject'
        )
        
        # Act & Assert
        with pytest.raises(Exception):  # Will raise ExternalServiceError from S3Client
            style_manager.generate_embeddings(user_id, content_id)
    
    def test_generate_embeddings_updates_status_on_failure(
        self,
        style_manager,
        mock_s3_client,
        mock_dynamodb_client,
        mock_bedrock_client
    ):
        """Test that embedding status is updated to FAILED on errors"""
        # Arrange
        user_id = "test-user-123"
        content_id = "test-content-456"
        
        metadata = {
            'user_id': user_id,
            'content_id': content_id,
            's3_uri': 's3://test-style-vault-bucket/test-user-123/test-content-456.txt',
            'embedding_status': 'PENDING'
        }
        mock_dynamodb_client.get_item.return_value = metadata
        mock_s3_client.download_file.return_value = b"Content"
        
        # Mock Bedrock error
        mock_bedrock_client.invoke_model.side_effect = Exception("Unexpected error")
        
        # Act & Assert
        with pytest.raises(ProcessingError):
            style_manager.generate_embeddings(user_id, content_id)
        
        # Verify status update to FAILED was attempted
        update_calls = mock_dynamodb_client.update_item.call_args_list
        assert len(update_calls) >= 1
        
        # Check that one of the calls updates to FAILED status
        failed_status_updated = any(
            EmbeddingStatus.FAILED.value in str(call[1].get('expression_attribute_values', {}))
            for call in update_calls
        )
        assert failed_status_updated
    
    def test_generate_embeddings_correct_vector_dimensions(
        self,
        style_manager,
        mock_s3_client,
        mock_dynamodb_client,
        mock_bedrock_client
    ):
        """Test that vector dimensions are correctly captured"""
        # Arrange
        user_id = "test-user-123"
        content_id = "test-content-456"
        
        metadata = {
            'user_id': user_id,
            'content_id': content_id,
            's3_uri': 's3://test-style-vault-bucket/test-user-123/test-content-456.txt',
            'embedding_status': 'PENDING'
        }
        mock_dynamodb_client.get_item.return_value = metadata
        mock_s3_client.download_file.return_value = b"Content"
        
        # Test with Titan G1's 1536 dimensions
        embedding_vector = [0.5] * 1536
        mock_bedrock_client.invoke_model.return_value = {
            'embedding': embedding_vector
        }
        
        # Act
        result = style_manager.generate_embeddings(user_id, content_id)
        
        # Assert
        assert result.vector_dimensions == 1536
        assert len(result.embedding_vector) == 1536
