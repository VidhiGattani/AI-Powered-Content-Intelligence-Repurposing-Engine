"""
Unit tests for SEOOptimizer
"""
import pytest
from unittest.mock import Mock, patch
from src.services.seo_optimizer import SEOOptimizer, SEOMetadata
from src.models.enums import Platform
from src.utils.errors import ProcessingError, ErrorCode


@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client"""
    client = Mock()
    return client


@pytest.fixture
def optimizer(mock_bedrock_client):
    """Create SEO optimizer with mocked Bedrock client"""
    return SEOOptimizer(bedrock_client=mock_bedrock_client)


@pytest.fixture
def sample_content():
    """Sample content for testing"""
    return """
    Artificial Intelligence is transforming how we work and live. 
    Machine learning algorithms are becoming more sophisticated every day.
    From healthcare to finance, AI is making an impact across industries.
    """


@pytest.fixture
def sample_topics():
    """Sample topics"""
    return ["AI", "Machine Learning", "Technology", "Innovation"]


class TestGenerateTitles:
    """Tests for generate_titles method"""
    
    def test_generate_titles_success(self, optimizer, mock_bedrock_client, sample_content, sample_topics):
        """Test successful title generation"""
        # Mock Bedrock response
        mock_bedrock_client.invoke_model = Mock(return_value={
            'content': [{
                'text': """1. How AI is Secretly Changing Your Daily Life
2. 5 Ways Machine Learning Will Boost Your Productivity
3. 7 AI Innovations You Need to Know About
4. Is Artificial Intelligence Really the Future?
5. AI Has Already Transformed These Industries"""
            }]
        })
        
        # Generate titles
        titles = optimizer.generate_titles(sample_content, sample_topics)
        
        # Assertions
        assert len(titles) == 5
        assert all(isinstance(title, str) for title in titles)
        assert all(len(title) > 0 for title in titles)
        
        # Verify Bedrock was called
        mock_bedrock_client.invoke_model.assert_called_once()
    
    def test_generate_titles_with_fewer_than_5(self, optimizer, mock_bedrock_client, sample_content, sample_topics):
        """Test title generation when Claude returns fewer than 5 titles"""
        # Mock Bedrock response with only 3 titles
        mock_bedrock_client.invoke_model = Mock(return_value={
            'content': [{
                'text': """1. AI is Changing Everything
2. Machine Learning Explained
3. The Future of Technology"""
            }]
        })
        
        # Generate titles
        titles = optimizer.generate_titles(sample_content, sample_topics)
        
        # Should pad to 5 titles
        assert len(titles) == 5
    
    def test_generate_titles_with_more_than_5(self, optimizer, mock_bedrock_client, sample_content, sample_topics):
        """Test title generation when Claude returns more than 5 titles"""
        # Mock Bedrock response with 7 titles
        mock_bedrock_client.invoke_model = Mock(return_value={
            'content': [{
                'text': """1. Title 1
