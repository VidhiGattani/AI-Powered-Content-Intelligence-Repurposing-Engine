"""
Content generation orchestrator for multi-platform content generation
"""
import json
import uuid
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models.enums import Platform
from ..utils.aws_clients import S3Client, DynamoDBClient
from ..utils.logger import get_logger
from ..utils.errors import ProcessingError, ErrorCode
from .platform_agents import (
    PlatformAgentFactory,
    StylePatterns,
    GeneratedContent as PlatformGeneratedContent
)
from .style_retrieval_service import StyleRetrievalService
from .topic_extraction_service import Topic

logger = get_logger(__name__)


@dataclass
class GenerationRequest:
    """Request for content generation"""
    user_id: str
    content_id: str
    platforms: List[Platform]
    original_content: str
    topics: List[Topic]


@dataclass
class GeneratedContent:
    """Generated content with metadata"""
    generation_id: str
    content_id: str
    user_id: str
    platform: Platform
    content_text: str
    generated_at: datetime
    version: int
    s3_uri: str
    status: str = "draft"


class ContentGenerationOrchestrator:
    """Orchestrates multi-platform content generation"""
    
    # Generation timeout per platform (seconds)
    GENERATION_TIMEOUT = 15
    
    # S3 bucket for generated content
    GENERATED_CONTENT_BUCKET = "generated-content"
    
    # DynamoDB table for generated content metadata
    GENERATED_CONTENT_TABLE = "generated_content"
    
    def __init__(
        self,
        s3_client: Optional[S3Client] = None,
        dynamodb_client: Optional[DynamoDBClient] = None,
        style_retrieval_service: Optional[StyleRetrievalService] = None
    ):
        self.s3_client = s3_client or S3Client()
        self.dynamodb_client = dynamodb_client or DynamoDBClient()
        self.style_retrieval_service = style_retrieval_service or StyleRetrievalService()
    
    def generate_for_platforms(
        self,
        user_id: str,
        content_id: str,
        platforms: List[Platform],
        original_content: str,
        topics: List[Topic]
    ) -> Dict[Platform, GeneratedContent]:
        """
        Generate content for multiple platforms in parallel
        
        Args:
            user_id: User identifier
            content_id: Original content identifier
            platforms: List of target platforms
            original_content: Original content text
            topics: Extracted topics
        
        Returns:
            Dictionary mapping platform to generated content
        
        Raises:
            ProcessingError: If generation fails for any platform
        """
        try:
            logger.info(
                "Starting multi-platform content generation",
                user_id=user_id,
                content_id=content_id,
                platforms=[p.value for p in platforms]
            )
            
            # Retrieve style patterns
            style_patterns = self._retrieve_style_patterns(user_id, original_content)
            
            # Generate content for each platform in parallel
            results = {}
            with ThreadPoolExecutor(max_workers=len(platforms)) as executor:
                # Submit generation tasks
                future_to_platform = {
                    executor.submit(
                        self._generate_for_single_platform,
                        user_id,
                        content_id,
                        platform,
                        original_content,
                        topics,
                        style_patterns,
                        version=1
                    ): platform
                    for platform in platforms
                }
                
                # Collect results
                for future in as_completed(future_to_platform):
                    platform = future_to_platform[future]
                    try:
                        generated_content = future.result(timeout=self.GENERATION_TIMEOUT)
                        results[platform] = generated_content
                        logger.info(
                            "Platform generation completed",
                            platform=platform.value,
                            generation_id=generated_content.generation_id
                        )
                    except Exception as e:
                        logger.log_error(
                            operation="generate_for_single_platform",
                            error=e,
                            platform=platform.value
                        )
                        raise ProcessingError(
                            error_code=ErrorCode.CONTENT_GENERATION_FAILED,
                            message=f"Failed to generate content for {platform.value}: {str(e)}",
                            details={"platform": platform.value, "content_id": content_id}
                        )
            
            logger.info(
                "Multi-platform generation completed",
                user_id=user_id,
                content_id=content_id,
                platforms_completed=len(results)
            )
            
            return results
            
        except ProcessingError:
            raise
        except Exception as e:
            logger.log_error(
                operation="generate_for_platforms",
                error=e,
                user_id=user_id,
                content_id=content_id
            )
            raise ProcessingError(
                error_code=ErrorCode.CONTENT_GENERATION_FAILED,
                message=f"Content generation failed: {str(e)}",
                details={"user_id": user_id, "content_id": content_id}
            )
    
    def regenerate_content(
        self,
        user_id: str,
        content_id: str,
        platform: Platform,
        original_content: str,
        topics: List[Topic],
        seed: Optional[int] = None
    ) -> GeneratedContent:
        """
        Regenerate content with different seed for variation
        
        Args:
            user_id: User identifier
            content_id: Original content identifier
            platform: Target platform
            original_content: Original content text
            topics: Extracted topics
            seed: Optional random seed for variation
        
        Returns:
            New GeneratedContent instance
        
        Raises:
            ProcessingError: If regeneration fails
        """
        try:
            logger.info(
                "Starting content regeneration",
                user_id=user_id,
                content_id=content_id,
                platform=platform.value,
                seed=seed
            )
            
            # Get current version number
            current_version = self._get_latest_version(content_id, platform)
            new_version = current_version + 1
            
            # Retrieve style patterns (same as original)
            style_patterns = self._retrieve_style_patterns(user_id, original_content)
            
            # Generate new content with different seed
            generated_content = self._generate_for_single_platform(
                user_id,
                content_id,
                platform,
                original_content,
                topics,
                style_patterns,
                version=new_version,
                seed=seed
            )
            
            logger.info(
                "Content regeneration completed",
                generation_id=generated_content.generation_id,
                version=new_version
            )
            
            return generated_content
            
        except Exception as e:
            logger.log_error(
                operation="regenerate_content",
                error=e,
                user_id=user_id,
                content_id=content_id,
                platform=platform.value
            )
            raise ProcessingError(
                error_code=ErrorCode.CONTENT_GENERATION_FAILED,
                message=f"Content regeneration failed: {str(e)}",
                details={"user_id": user_id, "content_id": content_id, "platform": platform.value}
            )
    
    def _retrieve_style_patterns(self, user_id: str, original_content: str) -> StylePatterns:
        """
        Retrieve style patterns for user
        
        Args:
            user_id: User identifier
            original_content: Content to generate embedding for
        
        Returns:
            StylePatterns object
        
        Raises:
            ProcessingError: If style retrieval fails
        """
        try:
            logger.debug(
                "Retrieving style patterns",
                user_id=user_id
            )
            
            # Import here to avoid circular dependency
            from .style_retrieval_service import StyleRetrievalService as StyleRetrievalServiceClass
            from .platform_agents import StylePatterns as PlatformStylePatterns
            
            # Get style patterns from retrieval service
            style_service = StyleRetrievalServiceClass()
            retrieved_patterns = style_service.retrieve_style_patterns(
                user_id=user_id,
                content_text=original_content
            )
            
            # Convert to platform agent format
            chars = retrieved_patterns.characteristics
            platform_patterns = PlatformStylePatterns(
                examples=retrieved_patterns.examples,
                sentence_structure=f"{chars.sentence_structure.get('complexity', 'moderate')} sentences, avg {chars.sentence_structure.get('avg_length', 15)} words",
                vocabulary=f"{chars.vocabulary.get('formality_level', 'neutral')} vocabulary, {chars.vocabulary.get('vocabulary_richness', 0.5):.0%} unique words",
                tone=chars.tone,
                emoji_usage=f"{chars.emoji_usage.get('frequency', 0):.1%} emoji frequency, {chars.emoji_usage.get('placement', 'none')} placement"
            )
            
            logger.debug(
                "Style patterns retrieved and converted",
                user_id=user_id,
                sample_count=len(platform_patterns.examples)
            )
            
            return platform_patterns
            
        except Exception as e:
            logger.log_error(
                operation="_retrieve_style_patterns",
                error=e,
                user_id=user_id
            )
            # Return simple defaults on error
            from .platform_agents import StylePatterns as PlatformStylePatterns
            return PlatformStylePatterns(
                examples=["Professional and engaging content."],
                sentence_structure="moderate sentences, avg 15 words",
                vocabulary="neutral vocabulary, 67% unique words",
                tone="professional",
                emoji_usage="0% emoji frequency, none placement"
            )
    
    def _generate_for_single_platform(
        self,
        user_id: str,
        content_id: str,
        platform: Platform,
        original_content: str,
        topics: List[Topic],
        style_patterns: StylePatterns,
        version: int = 1,
        seed: Optional[int] = None
    ) -> GeneratedContent:
        """
        Generate content for a single platform
        
        Args:
            user_id: User identifier
            content_id: Original content identifier
            platform: Target platform
            original_content: Original content text
            topics: Extracted topics
            style_patterns: Retrieved style patterns
            version: Version number
            seed: Optional random seed
        
        Returns:
            GeneratedContent object
        
        Raises:
            ProcessingError: If generation fails
        """
        try:
            logger.debug(
                "Generating content for platform",
                platform=platform.value,
                version=version
            )
            
            # Create platform agent
            agent = PlatformAgentFactory.create_agent(platform)
            
            # Generate content
            platform_content = agent.generate(
                topics=[t.name for t in topics],
                style_patterns=style_patterns,
                original_content=original_content
            )
            
            # Create generation ID
            generation_id = str(uuid.uuid4())
            
            # Serialize content (handle both string and list)
            if isinstance(platform_content.content, list):
                content_text = json.dumps(platform_content.content)
            else:
                content_text = platform_content.content
            
            # Store in S3
            s3_key = f"{user_id}/{content_id}/{generation_id}.json"
            s3_uri = self._store_generated_content(
                generation_id,
                content_text,
                platform,
                s3_key
            )
            
            # Create metadata object
            generated_content = GeneratedContent(
                generation_id=generation_id,
                content_id=content_id,
                user_id=user_id,
                platform=platform,
                content_text=content_text,
                generated_at=datetime.utcnow(),
                version=version,
                s3_uri=s3_uri,
                status="draft"
            )
            
            # Store metadata in DynamoDB
            self._store_metadata(generated_content)
            
            logger.debug(
                "Platform content generated",
                platform=platform.value,
                generation_id=generation_id
            )
            
            return generated_content
            
        except Exception as e:
            logger.log_error(
                operation="_generate_for_single_platform",
                error=e,
                platform=platform.value
            )
            raise
    
    def _store_generated_content(
        self,
        generation_id: str,
        content_text: str,
        platform: Platform,
        s3_key: str
    ) -> str:
        """
        Store generated content in S3
        
        Args:
            generation_id: Generation identifier
            content_text: Generated content text
            platform: Platform
            s3_key: S3 object key
        
        Returns:
            S3 URI
        
        Raises:
            ProcessingError: If storage fails
        """
        try:
            # Create content object
            content_object = {
                "generation_id": generation_id,
                "platform": platform.value,
                "content": content_text,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Upload to S3
            self.s3_client.put_object(
                bucket=self.GENERATED_CONTENT_BUCKET,
                key=s3_key,
                body=json.dumps(content_object),
                content_type="application/json"
            )
            
            s3_uri = f"s3://{self.GENERATED_CONTENT_BUCKET}/{s3_key}"
            
            logger.debug(
                "Generated content stored in S3",
                generation_id=generation_id,
                s3_uri=s3_uri
            )
            
            return s3_uri
            
        except Exception as e:
            logger.log_error(
                operation="_store_generated_content",
                error=e,
                generation_id=generation_id
            )
            raise ProcessingError(
                error_code=ErrorCode.S3_ACCESS_ERROR,
                message=f"Failed to store generated content: {str(e)}",
                details={"generation_id": generation_id}
            )
    
    def _store_metadata(self, generated_content: GeneratedContent) -> None:
        """
        Store generated content metadata in DynamoDB
        
        Args:
            generated_content: GeneratedContent object
        
        Raises:
            ProcessingError: If storage fails
        """
        try:
            # Convert to dict
            item = {
                "content_id": generated_content.content_id,
                "generation_id": generated_content.generation_id,
                "user_id": generated_content.user_id,
                "platform": generated_content.platform.value,
                "content_text": generated_content.content_text,
                "generated_at": generated_content.generated_at.isoformat(),
                "version": generated_content.version,
                "s3_uri": generated_content.s3_uri,
                "status": generated_content.status
            }
            
            # Store in DynamoDB
            self.dynamodb_client.put_item(
                table_name=self.GENERATED_CONTENT_TABLE,
                item=item
            )
            
            logger.debug(
                "Generated content metadata stored",
                generation_id=generated_content.generation_id
            )
            
        except Exception as e:
            logger.log_error(
                operation="_store_metadata",
                error=e,
                generation_id=generated_content.generation_id
            )
            raise ProcessingError(
                error_code=ErrorCode.DYNAMODB_ERROR,
                message=f"Failed to store metadata: {str(e)}",
                details={"generation_id": generated_content.generation_id}
            )
    
    def _get_latest_version(self, content_id: str, platform: Platform) -> int:
        """
        Get latest version number for content and platform
        
        Args:
            content_id: Content identifier
            platform: Platform
        
        Returns:
            Latest version number (0 if no versions exist)
        """
        try:
            # Query DynamoDB for all versions
            response = self.dynamodb_client.query(
                table_name=self.GENERATED_CONTENT_TABLE,
                key_condition_expression="content_id = :content_id",
                expression_attribute_values={
                    ":content_id": content_id,
                    ":platform": platform.value
                },
                filter_expression="platform = :platform"
            )
            
            items = response.get('Items', [])
            if not items:
                return 0
            
            # Find max version
            max_version = max(item.get('version', 0) for item in items)
            return max_version
            
        except Exception as e:
            logger.log_error(
                operation="_get_latest_version",
                error=e,
                content_id=content_id,
                platform=platform.value
            )
            # Return 0 if query fails (will create version 1)
            return 0
