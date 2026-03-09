"""
Unit tests for TranscriptionService
"""
import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from src.services.transcription_service import (
    TranscriptionService,
    TranscriptionJob,
    Transcription,
    TranscriptionProgress
)
from src.utils.errors import TranscriptionError, ErrorCode


class TestTranscriptionService:
    """Test suite for TranscriptionService"""
    
    @pytest.fixture
    def mock_transcribe_client(self):
        """Create mock Transcribe client"""
        return Mock()
    
    @pytest.fixture
    def mock_s3_client(self):
        """Create mock S3 client"""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_transcribe_client, mock_s3_client):
        """Create TranscriptionService instance with mocks"""
        return TranscriptionService(
            transcribe_client=mock_transcribe_client,
            s3_client=mock_s3_client
        )
    
    def test_start_transcription_success(self, service, mock_transcribe_client):
        """Test successful transcription job start"""
        # Arrange
        content_id = "test-content-123"
        s3_uri = "s3://bucket/test.mp4"
        media_format = "mp4"
        
        mock_transcribe_client.start_transcription_job.return_value = "job-123"
        
        # Act
        result = service.start_transcription(content_id, s3_uri, media_format)
        
        # Assert
        assert isinstance(result, TranscriptionJob)
        assert result.job_id == "job-123"
        assert result.status == "IN_PROGRESS"
        assert result.content_id == content_id
        
        # Verify client was called correctly
        mock_transcribe_client.start_transcription_job.assert_called_once()
        call_args = mock_transcribe_client.start_transcription_job.call_args
        assert call_args[1]['media_uri'] == s3_uri
        assert call_args[1]['media_format'] == 'mp4'
    
    def test_start_transcription_normalizes_format(self, service, mock_transcribe_client):
        """Test that media format is normalized correctly"""
        # Arrange
        content_id = "test-content-123"
        s3_uri = "s3://bucket/test.mov"
        
        mock_transcribe_client.start_transcription_job.return_value = "job-123"
        
        # Act - MOV should be normalized to MP4
        service.start_transcription(content_id, s3_uri, "mov")
        
        # Assert
        call_args = mock_transcribe_client.start_transcription_job.call_args
        assert call_args[1]['media_format'] == 'mp4'
    
    def test_start_transcription_handles_dot_in_format(self, service, mock_transcribe_client):
        """Test that leading dot in format is handled"""
        # Arrange
        content_id = "test-content-123"
        s3_uri = "s3://bucket/test.mp3"
        
        mock_transcribe_client.start_transcription_job.return_value = "job-123"
        
        # Act
        service.start_transcription(content_id, s3_uri, ".mp3")
        
        # Assert
        call_args = mock_transcribe_client.start_transcription_job.call_args
        assert call_args[1]['media_format'] == 'mp3'
    
    def test_start_transcription_failure(self, service, mock_transcribe_client):
        """Test transcription job start failure"""
        # Arrange
        content_id = "test-content-123"
        s3_uri = "s3://bucket/test.mp4"
        
        mock_transcribe_client.start_transcription_job.side_effect = Exception("API Error")
        
        # Act & Assert
        with pytest.raises(TranscriptionError) as exc_info:
            service.start_transcription(content_id, s3_uri, "mp4")
        
        assert exc_info.value.error_code == ErrorCode.TRANSCRIPTION_FAILED
        assert "Failed to start transcription" in exc_info.value.message
    
    def test_get_transcription_result_completed(self, service, mock_transcribe_client, mock_s3_client):
        """Test retrieving completed transcription"""
        # Arrange
        job_id = "job-123"
        
        # Mock job status
        mock_transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJobStatus': 'COMPLETED',
            'Transcript': {
                'TranscriptFileUri': 's3://bucket/transcript.json'
            }
        }
        
        # Mock transcript content
        transcript_data = {
            'results': {
                'transcripts': [
                    {'transcript': 'This is a test transcript'}
                ],
                'items': [
                    {
                        'type': 'pronunciation',
                        'alternatives': [{'content': 'This'}],
                        'start_time': '0.0',
                        'end_time': '0.5'
                    },
                    {
                        'type': 'pronunciation',
                        'alternatives': [{'content': 'is'}],
                        'start_time': '0.5',
                        'end_time': '0.8'
                    }
                ]
            }
        }
        
        mock_s3_client.download_file.return_value = json.dumps(transcript_data).encode('utf-8')
        
        # Act
        result = service.get_transcription_result(job_id)
        
        # Assert
        assert isinstance(result, Transcription)
        assert result.text == 'This is a test transcript'
        assert result.timestamps is not None
        assert len(result.timestamps) == 2
        assert result.timestamps[0]['word'] == 'This'
        assert result.timestamps[0]['start_time'] == 0.0
        assert result.timestamps[0]['end_time'] == 0.5
    
    def test_get_transcription_result_in_progress(self, service, mock_transcribe_client):
        """Test retrieving transcription that's still in progress"""
        # Arrange
        job_id = "job-123"
        
        mock_transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJobStatus': 'IN_PROGRESS'
        }
        
        # Act & Assert
        with pytest.raises(TranscriptionError) as exc_info:
            service.get_transcription_result(job_id)
        
        assert exc_info.value.error_code == ErrorCode.TRANSCRIPTION_IN_PROGRESS
        assert "not completed yet" in exc_info.value.message
    
    def test_get_transcription_result_failed(self, service, mock_transcribe_client):
        """Test retrieving failed transcription"""
        # Arrange
        job_id = "job-123"
        
        mock_transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJobStatus': 'FAILED',
            'FailureReason': 'Invalid audio format'
        }
        
        # Act & Assert
        with pytest.raises(TranscriptionError) as exc_info:
            service.get_transcription_result(job_id)
        
        assert exc_info.value.error_code == ErrorCode.TRANSCRIPTION_FAILED
        assert "Invalid audio format" in exc_info.value.message
    
    def test_get_progress_queued(self, service, mock_transcribe_client):
        """Test progress for queued job"""
        # Arrange
        job_id = "job-123"
        
        mock_transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJobStatus': 'QUEUED'
        }
        
        # Act
        result = service.get_progress(job_id)
        
        # Assert
        assert isinstance(result, TranscriptionProgress)
        assert result.job_id == job_id
        assert result.percentage == 10
        assert result.estimated_time_remaining == 120
    
    def test_get_progress_in_progress(self, service, mock_transcribe_client):
        """Test progress for in-progress job"""
        # Arrange
        job_id = "job-123"
        
        mock_transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJobStatus': 'IN_PROGRESS'
        }
        
        # Act
        result = service.get_progress(job_id)
        
        # Assert
        assert result.percentage == 50
        assert result.estimated_time_remaining == 60
    
    def test_get_progress_completed(self, service, mock_transcribe_client):
        """Test progress for completed job"""
        # Arrange
        job_id = "job-123"
        
        mock_transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJobStatus': 'COMPLETED'
        }
        
        # Act
        result = service.get_progress(job_id)
        
        # Assert
        assert result.percentage == 100
        assert result.estimated_time_remaining is None
    
    def test_get_progress_error_handling(self, service, mock_transcribe_client):
        """Test progress returns default on error"""
        # Arrange
        job_id = "job-123"
        
        mock_transcribe_client.get_transcription_job.side_effect = Exception("API Error")
        
        # Act
        result = service.get_progress(job_id)
        
        # Assert - should return default progress instead of raising
        assert result.percentage == 0
        assert result.estimated_time_remaining is None
    
    def test_poll_until_complete_success(self, service, mock_transcribe_client, mock_s3_client):
        """Test polling until job completes"""
        # Arrange
        job_id = "job-123"
        
        # First call: IN_PROGRESS, second call: COMPLETED
        mock_transcribe_client.get_transcription_job.side_effect = [
            {'TranscriptionJobStatus': 'IN_PROGRESS'},
            {
                'TranscriptionJobStatus': 'COMPLETED',
                'Transcript': {
                    'TranscriptFileUri': 's3://bucket/transcript.json'
                }
            }
        ]
        
        transcript_data = {
            'results': {
                'transcripts': [{'transcript': 'Test'}],
                'items': []
            }
        }
        mock_s3_client.download_file.return_value = json.dumps(transcript_data).encode('utf-8')
        
        # Act
        result = service.poll_until_complete(job_id, max_wait_seconds=30, poll_interval=1)
        
        # Assert
        assert isinstance(result, Transcription)
        assert result.text == 'Test'
    
    def test_poll_until_complete_timeout(self, service, mock_transcribe_client):
        """Test polling timeout"""
        # Arrange
        job_id = "job-123"
        
        # Always return IN_PROGRESS
        mock_transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJobStatus': 'IN_PROGRESS'
        }
        
        # Act & Assert
        with pytest.raises(TranscriptionError) as exc_info:
            service.poll_until_complete(job_id, max_wait_seconds=2, poll_interval=1)
        
        assert exc_info.value.error_code == ErrorCode.TRANSCRIPTION_TIMEOUT
        assert "timed out" in exc_info.value.message
    
    def test_download_transcript_s3_uri(self, service, mock_s3_client):
        """Test downloading transcript from s3:// URI"""
        # Arrange
        transcript_uri = "s3://my-bucket/path/to/transcript.json"
        transcript_data = {
            'results': {
                'transcripts': [{'transcript': 'Test'}],
                'items': []
            }
        }
        
        mock_s3_client.download_file.return_value = json.dumps(transcript_data).encode('utf-8')
        
        # Act
        result = service._download_transcript(transcript_uri)
        
        # Assert
        assert result == transcript_data
        mock_s3_client.download_file.assert_called_once_with('my-bucket', 'path/to/transcript.json')
    
    def test_download_transcript_https_uri(self, service, mock_s3_client):
        """Test downloading transcript from HTTPS URL"""
        # Arrange
        transcript_uri = "https://my-bucket.s3.us-east-1.amazonaws.com/path/to/transcript.json"
        transcript_data = {
            'results': {
                'transcripts': [{'transcript': 'Test'}],
                'items': []
            }
        }
        
        mock_s3_client.download_file.return_value = json.dumps(transcript_data).encode('utf-8')
        
        # Act
        result = service._download_transcript(transcript_uri)
        
        # Assert
        assert result == transcript_data
        mock_s3_client.download_file.assert_called_once_with('my-bucket', 'path/to/transcript.json')
    
    def test_download_transcript_invalid_uri(self, service):
        """Test downloading transcript with invalid URI"""
        # Arrange
        transcript_uri = "ftp://invalid.com/transcript.json"
        
        # Act & Assert
        with pytest.raises(TranscriptionError) as exc_info:
            service._download_transcript(transcript_uri)
        
        assert exc_info.value.error_code == ErrorCode.TRANSCRIPTION_FAILED
        assert "Unsupported transcript URI scheme" in exc_info.value.message
    
    def test_normalize_media_format_variations(self, service):
        """Test media format normalization for various inputs"""
        # Test cases: (input, expected_output)
        test_cases = [
            ('mp4', 'mp4'),
            ('MP4', 'mp4'),
            ('.mp4', 'mp4'),
            ('mov', 'mp4'),  # MOV -> MP4
            ('avi', 'mp4'),  # AVI -> MP4
            ('mp3', 'mp3'),
            ('wav', 'wav'),
            ('m4a', 'mp4'),  # M4A -> MP4
        ]
        
        for input_format, expected in test_cases:
            result = service._normalize_media_format(input_format)
            assert result == expected, f"Failed for input: {input_format}"
    
    def test_transcription_without_timestamps(self, service, mock_transcribe_client, mock_s3_client):
        """Test transcription result without timestamp items"""
        # Arrange
        job_id = "job-123"
        
        mock_transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJobStatus': 'COMPLETED',
            'Transcript': {
                'TranscriptFileUri': 's3://bucket/transcript.json'
            }
        }
        
        # Transcript without items
        transcript_data = {
            'results': {
                'transcripts': [{'transcript': 'Test transcript'}]
            }
        }
        
        mock_s3_client.download_file.return_value = json.dumps(transcript_data).encode('utf-8')
        
        # Act
        result = service.get_transcription_result(job_id)
        
        # Assert
        assert result.text == 'Test transcript'
        assert result.timestamps is None
    
    def test_transcription_with_punctuation_items(self, service, mock_transcribe_client, mock_s3_client):
        """Test that punctuation items are filtered out from timestamps"""
        # Arrange
        job_id = "job-123"
        
        mock_transcribe_client.get_transcription_job.return_value = {
            'TranscriptionJobStatus': 'COMPLETED',
            'Transcript': {
                'TranscriptFileUri': 's3://bucket/transcript.json'
            }
        }
        
        transcript_data = {
            'results': {
                'transcripts': [{'transcript': 'Hello, world!'}],
                'items': [
                    {
                        'type': 'pronunciation',
                        'alternatives': [{'content': 'Hello'}],
                        'start_time': '0.0',
                        'end_time': '0.5'
                    },
                    {
                        'type': 'punctuation',
                        'alternatives': [{'content': ','}]
                    },
                    {
                        'type': 'pronunciation',
                        'alternatives': [{'content': 'world'}],
                        'start_time': '0.6',
                        'end_time': '1.0'
                    },
                    {
                        'type': 'punctuation',
                        'alternatives': [{'content': '!'}]
                    }
                ]
            }
        }
        
        mock_s3_client.download_file.return_value = json.dumps(transcript_data).encode('utf-8')
        
        # Act
        result = service.get_transcription_result(job_id)
        
        # Assert
        assert len(result.timestamps) == 2  # Only pronunciation items
        assert result.timestamps[0]['word'] == 'Hello'
        assert result.timestamps[1]['word'] == 'world'
