"""
Content Editing Service

Handles content editing, approval, character counting, and platform limit validation.
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json

from src.models.enums import Platform, ContentStatus
from src.utils.errors import ValidationError, NotFoundError, ErrorCode
from src.utils.logger import get_logger
from src.utils.aws_clients import DynamoDBClient, S3Client

logger = get_logger(__name__)


@dataclass
class CharacterCount:
    """Character count information for content"""
    count: int
    limit: int
    exceeds_limit: bool
    platform: Platform


@dataclass
class ValidationWarning:
    """Validation warning for content"""
    field: str
    message: str
    current_value: int
    limit: int


class ContentEditingService:
    """Service for editing, approving, and validating generated content"""
    
    # Platform-specific character/word limits
    PLATFORM_LIMITS = {
        Platform.LINKEDIN: {
            "max_characters": 3000,
            "recommended_words": (150, 250),
            "type": "words"
        },
        Platform.TWITTER: {
            "max_characters": 280,  # Per tweet
            "max_tweets": 7,
            "min_tweets": 5,
            "type": "tweets"
        },
        Platform.INSTAGRAM: {
            "max_characters": 2200,
            "recommended_words": (100, 150),
            "type": "words"
        },
        Platform.YOUTUBE_SHORTS: {
            "max_duration": 60,  # seconds
            "min_duration": 30,
            "type": "duration"
        }
    }
    
    def __init__(
        self,
        dynamodb_client: Optional[DynamoDBClient] = None,
        s3_client: Optional[S3Client] = None,
        generated_content_table: str = "generated_content"
    ):
        """
        Initialize content editing service
        
        Args:
            dynamodb_client: DynamoDB client (optional)
            s3_client: S3 client (optional)
            generated_content_table: DynamoDB table name for generated content
        """
        self.dynamodb = dynamodb_client or DynamoDBClient()
        self.s3 = s3_client or S3Client()
        self.generated_content_table = generated_content_table
    
    def edit_content(
        self,
        generation_id: str,
        user_id: str,
        edited_content: str
    ) -> Dict:
        """
        Edit generated content and save the edited version
        
        Args:
            generation_id: Generated content ID
            user_id: User ID (for authorization)
            edited_content: Edited content text
            
        Returns:
            Updated content metadata
            
        Raises:
            NotFoundError: If content doesn't exist
            ValidationError: If edit fails
        """
        try:
            # Get existing content
            content = self.dynamodb.get_item(
                table_name=self.generated_content_table,
                key={
                    "generation_id": generation_id,
                    "user_id": user_id
                }
            )
            
            if not content:
                raise NotFoundError(
                    error_code=ErrorCode.CONTENT_NOT_FOUND,
                    message=f"Generated content {generation_id} not found"
                )
            
            # Store edited content in S3
            s3_key = f"generated-content/{user_id}/{generation_id}_edited.txt"
            self.s3.upload_file(
                file_content=edited_content.encode('utf-8'),
                bucket="generated-content",
                key=s3_key,
                content_type="text/plain"
            )
            
            # Update metadata
            self.dynamodb.update_item(
                table_name=self.generated_content_table,
                key={
                    "generation_id": generation_id,
                    "user_id": user_id
                },
                update_expression="SET edited_content_s3_uri = :uri, last_edited_at = :timestamp",
                expression_attribute_values={
                    ":uri": f"s3://generated-content/{s3_key}",
                    ":timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Content {generation_id} edited successfully")
            
            # Return updated content
            content["edited_content"] = edited_content
            content["last_edited_at"] = datetime.utcnow().isoformat()
            return content
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to edit content: {str(e)}")
            raise ValidationError(
                error_code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to edit content: {str(e)}"
            )
    
    def approve_content(
        self,
        generation_id: str,
        user_id: str
    ) -> Dict:
        """
        Approve content and mark it as ready for scheduling/publishing
        
        Args:
            generation_id: Generated content ID
            user_id: User ID (for authorization)
            
        Returns:
            Updated content metadata
            
        Raises:
            NotFoundError: If content doesn't exist
        """
        try:
            # Get existing content
            content = self.dynamodb.get_item(
                table_name=self.generated_content_table,
                key={
                    "generation_id": generation_id,
                    "user_id": user_id
                }
            )
            
            if not content:
                raise NotFoundError(
                    error_code=ErrorCode.CONTENT_NOT_FOUND,
                    message=f"Generated content {generation_id} not found"
                )
            
            # Update status to APPROVED
            self.dynamodb.update_item(
                table_name=self.generated_content_table,
                key={
                    "generation_id": generation_id,
                    "user_id": user_id
                },
                update_expression="SET #status = :approved, approved_at = :timestamp",
                expression_attribute_values={
                    ":approved": ContentStatus.APPROVED.value,
                    ":timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Content {generation_id} approved")
            
            # Return updated content
            content["status"] = ContentStatus.APPROVED.value
            content["approved_at"] = datetime.utcnow().isoformat()
            return content
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to approve content: {str(e)}")
            raise ValidationError(
                error_code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to approve content: {str(e)}"
            )
    
    def calculate_character_count(
        self,
        content: str,
        platform: Platform
    ) -> CharacterCount:
        """
        Calculate character count for content on a specific platform
        
        Args:
            content: Content text
            platform: Target platform
            
        Returns:
            CharacterCount with count, limit, and exceeds_limit flag
        """
        limits = self.PLATFORM_LIMITS.get(platform, {})
        
        if platform == Platform.TWITTER:
            # For Twitter, parse as JSON array of tweets
            try:
                tweets = json.loads(content) if isinstance(content, str) and content.startswith('[') else [content]
                max_length = max(len(tweet) for tweet in tweets) if tweets else 0
                limit = limits.get("max_characters", 280)
                exceeds = max_length > limit
            except:
                max_length = len(content)
                limit = limits.get("max_characters", 280)
                exceeds = max_length > limit
        else:
            max_length = len(content)
            limit = limits.get("max_characters", 3000)
            exceeds = max_length > limit
        
        return CharacterCount(
            count=max_length,
            limit=limit,
            exceeds_limit=exceeds,
            platform=platform
        )
    
    def validate_platform_limits(
        self,
        content: str,
        platform: Platform
    ) -> List[ValidationWarning]:
        """
        Validate content against platform-specific limits
        
        Args:
            content: Content text
            platform: Target platform
            
        Returns:
            List of validation warnings (empty if no issues)
        """
        warnings = []
        limits = self.PLATFORM_LIMITS.get(platform, {})
        
        if platform == Platform.TWITTER:
            # Validate Twitter thread
            try:
                tweets = json.loads(content) if isinstance(content, str) and content.startswith('[') else [content]
                
                # Check tweet count
                if len(tweets) > limits.get("max_tweets", 7):
                    warnings.append(ValidationWarning(
                        field="tweet_count",
                        message=f"Thread has too many tweets (max {limits['max_tweets']})",
                        current_value=len(tweets),
                        limit=limits["max_tweets"]
                    ))
                
                if len(tweets) < limits.get("min_tweets", 5):
                    warnings.append(ValidationWarning(
                        field="tweet_count",
                        message=f"Thread has too few tweets (min {limits['min_tweets']})",
                        current_value=len(tweets),
                        limit=limits["min_tweets"]
                    ))
                
                # Check individual tweet lengths
                for i, tweet in enumerate(tweets):
                    if len(tweet) > limits.get("max_characters", 280):
                        warnings.append(ValidationWarning(
                            field=f"tweet_{i+1}_length",
                            message=f"Tweet {i+1} exceeds character limit",
                            current_value=len(tweet),
                            limit=limits["max_characters"]
                        ))
            except:
                # If not valid JSON, treat as single tweet
                if len(content) > limits.get("max_characters", 280):
                    warnings.append(ValidationWarning(
                        field="character_count",
                        message="Content exceeds Twitter character limit",
                        current_value=len(content),
                        limit=limits["max_characters"]
                    ))
        
        elif platform == Platform.LINKEDIN:
            char_count = len(content)
            word_count = len(content.split())
            
            if char_count > limits.get("max_characters", 3000):
                warnings.append(ValidationWarning(
                    field="character_count",
                    message="Content exceeds LinkedIn character limit",
                    current_value=char_count,
                    limit=limits["max_characters"]
                ))
            
            recommended = limits.get("recommended_words", (150, 250))
            if word_count < recommended[0] or word_count > recommended[1]:
                warnings.append(ValidationWarning(
                    field="word_count",
                    message=f"Word count outside recommended range ({recommended[0]}-{recommended[1]})",
                    current_value=word_count,
                    limit=recommended[1]
                ))
        
        elif platform == Platform.INSTAGRAM:
            char_count = len(content)
            word_count = len(content.split())
            
            if char_count > limits.get("max_characters", 2200):
                warnings.append(ValidationWarning(
                    field="character_count",
                    message="Content exceeds Instagram character limit",
                    current_value=char_count,
                    limit=limits["max_characters"]
                ))
            
            recommended = limits.get("recommended_words", (100, 150))
            if word_count < recommended[0] or word_count > recommended[1]:
                warnings.append(ValidationWarning(
                    field="word_count",
                    message=f"Word count outside recommended range ({recommended[0]}-{recommended[1]})",
                    current_value=word_count,
                    limit=recommended[1]
                ))
        
        elif platform == Platform.YOUTUBE_SHORTS:
            # For YouTube Shorts, we'd need to parse timestamps
            # For now, just check if content has timestamp markers
            if "[" not in content or "]" not in content:
                warnings.append(ValidationWarning(
                    field="format",
                    message="YouTube Shorts script should include timestamps",
                    current_value=0,
                    limit=1
                ))
        
        return warnings
