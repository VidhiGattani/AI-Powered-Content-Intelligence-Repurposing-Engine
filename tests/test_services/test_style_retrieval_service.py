"""
Unit tests for Style Retrieval Service
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from src.services.style_retrieval_service import (
    StyleRetrievalService,
    StylePatterns,
    WritingCharacteristics
)
from src.utils.errors import NotFoundError, ProcessingError, ErrorCode


class TestStyleRetrievalService:
    """Test suite for StyleRetrievalService"""
    
    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock Bedrock client"""
        client = Mock()
        client.invoke_model = Mock(return_value={
            'embedding': [0.1] * 1536  # Titan embeddings are 1536 dimensions
        })
        return client
    
    @pytest.fixture
    def mock_bedrock_agent_client(self):
        """Mock Bedrock Agent Runtime client"""
        client = Mock()
        return client
    
    @pytest.fixture
    def service(self, mock_bedrock_client, mock_bedrock_agent_client):
        """Create StyleRetrievalService instance with mocked clients"""
        return StyleRetrievalService(
            bedrock_client=mock_bedrock_client,
            bedrock_agent_client=mock_bedrock_agent_client
        )
    
    @pytest.fixture
    def sample_style_content(self):
        """Sample style content for testing"""
        return [
            "I love building amazing products! 🚀 Let's create something awesome together.",
            "Innovation drives us forward. We're passionate about solving real problems!",
            "Hey there! Check out this cool feature we just launched. It's game-changing! 💡"
        ]
    
    def test_retrieve_style_patterns_success(
        self,
        service,
        mock_bedrock_agent_client,
        sample_style_content
    ):
        """Test successful style pattern retrieval"""
        # Arrange
        user_id = "test-user-123"
        content_text = "This is my original content about innovation"
        
        mock_bedrock_agent_client.retrieve = Mock(return_value=[
            {'content': {'text': sample_style_content[0]}},
            {'content': {'text': sample_style_content[1]}},
            {'content': {'text': sample_style_content[2]}}
        ])
        
        # Act
        result = service.retrieve_style_patterns(user_id, content_text)
        
        # Assert
        assert isinstance(result, StylePatterns)
        assert result.user_id == user_id
        assert len(result.examples) == 3
        assert result.examples == sample_style_content
        assert isinstance(result.characteristics, WritingCharacteristics)
        
        # Verify embedding was generated
        service.bedrock_client.invoke_model.assert_called_once()
        
        # Verify Knowledge Base was queried
        mock_bedrock_agent_client.retrieve.assert_called_once()
    
    def test_retrieve_style_patterns_no_results(
        self,
        service,
        mock_bedrock_agent_client
    ):
        """Test retrieval when no style content exists"""
        # Arrange
        user_id = "test-user-no-content"
        content_text = "Some content"
        
        mock_bedrock_agent_client.retrieve = Mock(return_value=[])
        
        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            service.retrieve_style_patterns(user_id, content_text)
        
        assert exc_info.value.error_code == ErrorCode.NO_STYLE_PROFILE
        assert user_id in exc_info.value.message
    
    def test_retrieve_style_patterns_empty_content(
        self,
        service,
        mock_bedrock_agent_client
    ):
        """Test retrieval when results have no text content"""
        # Arrange
        user_id = "test-user-empty"
        content_text = "Some content"
        
        mock_bedrock_agent_client.retrieve = Mock(return_value=[
            {'content': {'text': ''}},
            {'content': {}}
        ])
        
        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            service.retrieve_style_patterns(user_id, content_text)
        
        assert exc_info.value.error_code == ErrorCode.NO_STYLE_PROFILE
    
    def test_retrieve_style_patterns_embedding_failure(
        self,
        service,
        mock_bedrock_client
    ):
        """Test handling of embedding generation failure"""
        # Arrange
        user_id = "test-user-123"
        content_text = "Some content"
        
        mock_bedrock_client.invoke_model = Mock(side_effect=Exception("Bedrock error"))
        
        # Act & Assert
        with pytest.raises(ProcessingError) as exc_info:
            service.retrieve_style_patterns(user_id, content_text)
        
        assert exc_info.value.error_code == ErrorCode.STYLE_RETRIEVAL_FAILED
    
    def test_extract_writing_characteristics(self, service, sample_style_content):
        """Test extraction of writing characteristics"""
        # Act
        result = service.extract_writing_characteristics(sample_style_content)
        
        # Assert
        assert isinstance(result, WritingCharacteristics)
        
        # Check sentence structure
        assert 'avg_length' in result.sentence_structure
        assert 'length_variance' in result.sentence_structure
        assert 'complexity' in result.sentence_structure
        assert result.sentence_structure['avg_length'] > 0
        
        # Check vocabulary
        assert 'unique_words' in result.vocabulary
        assert 'avg_word_length' in result.vocabulary
        assert 'formality_level' in result.vocabulary
        assert result.vocabulary['unique_words'] > 0
        
        # Check tone
        assert isinstance(result.tone, str)
        assert result.tone in ['professional', 'casual', 'enthusiastic', 'inquisitive', 'neutral']
        
        # Check emoji usage
        assert 'frequency' in result.emoji_usage
        assert 'total_count' in result.emoji_usage
        assert result.emoji_usage['total_count'] >= 0
        
        # Check common phrases
        assert isinstance(result.common_phrases, list)
        
        # Check punctuation style
        assert 'exclamation_marks' in result.punctuation_style
        assert 'questions' in result.punctuation_style
    
    def test_analyze_sentence_structure_simple(self, service):
        """Test sentence structure analysis with simple sentences"""
        # Arrange
        text = "I like cats. Dogs are nice. Birds can fly."
        
        # Act
        result = service._analyze_sentence_structure(text)
        
        # Assert
        assert result['complexity'] == 'simple'
        assert result['avg_length'] < 10
        assert result['total_sentences'] == 3
    
    def test_analyze_sentence_structure_complex(self, service):
        """Test sentence structure analysis with complex sentences"""
        # Arrange
        text = ("The implementation of advanced artificial intelligence systems "
                "requires careful consideration of ethical implications, technical "
                "constraints, and societal impacts that may arise from widespread adoption.")
        
        # Act
        result = service._analyze_sentence_structure(text)
        
        # Assert
        assert result['complexity'] in ['moderate', 'complex']
        assert result['avg_length'] > 10
    
    def test_analyze_sentence_structure_empty(self, service):
        """Test sentence structure analysis with empty text"""
        # Act
        result = service._analyze_sentence_structure("")
        
        # Assert
        assert result['avg_length'] == 0
        assert result['length_variance'] == 0
        assert result['complexity'] == 'simple'
    
    def test_analyze_vocabulary_casual(self, service):
        """Test vocabulary analysis with casual language"""
        # Arrange
        text = "Hey! I'm gonna go get some food. Wanna come?"
        
        # Act
        result = service._analyze_vocabulary(text)
        
        # Assert
        assert result['formality_level'] == 'casual'
        assert result['avg_word_length'] < 5
    
    def test_analyze_vocabulary_formal(self, service):
        """Test vocabulary analysis with formal language"""
        # Arrange
        text = ("Furthermore, the implementation necessitates comprehensive "
                "consideration of multifaceted organizational requirements.")
        
        # Act
        result = service._analyze_vocabulary(text)
        
        # Assert
        assert result['formality_level'] == 'formal'
        assert result['avg_word_length'] > 5.5
    
    def test_analyze_vocabulary_empty(self, service):
        """Test vocabulary analysis with empty text"""
        # Act
        result = service._analyze_vocabulary("")
        
        # Assert
        assert result['unique_words'] == 0
        assert result['avg_word_length'] == 0
        assert result['total_words'] == 0
    
    def test_determine_tone_enthusiastic(self, service):
        """Test tone determination for enthusiastic writing"""
        # Arrange
        text = "This is amazing! I love it! So exciting! Wow! Incredible! Awesome!"
        vocabulary = {'formality_level': 'casual'}
        
        # Act
        result = service._determine_tone(text, vocabulary)
        
        # Assert
        assert result == 'enthusiastic'
    
    def test_determine_tone_professional(self, service):
        """Test tone determination for professional writing"""
        # Arrange
        text = "Therefore, we must consider the implications. However, further analysis is required. Furthermore, additional research is necessary."
        vocabulary = {'formality_level': 'formal'}
        
        # Act
        result = service._determine_tone(text, vocabulary)
        
        # Assert
        assert result == 'professional'
    
    def test_determine_tone_casual(self, service):
        """Test tone determination for casual writing"""
        # Arrange
        text = "Hey, I'm gonna check this out. Yeah, it's pretty cool and awesome!"
        vocabulary = {'formality_level': 'casual'}
        
        # Act
        result = service._determine_tone(text, vocabulary)
        
        # Assert
        assert result == 'casual'
    
    def test_determine_tone_inquisitive(self, service):
        """Test tone determination for inquisitive writing"""
        # Arrange
        text = "What do you think? How does this work? Why is this important? Can we improve it?"
        vocabulary = {'formality_level': 'neutral'}
        
        # Act
        result = service._determine_tone(text, vocabulary)
        
        # Assert
        assert result == 'inquisitive'
    
    def test_analyze_emoji_usage_with_emojis(self, service):
        """Test emoji analysis with emojis present"""
        # Arrange
        text = "I love this! 🚀 Let's build something amazing 💡 together! 🎉"
        
        # Act
        result = service._analyze_emoji_usage(text)
        
        # Assert
        assert result['total_count'] > 0
        assert result['frequency'] > 0
        assert len(result['types']) > 0
        assert result['placement'] in ['beginning', 'end', 'throughout', 'none']
    
    def test_analyze_emoji_usage_without_emojis(self, service):
        """Test emoji analysis without emojis"""
        # Arrange
        text = "This is plain text without any emojis."
        
        # Act
        result = service._analyze_emoji_usage(text)
        
        # Assert
        assert result['total_count'] == 0
        assert result['frequency'] == 0
        assert len(result['types']) == 0
        assert result['placement'] == 'none'
    
    def test_extract_common_phrases(self, service):
        """Test extraction of common phrases"""
        # Arrange
        style_content = [
            "I love building products. Building products is my passion.",
            "Building products requires dedication. I love the process.",
            "The process of building products is rewarding."
        ]
        
        # Act
        result = service._extract_common_phrases(style_content)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) > 0
        # "building products" should appear multiple times
        assert any('building products' in phrase for phrase in result)
    
    def test_extract_common_phrases_no_repetition(self, service):
        """Test phrase extraction with no repeated phrases"""
        # Arrange
        style_content = [
            "Every sentence is completely unique.",
            "No phrases repeat at all.",
            "All words are different here."
        ]
        
        # Act
        result = service._extract_common_phrases(style_content)
        
        # Assert
        assert isinstance(result, list)
        # May be empty or have very few phrases
    
    def test_analyze_punctuation_varied(self, service):
        """Test punctuation analysis with varied punctuation"""
        # Arrange
        text = "This is exciting! What do you think? Well... I'm not sure. Let's see—maybe it works."
        
        # Act
        result = service._analyze_punctuation(text)
        
        # Assert
        assert result['exclamation_marks'] > 0
        assert result['questions'] > 0
        assert result['ellipsis'] > 0
        assert result['dashes'] > 0
        assert 'exclamation_frequency' in result
        assert 'question_frequency' in result
    
    def test_analyze_punctuation_minimal(self, service):
        """Test punctuation analysis with minimal punctuation"""
        # Arrange
        text = "This is a simple sentence. Another simple sentence."
        
        # Act
        result = service._analyze_punctuation(text)
        
        # Assert
        assert result['exclamation_marks'] == 0
        assert result['questions'] == 0
        assert result['ellipsis'] == 0
    
    def test_generate_embedding_success(self, service, mock_bedrock_client):
        """Test successful embedding generation"""
        # Arrange
        text = "Sample text for embedding"
        
        # Act
        result = service._generate_embedding(text)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 1536  # Titan embedding dimensions
        mock_bedrock_client.invoke_model.assert_called_once()
    
    def test_generate_embedding_truncates_long_text(self, service, mock_bedrock_client):
        """Test that long text is truncated before embedding"""
        # Arrange
        text = "a" * 10000  # Very long text
        
        # Act
        result = service._generate_embedding(text)
        
        # Assert
        assert isinstance(result, list)
        # Verify the call was made with truncated text
        call_args = mock_bedrock_client.invoke_model.call_args
        assert len(call_args[1]['body']['inputText']) <= 8000
    
    def test_generate_embedding_empty_vector(self, service, mock_bedrock_client):
        """Test handling of empty embedding vector"""
        # Arrange
        text = "Sample text"
        mock_bedrock_client.invoke_model = Mock(return_value={'embedding': []})
        
        # Act & Assert
        with pytest.raises(ProcessingError) as exc_info:
            service._generate_embedding(text)
        
        assert exc_info.value.error_code == ErrorCode.EMBEDDING_GENERATION_FAILED
    
    def test_retrieve_style_patterns_top_3_results(
        self,
        service,
        mock_bedrock_agent_client
    ):
        """Test that exactly top 3 results are retrieved"""
        # Arrange
        user_id = "test-user-123"
        content_text = "Test content"
        
        # Mock 5 results but should only use top 3
        mock_bedrock_agent_client.retrieve = Mock(return_value=[
            {'content': {'text': 'Style 1'}},
            {'content': {'text': 'Style 2'}},
            {'content': {'text': 'Style 3'}},
            {'content': {'text': 'Style 4'}},
            {'content': {'text': 'Style 5'}}
        ])
        
        # Act
        result = service.retrieve_style_patterns(user_id, content_text)
        
        # Assert
        # The retrieve call should request 3 results
        call_args = mock_bedrock_agent_client.retrieve.call_args
        assert call_args[1]['number_of_results'] == 3
    
    def test_writing_characteristics_all_fields_present(self, service, sample_style_content):
        """Test that all required fields are present in WritingCharacteristics"""
        # Act
        result = service.extract_writing_characteristics(sample_style_content)
        
        # Assert - verify all required fields exist
        assert hasattr(result, 'sentence_structure')
        assert hasattr(result, 'vocabulary')
        assert hasattr(result, 'tone')
        assert hasattr(result, 'emoji_usage')
        assert hasattr(result, 'common_phrases')
        assert hasattr(result, 'punctuation_style')
        
        # Verify nested dictionaries have expected keys
        assert 'avg_length' in result.sentence_structure
        assert 'unique_words' in result.vocabulary
        assert 'frequency' in result.emoji_usage
        assert 'exclamation_marks' in result.punctuation_style


