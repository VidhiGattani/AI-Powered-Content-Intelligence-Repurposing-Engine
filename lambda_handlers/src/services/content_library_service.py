"""
Content Library Service for Content Repurposing Platform
Manages content storage and retrieval with pagination
"""
import os
from typing import Optional, List
from datetime import datetime

from ..models.content import ContentMetadata
from ..utils.aws_clients import DynamoDBClient
from ..utils.errors import NotFoundError, ErrorCode
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ContentLibraryService:
    """Manages content library retrieval and operations"""
    
    def __init__(self, dynamodb_client: Optional[DynamoDBClient] = None):
        """Initialize ContentLibraryService with AWS clients"""
        self.dynamodb_client = dynamodb_client or DynamoDBClient()
        
        # Get configuration from environment
        self.content_table = os.environ.get(
            'DYNAMODB_TABLE_ORIGINAL_CONTENT',
            'original_content'
        )
    
    def get_user_content(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """
        Retrieve user's content library sorted by creation date
        
        Args:
            user_id: User ID to retrieve content for
            limit: Maximum number of items to return (default: 50)
            offset: Number of items to skip for pagination (default: 0)
        
        Returns:
            Dictionary with:
                - items: List of ContentMetadata objects
                - total_count: Total number of items for the user
                - limit: Limit used for this query
                - offset: Offset used for this query
                - has_more: Boolean indicating if more items exist
        
        Validates: Requirements 10.3, 10.4
        """
        logger.info(
            "Retrieving user content library",
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        try:
            # Query DynamoDB for user's content
            # Using the partition key (user_id) to get all content for this user
            table = self.dynamodb_client.resource.Table(self.content_table)
            
            # Query with pagination support
            response = table.query(
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={
                    ':uid': user_id
                },
                ScanIndexForward=False  # Sort by sort key descending (newest first)
            )
            
            items = response.get('Items', [])
            
            # Convert DynamoDB items to ContentMetadata objects
            content_list = [
                ContentMetadata.from_dynamodb_item(item)
                for item in items
            ]
            
            # Sort by uploaded_at descending (newest first) to ensure correct order
            content_list.sort(key=lambda x: x.uploaded_at, reverse=True)
            
            # Apply pagination
            total_count = len(content_list)
            paginated_items = content_list[offset:offset + limit]
            has_more = (offset + limit) < total_count
            
            logger.info(
                "Content library retrieved successfully",
                user_id=user_id,
                total_count=total_count,
                returned_count=len(paginated_items),
                has_more=has_more
            )
            
            return {
                'items': [item.to_dict() for item in paginated_items],
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': has_more
            }
            
        except Exception as e:
            logger.log_error(
                operation="get_user_content",
                error=e,
                user_id=user_id
            )
            raise

    def get_content(
        self,
        user_id: str,
        content_id: str
    ) -> Optional[ContentMetadata]:
        """
        Get a single content item by ID
        
        Args:
            user_id: User ID (for authorization)
            content_id: Content ID to retrieve
        
        Returns:
            ContentMetadata object or None if not found
        
        Raises:
            NotFoundError: If content doesn't exist
        """
        logger.info(
            "Retrieving content",
            user_id=user_id,
            content_id=content_id
        )
        
        try:
            # Get the content from DynamoDB
            content = self.dynamodb_client.get_item(
                table_name=self.content_table,
                key={
                    "user_id": user_id,
                    "content_id": content_id
                }
            )
            
            if not content:
                raise NotFoundError(
                    error_code=ErrorCode.CONTENT_NOT_FOUND,
                    message=f"Content {content_id} not found"
                )
            
            # Convert to ContentMetadata object
            content_metadata = ContentMetadata.from_dynamodb_item(content)
            
            logger.info(
                "Content retrieved successfully",
                user_id=user_id,
                content_id=content_id
            )
            
            return content_metadata
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.log_error(
                operation="get_content",
                error=e,
                user_id=user_id,
                content_id=content_id
            )
            raise

    
    def search_content(
        self,
        user_id: str,
        keyword: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        platforms: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """
        Search content by keywords, dates, and platforms
        
        Args:
            user_id: User ID to search content for
            keyword: Optional keyword to search in filename
            start_date: Optional start date filter
            end_date: Optional end date filter
            platforms: Optional list of platforms to filter by
            limit: Maximum number of items to return (default: 50)
            offset: Number of items to skip for pagination (default: 0)
        
        Returns:
            Dictionary with:
                - items: List of ContentMetadata objects matching search criteria
                - total_count: Total number of matching items
                - limit: Limit used for this query
                - offset: Offset used for this query
                - has_more: Boolean indicating if more items exist
        
        Validates: Requirements 10.3
        """
        logger.info(
            "Searching user content",
            user_id=user_id,
            keyword=keyword,
            start_date=start_date,
            end_date=end_date,
            platforms=platforms
        )
        
        try:
            # First get all user content
            all_content = self.get_user_content(
                user_id=user_id,
                limit=1000,  # Get a large batch for filtering
                offset=0
            )
            
            items = all_content['items']
            
            # Apply filters
            filtered_items = items
            
            # Filter by keyword in filename
            if keyword:
                keyword_lower = keyword.lower()
                filtered_items = [
                    item for item in filtered_items
                    if keyword_lower in item['filename'].lower()
                ]
            
            # Filter by date range
            if start_date:
                filtered_items = [
                    item for item in filtered_items
                    if datetime.fromisoformat(item['uploaded_at']) >= start_date
                ]
            
            if end_date:
                filtered_items = [
                    item for item in filtered_items
                    if datetime.fromisoformat(item['uploaded_at']) <= end_date
                ]
            
            # Filter by platforms (if content has platform metadata)
            if platforms:
                # This would filter generated content by platform
                # For original content, we skip this filter
                pass
            
            # Apply pagination
            total_count = len(filtered_items)
            paginated_items = filtered_items[offset:offset + limit]
            has_more = (offset + limit) < total_count
            
            logger.info(
                "Content search completed",
                user_id=user_id,
                total_count=total_count,
                returned_count=len(paginated_items)
            )
            
            return {
                'items': paginated_items,  # Already dictionaries
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': has_more
            }
            
        except Exception as e:
            logger.log_error(
                operation="search_content",
                error=e,
                user_id=user_id
            )
            raise
    
    def delete_content(
        self,
        content_id: str,
        user_id: str
    ) -> bool:
        """
        Delete content and all associated data
        Implements soft delete by marking as deleted in DynamoDB
        and removes from S3
        
        Args:
            content_id: Content ID to delete
            user_id: User ID (for authorization)
        
        Returns:
            True if deleted successfully
        
        Raises:
            NotFoundError: If content doesn't exist
        
        Validates: Requirements 10.5
        """
        logger.info(
            "Deleting content",
            content_id=content_id,
            user_id=user_id
        )
        
        try:
            # Get the content to verify it exists and get S3 URI
            content = self.dynamodb_client.get_item(
                table_name=self.content_table,
                key={
                    "user_id": user_id,
                    "content_id": content_id
                }
            )
            
            if not content:
                raise NotFoundError(
                    error_code=ErrorCode.CONTENT_NOT_FOUND,
                    message=f"Content {content_id} not found"
                )
            
            # Soft delete: mark as deleted in DynamoDB
            self.dynamodb_client.update_item(
                table_name=self.content_table,
                key={
                    "user_id": user_id,
                    "content_id": content_id
                },
                update_expression="SET deleted = :true, deleted_at = :timestamp",
                expression_attribute_values={
                    ":true": True,
                    ":timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Remove from S3 if S3 URI exists
            if "s3_uri" in content and content["s3_uri"]:
                s3_uri = content["s3_uri"]
                # Parse S3 URI: s3://bucket/key
                if s3_uri.startswith("s3://"):
                    parts = s3_uri[5:].split("/", 1)
                    if len(parts) == 2:
                        bucket, key = parts
                        try:
                            from ..utils.aws_clients import S3Client
                            s3_client = S3Client()
                            s3_client.delete_file(bucket=bucket, key=key)
                            logger.info(
                                "S3 file deleted",
                                bucket=bucket,
                                key=key
                            )
                        except Exception as e:
                            logger.error(
                                "Failed to delete S3 file",
                                error=str(e),
                                s3_uri=s3_uri
                            )
                            # Continue even if S3 deletion fails
            
            logger.info(
                "Content deleted successfully",
                content_id=content_id,
                user_id=user_id
            )
            
            return True
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.log_error(
                operation="delete_content",
                error=e,
                content_id=content_id,
                user_id=user_id
            )
            raise
