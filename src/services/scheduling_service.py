"""
Scheduling Service

Handles post scheduling, optimal time recommendations, and notifications.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import uuid
from zoneinfo import ZoneInfo

from src.models.enums import Platform
from src.utils.errors import ValidationError, NotFoundError, ErrorCode
from src.utils.logger import get_logger
from src.utils.aws_clients import DynamoDBClient

logger = get_logger(__name__)


@dataclass
class ScheduledPost:
    """Represents a scheduled post"""
    schedule_id: str
    user_id: str
    generation_id: str
    platform: Platform
    scheduled_time: datetime
    created_at: datetime
    status: str  # PENDING, NOTIFIED, CANCELLED
    notification_sent: bool


class SchedulingService:
    """Service for scheduling posts and managing optimal posting times"""
    
    # Optimal posting times based on platform best practices
    # Format: (day_of_week, hour, minute) where day_of_week: 0=Monday, 6=Sunday
    OPTIMAL_TIMES = {
        Platform.LINKEDIN: [
            (1, 8, 0),   # Tuesday 8 AM
            (1, 12, 0),  # Tuesday 12 PM
            (2, 9, 0),   # Wednesday 9 AM
            (2, 12, 0),  # Wednesday 12 PM
            (3, 8, 0),   # Thursday 8 AM
            (3, 10, 0),  # Thursday 10 AM
        ],
        Platform.TWITTER: [
            (0, 9, 0),   # Monday 9 AM
            (0, 12, 0),  # Monday 12 PM
            (1, 9, 0),   # Tuesday 9 AM
            (2, 12, 0),  # Wednesday 12 PM
            (3, 9, 0),   # Thursday 9 AM
            (4, 17, 0),  # Friday 5 PM
        ],
        Platform.INSTAGRAM: [
            (0, 11, 0),  # Monday 11 AM
            (1, 14, 0),  # Tuesday 2 PM
            (2, 11, 0),  # Wednesday 11 AM
            (3, 19, 0),  # Thursday 7 PM
            (4, 14, 0),  # Friday 2 PM
        ],
        Platform.YOUTUBE_SHORTS: [
            (3, 14, 0),  # Thursday 2 PM
            (3, 16, 0),  # Thursday 4 PM
            (4, 15, 0),  # Friday 3 PM
            (5, 14, 0),  # Saturday 2 PM
            (5, 16, 0),  # Saturday 4 PM
        ],
    }
    
    def __init__(self, table_name: str = "scheduled_posts", timezone: str = "UTC"):
        """
        Initialize scheduling service
        
        Args:
            table_name: DynamoDB table name for scheduled posts
            timezone: Timezone for scheduling (default: UTC)
        """
        self.dynamodb = DynamoDBClient()
        self.table_name = table_name
        self.timezone = ZoneInfo(timezone)
    
    def get_optimal_times(
        self,
        platform: Platform,
        count: int = 3,
        days_ahead: int = 7
    ) -> List[datetime]:
        """
        Get recommended posting times for a platform
        
        Args:
            platform: Target platform
            count: Number of recommendations to return (default: 3)
            days_ahead: Number of days to look ahead (default: 7)
            
        Returns:
            List of recommended datetime objects
            
        Raises:
            ValidationError: If platform is invalid
        """
        if platform not in self.OPTIMAL_TIMES:
            raise ValidationError(
                error_code=ErrorCode.UNSUPPORTED_PLATFORM,
                message=f"Platform {platform.value} not supported for optimal time recommendations"
            )
        
        logger.info(f"Calculating optimal times for {platform.value}")
        
        optimal_slots = self.OPTIMAL_TIMES[platform]
        now = datetime.now(self.timezone)
        recommendations = []
        
        # Look ahead for the specified number of days
        for day_offset in range(days_ahead):
            check_date = now + timedelta(days=day_offset)
            
            for day_of_week, hour, minute in optimal_slots:
                # Calculate the target datetime
                days_until_target = (day_of_week - check_date.weekday()) % 7
                if days_until_target == 0 and day_offset > 0:
                    continue  # Skip if we already checked this day
                    
                target_date = check_date + timedelta(days=days_until_target)
                target_time = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Only include future times
                if target_time > now:
                    recommendations.append(target_time)
                    
                    if len(recommendations) >= count:
                        return sorted(recommendations)[:count]
        
        # Return what we have, sorted
        return sorted(recommendations)[:count]



    def schedule_post(
        self,
        user_id: str,
        generation_id: str,
        platform: Platform,
        scheduled_time: datetime
    ) -> ScheduledPost:
        """
        Schedule a post for future publication
        
        Args:
            user_id: User ID
            generation_id: Generated content ID
            platform: Target platform
            scheduled_time: When to publish
            
        Returns:
            ScheduledPost object
            
        Raises:
            ValidationError: If scheduled_time is in the past
        """
        now = datetime.now(self.timezone)
        
        # Validate scheduled time is in the future
        if scheduled_time <= now:
            raise ValidationError(
                error_code=ErrorCode.INVALID_SCHEDULE_TIME,
                message="Scheduled time must be in the future"
            )
        
        # Generate schedule ID
        schedule_id = str(uuid.uuid4())
        
        # Create scheduled post object
        scheduled_post = ScheduledPost(
            schedule_id=schedule_id,
            user_id=user_id,
            generation_id=generation_id,
            platform=platform,
            scheduled_time=scheduled_time,
            created_at=now,
            status="PENDING",
            notification_sent=False
        )
        
        # Store in DynamoDB
        try:
            self.dynamodb.put_item(
                table_name=self.table_name,
                item={
                    "user_id": user_id,
                    "schedule_id": schedule_id,
                    "generation_id": generation_id,
                    "platform": platform.value,
                    "scheduled_time": scheduled_time.isoformat(),
                    "created_at": now.isoformat(),
                    "status": "PENDING",
                    "notification_sent": False
                }
            )
            
            logger.info(f"Scheduled post {schedule_id} for user {user_id} at {scheduled_time}")
            return scheduled_post
            
        except Exception as e:
            logger.error(f"Failed to schedule post: {str(e)}")
            raise ValidationError(
                error_code=ErrorCode.DYNAMODB_ERROR,
                message=f"Failed to create schedule: {str(e)}"
            )
    
    def cancel_schedule(self, schedule_id: str, user_id: str) -> bool:
        """
        Cancel a scheduled post
        
        Args:
            schedule_id: Schedule ID to cancel
            user_id: User ID (for authorization)
            
        Returns:
            True if cancelled, False if already notified/published
            
        Raises:
            NotFoundError: If schedule doesn't exist
        """
        try:
            # Get the schedule
            item = self.dynamodb.get_item(
                table_name=self.table_name,
                key={
                    "user_id": user_id,
                    "schedule_id": schedule_id
                }
            )
            
            if not item:
                raise NotFoundError(
                    error_code=ErrorCode.SCHEDULE_NOT_FOUND,
                    message=f"Schedule {schedule_id} not found"
                )
            
            status = item["status"]
            
            # Can't cancel if already notified
            if status in ["NOTIFIED", "CANCELLED"]:
                logger.info(f"Schedule {schedule_id} already {status}")
                return False
            
            # Update status to CANCELLED
            self.dynamodb.update_item(
                table_name=self.table_name,
                key={
                    "user_id": user_id,
                    "schedule_id": schedule_id
                },
                update_expression="SET #status = :cancelled",
                expression_attribute_values={
                    ":cancelled": "CANCELLED"
                }
            )
            
            logger.info(f"Cancelled schedule {schedule_id}")
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to cancel schedule: {str(e)}")
            raise ValidationError(
                error_code=ErrorCode.DYNAMODB_ERROR,
                message=f"Failed to cancel schedule: {str(e)}"
            )
    
    def check_and_notify_due_posts(self) -> List[ScheduledPost]:
        """
        Check for posts that are due and send notifications
        This would typically be called by a Lambda function on a schedule
        
        Note: In production, this would use a GSI on scheduled_time for efficient queries.
        For now, this is a simplified implementation.
        
        Returns:
            List of posts that were notified
        """
        # In production, this would query a GSI: scheduled_time-index
        # For now, returning empty list as we don't have scan capability
        logger.info("check_and_notify_due_posts called - would use GSI in production")
        return []
    
    def get_user_schedules(
        self,
        user_id: str,
        status_filter: Optional[str] = None
    ) -> List[ScheduledPost]:
        """
        Get all schedules for a user
        
        Args:
            user_id: User ID
            status_filter: Optional status filter (PENDING, NOTIFIED, CANCELLED)
            
        Returns:
            List of ScheduledPost objects
        """
        try:
            # Query by user_id (partition key)
            items = self.dynamodb.query(
                table_name=self.table_name,
                key_condition_expression="user_id = :user_id",
                expression_attribute_values={
                    ":user_id": user_id
                }
            )
            
            schedules = []
            for item in items:
                # Apply status filter if provided
                if status_filter and item.get("status") != status_filter:
                    continue
                    
                schedule = ScheduledPost(
                    schedule_id=item["schedule_id"],
                    user_id=item["user_id"],
                    generation_id=item["generation_id"],
                    platform=Platform(item["platform"]),
                    scheduled_time=datetime.fromisoformat(item["scheduled_time"]),
                    created_at=datetime.fromisoformat(item["created_at"]),
                    status=item["status"],
                    notification_sent=item.get("notification_sent", False)
                )
                schedules.append(schedule)
            
            return schedules
            
        except Exception as e:
            logger.error(f"Failed to get user schedules: {str(e)}")
            return []
