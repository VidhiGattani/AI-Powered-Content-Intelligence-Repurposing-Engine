"""
Style content data models
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .enums import EmbeddingStatus, StyleProfileStatus


@dataclass
class StyleContentMetadata:
    """Style content metadata model"""
    content_id: str
    user_id: str
    filename: str
    s3_uri: str
    content_type: str
    uploaded_at: datetime
    embedding_id: Optional[str] = None
    embedding_status: EmbeddingStatus = EmbeddingStatus.PENDING
    
    def to_dict(self):
        """Convert to dictionary for DynamoDB"""
        return {
            "content_id": self.content_id,
            "user_id": self.user_id,
            "filename": self.filename,
            "s3_uri": self.s3_uri,
            "content_type": self.content_type,
            "uploaded_at": self.uploaded_at.isoformat(),
            "embedding_id": self.embedding_id,
            "embedding_status": self.embedding_status.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "StyleContentMetadata":
        """Create StyleContentMetadata from dictionary"""
        return cls(
            content_id=data["content_id"],
            user_id=data["user_id"],
            filename=data["filename"],
            s3_uri=data["s3_uri"],
            content_type=data["content_type"],
            uploaded_at=datetime.fromisoformat(data["uploaded_at"]),
            embedding_id=data.get("embedding_id"),
            embedding_status=EmbeddingStatus(data.get("embedding_status", "pending"))
        )


@dataclass
class StyleProfile:
    """Style profile model"""
    user_id: str
    status: StyleProfileStatus
    content_count: int
    last_updated: datetime
    knowledge_base_id: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary for DynamoDB"""
        return {
            "user_id": self.user_id,
            "status": self.status.value,
            "content_count": self.content_count,
            "last_updated": self.last_updated.isoformat(),
            "knowledge_base_id": self.knowledge_base_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "StyleProfile":
        """Create StyleProfile from dictionary"""
        return cls(
            user_id=data["user_id"],
            status=StyleProfileStatus(data["status"]),
            content_count=data["content_count"],
            last_updated=datetime.fromisoformat(data["last_updated"]),
            knowledge_base_id=data.get("knowledge_base_id")
        )
