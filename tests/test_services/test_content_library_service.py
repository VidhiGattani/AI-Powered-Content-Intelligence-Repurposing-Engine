"""
Unit tests for ContentLibraryService
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from src.services.content_library_service import ContentLibraryService
from src.models.content import ContentMetadata
from src.models.enums import ProcessingStatus


class TestContentLibraryService:
    """Test suite for ContentLibraryService"""
    
    @pytest.fixture
    def mock_dynamodb_client(self):
        """Mock DynamoDB client"""
        client = Mock()
        mock_table = Mock()
        client.resource = Mock()
        client.resource.Table = Mock(return_value=mock_table)
        return client
    
    @pytest.fixture
    def service(self, mock_dynamodb_client):
        """Create ContentLibraryService with mocked client"""
        return ContentLibraryService(dynamodb_client=mock_dynamodb_client)
    
    @pytest.fixture
    def sample_content_items(self):
        """Create sample content items for testing"""
        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        return [
            {
                'content_id': 'content-1',
                'user_id': 'user123',
                'filename': 'video1.mp4',
                's3_uri': 's3://bucket/user123/content-1.mp4',
                'content_type': 'video/mp4',
                'uploaded_at': base_time.isoformat(),
                'processing_status': 'uploaded'
            },
            {
                'content_id': 'content-2',
                'user_id': 'user123',
                'filename': 'video2.mp4',
                's3_uri': 's3://bucket/user123/content-2.mp4',
                'content_type': 'video/mp4',
                'uploaded_at': base_time.replace(hour=13).isoformat(),
                'processing_status': 'ready'
            },
            {
                'content_id': 'content-3',
                'user_id': 'user123',
                'filename': 'audio1.mp3',
                's3_uri': 's3://bucket/user123/content-3.mp3',
                'content_type': 'audio/mp3',
                'uploaded_at': base_time.replace(hour=14).isoformat(),
                'processing_status': 'ready'
            }
        ]
    
    def test_get_user_content_returns_sorted_by_date_descending(
        self, service, mock_dynamodb_client, sample_content_items
    ):
        """Test that content is returned sorted by creation date descending
        Validates: Requirements 10.4"""
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {'Items': sample_content_items}
        
        result = service.get_user_content('user123')
        
        assert len(result['items']) == 3
        assert result['items'][0].content_id == 'content-3'
        assert result['items'][1].content_id == 'content-2'
        assert result['items'][2].content_id == 'content-1'
    
    def test_get_user_content_with_pagination_limit(
        self, service, mock_dynamodb_client, sample_content_items
    ):
        """Test pagination with limit parameter
        Validates: Requirements 10.4"""
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {'Items': sample_content_items}
        
        result = service.get_user_content('user123', limit=2)
        
        assert len(result['items']) == 2
        assert result['total_count'] == 3
        assert result['has_more'] is True
    
    def test_get_user_content_with_pagination_offset(
        self, service, mock_dynamodb_client, sample_content_items
    ):
        """Test pagination with offset parameter
        Validates: Requirements 10.4"""
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {'Items': sample_content_items}
        
        result = service.get_user_content('user123', limit=2, offset=1)
        
        assert len(result['items']) == 2
        assert result['total_count'] == 3
        assert result['offset'] == 1
        assert result['has_more'] is False
        assert result['items'][0].content_id == 'content-2'
        assert result['items'][1].content_id == 'content-1'
    
    def test_get_user_content_empty_library(
        self, service, mock_dynamodb_client
    ):
        """Test retrieving content when user has no content
        Validates: Requirements 10.3"""
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {'Items': []}
        
        result = service.get_user_content('user123')
        
        assert len(result['items']) == 0
        assert result['total_count'] == 0
        assert result['has_more'] is False
    
    def test_get_user_content_queries_correct_user(
        self, service, mock_dynamodb_client, sample_content_items
    ):
        """Test that query filters by user_id correctly
        Validates: Requirements 10.3"""
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {'Items': sample_content_items}
        
        service.get_user_content('user123')
        
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs['KeyConditionExpression'] == 'user_id = :uid'
        assert call_kwargs['ExpressionAttributeValues'] == {':uid': 'user123'}
        assert call_kwargs['ScanIndexForward'] is False
    
    def test_get_user_content_default_pagination_values(
        self, service, mock_dynamodb_client, sample_content_items
    ):
        """Test default pagination values
        Validates: Requirements 10.4"""
        mock_table = mock_dynamodb_client.resource.Table.return_value
        mock_table.query.return_value = {'Items': sample_content_items}
        
        result = service.get_user_content('user123')
        
        assert result['limit'] == 50
        assert result['offset'] == 0
