"""
Transcription service for converting audio/video to text using Amazon Transcribe
"""
import os
import time
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from ..utils.aws_clients import TranscribeClient, S3Client
from ..utils.logger import get_logger
from ..utils.errors import TranscriptionError, ErrorCode

logger = get_logger(__name__)


@dataclass
class TranscriptionJob:
    """Transcription job information"""
    job_id: str
    status: str
    content_id: str


@dataclass
class Transcription:
    """Completed transcription result"""
    text: str
    timestamps: Optional[list] = None


@dataclass
class TranscriptionProgress:
    """Transcription progress information"""
    job_id: str
    percentage: int
    estimated_time_remaining: Optional[int] = None


class TranscriptionService:
    """Service for managing transcription operations"""
    
    def __init__(
        self,
        transcribe_client: Optional[TranscribeClient] = None,
        s3_client: Optional[S3Client] = None
    ):
        self.transcribe_client = transcribe_client or TranscribeClient()
        self.s3_client = s3_client or S3Client()
        self.output_bucket = os.environ.get("S3_BUCKET_TRANSCRIPTS", "transcripts")
    
    def start_transcription(
        self,
        content_id: str,
        s3_uri: str,
        media_format: str
    ) -> TranscriptionJob:
        """
        Start transcription job for audio/video content
        
        Args:
            content_id: Unique identifier for the content
            s3_uri: S3 URI of the media file
            media_format: Media format (mp4, mp3, wav, etc.)
        
        Returns:
            TranscriptionJob with job_id and status
        
        Raises:
            TranscriptionError: If job creation fails
        """
        try:
            # Generate unique job name
            job_name = f"transcription-{content_id}-{int(time.time())}"
            
            # Normalize media format
            normalized_format = self._normalize_media_format(media_format)
            
            logger.info(
                "Starting transcription job",
                content_id=content_id,
                job_name=job_name,
                media_format=normalized_format
            )
            
            # Start transcription job
            job_id = self.transcribe_client.start_transcription_job(
                job_name=job_name,
                media_uri=s3_uri,
                media_format=normalized_format,
                output_bucket=self.output_bucket
            )
            
            return TranscriptionJob(
                job_id=job_id,
                status="IN_PROGRESS",
                content_id=content_id
            )
            
        except Exception as e:
            logger.log_error(
                operation="start_transcription",
                error=e,
                content_id=content_id
            )
            raise TranscriptionError(
                error_code=ErrorCode.TRANSCRIPTION_FAILED,
                message=f"Failed to start transcription: {str(e)}",
                details={"content_id": content_id, "s3_uri": s3_uri}
            )
    
    def get_transcription_result(self, job_id: str) -> Transcription:
        """
        Retrieve completed transcription
        
        Args:
            job_id: Transcription job identifier
        
        Returns:
            Transcription with text and timestamps
        
        Raises:
            TranscriptionError: If job doesn't exist or retrieval fails
        """
        try:
            logger.info("Retrieving transcription result", job_id=job_id)
            
            # Get job status
            job = self.transcribe_client.get_transcription_job(job_id)
            
            status = job['TranscriptionJobStatus']
            
            if status == 'FAILED':
                failure_reason = job.get('FailureReason', 'Unknown error')
                raise TranscriptionError(
                    error_code=ErrorCode.TRANSCRIPTION_FAILED,
                    message=f"Transcription job failed: {failure_reason}",
                    details={"job_id": job_id}
                )
            
            if status != 'COMPLETED':
                raise TranscriptionError(
                    error_code=ErrorCode.TRANSCRIPTION_IN_PROGRESS,
                    message=f"Transcription job not completed yet. Status: {status}",
                    details={"job_id": job_id, "status": status}
                )
            
            # Get transcript URI
            transcript_uri = job['Transcript']['TranscriptFileUri']
            
            # Download and parse transcript
            transcript_data = self._download_transcript(transcript_uri)
            
            # Extract text and timestamps
            text = transcript_data['results']['transcripts'][0]['transcript']
            
            # Extract timestamps from items
            timestamps = []
            for item in transcript_data['results'].get('items', []):
                if item['type'] == 'pronunciation':
                    timestamps.append({
                        'word': item['alternatives'][0]['content'],
                        'start_time': float(item['start_time']),
                        'end_time': float(item['end_time'])
                    })
            
            logger.info(
                "Transcription retrieved successfully",
                job_id=job_id,
                text_length=len(text),
                timestamp_count=len(timestamps)
            )
            
            return Transcription(
                text=text,
                timestamps=timestamps if timestamps else None
            )
            
        except TranscriptionError:
            raise
        except Exception as e:
            logger.log_error(
                operation="get_transcription_result",
                error=e,
                job_id=job_id
            )
            raise TranscriptionError(
                error_code=ErrorCode.TRANSCRIPTION_FAILED,
                message=f"Failed to retrieve transcription: {str(e)}",
                details={"job_id": job_id}
            )
    
    def get_progress(self, job_id: str) -> TranscriptionProgress:
        """
        Get transcription progress
        
        Args:
            job_id: Transcription job identifier
        
        Returns:
            TranscriptionProgress with percentage and estimated time
        """
        try:
            logger.info("Getting transcription progress", job_id=job_id)
            
            # Get job status
            job = self.transcribe_client.get_transcription_job(job_id)
            
            status = job['TranscriptionJobStatus']
            
            # Map status to progress percentage
            progress_map = {
                'QUEUED': 10,
                'IN_PROGRESS': 50,
                'COMPLETED': 100,
                'FAILED': 0
            }
            
            percentage = progress_map.get(status, 0)
            
            # Estimate time remaining based on status
            estimated_time = None
            if status == 'QUEUED':
                estimated_time = 120  # 2 minutes
            elif status == 'IN_PROGRESS':
                estimated_time = 60  # 1 minute
            
            return TranscriptionProgress(
                job_id=job_id,
                percentage=percentage,
                estimated_time_remaining=estimated_time
            )
            
        except Exception as e:
            logger.log_error(
                operation="get_progress",
                error=e,
                job_id=job_id
            )
            # Return default progress on error
            return TranscriptionProgress(
                job_id=job_id,
                percentage=0,
                estimated_time_remaining=None
            )
    
    def poll_until_complete(
        self,
        job_id: str,
        max_wait_seconds: int = 300,
        poll_interval: int = 10
    ) -> Transcription:
        """
        Poll transcription job until completion
        
        Args:
            job_id: Transcription job identifier
            max_wait_seconds: Maximum time to wait (default 5 minutes)
            poll_interval: Seconds between polls (default 10 seconds)
        
        Returns:
            Transcription when job completes
        
        Raises:
            TranscriptionError: If job fails or times out
        """
        start_time = time.time()
        
        logger.info(
            "Starting to poll transcription job",
            job_id=job_id,
            max_wait_seconds=max_wait_seconds
        )
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait_seconds:
                raise TranscriptionError(
                    error_code=ErrorCode.TRANSCRIPTION_TIMEOUT,
                    message=f"Transcription job timed out after {max_wait_seconds} seconds",
                    details={"job_id": job_id}
                )
            
            try:
                # Try to get result
                return self.get_transcription_result(job_id)
            except TranscriptionError as e:
                # If job is still in progress, continue polling
                if e.error_code == ErrorCode.TRANSCRIPTION_IN_PROGRESS:
                    logger.info(
                        "Transcription still in progress, waiting...",
                        job_id=job_id,
                        elapsed_seconds=int(elapsed)
                    )
                    time.sleep(poll_interval)
                else:
                    # Other errors should be raised
                    raise
    
    def _normalize_media_format(self, media_format: str) -> str:
        """
        Normalize media format to Transcribe-compatible format
        
        Args:
            media_format: Original media format
        
        Returns:
            Normalized format string
        """
        # Remove leading dot if present
        format_lower = media_format.lower().lstrip('.')
        
        # Map common formats to Transcribe formats
        format_map = {
            'mp4': 'mp4',
            'mp3': 'mp3',
            'wav': 'wav',
            'flac': 'flac',
            'ogg': 'ogg',
            'amr': 'amr',
            'webm': 'webm',
            'mov': 'mp4',  # MOV is treated as MP4
            'avi': 'mp4',  # AVI is treated as MP4
            'm4a': 'mp4'   # M4A is treated as MP4
        }
        
        normalized = format_map.get(format_lower, format_lower)
        
        logger.debug(
            "Normalized media format",
            original=media_format,
            normalized=normalized
        )
        
        return normalized
    
    def _download_transcript(self, transcript_uri: str) -> Dict[str, Any]:
        """
        Download transcript from S3 URI
        
        Args:
            transcript_uri: S3 URI or HTTPS URL of transcript
        
        Returns:
            Parsed transcript JSON
        """
        try:
            # Parse S3 URI or HTTPS URL
            if transcript_uri.startswith('s3://'):
                # Extract bucket and key from s3:// URI
                parts = transcript_uri[5:].split('/', 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ''
            elif transcript_uri.startswith('https://'):
                # Extract from HTTPS URL (format: https://bucket.s3.region.amazonaws.com/key)
                import re
                match = re.match(
                    r'https://([^.]+)\.s3\.[^.]+\.amazonaws\.com/(.+)',
                    transcript_uri
                )
                if match:
                    bucket = match.group(1)
                    key = match.group(2)
                else:
                    raise ValueError(f"Invalid transcript URI format: {transcript_uri}")
            else:
                raise ValueError(f"Unsupported transcript URI scheme: {transcript_uri}")
            
            # Download from S3
            content = self.s3_client.download_file(bucket, key)
            
            # Parse JSON
            transcript_data = json.loads(content.decode('utf-8'))
            
            return transcript_data
            
        except Exception as e:
            logger.log_error(
                operation="_download_transcript",
                error=e,
                transcript_uri=transcript_uri
            )
            raise TranscriptionError(
                error_code=ErrorCode.TRANSCRIPTION_FAILED,
                message=f"Failed to download transcript: {str(e)}",
                details={"transcript_uri": transcript_uri}
            )