2. Title 2
3. Title 3
4. Title 4
5. Title 5
6. Title 6
7. Title 7"""
            }]
        })
        
        # Generate titles
        titles = optimizer.generate_titles(sample_content, sample_topics)
        
        # Should truncate to 5 titles
        assert len(titles) == 5
    
    def test_generate_titles_bedrock_failure(self, optimizer, mock_bedrock_client, sample_content, sample_topics):
        """Test title generation when Bedrock fails"""
        # Mock Bedrock to raise exception
        mock_bedrock_client.invoke_model = Mock(side_effect=Exception("Bedrock error"))
        
        # Should raise ProcessingError
        with pytest.raises(ProcessingError) as exc_info:
            optimizer.generate_titles(sample_content, sample_topics)
        
        assert exc_info.value.error_code == ErrorCode.CONTENT_GENERATION_FAILED
        assert "Failed to generate titles" in exc_info.value.message


class TestGenerateHashtags:
    """Tests for generate_hashtags method"""
    
    def test_generate_hashtags_success(self, optimizer, mock_bedrock_client, sample_content, sample_topics):
        """Test successful hashtag generation"""
        # Mock Bedrock response
        mock_bedrock_client.invoke_model = Mock(return_value={
            'content': [{
                'text': "#AI, #MachineLearning, #Technology, #Innovation, #FutureTech"
            }]
        })
        
        # Generate hashtags
        hashtags = optimizer.generate_hashtags(sample_content, Platform.TWITTER, sample_topics)
        
        # Assertions
        assert len(hashtags) >= 4
        assert len(hashtags) <= 8
        assert all(tag.startswith('#') for tag in hashtags)
        assert all(' ' not in tag for tag in hashtags)
        
        # Verify Bedrock was called
        mock_bedrock_client.invoke_model.assert_called_once()
    
    def test_generate_hashtags_twitter(self, optimizer, mock_bedrock_client, sample_content, sample_topics):
        """Test hashtag generation for Twitter"""
        mock_bedrock_client.invoke_model = Mock(return_value={
            'content': [{
                'text': "#AI #Tech #ML #Innovation #Future"
            }]
        })
        
        hashtags = optimizer.generate_hashtags(sample_content, Platform.TWITTER, sample_topics)
        
        assert len(hashtags) >= 4
        assert all(tag.startswith('#') for tag in hashtags)
    
    def test_generate_hashtags_instagram(self, optimizer, mock_bedrock_client, sample_content, sample_topics):
        """Test hashtag generation for Instagram"""
        mock_bedrock_client.invoke_model = Mock(return_value={
            'content': [{
                'text': "#AI #MachineLearning #TechLife #Innovation #FutureTech #AIRevolution"
            }]
        })
        
        hashtags = optimizer.generate_hashtags(sample_content, Platform.INSTAGRAM, sample_topics)
        
        assert len(hashtags) >= 4
        assert len(hashtags) <= 8
    
    def test_generate_hashtags_too_few(self, optimizer, mock_bedrock_client, sample_content, sample_topics):
        """Test hashtag generation when too few hashtags returned"""
        # Mock Bedrock response with only 2 hashtags
        mock_bedrock_client.invoke_model = Mock(return_value={
            'content': [{
                'text': "#AI #Tech"
            }]
        })
        
        hashtags = optimizer.generate_hashtags(sample_content, Platform.TWITTER, sample_topics)
        
        # Should pad to minimum 4
        assert len(hashtags) >= 4
    
    def test_generate_hashtags_too_many(self, optimizer, mock_bedrock_client, sample_content, sample_topics):
        """Test hashtag generation when too many hashtags returned"""
        # Mock Bedrock response with 10 hashtags
        mock_bedrock_client.invoke_model = Mock(return_value={
            'content': [{
                'text': "#AI #ML #Tech #Innovation #Future #Data #Code #Dev #Programming #Software"
            }]
        })
        
        hashtags = optimizer.generate_hashtags(sample_content, Platform.TWITTER, sample_topics)
        
        # Should truncate to maximum 8
        assert len(hashtags) <= 8
    
    def test_generate_hashtags_removes_spaces(self, optimizer, mock_bedrock_client, sample_content, sample_topics):
        """Test that hashtags with spaces are cleaned"""
        # Mock Bedrock response with spaces in hashtags
        mock_bedrock_client.invoke_model = Mock(return_value={
            'content': [{
                'text': "#Artificial Intelligence, #Machine Learning, #Tech"
            }]
        })
        
        hashtags = optimizer.generate_hashtags(sample_content, Platform.TWITTER, sample_topics)
        
        # All hashtags should have no spaces
        assert all(' ' not in tag for tag in hashtags)
    
    def test_generate_hashtags_bedrock_failure(self, optimizer, mock_bedrock_client, sample_content, sample_topics):
        """Test hashtag generation when Bedrock fails"""
        mock_bedrock_client.invoke_model = Mock(side_effect=Exception("Bedrock error"))
        
        with pytest.raises(ProcessingError) as exc_info:
            optimizer.generate_hashtags(sample_content, Platform.TWITTER, sample_topics)
        
        assert exc_info.value.error_code == ErrorCode.CONTENT_GENERATION_FAILED
        assert "Failed to generate hashtags" in exc_info.value.message


class TestGenerateAltText:
    """Tests for generate_alt_text method"""
    
    def test_generate_alt_text_success(self, optimizer, mock_bedrock_client):
        """Test successful alt-text generation"""
        # Mock Bedrock response
        mock_bedrock_client.invoke_model = Mock(return_value={
            'content': [{
                'text': "A person typing on a laptop with code on the screen"
            }]
        })
        
        # Generate alt-text
        alt_text = optimizer.generate_alt_text("Person coding on laptop")
        
        # Assertions
        assert isinstance(alt_text, str)
        assert len(alt_text) > 0
        assert len(alt_text) <= 125
        
        # Verify Bedrock was called
        mock_bedrock_client.invoke_model.assert_called_once()
    
    def test_generate_alt_text_truncates_long_text(self, optimizer, mock_bedrock_client):
        """Test alt-text truncation when too long"""
        # Mock Bedrock response with very long text
        long_text = "A" * 150
        mock_bedrock_client.invoke_model = Mock(return_value={
            'content': [{
                'text': long_text
            }]
        })
        
        alt_text = optimizer.generate_alt_text("Test image")
        
        # Should be truncated to max length
        assert len(alt_text) <= 125
        assert alt_text.endswith("...")
    
    def test_generate_alt_text_removes_quotes(self, optimizer, mock_bedrock_client):
        """Test that quotes are removed from alt-text"""
        # Mock Bedrock response with quotes
        mock_bedrock_client.invoke_model = Mock(return_value={
            'content': [{
                'text': '"A beautiful sunset over the ocean"'
            }]
        })
        
        alt_text = optimizer.generate_alt_text("Sunset photo")
        
        # Quotes should be removed
        assert not alt_text.startswith('"')
        assert not alt_text.endswith('"')
    
    def test_generate_alt_text_bedrock_failure(self, optimizer, mock_bedrock_client):
        """Test alt-text generation when Bedrock fails"""
        mock_bedrock_client.invoke_model = Mock(side_effect=Exception("Bedrock error"))
        
        with pytest.raises(ProcessingError) as exc_info:
            optimizer.generate_alt_text("Test image")
        
        assert exc_info.value.error_code == ErrorCode.CONTENT_GENERATION_FAILED
        assert "Failed to generate alt-text" in exc_info.value.message


class TestParsingMethods:
    """Tests for parsing helper methods"""
    
    def test_parse_titles_with_numbering(self, optimizer):
        """Test parsing titles with numbering"""
        response = """1. First Title
