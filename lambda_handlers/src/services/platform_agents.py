"""
Platform-specific content generation agents

Each agent generates content optimized for a specific social media platform
using Claude Sonnet 3.5 via Amazon Bedrock.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json
import re

from ..models.enums import Platform
from ..utils.aws_clients import BedrockClient
from ..utils.logger import get_logger
from ..utils.errors import ValidationError, ErrorCode

logger = get_logger(__name__)


@dataclass
class StylePatterns:
    """Style patterns retrieved from user's past content"""
    examples: List[str]
    sentence_structure: str
    vocabulary: str
    tone: str
    emoji_usage: str


@dataclass
class GeneratedContent:
    """Generated platform-specific content"""
    platform: Platform
    content: Any  # str for most platforms, List[str] for Twitter threads
    metadata: Dict[str, Any]
    word_count: Optional[int] = None
    character_count: Optional[int] = None


@dataclass
class ValidationResult:
    """Content validation result"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


@dataclass
class PlatformConstraints:
    """Platform-specific constraints"""
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    format_requirements: Optional[List[str]] = None
    style_guidelines: Optional[List[str]] = None


class PlatformAgent(ABC):
    """Base class for platform-specific content generation agents"""
    
    def __init__(self):
        self.bedrock_client = BedrockClient()
        self.model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        self.temperature = 0.7
    
    @abstractmethod
    def generate(
        self,
        topics: List[str],
        style_patterns: StylePatterns,
        original_content: str
    ) -> GeneratedContent:
        """
        Generate platform-optimized content
        
        Args:
            topics: Key topics extracted from original content
            style_patterns: User's writing style patterns
            original_content: Original content text
            
        Returns:
            GeneratedContent with platform-specific formatting
        """
        pass
    
    @abstractmethod
    def validate(self, content: Any) -> ValidationResult:
        """
        Validate content meets platform requirements
        
        Args:
            content: Generated content to validate
            
        Returns:
            ValidationResult with errors and warnings
        """
        pass
    
    @abstractmethod
    def get_constraints(self) -> PlatformConstraints:
        """
        Get platform-specific constraints
        
        Returns:
            PlatformConstraints for this platform
        """
        pass
    
    def _build_base_prompt(
        self,
        topics: List[str],
        style_patterns: StylePatterns,
        original_content: str,
        platform_instructions: str
    ) -> str:
        """Build base prompt with style patterns and platform instructions"""
        
        # Format style examples
        style_examples_text = "\n\n".join([
            f"Example {i+1}:\n{example}"
            for i, example in enumerate(style_patterns.examples[:3])
        ])
        
        # Format topics
        topics_text = "\n".join([f"- {topic}" for topic in topics])
        
        prompt = f"""You are a content repurposing assistant. Your ONLY job is to transform the ORIGINAL CONTENT below into a platform-optimized post.

==================== ORIGINAL CONTENT (READ THIS CAREFULLY) ====================
{original_content[:8000]}
================================================================================

KEY TOPICS FROM THE ORIGINAL CONTENT:
{topics_text}

CREATOR'S STYLE PROFILE:
The creator's writing style has these characteristics:
- Sentence Structure: {style_patterns.sentence_structure}
- Vocabulary: {style_patterns.vocabulary}
- Tone: {style_patterns.tone}
- Emoji Usage: {style_patterns.emoji_usage}

STYLE EXAMPLES FROM CREATOR'S PAST CONTENT:
{style_examples_text}

{platform_instructions}

🚨 CRITICAL REQUIREMENTS - YOU MUST FOLLOW THESE:
1. READ THE ORIGINAL CONTENT ABOVE CAREFULLY - Your post MUST be about the same topic
2. Extract the MAIN IDEAS, KEY FACTS, and SPECIFIC DETAILS from the original content
3. DO NOT write generic content about "innovation", "strategy", or "growth" unless those are the actual topics in the original content
4. If the original content is about blockchain, your post MUST be about blockchain
5. If the original content is about a specific technology, product, or concept, your post MUST be about that same thing
6. Use SPECIFIC information from the original content - mention actual concepts, technologies, or ideas discussed
7. Maintain the creator's voice using their style patterns
8. Your generated content should make it obvious you read and understood the original content

