"""
Unit tests for ContentLibraryService delete_content method
"""

import pytest
from unittest.mock import Mock, patch

from src.services.content_library_service import ContentLibraryService
from src.utils.errors import NotFoundError, ErrorCode


class TestDeleteContent:
    """Tests for delete_content method"""
    
    @patch('src.services.content_library_service.DynamoDBClient')
    def test_delete_content_success(self, mock_client_class):
        """Test successful content deletion"""
        mock_dynamodb = Mock()
        mock_client_class.return_value = mock_dynamodb
        
        mock_dynamodb.get_item.return_value = {
            "user_id": "user123",
            "content_id": "content456",
            "s3_uri": "s3://bucket/key.mp4"
        }
        
        service = ContentLibraryService()
        result = service.delete_content("content456", "user123")
        
        assert result is True
        mock_dynamodb.update_item.assert_called_once()
    
    @patch('src.services.content_library_service.DynamoDBClient')
    def test_delete_content_not_found(self, mock_client_class):
        """Test deleting non-existent content"""
        mock_dynamodb = Mock()
        mock_client_class.return_value = mock_dynamodb
        
        mock_dynamodb.get_item.return_value = None
        
        service = ContentLibraryService()
        
        with pytest.raises(NotFoundError) as exc_info:
            service.delete_content("nonexistent", "user123")
        
        assert exc_info.value.error_code == ErrorCode.CONTENT_NOT_FOUND
    
    @patch('src.services.content_library_service.DynamoDBClient')
    def test_delete_content_without_s3_uri(self, mock_client_class):
        """Test deleting content without S3 URI"""
        mock_dynamodb = Mock()
        mock_client_class.return_value = mock_dynamodb
        
        mock_dynamodb.get_item.return_value = {
            "user_id": "user123",
            "content_id": "content456"
            # No s3_uri
        }
        
        service = ContentLibraryService()
        result = service.delete_content("content456", "user123")
        
        assert result is True
        mock_dynamodb.update_item.assert_called_once()
