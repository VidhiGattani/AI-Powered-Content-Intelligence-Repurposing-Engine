"""
Unit tests for ContentEditingService
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import json

from src.services.content_editing_service import (
    ContentEditingService,
    CharacterCount,
    ValidationWarning
)
from src.models.enums import Platform, ContentStatus
from src.utils.errors import ValidationError, NotFoundError, ErrorCode


class TestEditContent:
    """Tests for edit_content method"""
    
    @patch('src.services.content_editing_service.S3Client')
    @patch('src.services.content_editing_service.DynamoDBClient')
    def test_edit_content_success(self, mock_ddb_class, mock_s3_class):
        """Test successful content editing"""
        mock_ddb = Mock()
        mock_s3 = Mock()
        mock_ddb_class.return_value = mock_ddb
        mock_s3_class.return_value = mock_s3
        
        mock_ddb.get_item.return_value = {
            "generation_id": "gen123",
            "user_id": "user456",
            "content": "Original content"
        }
        
        service = ContentEditingService()
        result = service.edit_content(
            generation_id="gen123",
            user_id="user456",
            edited_content="Edited content"
        )
        
        assert result["edited_content"] == "Edited content"
        assert "last_edited_at" in result
        mock_s3.upload_file.assert_called_once()
        mock_ddb.update_item.assert_called_once()
    
    @patch('src.services.content_editing_service.S3Client')
    @patch('src.services.content_editing_service.DynamoDBClient')
    def test_edit_content_not_found(self, mock_ddb_class, mock_s3_class):
        """Test editing non-existent content"""
        mock_ddb = Mock()
        mock_s3 = Mock()
        mock_ddb_class.return_value = mock_ddb
        mock_s3_class.return_value = mock_s3
        
        mock_ddb.get_item.return_value = None
        
        service = ContentEditingService()
        
        with pytest.raises(NotFoundError) as exc_info:
            service.edit_content(
                generation_id="nonexistent",
                user_id="user456",
                edited_content="Edited content"
            )
        
        assert exc_info.value.error_code == ErrorCode.CONTENT_NOT_FOUND


class TestApproveContent:
    """Tests for approve_content method"""
    
    @patch('src.services.content_editing_service.S3Client')
    @patch('src.services.content_editing_service.DynamoDBClient')
    def test_approve_content_success(self, mock_ddb_class, mock_s3_class):
        """Test successful content approval"""
        mock_ddb = Mock()
        mock_s3 = Mock()
        mock_ddb_class.return_value = mock_ddb
        mock_s3_class.return_value = mock_s3
        
        mock_ddb.get_item.return_value = {
            "generation_id": "gen123",
            "user_id": "user456",
            "status": "draft"
        }
        
        service = ContentEditingService()
        result = service.approve_content(
            generation_id="gen123",
            user_id="user456"
        )
        
        assert result["status"] == ContentStatus.APPROVED.value
        assert "approved_at" in result
        mock_ddb.update_item.assert_called_once()
    
    @patch('src.services.content_editing_service.S3Client')
    @patch('src.services.content_editing_service.DynamoDBClient')
    def test_approve_content_not_found(self, mock_ddb_class, mock_s3_class):
        """Test approving non-existent content"""
        mock_ddb = Mock()
        mock_s3 = Mock()
        mock_ddb_class.return_value = mock_ddb
        mock_s3_class.return_value = mock_s3
        
        mock_ddb.get_item.return_value = None
        
        service = ContentEditingService()
        
        with pytest.raises(NotFoundError) as exc_info:
            service.approve_content(
                generation_id="nonexistent",
                user_id="user456"
            )
        
        assert exc_info.value.error_code == ErrorCode.CONTENT_NOT_FOUND


class TestCalculateCharacterCount:
    """Tests for calculate_character_count method"""
    
    def test_calculate_character_count_linkedin(self):
        """Test character count for LinkedIn"""
        service = ContentEditingService()
        content = "This is a LinkedIn post with some content."
        
        result = service.calculate_character_count(content, Platform.LINKEDIN)
        
        assert isinstance(result, CharacterCount)
        assert result.count == len(content)
        assert result.limit == 3000
        assert result.exceeds_limit is False
        assert result.platform == Platform.LINKEDIN
    
    def test_calculate_character_count_twitter(self):
        """Test character count for Twitter"""
        service = ContentEditingService()
        tweets = ["Tweet 1", "Tweet 2 with more content", "Tweet 3"]
        content = json.dumps(tweets)
        
        result = service.calculate_character_count(content, Platform.TWITTER)
        
        assert result.count == len("Tweet 2 with more content")  # Max length
        assert result.limit == 280
        assert result.exceeds_limit is False
    
    def test_calculate_character_count_exceeds_limit(self):
        """Test character count exceeding limit"""
        service = ContentEditingService()
        content = "x" * 300  # Exceeds Twitter limit
        
        result = service.calculate_character_count(content, Platform.TWITTER)
        
        assert result.count == 300
        assert result.exceeds_limit is True
    
    def test_calculate_character_count_instagram(self):
        """Test character count for Instagram"""
        service = ContentEditingService()
        content = "Instagram caption with emojis 🎉"
        
        result = service.calculate_character_count(content, Platform.INSTAGRAM)
        
        assert result.count == len(content)
        assert result.limit == 2200
        assert result.exceeds_limit is False


class TestValidatePlatformLimits:
    """Tests for validate_platform_limits method"""
    
    def test_validate_twitter_valid(self):
        """Test validating valid Twitter thread"""
        service = ContentEditingService()
        tweets = ["Tweet " + str(i) for i in range(6)]  # 6 tweets
        content = json.dumps(tweets)
        
        warnings = service.validate_platform_limits(content, Platform.TWITTER)
        
        assert len(warnings) == 0
    
    def test_validate_twitter_too_many_tweets(self):
        """Test validating Twitter thread with too many tweets"""
        service = ContentEditingService()
        tweets = ["Tweet " + str(i) for i in range(10)]  # 10 tweets (max 7)
        content = json.dumps(tweets)
        
        warnings = service.validate_platform_limits(content, Platform.TWITTER)
        
        assert len(warnings) > 0
        assert any("too many tweets" in w.message for w in warnings)
    
    def test_validate_twitter_too_few_tweets(self):
        """Test validating Twitter thread with too few tweets"""
        service = ContentEditingService()
        tweets = ["Tweet 1", "Tweet 2"]  # 2 tweets (min 5)
        content = json.dumps(tweets)
        
        warnings = service.validate_platform_limits(content, Platform.TWITTER)
        
        assert len(warnings) > 0
        assert any("too few tweets" in w.message for w in warnings)
    
    def test_validate_twitter_tweet_too_long(self):
        """Test validating Twitter with tweet exceeding character limit"""
        service = ContentEditingService()
        tweets = ["Short tweet", "x" * 300]  # Second tweet too long
        content = json.dumps(tweets)
        
        warnings = service.validate_platform_limits(content, Platform.TWITTER)
        
        assert len(warnings) > 0
        assert any("exceeds character limit" in w.message for w in warnings)
    
    def test_validate_linkedin_valid(self):
        """Test validating valid LinkedIn post"""
        service = ContentEditingService()
        content = " ".join(["word"] * 200)  # 200 words
        
        warnings = service.validate_platform_limits(content, Platform.LINKEDIN)
        
        assert len(warnings) == 0
    
    def test_validate_linkedin_too_long(self):
        """Test validating LinkedIn post exceeding character limit"""
        service = ContentEditingService()
        content = "x" * 3500  # Exceeds 3000 char limit
        
        warnings = service.validate_platform_limits(content, Platform.LINKEDIN)
        
        assert len(warnings) > 0
        assert any("exceeds LinkedIn character limit" in w.message for w in warnings)
    
    def test_validate_linkedin_word_count_outside_range(self):
        """Test validating LinkedIn post with word count outside recommended range"""
        service = ContentEditingService()
        content = " ".join(["word"] * 50)  # 50 words (recommended 150-250)
        
        warnings = service.validate_platform_limits(content, Platform.LINKEDIN)
        
        assert len(warnings) > 0
        assert any("outside recommended range" in w.message for w in warnings)
    
    def test_validate_instagram_valid(self):
        """Test validating valid Instagram caption"""
        service = ContentEditingService()
        content = " ".join(["word"] * 120)  # 120 words
        
        warnings = service.validate_platform_limits(content, Platform.INSTAGRAM)
        
        assert len(warnings) == 0
    
    def test_validate_instagram_too_long(self):
        """Test validating Instagram caption exceeding character limit"""
        service = ContentEditingService()
        content = "x" * 2500  # Exceeds 2200 char limit
        
        warnings = service.validate_platform_limits(content, Platform.INSTAGRAM)
        
        assert len(warnings) > 0
        assert any("exceeds Instagram character limit" in w.message for w in warnings)
    
    def test_validate_youtube_shorts_missing_timestamps(self):
        """Test validating YouTube Shorts without timestamps"""
        service = ContentEditingService()
        content = "Script without timestamps"
        
        warnings = service.validate_platform_limits(content, Platform.YOUTUBE_SHORTS)
        
        assert len(warnings) > 0
        assert any("timestamps" in w.message for w in warnings)
    
    def test_validate_youtube_shorts_with_timestamps(self):
        """Test validating YouTube Shorts with timestamps"""
        service = ContentEditingService()
        content = "[0:00] Hook\n[0:05] Main content\n[0:55] CTA"
        
        warnings = service.validate_platform_limits(content, Platform.YOUTUBE_SHORTS)
        
        # Should have no warnings about timestamps
        assert not any("timestamps" in w.message for w in warnings)


class TestValidationWarning:
    """Tests for ValidationWarning dataclass"""
    
    def test_validation_warning_creation(self):
        """Test creating a ValidationWarning"""
        warning = ValidationWarning(
            field="character_count",
            message="Content exceeds limit",
            current_value=300,
            limit=280
        )
        
        assert warning.field == "character_count"
        assert warning.message == "Content exceeds limit"
        assert warning.current_value == 300
        assert warning.limit == 280


class TestCharacterCount:
    """Tests for CharacterCount dataclass"""
    
    def test_character_count_creation(self):
        """Test creating a CharacterCount"""
        char_count = CharacterCount(
            count=150,
            limit=280,
            exceeds_limit=False,
            platform=Platform.TWITTER
        )
        
        assert char_count.count == 150
        assert char_count.limit == 280
        assert char_count.exceeds_limit is False
        assert char_count.platform == Platform.TWITTER
