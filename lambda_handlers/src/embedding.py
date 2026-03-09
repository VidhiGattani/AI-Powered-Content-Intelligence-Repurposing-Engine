"""
Embedding models
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EmbeddingResult:
    """Result of embedding generation"""
    embedding_id: str
    content_id: str
    user_id: str
    vector_dimensions: int
    embedding_vector: List[float]
    model_id: str
    
    def to_dict(self):
        """Convert to dictionary for storage"""
        return {
            "embedding_id": self.embedding_id,
            "content_id": self.content_id,
            "user_id": self.user_id,
            "vector_dimensions": self.vector_dimensions,
            "model_id": self.model_id
            # Note: embedding_vector is stored separately in Knowledge Base
        }
