"""
Unit tests for SchedulingService
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from src.services.scheduling_service import SchedulingService, ScheduledPost
from src.models.enums import Platform
from src.utils.errors import ValidationError, NotFoundError, ErrorCode


class TestGetOptimalTimes:
    """Tests for get_optimal_times method"""
    
    def test_get_optimal_times_linkedin(self):
        """Test optimal times for LinkedIn"""
        service = SchedulingService()
        times = service.get_optimal_times(Platform.LINKEDIN, count=3)
        
        assert len(times) == 3
        assert all(isinstance(t, datetime) for t in times)
        # All times should be in the future
        now = datetime.now(service.timezone)
        assert all(t > now for t in times)
        # Times should be sorted
        assert times == sorted(times)
    
    def test_get_optimal_times_twitter(self):
        """Test optimal times for Twitter"""
        service = SchedulingService()
        times = service.get_optimal_times(Platform.TWITTER, count=5)
        
        assert len(times) == 5
        assert all(isinstance(t, datetime) for t in times)
    
    def test_get_optimal_times_instagram(self):
        """Test optimal times for Instagram"""
        service = SchedulingService()
        times = service.get_optimal_times(Platform.INSTAGRAM)
        
        assert len(times) == 3  # Default count
        assert all(isinstance(t, datetime) for t in times)
    
    def test_get_optimal_times_youtube(self):
        """Test optimal times for YouTube Shorts"""
        service = SchedulingService()
        times = service.get_optimal_times(Platform.YOUTUBE_SHORTS, count=4)
        
        assert len(times) == 4
        assert all(isinstance(t, datetime) for t in times)
    
    def test_get_optimal_times_custom_days_ahead(self):
        """Test optimal times with custom days_ahead"""
        service = SchedulingService()
        times = service.get_optimal_times(Platform.LINKEDIN, count=10, days_ahead=14)
        
        assert len(times) == 10
        # All times should be within 14 days
        now = datetime.now(service.timezone)
        max_time = now + timedelta(days=14)
        assert all(now < t <= max_time for t in times)
    
    def test_get_optimal_times_returns_future_only(self):
        """Test that only future times are returned"""
        service = SchedulingService()
        times = service.get_optimal_times(Platform.TWITTER, count=3)
        
        now = datetime.now(service.timezone)
        assert all(t > now for t in times)


class TestSchedulePost:
    """Tests for schedule_post method"""
    
    @patch('src.services.scheduling_service.DynamoDBClient')
    def test_schedule_post_success(self, mock_client_class):
        """Test successful post scheduling"""
        mock_dynamodb = Mock()
        mock_client_class.return_value = mock_dynamodb
        
        service = SchedulingService()
        future_time = datetime.now(service.timezone) + timedelta(hours=2)
        
        result = service.schedule_post(
            user_id="user123",
            generation_id="gen456",
            platform=Platform.LINKEDIN,
            scheduled_time=future_time
        )
        
        assert isinstance(result, ScheduledPost)
        assert result.user_id == "user123"
        assert result.generation_id == "gen456"
        assert result.platform == Platform.LINKEDIN
        assert result.scheduled_time == future_time
        assert result.status == "PENDING"
        assert result.notification_sent is False
        assert result.schedule_id is not None
        
        # Verify DynamoDB put_item was called
        mock_dynamodb.put_item.assert_called_once()
    
    @patch('src.services.scheduling_service.DynamoDBClient')
    def test_schedule_post_past_time_raises_error(self, mock_client_class):
        """Test scheduling with past time raises ValidationError"""
        mock_dynamodb = Mock()
        mock_client_class.return_value = mock_dynamodb
        
        service = SchedulingService()
        past_time = datetime.now(service.timezone) - timedelta(hours=1)
        
        with pytest.raises(ValidationError) as exc_info:
            service.schedule_post(
                user_id="user123",
                generation_id="gen456",
                platform=Platform.TWITTER,
                scheduled_time=past_time
            )
        
        assert "must be in the future" in str(exc_info.value)
        assert exc_info.value.error_code == ErrorCode.INVALID_SCHEDULE_TIME
    
    @patch('src.services.scheduling_service.DynamoDBClient')
    def test_schedule_post_dynamodb_failure(self, mock_client_class):
        """Test handling of DynamoDB failure"""
        mock_dynamodb = Mock()
        mock_dynamodb.put_item.side_effect = Exception("DynamoDB error")
        mock_client_class.return_value = mock_dynamodb
        
        service = SchedulingService()
        future_time = datetime.now(service.timezone) + timedelta(hours=2)
        
        with pytest.raises(ValidationError) as exc_info:
            service.schedule_post(
                user_id="user123",
                generation_id="gen456",
                platform=Platform.INSTAGRAM,
                scheduled_time=future_time
            )
        
        assert "Failed to create schedule" in str(exc_info.value)
        assert exc_info.value.error_code == ErrorCode.DYNAMODB_ERROR
    
    @patch('src.services.scheduling_service.DynamoDBClient')
    def test_schedule_post_stores_correct_data(self, mock_client_class):
        """Test that correct data is stored in DynamoDB"""
        mock_dynamodb = Mock()
        mock_client_class.return_value = mock_dynamodb
        
        service = SchedulingService()
        future_time = datetime.now(service.timezone) + timedelta(days=1)
        
        service.schedule_post(
            user_id="user789",
            generation_id="gen101",
            platform=Platform.YOUTUBE_SHORTS,
            scheduled_time=future_time
        )
        
        call_args = mock_dynamodb.put_item.call_args
        item = call_args.kwargs["item"]
        
        assert item["user_id"] == "user789"
        assert item["generation_id"] == "gen101"
        assert item["platform"] == "youtube_shorts"
        assert item["status"] == "PENDING"
        assert item["notification_sent"] is False


class TestCancelSchedule:
    """Tests for cancel_schedule method"""
    
    @patch('src.services.scheduling_service.DynamoDBClient')
    def test_cancel_schedule_success(self, mock_client_class):
        """Test successful schedule cancellation"""
        mock_dynamodb = Mock()
        mock_dynamodb.get_item.return_value = {
            "user_id": "user123",
            "schedule_id": "sched456",
            "status": "PENDING"
        }
        mock_client_class.return_value = mock_dynamodb
        
        service = SchedulingService()
        result = service.cancel_schedule("sched456", "user123")
        
        assert result is True
        mock_dynamodb.update_item.assert_called_once()
    
    @patch('src.services.scheduling_service.DynamoDBClient')
    def test_cancel_schedule_not_found(self, mock_client_class):
        """Test cancelling non-existent schedule"""
        mock_dynamodb = Mock()
        mock_dynamodb.get_item.return_value = None
        mock_client_class.return_value = mock_dynamodb
        
        service = SchedulingService()
        
        with pytest.raises(NotFoundError) as exc_info:
            service.cancel_schedule("nonexistent", "user123")
        
        assert "not found" in str(exc_info.value)
        assert exc_info.value.error_code == ErrorCode.SCHEDULE_NOT_FOUND
    
    @patch('src.services.scheduling_service.DynamoDBClient')
    def test_cancel_schedule_already_notified(self, mock_client_class):
        """Test cancelling already notified schedule"""
        mock_dynamodb = Mock()
        mock_dynamodb.get_item.return_value = {
            "user_id": "user123",
            "schedule_id": "sched456",
            "status": "NOTIFIED"
        }
        mock_client_class.return_value = mock_dynamodb
        
        service = SchedulingService()
        result = service.cancel_schedule("sched456", "user123")
        
        assert result is False
        mock_dynamodb.update_item.assert_not_called()
    
    @patch('src.services.scheduling_service.DynamoDBClient')
    def test_cancel_schedule_already_cancelled(self, mock_client_class):
        """Test cancelling already cancelled schedule"""
        mock_dynamodb = Mock()
        mock_dynamodb.get_item.return_value = {
            "user_id": "user123",
            "schedule_id": "sched456",
            "status": "CANCELLED"
        }
        mock_client_class.return_value = mock_dynamodb
        
        service = SchedulingService()
        result = service.cancel_schedule("sched456", "user123")
        
        assert result is False


class TestGetUserSchedules:
    """Tests for get_user_schedules method"""
    
    @patch('src.services.scheduling_service.DynamoDBClient')
    def test_get_user_schedules_success(self, mock_client_class):
        """Test retrieving user schedules"""
        mock_dynamodb = Mock()
        mock_dynamodb.query.return_value = [
            {
                "user_id": "user123",
                "schedule_id": "sched1",
                "generation_id": "gen1",
                "platform": "linkedin",
                "scheduled_time": datetime.now(ZoneInfo("UTC")).isoformat(),
                "created_at": datetime.now(ZoneInfo("UTC")).isoformat(),
                "status": "PENDING",
                "notification_sent": False
            }
        ]
        mock_client_class.return_value = mock_dynamodb
        
        service = SchedulingService()
        schedules = service.get_user_schedules("user123")
        
        assert len(schedules) == 1
        assert schedules[0].user_id == "user123"
        assert schedules[0].schedule_id == "sched1"
    
    @patch('src.services.scheduling_service.DynamoDBClient')
    def test_get_user_schedules_with_filter(self, mock_client_class):
        """Test retrieving user schedules with status filter"""
        mock_dynamodb = Mock()
        mock_dynamodb.query.return_value = [
            {
                "user_id": "user123",
                "schedule_id": "sched1",
                "generation_id": "gen1",
                "platform": "twitter",
                "scheduled_time": datetime.now(ZoneInfo("UTC")).isoformat(),
                "created_at": datetime.now(ZoneInfo("UTC")).isoformat(),
                "status": "NOTIFIED",
                "notification_sent": True
            }
        ]
        mock_client_class.return_value = mock_dynamodb
        
        service = SchedulingService()
        schedules = service.get_user_schedules("user123", status_filter="PENDING")
        
        # Should be filtered out since status is NOTIFIED
        assert len(schedules) == 0
    
    @patch('src.services.scheduling_service.DynamoDBClient')
    def test_get_user_schedules_empty(self, mock_client_class):
        """Test retrieving schedules for user with none"""
        mock_dynamodb = Mock()
        mock_dynamodb.query.return_value = []
        mock_client_class.return_value = mock_dynamodb
        
        service = SchedulingService()
        schedules = service.get_user_schedules("user_no_schedules")
        
        assert len(schedules) == 0


class TestScheduledPost:
    """Tests for ScheduledPost dataclass"""
    
    def test_scheduled_post_creation(self):
        """Test creating a ScheduledPost"""
        now = datetime.now(ZoneInfo("UTC"))
        post = ScheduledPost(
            schedule_id="sched123",
            user_id="user456",
            generation_id="gen789",
            platform=Platform.TWITTER,
            scheduled_time=now + timedelta(hours=1),
            created_at=now,
            status="PENDING",
            notification_sent=False
        )
        
        assert post.schedule_id == "sched123"
        assert post.user_id == "user456"
        assert post.platform == Platform.TWITTER
        assert post.status == "PENDING"
        assert post.notification_sent is False
