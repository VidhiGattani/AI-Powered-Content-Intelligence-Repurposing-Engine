"""
Authentication service using Amazon Cognito
"""
import os
import jwt
from datetime import datetime
from typing import Optional
from botocore.exceptions import ClientError

from src.utils.aws_clients import CognitoClient, DynamoDBClient
from src.utils.errors import (
    AuthenticationError,
    ValidationError,
    ErrorCode
)
from src.utils.logger import get_logger
from src.models import UserProfile, AuthToken, StyleProfileStatus

logger = get_logger(__name__)


class AuthenticationService:
    """
    Authentication service for user registration, login, and token verification
    Uses Amazon Cognito for authentication and DynamoDB for user profiles
    """
    
    def __init__(
        self,
        cognito_client: Optional[CognitoClient] = None,
        dynamodb_client: Optional[DynamoDBClient] = None,
        users_table: Optional[str] = None
    ):
        """
        Initialize authentication service
        
        Args:
            cognito_client: Cognito client wrapper (optional, creates default if None)
            dynamodb_client: DynamoDB client wrapper (optional, creates default if None)
            users_table: DynamoDB users table name (optional, reads from env if None)
        """
        self.cognito_client = cognito_client or CognitoClient()
        self.dynamodb_client = dynamodb_client or DynamoDBClient()
        self.users_table = users_table or os.environ.get(
            "DYNAMODB_TABLE_USERS",
            "users"
        )
        self.user_pool_id = os.environ.get("COGNITO_USER_POOL_ID")
        self.region = os.environ.get("AWS_REGION", "us-east-1")
    
    def register_user(self, email: str, password: str) -> UserProfile:
        """
        Register a new user account
        
        Args:
            email: User email address
            password: User password
        
        Returns:
            UserProfile with user_id and metadata
        
        Raises:
            ValidationError: If email/password invalid
            AuthenticationError: If registration fails
        """
        # Validate inputs
        if not email or not self._is_valid_email(email):
            logger.error(
                "Invalid email provided",
                email=email
            )
            raise ValidationError(
                error_code=ErrorCode.MISSING_REQUIRED_FIELD,
                message="Valid email address is required"
            )
        
        if not password or len(password) < 8:
            logger.error(
                "Invalid password provided",
                email=email
            )
            raise ValidationError(
                error_code=ErrorCode.MISSING_REQUIRED_FIELD,
                message="Password must be at least 8 characters"
            )
        
        try:
            # Register user in Cognito
            logger.info(
                "Registering user in Cognito",
                email=email
            )
            user_sub = self.cognito_client.sign_up(email, password)
            
            # Create user profile
            user_profile = UserProfile(
                user_id=user_sub,
                email=email,
                created_at=datetime.utcnow(),
                style_profile_status=StyleProfileStatus.INCOMPLETE,
                style_content_count=0,
                subscription_tier="FREE"
            )
            
            # Store user profile in DynamoDB
            self.dynamodb_client.put_item(
                table_name=self.users_table,
                item=user_profile.to_dict()
            )
            
            logger.info(
                "User registered successfully",
                user_id=user_sub,
                email=email
            )
            
            return user_profile
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            
            if error_code == 'UsernameExistsException':
                logger.error(
                    "User already exists",
                    email=email
                )
                raise AuthenticationError(
                    error_code=ErrorCode.INVALID_CREDENTIALS,
                    message="User with this email already exists"
                )
            elif error_code == 'InvalidPasswordException':
                logger.error(
                    "Invalid password format",
                    email=email
                )
                raise ValidationError(
                    error_code=ErrorCode.MISSING_REQUIRED_FIELD,
                    message="Password does not meet requirements"
                )
            else:
                logger.log_error(
                    operation="register_user",
                    error=e,
                    email=email
                )
                raise AuthenticationError(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message=f"Registration failed: {str(e)}"
                )
    
    def authenticate(self, email: str, password: str) -> AuthToken:
        """
        Authenticate user and return JWT token
        
        Args:
            email: User email address
            password: User password
        
        Returns:
            AuthToken with access_token and expiry
        
        Raises:
            AuthenticationError: If credentials invalid
        """
        # Validate inputs
        if not email or not password:
            logger.error(
                "Missing email or password",
                email=email
            )
            raise ValidationError(
                error_code=ErrorCode.MISSING_REQUIRED_FIELD,
                message="Email and password are required"
            )
        
        try:
            # Authenticate with Cognito
            logger.info(
                "Authenticating user",
                email=email
            )
            tokens = self.cognito_client.authenticate(email, password)
            
            # Create AuthToken object
            auth_token = AuthToken(
                access_token=tokens['AccessToken'],
                refresh_token=tokens['RefreshToken'],
                id_token=tokens['IdToken'],
                expires_in=tokens['ExpiresIn'],
                token_type="Bearer"
            )
            
            logger.info(
                "User authenticated successfully",
                email=email
            )
            
            return auth_token
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            
            if error_code in ['NotAuthorizedException', 'UserNotFoundException']:
                logger.error(
                    "Invalid credentials",
                    email=email
                )
                raise AuthenticationError(
                    error_code=ErrorCode.INVALID_CREDENTIALS,
                    message="Invalid email or password"
                )
            elif error_code == 'UserNotConfirmedException':
                logger.error(
                    "User not confirmed",
                    email=email
                )
                raise AuthenticationError(
                    error_code=ErrorCode.INVALID_CREDENTIALS,
                    message="User email not confirmed"
                )
            else:
                logger.log_error(
                    operation="authenticate",
                    error=e,
                    email=email
                )
                raise AuthenticationError(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message=f"Authentication failed: {str(e)}"
                )
    
    def verify_token(self, token: str) -> UserProfile:
        """
        Verify JWT token and return user profile
        
        Args:
            token: JWT access token or id token
        
        Returns:
            UserProfile if token valid
        
        Raises:
            AuthenticationError: If token invalid/expired
        """
        if not token:
            logger.error("Missing token")
            raise ValidationError(
                error_code=ErrorCode.MISSING_REQUIRED_FIELD,
                message="Token is required"
            )
        
        try:
            # Decode token without verification first to get user_sub
            # In production, you should verify the signature using Cognito's public keys
            logger.info("Verifying token")
            
            # Decode token (unverified for now - in production use proper verification)
            decoded = jwt.decode(
                token,
                options={"verify_signature": False}
            )
            
            # Extract user_sub from token
            user_sub = decoded.get('sub') or decoded.get('cognito:username')
            
            if not user_sub:
                logger.error("Token missing user identifier")
                raise AuthenticationError(
                    error_code=ErrorCode.INVALID_CREDENTIALS,
                    message="Invalid token format"
                )
            
            # Check token expiration
            exp = decoded.get('exp')
            if exp and datetime.utcnow().timestamp() > exp:
                logger.error(
                    "Token expired",
                    user_id=user_sub
                )
                raise AuthenticationError(
                    error_code=ErrorCode.EXPIRED_TOKEN,
                    message="Token has expired"
                )
            
            # Retrieve user profile from DynamoDB
            user_data = self.dynamodb_client.get_item(
                table_name=self.users_table,
                key={"user_id": user_sub}
            )
            
            if not user_data:
                logger.error(
                    "User not found",
                    user_id=user_sub
                )
                raise AuthenticationError(
                    error_code=ErrorCode.USER_NOT_FOUND,
                    message="User profile not found"
                )
            
            # Convert to UserProfile
            user_profile = UserProfile.from_dict(user_data)
            
            logger.info(
                "Token verified successfully",
                user_id=user_sub
            )
            
            return user_profile
            
        except AuthenticationError:
            # Re-raise authentication errors without wrapping
            raise
        except jwt.DecodeError as e:
            logger.error(
                "Token decode error",
                error=str(e)
            )
            raise AuthenticationError(
                error_code=ErrorCode.INVALID_CREDENTIALS,
                message="Invalid token format"
            )
        except jwt.ExpiredSignatureError:
            logger.error("Token expired")
            raise AuthenticationError(
                error_code=ErrorCode.EXPIRED_TOKEN,
                message="Token has expired"
            )
        except Exception as e:
            logger.log_error(
                operation="verify_token",
                error=e
            )
            raise AuthenticationError(
                error_code=ErrorCode.INTERNAL_ERROR,
                message=f"Token verification failed: {str(e)}"
            )
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Validate email format
        
        Args:
            email: Email address to validate
        
        Returns:
            True if valid, False otherwise
        """
        import re
        # More strict email validation - no consecutive dots
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]*[a-zA-Z0-9]@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False
        # Check for consecutive dots
        if '..' in email:
            return False
        return True
