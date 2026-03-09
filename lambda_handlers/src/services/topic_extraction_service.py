"""
Topic extraction service using Claude Sonnet for identifying key topics from content
"""
import json
from typing import List, Optional
from dataclasses import dataclass
from ..utils.aws_clients import BedrockClient
from ..utils.logger import get_logger
from ..utils.errors import ProcessingError, ErrorCode

logger = get_logger(__name__)


@dataclass
class Topic:
    """Represents an extracted topic"""
    name: str
    description: str
    relevance_score: float


@dataclass
class TopicExtractionResult:
    """Result of topic extraction"""
    topics: List[Topic]
    content_id: str


class TopicExtractionService:
    """Service for extracting topics from transcribed content using Claude Sonnet"""
    
    # Claude Sonnet 3.5 model ID
    CLAUDE_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    # Minimum content length in words
    MIN_CONTENT_LENGTH = 500
    
    # Topic count constraints
    MIN_TOPICS = 5
    MAX_TOPICS = 15
    
    def __init__(self, bedrock_client: Optional[BedrockClient] = None):
        self.bedrock_client = bedrock_client or BedrockClient()
    
    def extract_topics(
        self,
        content_id: str,
        transcript: str
    ) -> TopicExtractionResult:
        """
        Extract 5-15 main topics from content using Claude
        
        Args:
            content_id: Unique identifier for the content
            transcript: Transcribed text content
        
        Returns:
            TopicExtractionResult with topics and confidence scores
        
        Raises:
            ProcessingError: If content too short or extraction fails
        """
        try:
            # Validate content length
            word_count = len(transcript.split())
            if word_count < self.MIN_CONTENT_LENGTH:
                raise ProcessingError(
                    error_code=ErrorCode.INSUFFICIENT_CONTENT,
                    message=f"Content too short for topic extraction. Minimum {self.MIN_CONTENT_LENGTH} words required, got {word_count}",
                    details={"content_id": content_id, "word_count": word_count}
                )
            
            logger.info(
                "Starting topic extraction",
                content_id=content_id,
                word_count=word_count
            )
            
            # Build prompt for Claude
            prompt = self._build_topic_extraction_prompt(transcript)
            
            # Call Bedrock with Claude Sonnet
            response = self._invoke_claude(prompt)
            
            # Parse topics from response
            topics = self._parse_topics_response(response)
            
            # Validate topic count
            if len(topics) < self.MIN_TOPICS or len(topics) > self.MAX_TOPICS:
                logger.warning(
                    "Topic count outside expected range",
                    content_id=content_id,
                    topic_count=len(topics),
                    expected_range=f"{self.MIN_TOPICS}-{self.MAX_TOPICS}"
                )
            
            logger.info(
                "Topic extraction completed",
                content_id=content_id,
                topic_count=len(topics)
            )
            
            return TopicExtractionResult(
                topics=topics,
                content_id=content_id
            )
            
        except ProcessingError:
            raise
        except Exception as e:
            logger.log_error(
                operation="extract_topics",
                error=e,
                content_id=content_id
            )
            raise ProcessingError(
                error_code=ErrorCode.TOPIC_EXTRACTION_FAILED,
                message=f"Failed to extract topics: {str(e)}",
                details={"content_id": content_id}
            )
    
    def _build_topic_extraction_prompt(self, transcript: str) -> str:
        """
        Build prompt template for topic extraction
        
        Args:
            transcript: Content text
        
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert content analyst. Your task is to analyze the following content and extract the main topics discussed.

Instructions:
- Extract between {self.MIN_TOPICS} and {self.MAX_TOPICS} main topics from the content
- For each topic, provide:
  * A concise name (2-5 words)
  * A brief description (1-2 sentences)
  * A relevance score (0.0 to 1.0) indicating how central this topic is to the content
- Focus on the most important and substantive topics
- Avoid overly generic topics
- Return your response as a JSON array

Content to analyze:
{transcript}

Return your response in the following JSON format:
{{
  "topics": [
    {{
      "name": "Topic Name",
      "description": "Brief description of the topic",
      "relevance_score": 0.95
    }}
  ]
}}

Respond only with the JSON, no additional text."""
        
        return prompt
    
    def _invoke_claude(self, prompt: str) -> dict:
        """
        Invoke Claude Sonnet model via Bedrock
        
        Args:
            prompt: Formatted prompt
        
        Returns:
            Response from Claude
        
        Raises:
            ProcessingError: If Bedrock call fails
        """
        try:
            # Build request body for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.3,  # Lower temperature for more consistent extraction
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
            
            # Invoke model
            response = self.bedrock_client.invoke_model(
                model_id=self.CLAUDE_MODEL_ID,
                body=request_body
            )
            
            return response
            
        except Exception as e:
            logger.log_error(
                operation="_invoke_claude",
                error=e,
                model_id=self.CLAUDE_MODEL_ID
            )
            raise ProcessingError(
                error_code=ErrorCode.BEDROCK_UNAVAILABLE,
                message=f"Failed to invoke Claude model: {str(e)}",
                details={"model_id": self.CLAUDE_MODEL_ID}
            )
    
    def _parse_topics_response(self, response: dict) -> List[Topic]:
        """
        Parse JSON response from Claude to extract topics
        
        Args:
            response: Response from Bedrock
        
        Returns:
            List of Topic objects
        
        Raises:
            ProcessingError: If response parsing fails
        """
        try:
            # Extract content from Claude response
            content = response.get('content', [])
            if not content:
                raise ValueError("No content in response")
            
            # Get text from first content block
            text_content = content[0].get('text', '')
            if not text_content:
                raise ValueError("No text in content block")
            
            logger.debug(
                "Parsing Claude response",
                response_length=len(text_content)
            )
            
            # Parse JSON from response
            # Claude might wrap JSON in markdown code blocks, so clean it
            cleaned_text = text_content.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # Parse JSON
            data = json.loads(cleaned_text)
            
            # Extract topics array
            topics_data = data.get('topics', [])
            if not topics_data:
                raise ValueError("No topics in response")
            
            # Convert to Topic objects
            topics = []
            for topic_data in topics_data:
                topic = Topic(
                    name=topic_data.get('name', ''),
                    description=topic_data.get('description', ''),
                    relevance_score=float(topic_data.get('relevance_score', 0.0))
                )
                topics.append(topic)
            
            logger.debug(
                "Successfully parsed topics",
                topic_count=len(topics)
            )
            
            return topics
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.log_error(
                operation="_parse_topics_response",
                error=e,
                response=response
            )
            raise ProcessingError(
                error_code=ErrorCode.TOPIC_EXTRACTION_FAILED,
                message=f"Failed to parse topics from response: {str(e)}",
                details={"error_type": type(e).__name__}
            )
