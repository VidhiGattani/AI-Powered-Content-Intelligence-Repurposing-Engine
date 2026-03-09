"""
AWS client wrappers with retry logic and error handling
"""
import boto3
import os
from typing import Optional, Any, Dict
from botocore.config import Config
from botocore.exceptions import ClientError
from .logger import get_logger
from .errors import ExternalServiceError, ErrorCode

logger = get_logger(__name__)


class AWSClientWrapper:
    """Base class for AWS client wrappers with retry logic"""
    
    def __init__(self, service_name: str, region: Optional[str] = None):
        self.service_name = service_name
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        
        # Configure retry strategy
        config = Config(
            region_name=self.region,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            }
        )
        
        self.client = boto3.client(service_name, config=config)
    
    def _handle_client_error(
        self,
        error: ClientError,
        operation: str,
        **context: Any
    ) -> None:
        """Handle boto3 client errors"""
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        error_message = error.response.get('Error', {}).get('Message', str(error))
        
        logger.log_error(
            operation=f"{self.service_name}.{operation}",
            error=error,
            error_code=error_code,
            **context
        )
        
        raise ExternalServiceError(
            error_code=self._map_error_code(error_code),
            message=f"{self.service_name} error: {error_message}",
            details={"aws_error_code": error_code, **context}
        )
    
    def _map_error_code(self, aws_error_code: str) -> ErrorCode:
        """Map AWS error codes to platform error codes"""
        error_map = {
            'ThrottlingException': ErrorCode.RATE_LIMIT_EXCEEDED,
            'ServiceUnavailable': ErrorCode.BEDROCK_UNAVAILABLE,
            'AccessDenied': ErrorCode.INSUFFICIENT_PERMISSIONS,
            'NoSuchKey': ErrorCode.CONTENT_NOT_FOUND,
            'ResourceNotFoundException': ErrorCode.CONTENT_NOT_FOUND,
        }
        return error_map.get(aws_error_code, ErrorCode.INTERNAL_ERROR)


class S3Client(AWSClientWrapper):
    """S3 client wrapper with retry logic"""
    
    def __init__(self, region: Optional[str] = None):
        super().__init__("s3", region)
    
    def upload_file(
        self,
        file_content: bytes,
        bucket: str,
        key: str,
        content_type: Optional[str] = None
    ) -> str:
        """Upload file to S3 with encryption"""
        try:
            extra_args = {
                'ServerSideEncryption': 'AES256'
            }
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.client.put_object(
                Bucket=bucket,
                Key=key,
                Body=file_content,
                **extra_args
            )
            
            s3_uri = f"s3://{bucket}/{key}"
            logger.info(
                "File uploaded to S3",
                bucket=bucket,
                key=key,
                size=len(file_content)
            )
            return s3_uri
            
        except ClientError as e:
            self._handle_client_error(e, "upload_file", bucket=bucket, key=key)
    
    def download_file(self, bucket: str, key: str) -> bytes:
        """Download file from S3"""
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            logger.info(
                "File downloaded from S3",
                bucket=bucket,
                key=key,
                size=len(content)
            )
            return content
            
        except ClientError as e:
            self._handle_client_error(e, "download_file", bucket=bucket, key=key)
    
    def delete_file(self, bucket: str, key: str) -> None:
        """Delete file from S3"""
        try:
            self.client.delete_object(Bucket=bucket, Key=key)
            logger.info("File deleted from S3", bucket=bucket, key=key)
            
        except ClientError as e:
            self._handle_client_error(e, "delete_file", bucket=bucket, key=key)
    
    def check_encryption(self, bucket: str, key: str) -> bool:
        """Check if S3 object has encryption enabled"""
        try:
            response = self.client.head_object(Bucket=bucket, Key=key)
            encryption = response.get('ServerSideEncryption')
            return encryption is not None
            
        except ClientError as e:
            self._handle_client_error(e, "check_encryption", bucket=bucket, key=key)


