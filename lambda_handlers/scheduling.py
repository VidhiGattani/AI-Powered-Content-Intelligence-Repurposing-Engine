"""Lambda handlers for scheduling endpoints."""

import json
import os
from typing import Any, Dict

from src.services.scheduling_service import SchedulingService
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


def create_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle schedule creation.
    
    POST /schedule
    Headers: {"Authorization": "Bearer <token>"}
    Body: {
        "generated_content_id": "gen123",
        "platform": "LINKEDIN",
        "scheduled_time": "2024-12-01T10:00:00Z",
        "timezone": "America/New_York"
    }
    """
    try:
        user_id = _get_user_id_from_token(event)
        body = json.loads(event.get("body", "{}"))
        
        generated_content_id = body.get("generated_content_id")
        platform = body.get("platform")
        scheduled_time = body.get("scheduled_time")
        timezone = body.get("timezone", "UTC")

        if not generated_content_id or not platform or not scheduled_time:
            return _create_response(
                400, {"error": "Missing required fields: generated_content_id, platform, scheduled_time"}
            )

        scheduling_service = SchedulingService()
        result = scheduling_service.create_schedule(
            user_id, generated_content_id, platform, scheduled_time, timezone
        )

        logger.info(f"Schedule created for {platform}", extra={"user_id": user_id})
        return _create_response(201, result)

    except AppError as e:
        logger.error(f"Schedule creation error: {e.message}", extra={"error_code": e.error_code})
        return _create_response(e.status_code, {"error": e.message, "code": e.error_code})
    except Exception as e:
        logger.error(f"Unexpected schedule creation error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def list_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle schedule listing.
    
    GET /schedule
    Headers: {"Authorization": "Bearer <token>"}
    """
    try:
        user_id = _get_user_id_from_token(event)

        scheduling_service = SchedulingService()
        schedules = scheduling_service.get_user_schedules(user_id)

        logger.info("Schedules listed", extra={"user_id": user_id})
        return _create_response(200, {"schedules": schedules})

    except AppError as e:
        logger.error(f"Schedule listing error: {e.message}", extra={"error_code": e.error_code})
        return _create_response(e.status_code, {"error": e.message, "code": e.error_code})
    except Exception as e:
        logger.error(f"Unexpected schedule listing error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def delete_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle schedule deletion.
    
    DELETE /schedule/:id
    Headers: {"Authorization": "Bearer <token>"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        schedule_id = event.get("pathParameters", {}).get("id")

        if not schedule_id:
            return _create_response(400, {"error": "Missing schedule ID"})

        scheduling_service = SchedulingService()
        scheduling_service.delete_schedule(user_id, schedule_id)

        logger.info(f"Schedule deleted: {schedule_id}", extra={"user_id": user_id})
        return _create_response(200, {"message": "Schedule deleted successfully"})

    except AppError as e:
        logger.error(f"Schedule deletion error: {e.message}", extra={"error_code": e.error_code})
        return _create_response(e.status_code, {"error": e.message, "code": e.error_code})
    except Exception as e:
        logger.error(f"Unexpected schedule deletion error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def optimal_times_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle optimal times recommendation.
    
    GET /schedule/optimal-times?platform=LINKEDIN&timezone=America/New_York
    Headers: {"Authorization": "Bearer <token>"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        params = event.get("queryStringParameters") or {}
        
        platform = params.get("platform")
        timezone = params.get("timezone", "UTC")

        if not platform:
            return _create_response(400, {"error": "Missing required parameter: platform"})

        scheduling_service = SchedulingService()
        optimal_times = scheduling_service.get_optimal_times(platform, timezone)

        logger.info(f"Optimal times retrieved for {platform}", extra={"user_id": user_id})
        return _create_response(200, {"optimal_times": optimal_times})

    except AppError as e:
        logger.error(f"Optimal times error: {e.message}", extra={"error_code": e.error_code})
        return _create_response(e.status_code, {"error": e.message, "code": e.error_code})
    except Exception as e:
        logger.error(f"Unexpected optimal times error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})
