"""
Storage Stack - S3 Buckets for Content Repurposing Platform
"""
from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_s3 as s3,
)
from constructs import Construct


class StorageStack(Stack):
    """Creates S3 buckets for style vault, original content, transcripts, and generated content"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Style Vault - stores user's past content for style learning
        self.style_vault_bucket = s3.Bucket(
            self,
            "StyleVaultBucket",
            bucket_name=f"style-vault-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    noncurrent_version_expiration=Duration.days(90)
                )
            ]
        )

        # Original Content - stores uploaded content for repurposing
        self.original_content_bucket = s3.Bucket(
            self,
            "OriginalContentBucket",
            bucket_name=f"original-content-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=False,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ArchiveOldContent",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ]
        )

        # Transcripts - stores transcription results
        self.transcripts_bucket = s3.Bucket(
            self,
            "TranscriptsBucket",
            bucket_name=f"transcripts-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=False,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ArchiveTranscripts",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ]
        )

        # Generated Content - stores AI-generated posts
        self.generated_content_bucket = s3.Bucket(
            self,
            "GeneratedContentBucket",
            bucket_name=f"generated-content-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldGeneratedContent",
                    expiration=Duration.days(365),
                    noncurrent_version_expiration=Duration.days(30)
                )
            ]
        )