REMEMBER: The reader should be able to tell what the original content was about just by reading your generated post!
    
    def _invoke_bedrock(self, prompt: str, max_tokens: int = 1000) -> str:
        """Invoke Claude via Bedrock"""
        try:
            # Log first 1000 chars of prompt to verify what's being sent
            logger.info(
                "Invoking Bedrock with prompt",
                model_id=self.model_id,
                prompt_length=len(prompt),
                prompt_preview=prompt[:1000] + "..." if len(prompt) > 1000 else prompt
            )
            
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": self.temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                model_id=self.model_id,
                body=body
            )
            
            # Extract text from Claude response
            content = response.get("content", [])
            if content and len(content) > 0:
                generated_text = content[0].get("text", "")
                logger.info(
                    "Bedrock response received",
                    response_length=len(generated_text),
                    response_preview=generated_text[:200] + "..." if len(generated_text) > 200 else generated_text
                )
                return generated_text
            
            raise ValidationError(
                error_code=ErrorCode.GENERATION_FAILED,
                message="Empty response from Bedrock",
                details={"response": response}
            )
            
        except Exception as e:
            logger.log_error(
                operation="invoke_bedrock",
                error=e,
                model_id=self.model_id
            )
            raise


class LinkedInAgent(PlatformAgent):
    """LinkedIn content generation agent"""
    
    MIN_WORDS = 150
    MAX_WORDS = 250
    
    def generate(
        self,
        topics: List[str],
        style_patterns: StylePatterns,
        original_content: str
    ) -> GeneratedContent:
        """Generate LinkedIn post with hook and discussion prompt"""
        
        platform_instructions = f"""PLATFORM: LinkedIn
TARGET LENGTH: {self.MIN_WORDS}-{self.MAX_WORDS} words

STRUCTURE REQUIREMENTS:
1. Hook (first 1-2 sentences): Grab attention immediately
2. Body (3-4 short paragraphs): Develop the main idea with insights
3. Discussion Prompt (final sentence): End with a question to encourage engagement

STYLE GUIDELINES:
- Professional yet conversational tone
- Use short paragraphs (2-3 sentences each)
- Include line breaks for readability
- Focus on thought leadership and insights
- Encourage professional discussion

Generate the LinkedIn post now:"""

        prompt = self._build_base_prompt(
            topics, style_patterns, original_content, platform_instructions
        )
        
        content_text = self._invoke_bedrock(prompt, max_tokens=1000)
        
        # Count words
        word_count = len(content_text.split())
        
        logger.info(
            "LinkedIn content generated",
            word_count=word_count,
            topics_count=len(topics)
        )
        
        return GeneratedContent(
            platform=Platform.LINKEDIN,
            content=content_text,
            metadata={
                "has_hook": True,
                "has_discussion_prompt": "?" in content_text[-100:]
            },
            word_count=word_count,
            character_count=len(content_text)
        )
    
    def validate(self, content: str) -> ValidationResult:
        """Validate LinkedIn post"""
        errors = []
        warnings = []
        
        if not isinstance(content, str):
            errors.append("Content must be a string")
            return ValidationResult(False, errors, warnings)
        
        word_count = len(content.split())
        
        if word_count < self.MIN_WORDS:
            errors.append(f"Content too short: {word_count} words (minimum {self.MIN_WORDS})")
        elif word_count > self.MAX_WORDS:
            errors.append(f"Content too long: {word_count} words (maximum {self.MAX_WORDS})")
        
        # Check for discussion prompt (question at the end)
        if "?" not in content[-100:]:
            warnings.append("No discussion prompt (question) found at the end")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(is_valid, errors, warnings)
    
    def get_constraints(self) -> PlatformConstraints:
        """Get LinkedIn constraints"""
        return PlatformConstraints(
            min_length=self.MIN_WORDS,
            max_length=self.MAX_WORDS,
            format_requirements=[
                "Hook in first 1-2 sentences",
                "3-5 short paragraphs",
                "Discussion prompt at end"
            ],
            style_guidelines=[
                "Professional tone",
                "Thought leadership focus",
                "Encourage engagement"
            ]
        )


