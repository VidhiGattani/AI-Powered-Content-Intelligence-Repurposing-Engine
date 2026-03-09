"""
Content models for Content Repurposing Platform
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from .enums import ProcessingStatus as ProcessingStatusEnum


@dataclass
class ContentMetadata:
    """Metadata for original content"""
    content_id: str
    user_id: str
    filename: str
    s3_uri: str
    content_type: str
    uploaded_at: datetime
    processing_status: ProcessingStatusEnum
    transcription_job_id: Optional[str] = None
    transcript_s3_uri: Optional[str] = None
    topics: Optional[List[str]] = None
    duration_seconds: Optional[int] = None
    content_text: Optional[str] = None  # Extracted text from PDF/text files
    transcript: Optional[str] = None  # Transcribed text from video/audio
    
    def to_dynamodb_item(self) -> dict:
        """Convert to DynamoDB item format"""
        item = {
            'content_id': self.content_id,
            'user_id': self.user_id,
            'filename': self.filename,
            's3_uri': self.s3_uri,
            'content_type': self.content_type,
            'uploaded_at': self.uploaded_at.isoformat(),
            'processing_status': self.processing_status.value
        }
        
        if self.transcription_job_id:
            item['transcription_job_id'] = self.transcription_job_id
        if self.transcript_s3_uri:
            item['transcript_s3_uri'] = self.transcript_s3_uri
        if self.topics:
            item['topics'] = self.topics
        if self.duration_seconds:
            item['duration_seconds'] = self.duration_seconds
        if self.content_text:
            item['content_text'] = self.content_text
        if self.transcript:
            item['transcript'] = self.transcript
        
        return item
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'content_id': self.content_id,
            'user_id': self.user_id,
            'filename': self.filename,
            's3_uri': self.s3_uri,
            'content_type': self.content_type,
            'uploaded_at': self.uploaded_at.isoformat(),
            'processing_status': self.processing_status.value,
            'transcription_job_id': self.transcription_job_id,
            'transcript_s3_uri': self.transcript_s3_uri,
            'topics': self.topics,
            'duration_seconds': self.duration_seconds,
            'content_text': self.content_text,
            'transcript': self.transcript
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: dict) -> 'ContentMetadata':
        """Create from DynamoDB item"""
        return cls(
            content_id=item['content_id'],
            user_id=item['user_id'],
            filename=item['filename'],
            s3_uri=item['s3_uri'],
            content_type=item['content_type'],
            uploaded_at=datetime.fromisoformat(item['uploaded_at']),
            processing_status=ProcessingStatusEnum(item['processing_status']),
            transcription_job_id=item.get('transcription_job_id'),
            transcript_s3_uri=item.get('transcript_s3_uri'),
            topics=item.get('topics'),
            duration_seconds=item.get('duration_seconds'),
            content_text=item.get('content_text'),
            transcript=item.get('transcript')
        )


@dataclass
class UploadStatus:
    """Processing status information for uploads"""
    content_id: str
    stage: str
    progress_percentage: int
    message: Optional[str] = None