class DynamoDBClient(AWSClientWrapper):
    """DynamoDB client wrapper with retry logic"""
    
    def __init__(self, region: Optional[str] = None):
        super().__init__("dynamodb", region)
        self.resource = boto3.resource("dynamodb", region_name=self.region)
    
    def put_item(self, table_name: str, item: Dict[str, Any]) -> None:
        """Put item in DynamoDB table"""
        try:
            table = self.resource.Table(table_name)
            table.put_item(Item=item)
            
            logger.info(
                "Item stored in DynamoDB",
                table=table_name,
                item_keys=list(item.keys())
            )
            
        except ClientError as e:
            self._handle_client_error(e, "put_item", table=table_name)
    
    def get_item(
        self,
        table_name: str,
        key: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Get item from DynamoDB table"""
        try:
            table = self.resource.Table(table_name)
            response = table.get_item(Key=key)
            
            item = response.get('Item')
            logger.info(
                "Item retrieved from DynamoDB",
                table=table_name,
                found=item is not None
            )
            return item
            
        except ClientError as e:
            self._handle_client_error(e, "get_item", table=table_name)
    
    def query(
        self,
        table_name: str,
        key_condition_expression: str,
        expression_attribute_values: Dict[str, Any],
        index_name: Optional[str] = None
    ) -> list:
        """Query DynamoDB table"""
        try:
            table = self.resource.Table(table_name)
            
            kwargs = {
                'KeyConditionExpression': key_condition_expression,
                'ExpressionAttributeValues': expression_attribute_values
            }
            if index_name:
                kwargs['IndexName'] = index_name
            
            response = table.query(**kwargs)
            items = response.get('Items', [])
            
            logger.info(
                "Query executed on DynamoDB",
                table=table_name,
                index=index_name,
                count=len(items)
            )
            return items
            
        except ClientError as e:
            self._handle_client_error(e, "query", table=table_name)
    
    def update_item(
        self,
        table_name: str,
        key: Dict[str, Any],
        update_expression: str,
        expression_attribute_values: Dict[str, Any]
    ) -> None:
        """Update item in DynamoDB table"""
        try:
            table = self.resource.Table(table_name)
            table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            
            logger.info(
                "Item updated in DynamoDB",
                table=table_name
            )
            
        except ClientError as e:
            self._handle_client_error(e, "update_item", table=table_name)


class BedrockClient(AWSClientWrapper):
    """Bedrock client wrapper with retry logic"""
    
    def __init__(self, region: Optional[str] = None):
        super().__init__("bedrock-runtime", region)
    
    def invoke_model(
        self,
        model_id: str,
        body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invoke Bedrock model"""
        try:
            import json
            
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            logger.info(
                "Bedrock model invoked",
                model_id=model_id
            )
            return response_body
            
        except ClientError as e:
            self._handle_client_error(e, "invoke_model", model_id=model_id)


class TranscribeClient(AWSClientWrapper):
    """Transcribe client wrapper with retry logic"""
    
    def __init__(self, region: Optional[str] = None):
        super().__init__("transcribe", region)
    
    def start_transcription_job(
        self,
        job_name: str,
        media_uri: str,
        media_format: str,
        output_bucket: str
    ) -> str:
        """Start transcription job"""
        try:
            response = self.client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': media_uri},
                MediaFormat=media_format,
                LanguageCode='en-US',
                OutputBucketName=output_bucket
            )
            
            job_name = response['TranscriptionJob']['TranscriptionJobName']
            
            logger.info(
                "Transcription job started",
                job_name=job_name,
                media_uri=media_uri
            )
            return job_name
            
        except ClientError as e:
            self._handle_client_error(
                e,
                "start_transcription_job",
                job_name=job_name
            )
    
    def get_transcription_job(self, job_name: str) -> Dict[str, Any]:
        """Get transcription job status"""
        try:
            response = self.client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            
            job = response['TranscriptionJob']
            
            logger.info(
                "Transcription job status retrieved",
                job_name=job_name,
                status=job['TranscriptionJobStatus']
            )
            return job
            
        except ClientError as e:
            self._handle_client_error(
                e,
                "get_transcription_job",
                job_name=job_name
            )


class BedrockAgentRuntimeClient(AWSClientWrapper):
    """Bedrock Agent Runtime client for Knowledge Base operations"""
    
    def __init__(self, region: Optional[str] = None):
        super().__init__("bedrock-agent-runtime", region)
        self.knowledge_base_id = os.environ.get("KNOWLEDGE_BASE_ID")
    
    def retrieve(
        self,
        query_text: str,
        retrieval_query_embedding: list,
        number_of_results: int = 3
    ) -> list:
        """Retrieve documents from Knowledge Base"""
        try:
            response = self.client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={
                    'text': query_text,
                    'vector': retrieval_query_embedding
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': number_of_results
                    }
                }
            )
            
            results = response.get('retrievalResults', [])
            
            logger.info(
                "Knowledge Base retrieval completed",
                knowledge_base_id=self.knowledge_base_id,
                results_count=len(results)
            )
            return results
            
        except ClientError as e:
            self._handle_client_error(
                e,
                "retrieve",
                knowledge_base_id=self.knowledge_base_id
            )


class CognitoClient(AWSClientWrapper):
    """Cognito client wrapper with retry logic"""
    
    def __init__(self, region: Optional[str] = None):
        super().__init__("cognito-idp", region)
        self.user_pool_id = os.environ.get("COGNITO_USER_POOL_ID")
        self.client_id = os.environ.get("COGNITO_USER_POOL_CLIENT_ID")
    
    def sign_up(self, email: str, password: str) -> str:
        """Sign up new user"""
        try:
            response = self.client.sign_up(
                ClientId=self.client_id,
                Username=email,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email}
                ]
            )
            
            user_sub = response['UserSub']
            
            logger.info(
                "User signed up",
                email=email,
                user_sub=user_sub
            )
            return user_sub
            
        except ClientError as e:
            self._handle_client_error(e, "sign_up", email=email)
    
    def authenticate(self, email: str, password: str) -> Dict[str, str]:
        """Authenticate user"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password
                }
            )
            
            tokens = response['AuthenticationResult']
            
            logger.info(
                "User authenticated",
                email=email
            )
            return tokens
            
        except ClientError as e:
            self._handle_client_error(e, "authenticate", email=email)
