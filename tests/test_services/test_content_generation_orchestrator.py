"""
Unit tests for ContentGenerationOrchestrator
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.services.content_generation_orchestrator import (
    ContentGenerationOrchestrator,
    GeneratedContent,
    GenerationRequest
)
from src.models.enums import Platform
from src.services.topic_extraction_service import Topic
from src.services.platform_agents import GeneratedContent as PlatformGeneratedContent
from src.services.style_retrieval_service import StylePatterns, WritingCharacteristics
from src.utils.errors import ProcessingError, ErrorCode


@pytest.fixture
def mock_s3_client():
    """Mock S3 client"""
    client = Mock()
    client.put_object = Mock()
    return client


@pytest.fixture
def mock_dynamodb_client():
    """Mock DynamoDB client"""
    client = Mock()
    client.put_item = Mock()
    client.query = Mock(return_value={'Items': []})
    return client


@pytest.fixture
def mock_style_retrieval_service():
    """Mock StyleRetrievalService"""
    service = Mock()
    service.retrieve_style_patterns = Mock(return_value=StylePatterns(
        examples=["Sample 1", "Sample 2", "Sample 3"],
        characteristics=WritingCharacteristics(
            sentence_structure={"avg_length": 15, "complexity": "medium"},
            vocabulary={"level": "professional", "unique_words": 500},
            tone="professional",
            emoji_usage={"frequency": "low", "types": []},
            common_phrases=["let's dive in", "key takeaway"],
            punctuation_style={"exclamation_marks": "rare", "questions": "occasional"}
        ),
        user_id="user123"
    ))
    return service


@pytest.fixture
def sample_topics():
    """Sample topics"""
    return [
        Topic(name="AI Technology", description="Discussion of AI advancements", relevance_score=0.95),
        Topic(name="Machine Learning", description="ML applications", relevance_score=0.90),
        Topic(name="Data Science", description="Data analysis techniques", relevance_score=0.85)
    ]


@pytest.fixture
def orchestrator(mock_s3_client, mock_dynamodb_client, mock_style_retrieval_service):
    """Create orchestrator with mocked dependencies"""
    return ContentGenerationOrchestrator(
        s3_client=mock_s3_client,
        dynamodb_client=mock_dynamodb_client,
        style_retrieval_service=mock_style_retrieval_service
    )


class TestGenerateForPlatforms:
    """Tests for generate_for_platforms method"""
    
    @patch('src.services.content_generation_orchestrator.PlatformAgentFactory')
    def test_generate_single_platform_success(
        self,
        mock_factory,
        orchestrator,
        sample_topics,
        mock_s3_client,
        mock_dynamodb_client
    ):
        """Test successful generation for single platform"""
        # Setup mock agent
        mock_agent = Mock()
        mock_agent.generate = Mock(return_value=PlatformGeneratedContent(
            content="Test LinkedIn post content",
            platform=Platform.LINKEDIN,
            metadata={}
        ))
        mock_factory.create_agent = Mock(return_value=mock_agent)
        
        # Generate content
        result = orchestrator.generate_for_platforms(
            user_id="user123",
            content_id="content456",
            platforms=[Platform.LINKEDIN],
            original_content="Original content text",
            topics=sample_topics
        )
        
        # Assertions
        assert len(result) == 1
        assert Platform.LINKEDIN in result
        assert result[Platform.LINKEDIN].platform == Platform.LINKEDIN
        assert result[Platform.LINKEDIN].user_id == "user123"
        assert result[Platform.LINKEDIN].content_id == "content456"
        assert result[Platform.LINKEDIN].version == 1
        assert result[Platform.LINKEDIN].status == "draft"
        
        # Verify S3 upload
        mock_s3_client.put_object.assert_called_once()
        
        # Verify DynamoDB storage
        mock_dynamodb_client.put_item.assert_called_once()
    
    @patch('src.services.content_generation_orchestrator.PlatformAgentFactory')
    def test_generate_multiple_platforms_parallel(
        self,
        mock_factory,
        orchestrator,
        sample_topics,
        mock_s3_client,
        mock_dynamodb_client
    ):
        """Test parallel generation for multiple platforms"""
        # Setup mock agents
        def create_mock_agent(platform):
            agent = Mock()
            agent.generate = Mock(return_value=PlatformGeneratedContent(
                content=f"Content for {platform.value}",
                platform=platform,
                metadata={}
            ))
            return agent
        
        mock_factory.create_agent = Mock(side_effect=lambda p: create_mock_agent(p))
        
        # Generate content for multiple platforms
        platforms = [Platform.LINKEDIN, Platform.TWITTER, Platform.INSTAGRAM]
        result = orchestrator.generate_for_platforms(
            user_id="user123",
            content_id="content456",
            platforms=platforms,
            original_content="Original content text",
            topics=sample_topics
        )
        
        # Assertions
        assert len(result) == 3
        assert all(p in result for p in platforms)
        
        # Verify all platforms generated
        for platform in platforms:
            assert result[platform].platform == platform
            assert result[platform].user_id == "user123"
        
        # Verify S3 uploads (one per platform)
        assert mock_s3_client.put_object.call_count == 3
        
        # Verify DynamoDB storage (one per platform)
        assert mock_dynamodb_client.put_item.call_count == 3
    
    @patch('src.services.content_generation_orchestrator.PlatformAgentFactory')
    def test_generate_with_twitter_thread(
        self,
        mock_factory,
        orchestrator,
        sample_topics,
        mock_s3_client
    ):
        """Test generation with Twitter thread (list content)"""
        # Setup mock agent returning list
        mock_agent = Mock()
        mock_agent.generate = Mock(return_value=PlatformGeneratedContent(
            content=["Tweet 1", "Tweet 2", "Tweet 3"],
            platform=Platform.TWITTER,
            metadata={}
        ))
        mock_factory.create_agent = Mock(return_value=mock_agent)
        
        # Generate content
        result = orchestrator.generate_for_platforms(
            user_id="user123",
            content_id="content456",
            platforms=[Platform.TWITTER],
            original_content="Original content text",
            topics=sample_topics
        )
        
        # Assertions
        assert Platform.TWITTER in result
        content_text = result[Platform.TWITTER].content_text
        
        # Verify content is JSON serialized
        parsed_content = json.loads(content_text)
        assert isinstance(parsed_content, list)
        assert len(parsed_content) == 3
    
    @patch('src.services.content_generation_orchestrator.PlatformAgentFactory')
    def test_generate_style_patterns_retrieved(
        self,
        mock_factory,
        orchestrator,
        sample_topics,
        mock_style_retrieval_service
    ):
        """Test that style patterns are retrieved before generation"""
        # Setup mock agent
        mock_agent = Mock()
        mock_agent.generate = Mock(return_value=PlatformGeneratedContent(
            content="Test content",
            platform=Platform.LINKEDIN,
            metadata={}
        ))
        mock_factory.create_agent = Mock(return_value=mock_agent)
        
        # Generate content
        orchestrator.generate_for_platforms(
            user_id="user123",
            content_id="content456",
            platforms=[Platform.LINKEDIN],
            original_content="Original content text",
            topics=sample_topics
        )
        
        # Verify style retrieval was called
        mock_style_retrieval_service.retrieve_style_patterns.assert_called_once()
        call_args = mock_style_retrieval_service.retrieve_style_patterns.call_args
        assert call_args[1]['user_id'] == "user123"
        assert call_args[1]['content_text'] == "Original content text"
    
    @patch('src.services.content_generation_orchestrator.PlatformAgentFactory')
    def test_generate_platform_failure_raises_error(
        self,
        mock_factory,
        orchestrator,
        sample_topics
    ):
        """Test that platform generation failure raises ProcessingError"""
        # Setup mock agent that raises exception
        mock_agent = Mock()
        mock_agent.generate = Mock(side_effect=Exception("Generation failed"))
        mock_factory.create_agent = Mock(return_value=mock_agent)
        
        # Attempt generation
        with pytest.raises(ProcessingError) as exc_info:
            orchestrator.generate_for_platforms(
                user_id="user123",
                content_id="content456",
                platforms=[Platform.LINKEDIN],
                original_content="Original content text",
                topics=sample_topics
            )
        
        assert exc_info.value.error_code == ErrorCode.CONTENT_GENERATION_FAILED
        assert "linkedin" in str(exc_info.value.message).lower()
    
    def test_generate_style_retrieval_failure(
        self,
        orchestrator,
        sample_topics,
        mock_style_retrieval_service
    ):
        """Test handling of style retrieval failure"""
        # Setup mock to raise exception
        mock_style_retrieval_service.retrieve_style_patterns = Mock(
            side_effect=Exception("Style retrieval failed")
        )
        
        # Attempt generation
        with pytest.raises(ProcessingError) as exc_info:
            orchestrator.generate_for_platforms(
                user_id="user123",
                content_id="content456",
                platforms=[Platform.LINKEDIN],
                original_content="Original content text",
                topics=sample_topics
            )
        
        assert exc_info.value.error_code == ErrorCode.STYLE_RETRIEVAL_FAILED


class TestRegenerateContent:
    """Tests for regenerate_content method"""
    
    @patch('src.services.content_generation_orchestrator.PlatformAgentFactory')
    def test_regenerate_increments_version(
        self,
        mock_factory,
        orchestrator,
        sample_topics,
        mock_dynamodb_client
    ):
        """Test that regeneration increments version number"""
        # Setup existing versions
        mock_dynamodb_client.query = Mock(return_value={
            'Items': [
                {'version': 1, 'platform': 'linkedin'},
                {'version': 2, 'platform': 'linkedin'}
            ]
        })
        
        # Setup mock agent
        mock_agent = Mock()
        mock_agent.generate = Mock(return_value=PlatformGeneratedContent(
            content="Regenerated content",
            platform=Platform.LINKEDIN,
            metadata={}
        ))
        mock_factory.create_agent = Mock(return_value=mock_agent)
        
        # Regenerate content
        result = orchestrator.regenerate_content(
            user_id="user123",
            content_id="content456",
            platform=Platform.LINKEDIN,
            original_content="Original content text",
            topics=sample_topics
        )
        
        # Assertions
        assert result.version == 3  # Should be max(1, 2) + 1
    
    @patch('src.services.content_generation_orchestrator.PlatformAgentFactory')
    def test_regenerate_with_seed(
        self,
        mock_factory,
        orchestrator,
        sample_topics
    ):
        """Test regeneration with custom seed"""
        # Setup mock agent
        mock_agent = Mock()
        mock_agent.generate = Mock(return_value=PlatformGeneratedContent(
            content="Regenerated content",
            platform=Platform.LINKEDIN,
            metadata={}
        ))
        mock_factory.create_agent = Mock(return_value=mock_agent)
        
        # Regenerate with seed
        result = orchestrator.regenerate_content(
            user_id="user123",
            content_id="content456",
            platform=Platform.LINKEDIN,
            original_content="Original content text",
            topics=sample_topics,
            seed=42
        )
        
        # Verify result
        assert result.platform == Platform.LINKEDIN
        assert result.version >= 1
    
    @patch('src.services.content_generation_orchestrator.PlatformAgentFactory')
    def test_regenerate_uses_same_style_patterns(
        self,
        mock_factory,
        orchestrator,
        sample_topics,
        mock_style_retrieval_service
    ):
        """Test that regeneration uses same style patterns as original"""
        # Setup mock agent
        mock_agent = Mock()
        mock_agent.generate = Mock(return_value=PlatformGeneratedContent(
            content="Regenerated content",
            platform=Platform.LINKEDIN,
            metadata={}
        ))
        mock_factory.create_agent = Mock(return_value=mock_agent)
        
        # Regenerate content
        orchestrator.regenerate_content(
            user_id="user123",
            content_id="content456",
            platform=Platform.LINKEDIN,
            original_content="Original content text",
            topics=sample_topics
        )
        
        # Verify style retrieval called with same parameters
        mock_style_retrieval_service.retrieve_style_patterns.assert_called_once()
        call_args = mock_style_retrieval_service.retrieve_style_patterns.call_args
        assert call_args[1]['user_id'] == "user123"
        assert call_args[1]['content_text'] == "Original content text"


class TestStorageOperations:
    """Tests for storage operations"""
    
    def test_store_generated_content_s3(
        self,
        orchestrator,
        mock_s3_client
    ):
        """Test storing generated content in S3"""
        # Store content
        s3_uri = orchestrator._store_generated_content(
            generation_id="gen123",
            content_text="Test content",
            platform=Platform.LINKEDIN,
            s3_key="user123/content456/gen123.json"
        )
        
        # Assertions
        assert s3_uri.startswith("s3://")
        assert "gen123.json" in s3_uri
        
        # Verify S3 call
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args[1]
        assert call_args['bucket'] == "generated-content"
        assert call_args['key'] == "user123/content456/gen123.json"
        assert call_args['content_type'] == "application/json"
        
        # Verify body is valid JSON
        body = json.loads(call_args['body'])
        assert body['generation_id'] == "gen123"
        assert body['platform'] == "linkedin"
        assert body['content'] == "Test content"
    
    def test_store_metadata_dynamodb(
        self,
        orchestrator,
        mock_dynamodb_client
    ):
        """Test storing metadata in DynamoDB"""
        # Create generated content
        generated_content = GeneratedContent(
            generation_id="gen123",
            content_id="content456",
            user_id="user123",
            platform=Platform.LINKEDIN,
            content_text="Test content",
            generated_at=datetime(2024, 1, 1, 12, 0, 0),
            version=1,
            s3_uri="s3://bucket/key",
            status="draft"
        )
        
        # Store metadata
        orchestrator._store_metadata(generated_content)
        
        # Verify DynamoDB call
        mock_dynamodb_client.put_item.assert_called_once()
        call_args = mock_dynamodb_client.put_item.call_args[1]
        assert call_args['table_name'] == "generated_content"
        
        item = call_args['item']
        assert item['generation_id'] == "gen123"
        assert item['content_id'] == "content456"
        assert item['user_id'] == "user123"
        assert item['platform'] == "linkedin"
        assert item['version'] == 1
        assert item['status'] == "draft"
    
    def test_get_latest_version_no_versions(
        self,
        orchestrator,
        mock_dynamodb_client
    ):
        """Test getting latest version when no versions exist"""
        # Setup empty query result
        mock_dynamodb_client.query = Mock(return_value={'Items': []})
        
        # Get latest version
        version = orchestrator._get_latest_version("content456", Platform.LINKEDIN)
        
        # Should return 0
        assert version == 0
    
    def test_get_latest_version_multiple_versions(
        self,
        orchestrator,
        mock_dynamodb_client
    ):
        """Test getting latest version with multiple versions"""
        # Setup query result with multiple versions
        mock_dynamodb_client.query = Mock(return_value={
            'Items': [
                {'version': 1},
                {'version': 3},
                {'version': 2}
            ]
        })
        
        # Get latest version
        version = orchestrator._get_latest_version("content456", Platform.LINKEDIN)
        
        # Should return max version
        assert version == 3
    
    def test_storage_failure_raises_error(
        self,
        orchestrator,
        mock_s3_client
    ):
        """Test that storage failure raises ProcessingError"""
        # Setup S3 to raise exception
        mock_s3_client.put_object = Mock(side_effect=Exception("S3 error"))
        
        # Attempt storage
        with pytest.raises(ProcessingError) as exc_info:
            orchestrator._store_generated_content(
                generation_id="gen123",
                content_text="Test content",
                platform=Platform.LINKEDIN,
                s3_key="user123/content456/gen123.json"
            )
        
        assert exc_info.value.error_code == ErrorCode.S3_ACCESS_ERROR


class TestErrorHandling:
    """Tests for error handling"""
    
    @patch('src.services.content_generation_orchestrator.PlatformAgentFactory')
    def test_generation_error_maintains_state(
        self,
        mock_factory,
        orchestrator,
        sample_topics,
        mock_s3_client,
        mock_dynamodb_client
    ):
        """Test that generation error doesn't corrupt state"""
        # Setup mock agent that fails
        mock_agent = Mock()
        mock_agent.generate = Mock(side_effect=Exception("Generation failed"))
        mock_factory.create_agent = Mock(return_value=mock_agent)
        
        # Attempt generation
        with pytest.raises(ProcessingError):
            orchestrator.generate_for_platforms(
                user_id="user123",
                content_id="content456",
                platforms=[Platform.LINKEDIN],
                original_content="Original content text",
                topics=sample_topics
            )
        
        # Verify no partial data stored
        mock_s3_client.put_object.assert_not_called()
        mock_dynamodb_client.put_item.assert_not_called()
    
    @patch('src.services.content_generation_orchestrator.PlatformAgentFactory')
    def test_partial_platform_failure(
        self,
        mock_factory,
        orchestrator,
        sample_topics
    ):
        """Test handling when one platform fails in multi-platform generation"""
        # Setup mock agents - one succeeds, one fails
        def create_agent(platform):
            agent = Mock()
            if platform == Platform.LINKEDIN:
                agent.generate = Mock(return_value=PlatformGeneratedContent(
                    content="Success",
                    platform=platform,
                    metadata={}
                ))
            else:
                agent.generate = Mock(side_effect=Exception("Failed"))
            return agent
        
        mock_factory.create_agent = Mock(side_effect=create_agent)
        
        # Attempt generation for multiple platforms
        with pytest.raises(ProcessingError):
            orchestrator.generate_for_platforms(
                user_id="user123",
                content_id="content456",
                platforms=[Platform.LINKEDIN, Platform.TWITTER],
                original_content="Original content text",
                topics=sample_topics
            )
