"""
Enums for Content Repurposing Platform
"""
from enum import Enum


class Platform(Enum):
    """Social media platforms"""
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    YOUTUBE_SHORTS = "youtube_shorts"


class ProcessingStatus(Enum):
    """Content processing status"""
    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    READY = "ready"
    FAILED = "failed"


class StyleProfileStatus(Enum):
    """Style profile status"""
    INCOMPLETE = "incomplete"
    READY = "ready"


class ContentStatus(Enum):
    """Generated content status"""
    DRAFT = "draft"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


class ScheduleStatus(Enum):
    """Scheduled post status"""
    PENDING = "pending"
    NOTIFIED = "notified"
    CANCELLED = "cancelled"


class EmbeddingStatus(Enum):
    """Embedding generation status"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
