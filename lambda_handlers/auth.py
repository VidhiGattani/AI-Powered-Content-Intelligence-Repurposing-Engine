"""Lambda handlers for authentication endpoints."""

import json
import os
from typing import Any, Dict

from src.services.authentication_service import AuthenticationService
from src.utils.errors import AppError
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        },
        "body": json.dumps(body),
    }


def _get_auth_service() -> AuthenticationService:
    """Get authentication service instance."""
    # The AuthenticationService reads USER_POOL_ID from environment
    # No need to pass it as constructor argument
    return AuthenticationService()


def signup_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle user signup requests.
    
    POST /auth/signup
    Body: {"email": "user@example.com", "password": "password123", "name": "John Doe"}
    """
    try:
        body = json.loads(event.get("body", "{}"))
        email = body.get("email")
        password = body.get("password")

        if not email or not password:
            return _create_response(
                400, {"error": "Missing required fields: email, password"}
            )

        auth_service = _get_auth_service()
        result = auth_service.register_user(email, password)

        logger.info(f"User registered successfully: {email}")
        return _create_response(201, result.to_dict())

    except AppError as e:
        logger.error(f"Signup error: {e.message}", extra={"error_code": str(e.error_code)})
        # Get status code, default to 500 if not available
        status_code = getattr(e, 'status_code', 500)
        return _create_response(status_code, {"error": e.message, "code": str(e.error_code)})
    except Exception as e:
        logger.error(f"Unexpected signup error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def signin_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle user signin requests.
    
    POST /auth/signin
    Body: {"email": "user@example.com", "password": "password123"}
    """
    try:
        body = json.loads(event.get("body", "{}"))
        email = body.get("email")
        password = body.get("password")

        if not email or not password:
            return _create_response(
                400, {"error": "Missing required fields: email, password"}
            )

        auth_service = _get_auth_service()
        result = auth_service.authenticate(email, password)

        logger.info(f"User signed in successfully: {email}")
        return _create_response(200, result.to_dict())

    except AppError as e:
        logger.error(f"Signin error: {e.message}", extra={"error_code": str(e.error_code)})
        # Get status code, default to 500 if not available
        status_code = getattr(e, 'status_code', 500)
        return _create_response(status_code, {"error": e.message, "code": str(e.error_code)})
    except Exception as e:
        logger.error(f"Unexpected signin error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def signout_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle user signout requests.
    
    POST /auth/signout
    Headers: {"Authorization": "Bearer <access_token>"}
    """
    try:
        # Extract token from Authorization header
        headers = event.get("headers", {})
        auth_header = headers.get("Authorization") or headers.get("authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return _create_response(401, {"error": "Missing or invalid authorization header"})

        access_token = auth_header.split(" ")[1]

        auth_service = _get_auth_service()
        # Note: Cognito doesn't have a direct signout API that invalidates tokens
        # Tokens expire naturally. This endpoint is for client-side cleanup.
        
        logger.info("User signed out successfully")
        return _create_response(200, {"message": "Signed out successfully"})

    except Exception as e:
        logger.error(f"Unexpected signout error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def refresh_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle token refresh requests.
    
    POST /auth/refresh
    Body: {"refresh_token": "<refresh_token>"}
    """
    try:
        body = json.loads(event.get("body", "{}"))
        refresh_token = body.get("refresh_token")

        if not refresh_token:
            return _create_response(400, {"error": "Missing required field: refresh_token"})

        # Note: Token refresh would require additional Cognito API calls
        # This is a placeholder for the implementation
        logger.info("Token refresh requested")
        return _create_response(200, {"message": "Token refresh not yet implemented"})

    except Exception as e:
        logger.error(f"Unexpected refresh error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})