class TwitterAgent(PlatformAgent):
    """Twitter thread generation agent"""
    
    MAX_TWEET_LENGTH = 280
    MIN_TWEETS = 5
    MAX_TWEETS = 7
    
    def generate(
        self,
        topics: List[str],
        style_patterns: StylePatterns,
        original_content: str
    ) -> GeneratedContent:
        """Generate Twitter thread with 5-7 tweets"""
        
        platform_instructions = f"""PLATFORM: Twitter Thread
TARGET: {self.MIN_TWEETS}-{self.MAX_TWEETS} tweets
MAX LENGTH PER TWEET: {self.MAX_TWEET_LENGTH} characters

STRUCTURE REQUIREMENTS:
1. Tweet 1 (Hook): Attention-grabbing opening that makes people want to read more
2. Tweets 2-6: Break down the main points, one key idea per tweet
3. Final Tweet: Call-to-action or summary

FORMATTING:
- Number each tweet (1/, 2/, 3/, etc.)
- Each tweet MUST be under {self.MAX_TWEET_LENGTH} characters
- Use line breaks within tweets for readability
- Keep language concise and punchy

STYLE GUIDELINES:
- Direct and engaging
- One idea per tweet
- Use thread format effectively
- Encourage retweets and replies

Generate the Twitter thread now. Format as:

1/ [First tweet text]

2/ [Second tweet text]

[Continue for {self.MIN_TWEETS}-{self.MAX_TWEETS} tweets]"""

        prompt = self._build_base_prompt(
            topics, style_patterns, original_content, platform_instructions
        )
        
        response_text = self._invoke_bedrock(prompt, max_tokens=1500)
        
        # Parse tweets from response
        tweets = self._parse_twitter_thread(response_text)
        
        # Validate tweet count
        if len(tweets) < self.MIN_TWEETS or len(tweets) > self.MAX_TWEETS:
            logger.warning(
                "Tweet count out of range, adjusting",
                actual_count=len(tweets),
                min=self.MIN_TWEETS,
                max=self.MAX_TWEETS
            )
            # Truncate or pad as needed
            if len(tweets) > self.MAX_TWEETS:
                tweets = tweets[:self.MAX_TWEETS]
        
        logger.info(
            "Twitter thread generated",
            tweet_count=len(tweets),
            topics_count=len(topics)
        )
        
        return GeneratedContent(
            platform=Platform.TWITTER,
            content=tweets,
            metadata={
                "tweet_count": len(tweets),
                "thread_format": True
            },
            character_count=sum(len(t) for t in tweets)
        )
    
    def _parse_twitter_thread(self, response_text: str) -> List[str]:
        """Parse individual tweets from thread response"""
        # Split by tweet numbers (1/, 2/, 3/, etc.)
        pattern = r'\d+/\s*'
        parts = re.split(pattern, response_text)
        
        # Filter out empty parts and clean up
        tweets = []
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                # Ensure tweet is under character limit
                if len(cleaned) > self.MAX_TWEET_LENGTH:
                    # Truncate with ellipsis
                    cleaned = cleaned[:self.MAX_TWEET_LENGTH-3] + "..."
                tweets.append(cleaned)
        
        return tweets
    
    def validate(self, content: List[str]) -> ValidationResult:
        """Validate Twitter thread"""
        errors = []
        warnings = []
        
        if not isinstance(content, list):
            errors.append("Content must be a list of tweets")
            return ValidationResult(False, errors, warnings)
        
        tweet_count = len(content)
        
        if tweet_count < self.MIN_TWEETS:
            errors.append(f"Too few tweets: {tweet_count} (minimum {self.MIN_TWEETS})")
        elif tweet_count > self.MAX_TWEETS:
            errors.append(f"Too many tweets: {tweet_count} (maximum {self.MAX_TWEETS})")
        
        # Validate each tweet length
        for i, tweet in enumerate(content):
            if len(tweet) > self.MAX_TWEET_LENGTH:
                errors.append(
                    f"Tweet {i+1} exceeds {self.MAX_TWEET_LENGTH} characters: {len(tweet)}"
                )
        
        is_valid = len(errors) == 0
        
        return ValidationResult(is_valid, errors, warnings)
    
    def get_constraints(self) -> PlatformConstraints:
        """Get Twitter constraints"""
        return PlatformConstraints(
            min_length=self.MIN_TWEETS,
            max_length=self.MAX_TWEETS,
            format_requirements=[
                f"Each tweet under {self.MAX_TWEET_LENGTH} characters",
                f"{self.MIN_TWEETS}-{self.MAX_TWEETS} tweets total",
                "Numbered thread format"
            ],
            style_guidelines=[
                "Concise and punchy",
                "One idea per tweet",
                "Engaging hook"
            ]
        )


