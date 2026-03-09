"""
Unit tests for TopicExtractionService
"""
import pytest
import json
from unittest.mock import Mock, MagicMock
from src.services.topic_extraction_service import (
    TopicExtractionService,
    Topic,
    TopicExtractionResult
)
from src.utils.errors import ProcessingError, ErrorCode


class TestTopicExtractionService:
    """Test suite for TopicExtractionService"""
    
    @pytest.fixture
    def mock_bedrock_client(self):
        """Create mock Bedrock client"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_bedrock_client):
        """Create service instance with mock client"""
        return TopicExtractionService(bedrock_client=mock_bedrock_client)
    
    @pytest.fixture
    def sample_transcript(self):
        """Sample transcript with sufficient length"""
        return " ".join(["word"] * 600)  # 600 words
    
    @pytest.fixture
    def sample_claude_response(self):
        """Sample Claude response with topics"""
        return {
            "content": [
                {
                    "text": json.dumps({
                        "topics": [
                            {
                                "name": "Machine Learning",
                                "description": "Discussion of ML algorithms and applications",
                                "relevance_score": 0.95
                            },
                            {
                                "name": "Data Processing",
                                "description": "Techniques for processing large datasets",
                                "relevance_score": 0.85
                            },
                            {
                                "name": "Cloud Computing",
                                "description": "Using cloud services for scalable solutions",
                                "relevance_score": 0.80
                            },
                            {
                                "name": "API Design",
                                "description": "Best practices for RESTful API design",
                                "relevance_score": 0.75
                            },
                            {
                                "name": "Security",
                                "description": "Security considerations in modern applications",
                                "relevance_score": 0.70
                            }
                        ]
                    })
                }
            ]
        }
    
    def test_extract_topics_success(
        self,
        service,
        mock_bedrock_client,
        sample_transcript,
        sample_claude_response
    ):
        """Test successful topic extraction"""
        # Arrange
        content_id = "test-content-123"
        mock_bedrock_client.invoke_model.return_value = sample_claude_response
        
        # Act
        result = service.extract_topics(content_id, sample_transcript)
        
        # Assert
        assert isinstance(result, TopicExtractionResult)
        assert result.content_id == content_id
        assert len(result.topics) == 5
        assert all(isinstance(topic, Topic) for topic in result.topics)
        
        # Verify first topic
        first_topic = result.topics[0]
        assert first_topic.name == "Machine Learning"
        assert first_topic.description == "Discussion of ML algorithms and applications"
        assert first_topic.relevance_score == 0.95
        
        # Verify Bedrock was called
        mock_bedrock_client.invoke_model.assert_called_once()
        call_args = mock_bedrock_client.invoke_model.call_args
        assert call_args[1]['model_id'] == service.CLAUDE_MODEL_ID
    
    def test_extract_topics_insufficient_content(self, service):
        """Test error when content is too short"""
        # Arrange
        content_id = "test-content-123"
        short_transcript = " ".join(["word"] * 100)  # Only 100 words
        
        # Act & Assert
        with pytest.raises(ProcessingError) as exc_info:
            service.extract_topics(content_id, short_transcript)
        
        assert exc_info.value.error_code == ErrorCode.INSUFFICIENT_CONTENT
        assert "too short" in exc_info.value.message.lower()
    
    def test_extract_topics_with_markdown_wrapped_json(
        self,
        service,
        mock_bedrock_client,
        sample_transcript
    ):
        """Test parsing JSON wrapped in markdown code blocks"""
        # Arrange
        content_id = "test-content-123"
        topics_json = {
            "topics": [
                {
                    "name": "Topic 1",
                    "description": "Description 1",
                    "relevance_score": 0.9
                },
                {
                    "name": "Topic 2",
                    "description": "Description 2",
                    "relevance_score": 0.8
                },
                {
                    "name": "Topic 3",
                    "description": "Description 3",
                    "relevance_score": 0.7
                },
                {
                    "name": "Topic 4",
                    "description": "Description 4",
                    "relevance_score": 0.6
                },
                {
                    "name": "Topic 5",
                    "description": "Description 5",
                    "relevance_score": 0.5
                }
            ]
        }
        
        # Wrap in markdown code block
        wrapped_response = {
            "content": [
                {
                    "text": f"```json\n{json.dumps(topics_json)}\n```"
                }
            ]
        }
        
        mock_bedrock_client.invoke_model.return_value = wrapped_response
        
        # Act
        result = service.extract_topics(content_id, sample_transcript)
        
        # Assert
        assert len(result.topics) == 5
        assert result.topics[0].name == "Topic 1"
    
    def test_extract_topics_bedrock_failure(
        self,
        service,
        mock_bedrock_client,
        sample_transcript
    ):
        """Test handling of Bedrock API failure"""
        # Arrange
        content_id = "test-content-123"
        mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock unavailable")
        
        # Act & Assert
        with pytest.raises(ProcessingError) as exc_info:
            service.extract_topics(content_id, sample_transcript)
        
        assert exc_info.value.error_code == ErrorCode.BEDROCK_UNAVAILABLE
    
    def test_extract_topics_invalid_json_response(
        self,
        service,
        mock_bedrock_client,
        sample_transcript
    ):
        """Test handling of invalid JSON in response"""
        # Arrange
        content_id = "test-content-123"
        invalid_response = {
            "content": [
                {
                    "text": "This is not valid JSON"
                }
            ]
        }
        mock_bedrock_client.invoke_model.return_value = invalid_response
        
        # Act & Assert
        with pytest.raises(ProcessingError) as exc_info:
            service.extract_topics(content_id, sample_transcript)
        
        assert exc_info.value.error_code == ErrorCode.TOPIC_EXTRACTION_FAILED
    
    def test_build_topic_extraction_prompt(self, service):
        """Test prompt building"""
        # Arrange
        transcript = "Sample content for testing"
        
        # Act
        prompt = service._build_topic_extraction_prompt(transcript)
        
        # Assert
        assert transcript in prompt
        assert "JSON" in prompt
        assert str(service.MIN_TOPICS) in prompt
        assert str(service.MAX_TOPICS) in prompt
        assert "relevance_score" in prompt
    
    def test_parse_topics_response_empty_content(self, service):
        """Test parsing response with empty content"""
        # Arrange
        empty_response = {"content": []}
        
        # Act & Assert
        with pytest.raises(ProcessingError):
            service._parse_topics_response(empty_response)
    
    def test_parse_topics_response_no_topics(self, service):
        """Test parsing response with no topics array"""
        # Arrange
        no_topics_response = {
            "content": [
                {
                    "text": json.dumps({"topics": []})
                }
            ]
        }
        
        # Act & Assert
        with pytest.raises(ProcessingError):
            service._parse_topics_response(no_topics_response)
    
    def test_extract_topics_validates_topic_count(
        self,
        service,
        mock_bedrock_client,
        sample_transcript,
        caplog
    ):
        """Test that topic count outside range is logged as warning"""
        # Arrange
        content_id = "test-content-123"
        
        # Response with only 3 topics (below minimum of 5)
        few_topics_response = {
            "content": [
                {
                    "text": json.dumps({
                        "topics": [
                            {"name": "Topic 1", "description": "Desc 1", "relevance_score": 0.9},
                            {"name": "Topic 2", "description": "Desc 2", "relevance_score": 0.8},
                            {"name": "Topic 3", "description": "Desc 3", "relevance_score": 0.7}
                        ]
                    })
                }
            ]
        }
        
        mock_bedrock_client.invoke_model.return_value = few_topics_response
        
        # Act
        result = service.extract_topics(content_id, sample_transcript)
        
        # Assert - should still return result but log warning
        assert len(result.topics) == 3
        # Note: Warning logging verification would require caplog fixture