2. Second Title
3. Third Title
4. Fourth Title
5. Fifth Title"""
        
        titles = optimizer._parse_titles(response)
        
        assert len(titles) == 5
        assert titles[0] == "First Title"
        assert titles[4] == "Fifth Title"
    
    def test_parse_titles_with_markdown(self, optimizer):
        """Test parsing titles with markdown formatting"""
        response = """1. **First Title**
2. *Second Title*
3. Third Title"""
        
        titles = optimizer._parse_titles(response)
        
        assert len(titles) == 3
        assert "**" not in titles[0]
        assert "*" not in titles[1]
    
    def test_parse_hashtags_comma_separated(self, optimizer):
        """Test parsing comma-separated hashtags"""
        response = "#AI, #MachineLearning, #Technology, #Innovation"
        
        hashtags = optimizer._parse_hashtags(response)
        
        assert len(hashtags) == 4
        assert all(tag.startswith('#') for tag in hashtags)
    
    def test_parse_hashtags_space_separated(self, optimizer):
        """Test parsing space-separated hashtags"""
        response = "#AI #MachineLearning #Technology #Innovation"
        
        hashtags = optimizer._parse_hashtags(response)
        
        assert len(hashtags) == 4
        assert all(tag.startswith('#') for tag in hashtags)
    
    def test_parse_alt_text_with_quotes(self, optimizer):
        """Test parsing alt-text with quotes"""
        response = '"A person working on a computer"'
        
        alt_text = optimizer._parse_alt_text(response)
        
        assert alt_text == "A person working on a computer"
        assert not alt_text.startswith('"')


class TestSEOMetadata:
    """Tests for SEOMetadata dataclass"""
    
    def test_seo_metadata_creation(self):
        """Test creating SEO metadata"""
        metadata = SEOMetadata(
            titles=["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"],
            hashtags=["#AI", "#Tech", "#ML", "#Innovation"],
            alt_text="A descriptive alt text"
        )
        
        assert len(metadata.titles) == 5
        assert len(metadata.hashtags) == 4
        assert metadata.alt_text == "A descriptive alt text"
    
    def test_seo_metadata_optional_alt_text(self):
        """Test SEO metadata with optional alt-text"""
        metadata = SEOMetadata(
            titles=["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"],
            hashtags=["#AI", "#Tech"]
        )
        
        assert metadata.alt_text is None