class InstagramAgent(PlatformAgent):
    """Instagram caption generation agent"""
    
    MIN_WORDS = 100
    MAX_WORDS = 150
    
    def generate(
        self,
        topics: List[str],
        style_patterns: StylePatterns,
        original_content: str
    ) -> GeneratedContent:
        """Generate Instagram caption with emojis and story-driven content"""
        
        platform_instructions = f"""PLATFORM: Instagram
TARGET LENGTH: {self.MIN_WORDS}-{self.MAX_WORDS} words

STRUCTURE REQUIREMENTS:
1. Hook (first line): Grab attention with emotion or curiosity
2. Story/Body: Tell a story or share insights in a relatable way
3. Call-to-Action: Encourage likes, comments, or shares

STYLE GUIDELINES:
- Story-driven and personal
- Use emojis naturally throughout (at least 3-5 emojis)
- Conversational and authentic tone
- Create emotional connection
- Use line breaks for readability
- Include relevant hashtags at the end (3-5 hashtags)

Generate the Instagram caption now:"""

        prompt = self._build_base_prompt(
            topics, style_patterns, original_content, platform_instructions
        )
        
        content_text = self._invoke_bedrock(prompt, max_tokens=800)
        
        # Count words and emojis
        word_count = len(content_text.split())
        emoji_count = self._count_emojis(content_text)
        
        logger.info(
            "Instagram content generated",
            word_count=word_count,
            emoji_count=emoji_count,
            topics_count=len(topics)
        )
        
        return GeneratedContent(
            platform=Platform.INSTAGRAM,
            content=content_text,
            metadata={
                "emoji_count": emoji_count,
                "story_driven": True
            },
            word_count=word_count,
            character_count=len(content_text)
        )
    
    def _count_emojis(self, text: str) -> int:
        """Count emojis in text"""
        # Simple emoji detection (Unicode ranges for common emojis)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        return len(emoji_pattern.findall(text))
    
    def validate(self, content: str) -> ValidationResult:
        """Validate Instagram caption"""
        errors = []
        warnings = []
        
        if not isinstance(content, str):
            errors.append("Content must be a string")
            return ValidationResult(False, errors, warnings)
        
        word_count = len(content.split())
        
        if word_count < self.MIN_WORDS:
            errors.append(f"Content too short: {word_count} words (minimum {self.MIN_WORDS})")
        elif word_count > self.MAX_WORDS:
            errors.append(f"Content too long: {word_count} words (maximum {self.MAX_WORDS})")
        
        # Check for emojis
        emoji_count = self._count_emojis(content)
        if emoji_count == 0:
            warnings.append("No emojis found - Instagram content typically includes emojis")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(is_valid, errors, warnings)
    
    def get_constraints(self) -> PlatformConstraints:
        """Get Instagram constraints"""
        return PlatformConstraints(
            min_length=self.MIN_WORDS,
            max_length=self.MAX_WORDS,
            format_requirements=[
                "Story-driven narrative",
                "Emojis throughout",
                "Call-to-action"
            ],
            style_guidelines=[
                "Personal and authentic",
                "Emotional connection",
                "Visual and engaging"
            ]
        )


