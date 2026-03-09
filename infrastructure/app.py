#!/usr/bin/env python3
"""
AWS CDK App for Content Repurposing Platform
"""
import aws_cdk as cdk
from stacks.storage_stack import StorageStack
from stacks.auth_stack import AuthStack
from stacks.database_stack import DatabaseStack
from stacks.api_stack import ApiStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1"
)

# Storage Stack - S3 buckets
storage_stack = StorageStack(
    app,
    "ContentRepurposingStorageStack",
    env=env,
    description="S3 buckets for content storage"
)

# Database Stack - DynamoDB tables
database_stack = DatabaseStack(
    app,
    "ContentRepurposingDatabaseStack",
    env=env,
    description="DynamoDB tables for metadata storage"
)

# Auth Stack - Cognito User Pool
auth_stack = AuthStack(
    app,
    "ContentRepurposingAuthStack",
    env=env,
    description="Cognito User Pool for authentication"
)

# API Stack - API Gateway and Lambda handlers
api_stack = ApiStack(
    app,
    "ContentRepurposingApiStack",
    user_pool_id=auth_stack.user_pool.user_pool_id,
    user_pool_client_id=auth_stack.user_pool_client.user_pool_client_id,
    original_content_bucket=storage_stack.original_content_bucket.bucket_name,
    generated_content_bucket=storage_stack.generated_content_bucket.bucket_name,
    style_vault_bucket=storage_stack.style_vault_bucket.bucket_name,
    transcripts_bucket=storage_stack.transcripts_bucket.bucket_name,
    env=env,
    description="API Gateway and Lambda handlers"
)

# Add dependencies
api_stack.add_dependency(auth_stack)
api_stack.add_dependency(storage_stack)
api_stack.add_dependency(database_stack)

app.synth()
