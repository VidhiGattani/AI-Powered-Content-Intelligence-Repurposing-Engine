"""
Database Stack - DynamoDB Tables for Content Repurposing Platform
"""
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
)
from constructs import Construct


class DatabaseStack(Stack):
    """Creates DynamoDB tables for users, style content, original content, generated content, and scheduled posts"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Users Table
        self.users_table = dynamodb.Table(
            self,
            "UsersTable",
            table_name="users",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        # Style Content Table
        self.style_content_table = dynamodb.Table(
            self,
            "StyleContentTable",
            table_name="style_content",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="content_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        # Add GSI for querying by embedding status
        self.style_content_table.add_global_secondary_index(
            index_name="embedding_status-index",
            partition_key=dynamodb.Attribute(
                name="embedding_status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="uploaded_at",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Original Content Table
        self.original_content_table = dynamodb.Table(
            self,
            "OriginalContentTable",
            table_name="original_content",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="content_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        # Add GSI for querying by processing status
        self.original_content_table.add_global_secondary_index(
            index_name="processing_status-index",
            partition_key=dynamodb.Attribute(
                name="processing_status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="uploaded_at",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Generated Content Table
        self.generated_content_table = dynamodb.Table(
            self,
            "GeneratedContentTable",
            table_name="generated_content",
            partition_key=dynamodb.Attribute(
                name="content_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="generation_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        # Add GSI for querying user's generated content
        self.generated_content_table.add_global_secondary_index(
            index_name="user_id-generated_at-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="generated_at",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Scheduled Posts Table
        self.scheduled_posts_table = dynamodb.Table(
            self,
            "ScheduledPostsTable",
            table_name="scheduled_posts",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="schedule_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
        )

        # Add GSI for querying by scheduled time
        self.scheduled_posts_table.add_global_secondary_index(
            index_name="scheduled_time-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="scheduled_time",
                type=dynamodb.AttributeType.STRING
            )
        )