class YouTubeShortsAgent(PlatformAgent):
    """YouTube Shorts script generation agent"""
    
    MIN_DURATION = 30
    MAX_DURATION = 60
    
    def generate(
        self,
        topics: List[str],
        style_patterns: StylePatterns,
        original_content: str
    ) -> GeneratedContent:
        """Generate YouTube Shorts script with timestamps and visual cues"""
        
        platform_instructions = f"""PLATFORM: YouTube Shorts
TARGET DURATION: {self.MIN_DURATION}-{self.MAX_DURATION} seconds

STRUCTURE REQUIREMENTS:
1. Hook (0-3s): Immediate attention grabber
2. Content (3-55s): Main points with visual directions
3. CTA (55-60s): Call-to-action (like, subscribe, comment)

FORMATTING:
Use this exact format for each section:

[00:00-00:03] HOOK
Voiceover: [What you say]
Visual: [What viewers see]
B-roll: [Suggested footage]

[00:03-00:10] POINT 1
Voiceover: [What you say]
Visual: [What viewers see]
B-roll: [Suggested footage]

[Continue with more sections...]

STYLE GUIDELINES:
- Fast-paced and dynamic
- Clear visual directions for each timestamp
- Specific B-roll suggestions
- Keep voiceover concise
- Maintain energy throughout

Generate the YouTube Shorts script now:"""

        prompt = self._build_base_prompt(
            topics, style_patterns, original_content, platform_instructions
        )
        
        content_text = self._invoke_bedrock(prompt, max_tokens=1200)
        
        # Parse timestamps to verify duration
        timestamps = self._extract_timestamps(content_text)
        duration = timestamps[-1] if timestamps else 0
        
        logger.info(
            "YouTube Shorts script generated",
            duration=duration,
            timestamp_count=len(timestamps),
            topics_count=len(topics)
        )
        
        return GeneratedContent(
            platform=Platform.YOUTUBE_SHORTS,
            content=content_text,
            metadata={
                "duration_seconds": duration,
                "has_timestamps": len(timestamps) > 0,
                "has_visual_cues": "Visual:" in content_text,
                "has_broll": "B-roll:" in content_text
            },
            character_count=len(content_text)
        )
    
    def _extract_timestamps(self, script: str) -> List[int]:
        """Extract timestamps from script"""
        # Match patterns like [00:30-00:45] or [00:30]
        pattern = r'\[(\d{2}):(\d{2})'
        matches = re.findall(pattern, script)
        
        timestamps = []
        for minutes, seconds in matches:
            total_seconds = int(minutes) * 60 + int(seconds)
            timestamps.append(total_seconds)
        
        return sorted(set(timestamps))
    
    def validate(self, content: str) -> ValidationResult:
        """Validate YouTube Shorts script"""
        errors = []
        warnings = []
        
        if not isinstance(content, str):
            errors.append("Content must be a string")
            return ValidationResult(False, errors, warnings)
        
        # Check for timestamps
        timestamps = self._extract_timestamps(content)
        if not timestamps:
            errors.append("No timestamps found in script")
        else:
            duration = timestamps[-1]
            if duration < self.MIN_DURATION:
                errors.append(
                    f"Script too short: {duration}s (minimum {self.MIN_DURATION}s)"
                )
            elif duration > self.MAX_DURATION:
                errors.append(
                    f"Script too long: {duration}s (maximum {self.MAX_DURATION}s)"
                )
        
        # Check for required elements
        if "Visual:" not in content:
            warnings.append("No visual cues found")
        if "B-roll:" not in content:
            warnings.append("No B-roll suggestions found")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(is_valid, errors, warnings)
    
    def get_constraints(self) -> PlatformConstraints:
        """Get YouTube Shorts constraints"""
        return PlatformConstraints(
            min_length=self.MIN_DURATION,
            max_length=self.MAX_DURATION,
            format_requirements=[
                "Timestamped script format",
                "Visual cues for each section",
                "B-roll suggestions"
            ],
            style_guidelines=[
                "Fast-paced",
                "Dynamic visuals",
                "Clear voiceover"
            ]
        )


class PlatformAgentFactory:
    """Factory for creating platform-specific agents"""
    
    _agents = {
        Platform.LINKEDIN: LinkedInAgent,
        Platform.TWITTER: TwitterAgent,
        Platform.INSTAGRAM: InstagramAgent,
        Platform.YOUTUBE_SHORTS: YouTubeShortsAgent
    }
    
    @classmethod
    def create_agent(cls, platform: Platform) -> PlatformAgent:
        """
        Create platform-specific agent
        
        Args:
            platform: Target platform
            
        Returns:
            PlatformAgent instance for the platform
            
        Raises:
            ValidationError: If platform not supported
        """
        agent_class = cls._agents.get(platform)
        
        if not agent_class:
            raise ValidationError(
                error_code=ErrorCode.UNSUPPORTED_PLATFORM,
                message=f"Platform {platform.value} not supported",
                details={"platform": platform.value}
            )
        
        return agent_class()
    
    @classmethod
    def get_supported_platforms(cls) -> List[Platform]:
        """Get list of supported platforms"""
        return list(cls._agents.keys())
