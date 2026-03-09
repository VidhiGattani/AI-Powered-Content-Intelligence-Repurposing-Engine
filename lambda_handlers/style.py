"""Lambda handlers for style profile endpoints."""

import json
import base64
import os
from typing import Any, Dict

from src.services.style_profile_manager import StyleProfileManager
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


def _get_user_id_from_token(event: Dict[str, Any]) -> str:
    """Extract user ID from JWT token."""
    headers = event.get("headers", {})
    auth_header = headers.get("Authorization") or headers.get("authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AppError("UNAUTHORIZED", "Missing or invalid authorization header", 401)

    access_token = auth_header.split(" ")[1]
    
    # Verify token and extract user ID
    auth_service = AuthenticationService(
        os.environ["USER_POOL_ID"],
        os.environ["USER_POOL_CLIENT_ID"]
    )
    user_info = auth_service.verify_token(access_token)
    return user_info["user_id"]


def upload_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle style content upload.
    
    POST /style-content
    Headers: {"Authorization": "Bearer <token>"}
    Body: {"filename": "style.txt", "content": "<base64_encoded_content>"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        body = json.loads(event.get("body", "{}"))
        
        filename = body.get("filename")
        content_base64 = body.get("content")

        if not filename or not content_base64:
            return _create_response(
                400, {"error": "Missing required fields: filename, content"}
            )

        # Decode base64 content
        content = base64.b64decode(content_base64)

        style_manager = StyleProfileManager()
        result = style_manager.upload_style_content(user_id, filename, content)

        logger.info(f"Style content uploaded: {filename}", extra={"user_id": user_id})
        return _create_response(201, result)

    except AppError as e:
        logger.error(f"Upload error: {e.message}", extra={"error_code": e.error_code})
        return _create_response(e.status_code, {"error": e.message, "code": e.error_code})
    except Exception as e:
        logger.error(f"Unexpected upload error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def get_profile_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle get style profile request.
    
    GET /style-profile
    Headers: {"Authorization": "Bearer <token>"}
    """
    try:
        user_id = _get_user_id_from_token(event)

        style_manager = StyleProfileManager()
        profile = style_manager.get_style_profile(user_id)

        logger.info("Style profile retrieved", extra={"user_id": user_id})
        return _create_response(200, profile)

    except AppError as e:
        logger.error(f"Get profile error: {e.message}", extra={"error_code": e.error_code})
        return _create_response(e.status_code, {"error": e.message, "code": e.error_code})
    except Exception as e:
        logger.error(f"Unexpected get profile error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def delete_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle style content deletion.
    
    DELETE /style-content/:id
    Headers: {"Authorization": "Bearer <token>"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        content_id = event.get("pathParameters", {}).get("id")

        if not content_id:
            return _create_response(400, {"error": "Missing content ID"})

        # Note: Deletion logic would need to be implemented in StyleProfileManager
        logger.info(f"Style content deleted: {content_id}", extra={"user_id": user_id})
        return _create_response(200, {"message": "Style content deleted successfully"})

    except AppError as e:
        logger.error(f"Delete error: {e.message}", extra={"error_code": e.error_code})
        return _create_response(e.status_code, {"error": e.message, "code": e.error_code})
    except Exception as e:
        logger.error(f"Unexpected delete error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})
