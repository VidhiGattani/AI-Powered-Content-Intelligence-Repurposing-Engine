"""Lambda handlers for content generation endpoints."""

import json
import os
import random
from typing import Any, Dict

from src.services.content_generation_orchestrator import ContentGenerationOrchestrator
from src.services.content_editing_service import ContentEditingService
from src.services.authentication_service import AuthenticationService
from src.services.content_library_service import ContentLibraryService
from src.services.topic_extraction_service import TopicExtractionService
from src.utils.aws_clients import DynamoDBClient
from src.models.enums import Platform
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


def generate_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle initial content generation.
    
    POST /generate
    Headers: {"Authorization": "Bearer <token>"}
    Body: {"content_id": "content123", "platforms": ["LINKEDIN", "TWITTER"]}
    """
    try:
        user_id = _get_user_id_from_token(event)
        body = json.loads(event.get("body", "{}"))
        
        content_id = body.get("content_id")
        platforms = body.get("platforms", [])

        if not content_id or not platforms:
            return _create_response(
                400, {"error": "Missing required fields: content_id, platforms"}
            )

        # Get content from database
        content_service = ContentLibraryService()
        content = content_service.get_content(user_id, content_id)
        
        if not content:
            return _create_response(404, {"error": "Content not found"})
        
        # Get content text (transcript or original text)
        # For PDFs, try to extract text from S3
        content_text = getattr(content, 'transcript', None) or getattr(content, 'content_text', None)
        
        # If no text content, try to extract from PDF in S3
        if not content_text and content.content_type == 'application/pdf':
            try:
                logger.info(f"Attempting to extract text from PDF: {content.s3_uri}")
                from src.utils.aws_clients import S3Client
                import PyPDF2
                from io import BytesIO
                
                # Parse S3 URI
                s3_uri = content.s3_uri
                if s3_uri.startswith("s3://"):
                    parts = s3_uri[5:].split("/", 1)
                    if len(parts) == 2:
                        bucket, key = parts
                        
                        # Download PDF from S3
                        s3_client = S3Client()
                        pdf_bytes = s3_client.client.get_object(Bucket=bucket, Key=key)['Body'].read()
                        
                        # Extract text from PDF
                        pdf_file = BytesIO(pdf_bytes)
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        
                        extracted_text = ""
                        for page in pdf_reader.pages:
                            extracted_text += page.extract_text() + "\n"
                        
                        if extracted_text.strip():
                            content_text = extracted_text
                            logger.info(f"Successfully extracted {len(content_text)} characters from PDF")
                        else:
                            logger.warning("PDF text extraction returned empty string")
            except Exception as pdf_error:
                logger.warning(f"Failed to extract PDF text: {str(pdf_error)}")
        
        if not content_text:
            # Fallback: use filename as content description
            content_text = f"Content about: {content.filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ')}"
            logger.info(f"Using filename as content: {content_text}")
        
        # Extract topics - handle short content gracefully
        from src.services.topic_extraction_service import Topic
        topic_service = TopicExtractionService()
        try:
            topic_result = topic_service.extract_topics(content_id, content_text)
            topics = topic_result.topics
        except Exception as topic_error:
            # If topic extraction fails (e.g., content too short), use filename as single topic
            logger.warning(f"Topic extraction failed, using filename as topic: {str(topic_error)}")
            topics = [Topic(
                name=content.filename.replace('.pdf', '').replace('_', ' ').replace('-', ' '),
                description=f"Content about {content.filename}",
                relevance_score=1.0
            )]
        
        # Convert platform strings to enum
        platform_enums = []
        for p in platforms:
            try:
                platform_enums.append(Platform[p])
            except KeyError:
                return _create_response(400, {"error": f"Invalid platform: {p}"})
        
        # Generate content
        orchestrator = ContentGenerationOrchestrator()
        results = orchestrator.generate_for_platforms(
            user_id=user_id,
            content_id=content_id,
            platforms=platform_enums,
            original_content=content_text,
            topics=topics
        )
        
        # Format response
        formatted_results = {}
        for platform, generated in results.items():
            formatted_results[platform.value] = {
                "generated_id": generated.generation_id,
                "text": generated.content_text,
                "status": "success"
            }
        
        response = {
            "generation_id": list(results.values())[0].generation_id if results else None,
            "results": formatted_results
        }

        logger.info(f"Content generated for {len(platforms)} platforms", extra={"user_id": user_id})
        return _create_response(201, response)

    except AppError as e:
        logger.error(f"Generation error: {e.message}", extra={"error_code": str(e.error_code)})
        status_code = getattr(e, 'status_code', 500)
        return _create_response(status_code, {"error": e.message, "code": str(e.error_code)})
    except Exception as e:
        logger.error(f"Unexpected generation error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def regenerate_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle content regeneration.
    
    POST /regenerate/:id
    Headers: {"Authorization": "Bearer <token>"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        generated_id = event.get("pathParameters", {}).get("id")

        if not generated_id:
            return _create_response(400, {"error": "Missing generated content ID"})

        # Get generated content metadata from DynamoDB
        dynamodb = DynamoDBClient()
        generated_item = dynamodb.get_item(
            table_name="generated_content",
            key={"generation_id": generated_id}
        )
        
        if not generated_item:
            return _create_response(404, {"error": "Generated content not found"})
        
        content_id = generated_item.get("content_id")
        platform_str = generated_item.get("platform")
        
        if not content_id or not platform_str:
            return _create_response(400, {"error": "Invalid generated content metadata"})
        
        try:
            platform = Platform[platform_str]
        except KeyError:
            return _create_response(400, {"error": f"Invalid platform: {platform_str}"})
        
        # Get original content
        content_service = ContentLibraryService()
        content = content_service.get_content(user_id, content_id)
        
        if not content:
            return _create_response(404, {"error": "Original content not found"})
        
        # Get content text
        content_text = getattr(content, 'transcript', None) or getattr(content, 'content_text', None)
        
        # If no text content, try to extract from PDF in S3
        if not content_text and content.content_type == 'application/pdf':
            try:
                logger.info(f"Attempting to extract text from PDF: {content.s3_uri}")
                from src.utils.aws_clients import S3Client
                import PyPDF2
                from io import BytesIO
                
                # Parse S3 URI
                s3_uri = content.s3_uri
                if s3_uri.startswith("s3://"):
                    parts = s3_uri[5:].split("/", 1)
                    if len(parts) == 2:
                        bucket, key = parts
                        
                        # Download PDF from S3
                        s3_client = S3Client()
                        pdf_bytes = s3_client.client.get_object(Bucket=bucket, Key=key)['Body'].read()
                        
                        # Extract text from PDF
                        pdf_file = BytesIO(pdf_bytes)
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        
                        extracted_text = ""
                        for page in pdf_reader.pages:
                            extracted_text += page.extract_text() + "\n"
                        
                        if extracted_text.strip():
                            content_text = extracted_text
                            logger.info(f"Successfully extracted {len(content_text)} characters from PDF")
                        else:
                            logger.warning("PDF text extraction returned empty string")
            except Exception as pdf_error:
                logger.warning(f"Failed to extract PDF text: {str(pdf_error)}")
        
        if not content_text:
            # Fallback: use filename as content description
            content_text = f"Content about: {content.filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ')}"
            logger.info(f"Using filename as content: {content_text}")
        
        # Extract topics - handle short content gracefully
        from src.services.topic_extraction_service import Topic
        topic_service = TopicExtractionService()
        try:
            topic_result = topic_service.extract_topics(content_id, content_text)
            topics = topic_result.topics
        except Exception as topic_error:
            # If topic extraction fails (e.g., content too short), use filename as single topic
            logger.warning(f"Topic extraction failed, using filename as topic: {str(topic_error)}")
            topics = [Topic(
                name=content.filename.replace('.pdf', '').replace('_', ' ').replace('-', ' '),
                description=f"Content about {content.filename}",
                relevance_score=1.0
            )]
        
        # Regenerate with different seed
        seed = random.randint(1, 10000)
        
        orchestrator = ContentGenerationOrchestrator()
        generated = orchestrator.regenerate_content(
            user_id=user_id,
            content_id=content_id,
            platform=platform,
            original_content=content_text,
            topics=topics,
            seed=seed
        )
        
        response = {
            "generated_id": generated.generation_id,
            "text": generated.content_text,
            "platform": platform.value,
            "version": generated.version,
            "status": "success"
        }

        logger.info(f"Content regenerated: {generated_id}", extra={"user_id": user_id})
        return _create_response(201, response)

    except AppError as e:
        logger.error(f"Regeneration error: {e.message}", extra={"error_code": str(e.error_code)})
        status_code = getattr(e, 'status_code', 500)
        return _create_response(status_code, {"error": e.message, "code": str(e.error_code)})
    except Exception as e:
        logger.error(f"Unexpected regeneration error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def get_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle get generated content.
    
    GET /generated/:id
    Headers: {"Authorization": "Bearer <token>"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        generated_id = event.get("pathParameters", {}).get("id")

        if not generated_id:
            return _create_response(400, {"error": "Missing generated content ID"})

        # Note: Would need to implement get method in orchestrator
        logger.info(f"Generated content retrieved: {generated_id}", extra={"user_id": user_id})
        return _create_response(200, {"message": "Get generated content not yet implemented"})

    except AppError as e:
        logger.error(f"Get error: {e.message}", extra={"error_code": str(e.error_code)})
        return _create_response(e.status_code, {"error": e.message, "code": str(e.error_code)})
    except Exception as e:
        logger.error(f"Unexpected get error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def edit_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle content editing.
    
    PUT /generated/:id/edit
    Headers: {"Authorization": "Bearer <token>"}
    Body: {"edited_text": "New content text"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        generated_id = event.get("pathParameters", {}).get("id")
        body = json.loads(event.get("body", "{}"))
        
        edited_text = body.get("edited_text")

        if not generated_id or not edited_text:
            return _create_response(
                400, {"error": "Missing required fields: generated_id, edited_text"}
            )

        editing_service = ContentEditingService()
        result = editing_service.edit_content(user_id, generated_id, edited_text)

        logger.info(f"Content edited: {generated_id}", extra={"user_id": user_id})
        return _create_response(200, result)

    except AppError as e:
        logger.error(f"Edit error: {e.message}", extra={"error_code": str(e.error_code)})
        return _create_response(e.status_code, {"error": e.message, "code": str(e.error_code)})
    except Exception as e:
        logger.error(f"Unexpected edit error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})


def approve_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle content approval.
    
    POST /generated/:id/approve
    Headers: {"Authorization": "Bearer <token>"}
    """
    try:
        user_id = _get_user_id_from_token(event)
        generated_id = event.get("pathParameters", {}).get("id")

        if not generated_id:
            return _create_response(400, {"error": "Missing generated content ID"})

        editing_service = ContentEditingService()
        result = editing_service.approve_content(user_id, generated_id)

        logger.info(f"Content approved: {generated_id}", extra={"user_id": user_id})
        return _create_response(200, result)

    except AppError as e:
        logger.error(f"Approval error: {e.message}", extra={"error_code": str(e.error_code)})
        return _create_response(e.status_code, {"error": e.message, "code": str(e.error_code)})
    except Exception as e:
        logger.error(f"Unexpected approval error: {str(e)}")
        return _create_response(500, {"error": "Internal server error"})
