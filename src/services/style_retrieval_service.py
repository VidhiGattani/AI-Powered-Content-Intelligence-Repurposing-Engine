"""
Style Retrieval Service

Retrieves relevant style patterns using RAG and extracts writing characteristics.
"""
import os
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from src.utils.aws_clients import BedrockClient, BedrockAgentRuntimeClient
from src.utils.errors import NotFoundError, ErrorCode, ProcessingError
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WritingCharacteristics:
    """Extracted writing style characteristics"""
    sentence_structure: Dict[str, Any]  # avg_length, length_variance, complexity
    vocabulary: Dict[str, Any]  # unique_words, avg_word_length, formality_level
    tone: str  # professional, casual, enthusiastic, etc.
    emoji_usage: Dict[str, Any]  # frequency, types, placement
    common_phrases: List[str]
    punctuation_style: Dict[str, Any]  # exclamation_marks, questions, ellipsis


@dataclass
class StylePatterns:
    """Style patterns retrieved from Knowledge Base"""
    examples: List[str]  # Top 3 similar style content pieces
    characteristics: WritingCharacteristics
    user_id: str


class StyleRetrievalService:
    """Retrieves relevant style patterns using RAG"""
    
    def __init__(
        self,
        bedrock_client: Optional[BedrockClient] = None,
        bedrock_agent_client: Optional[BedrockAgentRuntimeClient] = None
    ):
        """
        Initialize StyleRetrievalService
        
        Args:
            bedrock_client: Bedrock client for embedding generation
            bedrock_agent_client: Bedrock Agent Runtime client for KB queries
        """
        self.bedrock_client = bedrock_client or BedrockClient()
        self.bedrock_agent_client = bedrock_agent_client or BedrockAgentRuntimeClient()
        self.knowledge_base_id = os.environ.get("KNOWLEDGE_BASE_ID")
    
    def retrieve_style_patterns(
        self,
        user_id: str,
        content_text: str
    ) -> StylePatterns:
        """
        Retrieve top 3 most similar style content pieces using RAG
        
        Args:
            user_id: User identifier
            content_text: Original content text to match style against
        
        Returns:
            StylePatterns with examples and characteristics
        
        Raises:
            NotFoundError: If user has no style content
            ProcessingError: If retrieval fails
        """
        # If no knowledge base is configured, return default style patterns
        if not self.knowledge_base_id:
            logger.info(
                "No knowledge base configured, using default style patterns",
                user_id=user_id
            )
            return self._get_default_style_patterns(user_id)
        
        try:
            # Generate embedding for the original content
            content_embedding = self._generate_embedding(content_text)
            
            # Query Knowledge Base filtered by userId
            # Note: The actual filtering by user_id would be done through
            # Knowledge Base metadata filters in the retrieval configuration
            results = self.bedrock_agent_client.retrieve(
                query_text=content_text[:1000],  # Limit query text length
                retrieval_query_embedding=content_embedding,
                number_of_results=3
            )
            
            if not results:
                raise NotFoundError(
                    error_code=ErrorCode.NO_STYLE_PROFILE,
                    message=f"No style content found for user: {user_id}",
                    details={"user_id": user_id}
                )
            
            # Extract text content from results
            style_examples = []
            for result in results:
                # Extract content from retrieval result
                content = result.get('content', {}).get('text', '')
                if content:
                    style_examples.append(content)
            
            if not style_examples:
                raise NotFoundError(
                    error_code=ErrorCode.NO_STYLE_PROFILE,
                    message=f"No valid style content found for user: {user_id}",
                    details={"user_id": user_id}
                )
            
            # Extract writing characteristics from the retrieved examples
            characteristics = self.extract_writing_characteristics(style_examples)
            
            # Create style patterns object
            style_patterns = StylePatterns(
                examples=style_examples,
                characteristics=characteristics,
                user_id=user_id
            )
            
            logger.info(
                "Style patterns retrieved successfully",
                user_id=user_id,
                examples_count=len(style_examples)
            )
            
            return style_patterns
            
        except NotFoundError:
            # Re-raise known errors
            raise
            
        except Exception as e:
            logger.log_error(
                operation="retrieve_style_patterns",
                error=e,
                user_id=user_id
            )
            
            raise ProcessingError(
                error_code=ErrorCode.STYLE_RETRIEVAL_FAILED,
                message=f"Failed to retrieve style patterns: {str(e)}",
                details={"user_id": user_id}
            )
    
    def extract_writing_characteristics(
        self,
        style_content: List[str]
    ) -> WritingCharacteristics:
        """
        Extract writing style characteristics from retrieved content
        
        Analyzes:
        - Sentence length and structure
        - Vocabulary complexity and formality
        - Tone (professional, casual, enthusiastic, etc.)
        - Emoji usage patterns
        - Common phrases and expressions
        - Punctuation style
        
        Args:
            style_content: List of style content examples
        
        Returns:
            WritingCharacteristics with extracted patterns
        """
        # Combine all content for analysis
        combined_text = " ".join(style_content)
        
        # Extract sentence structure characteristics
        sentence_structure = self._analyze_sentence_structure(combined_text)
        
        # Extract vocabulary characteristics
        vocabulary = self._analyze_vocabulary(combined_text)
        
        # Determine tone
        tone = self._determine_tone(combined_text, vocabulary)
        
        # Analyze emoji usage
        emoji_usage = self._analyze_emoji_usage(combined_text)
        
        # Extract common phrases
        common_phrases = self._extract_common_phrases(style_content)
        
        # Analyze punctuation style
        punctuation_style = self._analyze_punctuation(combined_text)
        
        characteristics = WritingCharacteristics(
            sentence_structure=sentence_structure,
            vocabulary=vocabulary,
            tone=tone,
            emoji_usage=emoji_usage,
            common_phrases=common_phrases,
            punctuation_style=punctuation_style
        )
        
        logger.info(
            "Writing characteristics extracted",
            tone=tone,
            avg_sentence_length=sentence_structure.get('avg_length', 0),
            emoji_frequency=emoji_usage.get('frequency', 0)
        )
        
        return characteristics
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Titan Embeddings"""
        try:
            model_id = "amazon.titan-embed-text-v1"
            
            # Truncate text if too long (Titan has token limits)
            max_chars = 8000
            if len(text) > max_chars:
                text = text[:max_chars]
            
            response = self.bedrock_client.invoke_model(
                model_id=model_id,
                body={"inputText": text}
            )
            
            embedding_vector = response.get('embedding', [])
            
            if not embedding_vector:
                raise ProcessingError(
                    error_code=ErrorCode.EMBEDDING_GENERATION_FAILED,
                    message="Embedding generation returned empty vector",
                    details={"text_length": len(text)}
                )
            
            return embedding_vector
            
        except Exception as e:
            logger.log_error(
                operation="generate_embedding",
                error=e,
                text_length=len(text)
            )
            raise
    
    def _analyze_sentence_structure(self, text: str) -> Dict[str, Any]:
        """Analyze sentence length and structure patterns"""
        # Split into sentences (simple approach)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return {
                'avg_length': 0,
                'length_variance': 0,
                'complexity': 'simple'
            }
        
        # Calculate sentence lengths
        sentence_lengths = [len(s.split()) for s in sentences]
        avg_length = sum(sentence_lengths) / len(sentence_lengths)
        
        # Calculate variance
        variance = sum((l - avg_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)
        
        # Determine complexity based on average length
        if avg_length < 10:
            complexity = 'simple'
        elif avg_length < 20:
            complexity = 'moderate'
        else:
            complexity = 'complex'
        
        return {
            'avg_length': round(avg_length, 2),
            'length_variance': round(variance, 2),
            'complexity': complexity,
            'total_sentences': len(sentences)
        }
    
    def _analyze_vocabulary(self, text: str) -> Dict[str, Any]:
        """Analyze vocabulary patterns and complexity"""
        # Tokenize words (simple approach)
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        if not words:
            return {
                'unique_words': 0,
                'avg_word_length': 0,
                'formality_level': 'neutral',
                'total_words': 0
            }
        
        # Calculate unique words
        unique_words = len(set(words))
        
        # Calculate average word length
        avg_word_length = sum(len(w) for w in words) / len(words)
        
        # Determine formality based on word length and complexity
        if avg_word_length < 4:
            formality_level = 'casual'
        elif avg_word_length < 5.5:
            formality_level = 'neutral'
        else:
            formality_level = 'formal'
        
        return {
            'unique_words': unique_words,
            'avg_word_length': round(avg_word_length, 2),
            'formality_level': formality_level,
            'total_words': len(words),
            'vocabulary_richness': round(unique_words / len(words), 2) if words else 0
        }
    
    def _determine_tone(self, text: str, vocabulary: Dict[str, Any]) -> str:
        """Determine overall tone of the writing"""
        text_lower = text.lower()
        
        # Count tone indicators
        enthusiastic_indicators = len(re.findall(r'!+', text))
        question_indicators = len(re.findall(r'\?+', text))
        
        # Check for casual markers
        casual_markers = ['gonna', 'wanna', 'yeah', 'hey', 'cool', 'awesome']
        casual_count = sum(1 for marker in casual_markers if marker in text_lower)
        
        # Check for professional markers
        professional_markers = ['therefore', 'however', 'furthermore', 'consequently', 'moreover']
        professional_count = sum(1 for marker in professional_markers if marker in text_lower)
        
        # Determine tone based on indicators
        if enthusiastic_indicators > 5:
            return 'enthusiastic'
        elif professional_count > casual_count and vocabulary.get('formality_level') == 'formal':
            return 'professional'
        elif casual_count > professional_count or vocabulary.get('formality_level') == 'casual':
            return 'casual'
        elif question_indicators > 3:
            return 'inquisitive'
        else:
            return 'neutral'
    
    def _analyze_emoji_usage(self, text: str) -> Dict[str, Any]:
        """Analyze emoji usage patterns"""
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
        
        emojis = emoji_pattern.findall(text)
        
        # Count words for frequency calculation
        words = len(re.findall(r'\b\w+\b', text))
        
        # Determine placement (beginning, middle, end)
        placement = 'none'
        if emojis:
            # Simple heuristic: check if emojis appear in first/last 20% of text
            text_length = len(text)
            first_emoji_pos = text.find(emojis[0])
            
            if first_emoji_pos < text_length * 0.2:
                placement = 'beginning'
            elif first_emoji_pos > text_length * 0.8:
                placement = 'end'
            else:
                placement = 'throughout'
        
        return {
            'frequency': len(emojis) / max(words, 1) if words > 0 else 0,
            'total_count': len(emojis),
            'types': list(set(emojis)),
            'placement': placement
        }
    
    def _extract_common_phrases(self, style_content: List[str]) -> List[str]:
        """Extract common phrases that appear across multiple examples"""
        # Simple approach: find 2-3 word phrases that appear multiple times
        phrase_counts = {}
        
        for content in style_content:
            # Extract 2-3 word phrases
            words = re.findall(r'\b[a-zA-Z]+\b', content.lower())
            
            # 2-word phrases
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
            
            # 3-word phrases
            for i in range(len(words) - 2):
                phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        
        # Filter phrases that appear at least twice
        common_phrases = [
            phrase for phrase, count in phrase_counts.items()
            if count >= 2
        ]
        
        # Sort by frequency and return top 10
        common_phrases.sort(key=lambda p: phrase_counts[p], reverse=True)
        return common_phrases[:10]
    
    def _analyze_punctuation(self, text: str) -> Dict[str, Any]:
        """Analyze punctuation style and patterns"""
        # Count different punctuation types
        exclamation_marks = len(re.findall(r'!+', text))
        questions = len(re.findall(r'\?+', text))
        ellipsis = len(re.findall(r'\.{2,}', text))
        dashes = len(re.findall(r'[-—–]+', text))
        
        # Count sentences for frequency calculation
        sentences = len(re.split(r'[.!?]+', text))
        
        return {
            'exclamation_marks': exclamation_marks,
            'exclamation_frequency': exclamation_marks / max(sentences, 1),
            'questions': questions,
            'question_frequency': questions / max(sentences, 1),
            'ellipsis': ellipsis,
            'ellipsis_frequency': ellipsis / max(sentences, 1),
            'dashes': dashes,
            'dash_frequency': dashes / max(sentences, 1)
        }
    
    def _get_default_style_patterns(self, user_id: str) -> StylePatterns:
        """
        Return default style patterns when no knowledge base is configured
        
        Args:
            user_id: User identifier
        
        Returns:
            StylePatterns with generic defaults
        """
        # Create generic style examples
        default_examples = [
            "This is a professional and engaging piece of content that demonstrates clear communication.",
            "Here's an example of conversational writing that connects with the audience.",
            "Content that balances information with readability and maintains a consistent tone."
        ]
        
        # Create default characteristics
        default_characteristics = WritingCharacteristics(
            sentence_structure={
                'avg_length': 15.0,
                'length_variance': 25.0,
                'complexity': 'moderate',
                'total_sentences': 10
            },
            vocabulary={
                'unique_words': 100,
                'avg_word_length': 5.0,
                'formality_level': 'neutral',
                'total_words': 150,
                'vocabulary_richness': 0.67
            },
            tone='professional',
            emoji_usage={
                'frequency': 0.0,
                'total_count': 0,
                'types': [],
                'placement': 'none'
            },
            common_phrases=[],
            punctuation_style={
                'exclamation_marks': 0,
                'exclamation_frequency': 0.0,
                'questions': 1,
                'question_frequency': 0.1,
                'ellipsis': 0,
                'ellipsis_frequency': 0.0,
                'dashes': 2,
                'dash_frequency': 0.2
            }
        )
        
        logger.info(
            "Default style patterns created",
            user_id=user_id
        )
        
        return StylePatterns(
            examples=default_examples,
            characteristics=default_characteristics,
            user_id=user_id
        )
