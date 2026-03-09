"""
SEO Optimizer service for generating titles, hashtags, and alt-text
"""
from typing import List, Optional
from dataclasses import dataclass
from ..models.enums import Platform
from ..utils.aws_clients import BedrockClient
from ..utils.logger import get_logger
from ..utils.errors import ProcessingError, ErrorCode

logger = get_logger(__name__)


@dataclass
class SEOMetadata:
    """SEO metadata for generated content"""
    titles: List[str]  # 5 variants
    hashtags: List[str]  # 4-8 hashtags
    alt_text: Optional[str] = None


class SEOOptimizer:
    """Service for generating SEO-optimized titles, hashtags, and alt-text"""
    
    # Claude Sonnet 3.5 model ID
    CLAUDE_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    # Title generation approaches
    TITLE_APPROACHES = ["curiosity", "benefit", "listicle", "question", "statement"]
    
    # Hashtag count constraints
    MIN_HASHTAGS = 4
    MAX_HASHTAGS = 8
    
    # Alt-text max length
    MAX_ALT_TEXT_LENGTH = 125
    
    def __init__(self, bedrock_client: Optional[BedrockClient] = None):
        self.bedrock_client = bedrock_client or BedrockClient()
    
    def generate_titles(
        self,
        content: str,
        topics: List[str]
    ) -> List[str]:
        """
        Generate 5 title variants using different approaches
        
        Args:
            content: Content text
            topics: Key topics from content
        
        Returns:
            List of 5 titles (curiosity, benefit, listicle, question, statement)
        
        Raises:
            ProcessingError: If title generation fails
        """
        try:
            logger.info(
                "Generating SEO titles",
                topics_count=len(topics)
            )
            
            # Build prompt for title generation
            prompt = self._build_title_prompt(content, topics)
            
            # Call Claude
            response = self._invoke_claude(prompt, max_tokens=500)
            
            # Parse titles from response
            titles = self._parse_titles(response)
            
            # Validate we have exactly 5 titles
            if len(titles) != 5:
                logger.warning(
                    "Title count mismatch",
                    expected=5,
                    actual=len(titles)
                )
                # Pad or truncate to 5
                if len(titles) < 5:
                    titles.extend([titles[0]] * (5 - len(titles)))
                else:
                    titles = titles[:5]
            
            logger.info(
                "SEO titles generated",
                title_count=len(titles)
            )
            
            return titles
            
        except Exception as e:
            logger.log_error(
                operation="generate_titles",
                error=e
            )
            raise ProcessingError(
                error_code=ErrorCode.CONTENT_GENERATION_FAILED,
                message=f"Failed to generate titles: {str(e)}",
                details={"topics_count": len(topics)}
            )
    
    def generate_hashtags(
        self,
        content: str,
        platform: Platform,
        topics: List[str]
    ) -> List[str]:
        """
        Generate 4-8 platform-specific hashtags
        
        Args:
            content: Content text
            platform: Target platform
            topics: Key topics from content
        
        Returns:
            List of hashtags with # prefix
        
        Raises:
            ProcessingError: If hashtag generation fails
        """
        try:
            logger.info(
                "Generating hashtags",
                platform=platform.value,
                topics_count=len(topics)
            )
            
            # Build prompt for hashtag generation
            prompt = self._build_hashtag_prompt(content, platform, topics)
            
            # Call Claude
            response = self._invoke_claude(prompt, max_tokens=300)
            
            # Parse hashtags from response
            hashtags = self._parse_hashtags(response)
            
            # Validate hashtag count
            if len(hashtags) < self.MIN_HASHTAGS or len(hashtags) > self.MAX_HASHTAGS:
                logger.warning(
                    "Hashtag count out of range",
                    expected_range=f"{self.MIN_HASHTAGS}-{self.MAX_HASHTAGS}",
                    actual=len(hashtags)
                )
                # Adjust to valid range
                if len(hashtags) < self.MIN_HASHTAGS:
                    # Pad with generic hashtags
                    hashtags.extend([f"#{topic.replace(' ', '')}" for topic in topics[:self.MIN_HASHTAGS - len(hashtags)]])
                else:
                    hashtags = hashtags[:self.MAX_HASHTAGS]
            
            logger.info(
                "Hashtags generated",
                hashtag_count=len(hashtags),
                platform=platform.value
            )
            
            return hashtags
            
        except Exception as e:
            logger.log_error(
                operation="generate_hashtags",
                error=e,
                platform=platform.value
            )
            raise ProcessingError(
                error_code=ErrorCode.CONTENT_GENERATION_FAILED,
                message=f"Failed to generate hashtags: {str(e)}",
                details={"platform": platform.value, "topics_count": len(topics)}
            )
    
    def generate_alt_text(self, image_description: str) -> str:
        """
        Generate descriptive alt-text for accessibility
        
        Args:
            image_description: Description of the image
        
        Returns:
            Alt-text string (max 125 characters)
        
        Raises:
            ProcessingError: If alt-text generation fails
        """
        try:
            logger.info(
                "Generating alt-text",
                description_length=len(image_description)
            )
            
            # Build prompt for alt-text generation
            prompt = self._build_alt_text_prompt(image_description)
            
            # Call Claude
            response = self._invoke_claude(prompt, max_tokens=200)
            
            # Parse alt-text from response
            alt_text = self._parse_alt_text(response)
            
            # Ensure max length
            if len(alt_text) > self.MAX_ALT_TEXT_LENGTH:
                logger.warning(
                    "Alt-text too long, truncating",
                    original_length=len(alt_text),
                    max_length=self.MAX_ALT_TEXT_LENGTH
                )
                alt_text = alt_text[:self.MAX_ALT_TEXT_LENGTH-3] + "..."
            
            logger.info(
                "Alt-text generated",
                length=len(alt_text)
            )
            
            return alt_text
            
        except Exception as e:
            logger.log_error(
                operation="generate_alt_text",
                error=e
            )
            raise ProcessingError(
                error_code=ErrorCode.CONTENT_GENERATION_FAILED,
                message=f"Failed to generate alt-text: {str(e)}",
                details={"description_length": len(image_description)}
            )
    
    def _build_title_prompt(self, content: str, topics: List[str]) -> str:
        """Build prompt for title generation"""
        topics_text = ", ".join(topics)
        
        prompt = f"""You are an expert content marketer. Generate 5 compelling title variants for the following content using different approaches.

Content:
{content[:1000]}

Key Topics: {topics_text}

Generate exactly 5 titles using these approaches:
1. Curiosity: Create intrigue and make readers want to learn more
2. Benefit: Highlight the value or benefit readers will get
3. Listicle: Use a numbered list format (e.g., "7 Ways to...")
4. Question: Pose a thought-provoking question
5. Statement: Make a bold, declarative statement

Requirements:
- Each title should be 50-70 characters
- Make them engaging and click-worthy
- Ensure they're relevant to the content and topics

Format your response as:
1. [Curiosity title]
2. [Benefit title]
3. [Listicle title]
4. [Question title]
5. [Statement title]

Respond only with the 5 titles, one per line."""

        return prompt
    
    def _build_hashtag_prompt(
        self,
        content: str,
        platform: Platform,
        topics: List[str]
    ) -> str:
        """Build prompt for hashtag generation"""
        topics_text = ", ".join(topics)
        
        # Platform-specific guidance
        platform_guidance = {
            Platform.TWITTER: "Focus on trending and conversational hashtags. Keep them concise.",
            Platform.INSTAGRAM: "Use high-engagement hashtags. Mix popular and niche tags.",
            Platform.LINKEDIN: "Use professional and industry-specific hashtags.",
            Platform.YOUTUBE_SHORTS: "Use discovery-focused hashtags for video content."
        }
        
        guidance = platform_guidance.get(platform, "Use relevant and engaging hashtags.")
        
        prompt = f"""You are a social media expert. Generate 4-8 relevant hashtags for the following content.

Content:
{content[:800]}

Key Topics: {topics_text}
Platform: {platform.value}

Platform Guidance: {guidance}

Requirements:
- Generate between 4 and 8 hashtags
- Each hashtag should start with #
- No spaces in hashtags (use camelCase if needed)
- Make them relevant to the content and topics
- Mix popular and specific hashtags

Format your response as a comma-separated list:
#hashtag1, #hashtag2, #hashtag3, ...

Respond only with the hashtags."""

        return prompt
    
    def _build_alt_text_prompt(self, image_description: str) -> str:
        """Build prompt for alt-text generation"""
        
        prompt = f"""You are an accessibility expert. Generate descriptive alt-text for an image based on this description.

Image Description:
{image_description}

Requirements:
- Maximum 125 characters
- Be descriptive and specific
- Focus on what's important in the image
- Use clear, concise language
- Don't start with "Image of" or "Picture of"

Respond only with the alt-text, nothing else."""

        return prompt
    
    def _invoke_claude(self, prompt: str, max_tokens: int = 500) -> str:
        """Invoke Claude Sonnet model via Bedrock"""
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            logger.debug(
                "Invoking Claude Sonnet",
                model_id=self.CLAUDE_MODEL_ID
            )
            
            response = self.bedrock_client.invoke_model(
                model_id=self.CLAUDE_MODEL_ID,
                body=request_body
            )
            
            # Extract text from response
            content = response.get('content', [])
            if content and len(content) > 0:
                return content[0].get('text', '')
            
            raise ProcessingError(
                error_code=ErrorCode.BEDROCK_UNAVAILABLE,
                message="Empty response from Bedrock",
                details={"response": response}
            )
            
        except Exception as e:
            logger.log_error(
                operation="_invoke_claude",
                error=e,
                model_id=self.CLAUDE_MODEL_ID
            )
            raise
    
    def _parse_titles(self, response: str) -> List[str]:
        """Parse titles from Claude response"""
        lines = response.strip().split('\n')
        titles = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove numbering (1., 2., etc.)
            if line[0].isdigit() and '.' in line[:3]:
                line = line.split('.', 1)[1].strip()
            
            # Remove markdown formatting
            line = line.strip('*').strip()
            
            if line:
                titles.append(line)
        
        return titles
    
    def _parse_hashtags(self, response: str) -> List[str]:
        """Parse hashtags from Claude response"""
        # Remove any extra text
        text = response.strip()
        
        # Split by comma or whitespace
        parts = text.replace(',', ' ').split()
        
        hashtags = []
        for part in parts:
            part = part.strip()
            if part.startswith('#'):
                # Ensure no spaces in hashtag
                hashtag = part.replace(' ', '')
                hashtags.append(hashtag)
        
        return hashtags
    
    def _parse_alt_text(self, response: str) -> str:
        """Parse alt-text from Claude response"""
        # Clean up response
        alt_text = response.strip()
        
        # Remove quotes if present
        if alt_text.startswith('"') and alt_text.endswith('"'):
            alt_text = alt_text[1:-1]
        
        return alt_text