class TestWritingCharacteristicsIntegration:
    """Integration tests for writing characteristics extraction"""
    
    @pytest.fixture
    def service(self):
        """Create service with real clients (will be mocked at AWS level)"""
        mock_bedrock = Mock()
        mock_bedrock.invoke_model = Mock(return_value={'embedding': [0.1] * 1536})
        mock_agent = Mock()
        return StyleRetrievalService(
            bedrock_client=mock_bedrock,
            bedrock_agent_client=mock_agent
        )
    
    def test_professional_blog_style(self, service):
        """Test characteristics extraction from professional blog content"""
        # Arrange
        content = [
            "In today's rapidly evolving technological landscape, organizations must adapt to remain competitive. "
            "The integration of artificial intelligence presents both opportunities and challenges. "
            "Therefore, strategic planning is essential for successful implementation.",
            
            "Furthermore, stakeholder engagement plays a crucial role in digital transformation initiatives. "
            "Companies that prioritize communication and collaboration tend to achieve better outcomes. "
            "However, resistance to change remains a significant barrier."
        ]
        
        # Act
        result = service.extract_writing_characteristics(content)
        
        # Assert
        assert result.tone in ['professional', 'neutral']
        assert result.vocabulary['formality_level'] in ['formal', 'neutral']
        assert result.sentence_structure['complexity'] in ['moderate', 'complex']
        assert result.emoji_usage['total_count'] == 0
    
    def test_casual_social_media_style(self, service):
        """Test characteristics extraction from casual social media content"""
        # Arrange
        content = [
            "Hey everyone! 👋 Just launched our new feature and I'm so excited! 🚀",
            "Can't wait to hear what you think! Drop a comment below! 💬",
            "This is gonna be awesome! Let's gooo! 🎉"
        ]
        
        # Act
        result = service.extract_writing_characteristics(content)
        
        # Assert
        assert result.tone in ['enthusiastic', 'casual']
        assert result.vocabulary['formality_level'] == 'casual'
        assert result.emoji_usage['total_count'] > 0
        assert result.punctuation_style['exclamation_marks'] > 0
    
    def test_technical_documentation_style(self, service):
        """Test characteristics extraction from technical documentation"""
        # Arrange
        content = [
            "The API endpoint accepts POST requests with JSON payloads. "
            "Authentication requires a valid Bearer token in the Authorization header. "
            "Response codes include 200 for success, 400 for invalid requests, and 401 for unauthorized access.",
            
            "To configure the service, set the following environment variables: "
            "API_KEY, DATABASE_URL, and LOG_LEVEL. "
            "The service will automatically connect to the database on startup."
        ]
        
        # Act
        result = service.extract_writing_characteristics(content)
        
        # Assert
        assert result.tone in ['professional', 'neutral']
        assert result.vocabulary['formality_level'] in ['formal', 'neutral']
        assert result.sentence_structure['avg_length'] > 10
        assert result.emoji_usage['total_count'] == 0
        assert result.punctuation_style['exclamation_marks'] == 0
