"""Lambda handlers for content endpoints."""

import json
import base64
import os
from typing import Any, Dict

from src.services.content_upload_handler import ContentUploadHandler
from src.services.content_library_service import ContentLibraryService
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
    
    auth_service = AuthenticationService()
    user_info = auth_service.verify_token(access_token)
    return user_info.user_id


def upload_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle content upload.
    
    POST /content
    Headers: {"Authorization": "Bearer <token>"}
    Body: {"filename": "video.mp4", "content": "<base64_encoded_content>"}
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
        from io import BytesIO
        content_bytes = base64.b64decode(content_base64)
        content_file = BytesIO(content_bytes)

        upload_handler_service = ContentUploadHandler()
        result = upload_handler_service.upload_content(user_id, content_file, filename)

        logger.info(f"Content uploaded: {filename}", extra={"user_id": user_id})
        return _create_response(201, result.to_dict())

    except AppError as e:
        logger.error(f"Upload error: {e.message}", extra={"error_code": str(e.error_code)})
        status_code = getattr(e, 'status_code', 500)
        return _create_response(status_code, {"error": e.message, "code": str(e.error_code)})
    except Exception as e:
        logger.error(f"Unexpected upload error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def list_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle content listing.
    
    GET /content?limit=10&offset=0
    Headers: {"Authorization": "Bearer <token>"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        params = event.get("queryStringParameters") or {}
        
        limit = int(params.get("limit", 10))
        offset = int(params.get("offset", 0))

        library_service = ContentLibraryService()
        result = library_service.get_user_content(user_id, limit, offset)

        logger.info("Content listed", extra={"user_id": user_id})
        return _create_response(200, result)

    except AppError as e:
        logger.error(f"List error: {e.message}", extra={"error_code": str(e.error_code)})
        return _create_response(e.status_code, {"error": e.message, "code": str(e.error_code)})
    except Exception as e:
        logger.error(f"Unexpected list error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def get_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle get content by ID.
    
    GET /content/:id
    Headers: {"Authorization": "Bearer <token>"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        content_id = event.get("pathParameters", {}).get("id")

        if not content_id:
            return _create_response(400, {"error": "Missing content ID"})

        library_service = ContentLibraryService()
        # Note: Would need to implement get_content_by_id method
        
        logger.info(f"Content retrieved: {content_id}", extra={"user_id": user_id})
        return _create_response(200, {"message": "Get content not yet implemented"})

    except AppError as e:
        logger.error(f"Get error: {e.message}", extra={"error_code": str(e.error_code)})
        return _create_response(e.status_code, {"error": e.message, "code": str(e.error_code)})
    except Exception as e:
        logger.error(f"Unexpected get error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def delete_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle content deletion.
    
    DELETE /content/:id
    Headers: {"Authorization": "Bearer <token>"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        content_id = event.get("pathParameters", {}).get("id")

        if not content_id:
            return _create_response(400, {"error": "Missing content ID"})

        library_service = ContentLibraryService()
        library_service.delete_content(content_id, user_id)

        logger.info(f"Content deleted: {content_id}", extra={"user_id": user_id})
        return _create_response(200, {"message": "Content deleted successfully"})

    except AppError as e:
        logger.error(f"Delete error: {e.message}", extra={"error_code": str(e.error_code)})
        return _create_response(e.status_code, {"error": e.message, "code": str(e.error_code)})
    except Exception as e:
        logger.error(f"Unexpected delete error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})
