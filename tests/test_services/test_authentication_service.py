"""
Unit tests for AuthenticationService
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from botocore.exceptions import ClientError
import jwt

from src.services.authentication_service import AuthenticationService
from src.models import UserProfile, AuthToken, StyleProfileStatus
from src.utils.errors import (
    AuthenticationError,
    ValidationError,
    ErrorCode
)


class TestAuthenticationService:
    """Test suite for AuthenticationService"""
    
    @pytest.fixture
    def mock_cognito_client(self):
        """Mock Cognito client"""
        return Mock()
    
    @pytest.fixture
    def mock_dynamodb_client(self):
        """Mock DynamoDB client"""
        return Mock()
    
    @pytest.fixture
    def auth_service(self, mock_cognito_client, mock_dynamodb_client):
        """Create AuthenticationService with mocked dependencies"""
        return AuthenticationService(
            cognito_client=mock_cognito_client,
            dynamodb_client=mock_dynamodb_client,
            users_table="test-users-table"
        )
    
    # Tests for register_user()
    
    def test_register_user_success(
        self,
        auth_service,
        mock_cognito_client,
        mock_dynamodb_client
    ):
        """Test successful user registration"""
        # Arrange
        email = "test@example.com"
        password = "SecurePass123!"
        user_sub = "test-user-id-123"
        
        mock_cognito_client.sign_up.return_value = user_sub
        
        # Act
        result = auth_service.register_user(email, password)
        
        # Assert
        assert isinstance(result, UserProfile)
        assert result.user_id == user_sub
        assert result.email == email
        assert result.style_profile_status == StyleProfileStatus.INCOMPLETE
        assert result.style_content_count == 0
        assert result.subscription_tier == "FREE"
        
        # Verify Cognito was called
        mock_cognito_client.sign_up.assert_called_once_with(email, password)
        
        # Verify DynamoDB was called
        mock_dynamodb_client.put_item.assert_called_once()
        call_args = mock_dynamodb_client.put_item.call_args
        assert call_args[1]["table_name"] == "test-users-table"
        assert call_args[1]["item"]["user_id"] == user_sub
        assert call_args[1]["item"]["email"] == email
    
    def test_register_user_invalid_email(self, auth_service):
        """Test registration with invalid email"""
        # Arrange
        invalid_emails = ["", "invalid", "test@", "@example.com", "test@.com"]
        
        for email in invalid_emails:
            # Act & Assert
            with pytest.raises(ValidationError) as exc_info:
                auth_service.register_user(email, "SecurePass123!")
            
            assert exc_info.value.error_code == ErrorCode.MISSING_REQUIRED_FIELD
            assert "email" in exc_info.value.message.lower()
    
    def test_register_user_invalid_password(self, auth_service):
        """Test registration with invalid password"""
        # Arrange
        email = "test@example.com"
        invalid_passwords = ["", "short", "1234567"]  # Less than 8 characters
        
        for password in invalid_passwords:
            # Act & Assert
            with pytest.raises(ValidationError) as exc_info:
                auth_service.register_user(email, password)
            
            assert exc_info.value.error_code == ErrorCode.MISSING_REQUIRED_FIELD
            assert "password" in exc_info.value.message.lower()
    
    def test_register_user_already_exists(
        self,
        auth_service,
        mock_cognito_client
    ):
        """Test registration when user already exists"""
        # Arrange
        email = "existing@example.com"
        password = "SecurePass123!"
        
        error_response = {
            'Error': {
                'Code': 'UsernameExistsException',
                'Message': 'User already exists'
            }
        }
        mock_cognito_client.sign_up.side_effect = ClientError(
            error_response,
            'SignUp'
        )
        
        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.register_user(email, password)
        
        assert exc_info.value.error_code == ErrorCode.INVALID_CREDENTIALS
        assert "already exists" in exc_info.value.message.lower()
    
    def test_register_user_cognito_password_policy_error(
        self,
        auth_service,
        mock_cognito_client
    ):
        """Test registration with password that doesn't meet Cognito policy"""
        # Arrange
        email = "test@example.com"
        password = "weakpass"
        
        error_response = {
            'Error': {
                'Code': 'InvalidPasswordException',
                'Message': 'Password does not meet requirements'
            }
        }
        mock_cognito_client.sign_up.side_effect = ClientError(
            error_response,
            'SignUp'
        )
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            auth_service.register_user(email, password)
        
        assert exc_info.value.error_code == ErrorCode.MISSING_REQUIRED_FIELD
        assert "password" in exc_info.value.message.lower()
    
    # Tests for authenticate()
    
    def test_authenticate_success(
        self,
        auth_service,
        mock_cognito_client
    ):
        """Test successful authentication"""
        # Arrange
        email = "test@example.com"
        password = "SecurePass123!"
        
        mock_tokens = {
            'AccessToken': 'access-token-123',
            'RefreshToken': 'refresh-token-456',
            'IdToken': 'id-token-789',
            'ExpiresIn': 3600
        }
        mock_cognito_client.authenticate.return_value = mock_tokens
        
        # Act
        result = auth_service.authenticate(email, password)
        
        # Assert
        assert isinstance(result, AuthToken)
        assert result.access_token == 'access-token-123'
        assert result.refresh_token == 'refresh-token-456'
        assert result.id_token == 'id-token-789'
        assert result.expires_in == 3600
        assert result.token_type == "Bearer"
        
        # Verify Cognito was called
        mock_cognito_client.authenticate.assert_called_once_with(email, password)
    
    def test_authenticate_invalid_credentials(
        self,
        auth_service,
        mock_cognito_client
    ):
        """Test authentication with invalid credentials"""
        # Arrange
        email = "test@example.com"
        password = "WrongPassword"
        
        error_response = {
            'Error': {
                'Code': 'NotAuthorizedException',
                'Message': 'Incorrect username or password'
            }
        }
        mock_cognito_client.authenticate.side_effect = ClientError(
            error_response,
            'InitiateAuth'
        )
        
        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.authenticate(email, password)
        
        assert exc_info.value.error_code == ErrorCode.INVALID_CREDENTIALS
        assert "invalid" in exc_info.value.message.lower()
    
    def test_authenticate_user_not_found(
        self,
        auth_service,
        mock_cognito_client
    ):
        """Test authentication when user doesn't exist"""
        # Arrange
        email = "nonexistent@example.com"
        password = "SecurePass123!"
        
        error_response = {
            'Error': {
                'Code': 'UserNotFoundException',
                'Message': 'User does not exist'
            }
        }
        mock_cognito_client.authenticate.side_effect = ClientError(
            error_response,
            'InitiateAuth'
        )
        
        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.authenticate(email, password)
        
        assert exc_info.value.error_code == ErrorCode.INVALID_CREDENTIALS
    
    def test_authenticate_user_not_confirmed(
        self,
        auth_service,
        mock_cognito_client
    ):
        """Test authentication when user email not confirmed"""
        # Arrange
        email = "unconfirmed@example.com"
        password = "SecurePass123!"
        
        error_response = {
            'Error': {
                'Code': 'UserNotConfirmedException',
                'Message': 'User is not confirmed'
            }
        }
        mock_cognito_client.authenticate.side_effect = ClientError(
            error_response,
            'InitiateAuth'
        )
        
        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.authenticate(email, password)
        
        assert exc_info.value.error_code == ErrorCode.INVALID_CREDENTIALS
        assert "not confirmed" in exc_info.value.message.lower()
    
    def test_authenticate_missing_credentials(self, auth_service):
        """Test authentication with missing email or password"""
        # Test missing email
        with pytest.raises(ValidationError) as exc_info:
            auth_service.authenticate("", "password")
        assert exc_info.value.error_code == ErrorCode.MISSING_REQUIRED_FIELD
        
        # Test missing password
        with pytest.raises(ValidationError) as exc_info:
            auth_service.authenticate("test@example.com", "")
        assert exc_info.value.error_code == ErrorCode.MISSING_REQUIRED_FIELD
    
    # Tests for verify_token()
    
    def test_verify_token_success(
        self,
        auth_service,
        mock_dynamodb_client
    ):
        """Test successful token verification"""
        # Arrange
        user_sub = "test-user-id-123"
        email = "test@example.com"
        
        # Create a valid token
        exp_time = datetime.utcnow() + timedelta(hours=1)
        token_payload = {
            'sub': user_sub,
            'email': email,
            'exp': int(exp_time.timestamp())
        }
        token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        # Mock DynamoDB response
        user_data = {
            'user_id': user_sub,
            'email': email,
            'created_at': datetime.utcnow().isoformat(),
            'style_profile_status': 'incomplete',
            'style_content_count': 0,
            'subscription_tier': 'FREE'
        }
        mock_dynamodb_client.get_item.return_value = user_data
        
        # Act
        result = auth_service.verify_token(token)
        
        # Assert
        assert isinstance(result, UserProfile)
        assert result.user_id == user_sub
        assert result.email == email
        
        # Verify DynamoDB was called
        mock_dynamodb_client.get_item.assert_called_once()
        call_args = mock_dynamodb_client.get_item.call_args
        assert call_args[1]["table_name"] == "test-users-table"
        assert call_args[1]["key"]["user_id"] == user_sub
    
    def test_verify_token_expired(self, auth_service):
        """Test verification of expired token"""
        # Arrange
        user_sub = "test-user-id-123"
        
        # Create an expired token
        exp_time = datetime.utcnow() - timedelta(hours=1)
        token_payload = {
            'sub': user_sub,
            'exp': int(exp_time.timestamp())
        }
        token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.verify_token(token)
        
        assert exc_info.value.error_code == ErrorCode.EXPIRED_TOKEN
        assert "expired" in exc_info.value.message.lower()
    
    def test_verify_token_invalid_format(self, auth_service):
        """Test verification of invalid token format"""
        # Arrange
        invalid_token = "invalid.token.format"
        
        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.verify_token(invalid_token)
        
        assert exc_info.value.error_code == ErrorCode.INVALID_CREDENTIALS
        assert "invalid" in exc_info.value.message.lower()
    
    def test_verify_token_missing_user_id(self, auth_service):
        """Test verification of token without user identifier"""
        # Arrange
        token_payload = {
            'email': 'test@example.com',
            'exp': int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.verify_token(token)
        
        assert exc_info.value.error_code == ErrorCode.INVALID_CREDENTIALS
    
    def test_verify_token_user_not_found(
        self,
        auth_service,
        mock_dynamodb_client
    ):
        """Test verification when user profile doesn't exist"""
        # Arrange
        user_sub = "nonexistent-user-id"
        
        token_payload = {
            'sub': user_sub,
            'exp': int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        # Mock DynamoDB to return None
        mock_dynamodb_client.get_item.return_value = None
        
        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.verify_token(token)
        
        assert exc_info.value.error_code == ErrorCode.USER_NOT_FOUND
        assert "not found" in exc_info.value.message.lower()
    
    def test_verify_token_missing_token(self, auth_service):
        """Test verification with missing token"""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            auth_service.verify_token("")
        
        assert exc_info.value.error_code == ErrorCode.MISSING_REQUIRED_FIELD
        assert "token" in exc_info.value.message.lower()
    
    def test_verify_token_with_cognito_username(
        self,
        auth_service,
        mock_dynamodb_client
    ):
        """Test verification with cognito:username instead of sub"""
        # Arrange
        user_sub = "test-user-id-123"
        email = "test@example.com"
        
        # Create token with cognito:username
        token_payload = {
            'cognito:username': user_sub,
            'email': email,
            'exp': int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        # Mock DynamoDB response
        user_data = {
            'user_id': user_sub,
            'email': email,
            'created_at': datetime.utcnow().isoformat(),
            'style_profile_status': 'incomplete',
            'style_content_count': 0,
            'subscription_tier': 'FREE'
        }
        mock_dynamodb_client.get_item.return_value = user_data
        
        # Act
        result = auth_service.verify_token(token)
        
        # Assert
        assert isinstance(result, UserProfile)
        assert result.user_id == user_sub
    
    # Test email validation helper
    
    def test_is_valid_email(self, auth_service):
        """Test email validation helper method"""
        # Valid emails
        valid_emails = [
            "test@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "123@example.com"
        ]
        for email in valid_emails:
            assert auth_service._is_valid_email(email) is True
        
        # Invalid emails
        invalid_emails = [
            "",
            "invalid",
            "test@",
            "@example.com",
            "test@.com",
            "test..user@example.com"
        ]
        for email in invalid_emails:
            assert auth_service._is_valid_email(email) is False
