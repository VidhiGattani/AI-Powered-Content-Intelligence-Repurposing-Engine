"""Lambda handlers for SEO endpoints."""

import json
import os
from typing import Any, Dict

from src.services.seo_optimizer import SEOOptimizer
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
    
    auth_service = AuthenticationService(
        os.environ["USER_POOL_ID"],
        os.environ["USER_POOL_CLIENT_ID"]
    )
    user_info = auth_service.verify_token(access_token)
    return user_info["user_id"]


def titles_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle title generation.
    
    POST /seo/titles
    Headers: {"Authorization": "Bearer <token>"}
    Body: {"content": "Content text", "platform": "LINKEDIN"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        body = json.loads(event.get("body", "{}"))
        
        content = body.get("content")
        platform = body.get("platform")

        if not content or not platform:
            return _create_response(
                400, {"error": "Missing required fields: content, platform"}
            )

        seo_optimizer = SEOOptimizer()
        titles = seo_optimizer.generate_titles(content, platform)

        logger.info("Titles generated", extra={"user_id": user_id})
        return _create_response(200, {"titles": titles})

    except AppError as e:
        logger.error(f"Title generation error: {e.message}", extra={"error_code": e.error_code})
        return _create_response(e.status_code, {"error": e.message, "code": e.error_code})
    except Exception as e:
        logger.error(f"Unexpected title generation error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def hashtags_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle hashtag generation.
    
    POST /seo/hashtags
    Headers: {"Authorization": "Bearer <token>"}
    Body: {"content": "Content text", "platform": "TWITTER"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        body = json.loads(event.get("body", "{}"))
        
        content = body.get("content")
        platform = body.get("platform")

        if not content or not platform:
            return _create_response(
                400, {"error": "Missing required fields: content, platform"}
            )

        seo_optimizer = SEOOptimizer()
        hashtags = seo_optimizer.generate_hashtags(content, platform)

        logger.info("Hashtags generated", extra={"user_id": user_id})
        return _create_response(200, {"hashtags": hashtags})

    except AppError as e:
        logger.error(f"Hashtag generation error: {e.message}", extra={"error_code": e.error_code})
        return _create_response(e.status_code, {"error": e.message, "code": e.error_code})
    except Exception as e:
        logger.error(f"Unexpected hashtag generation error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def alttext_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle alt-text generation.
    
    POST /seo/alt-text
    Headers: {"Authorization": "Bearer <token>"}
    Body: {"image_description": "Description of the image"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        body = json.loads(event.get("body", "{}"))
        
        image_description = body.get("image_description")

        if not image_description:
            return _create_response(
                400, {"error": "Missing required field: image_description"}
            )

        seo_optimizer = SEOOptimizer()
        alt_text = seo_optimizer.generate_alt_text(image_description)

        logger.info("Alt-text generated", extra={"user_id": user_id})
        return _create_response(200, {"alt_text": alt_text})

    except AppError as e:
        logger.error(f"Alt-text generation error: {e.message}", extra={"error_code": e.error_code})
        return _create_response(e.status_code, {"error": e.message, "code": e.error_code})
    except Exception as e:
        logger.error(f"Unexpected alt-text generation error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})
