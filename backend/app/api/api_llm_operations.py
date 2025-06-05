# backend/app/api/api_llm_operations.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession # Keep if any endpoint here needs DB directly
from typing import List
import logging

from app.services import llm_service
from app import models as pydantic_models # Pydantic models
# from app.database import get_db_session # Import if DB session is needed

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["LLM Operations"] # Tag for OpenAPI docs
)

@router.get("/models", response_model=List[pydantic_models.LLMModel])
async def list_available_llm_models():
    """
    Lists all available LLM models from the configured LLM service.
    """
    logger.info("Attempting to fetch available LLM models via /models router.")
    try:
        models = await llm_service.get_available_models()
        if not models:
            logger.warning("No models returned from LLM service for /models router.")
        return models
    except llm_service.LLMServiceError as e:
        logger.error(f"LLMServiceError when fetching models for /models router: {str(e)} (Status: {e.status_code})")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error fetching models for /models router.")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching models.")

@router.post("/testing/chat", summary="Test Chat Completions with LLM Service")
async def test_chat_completions_with_llm_service(request: pydantic_models.ChatCompletionRequest):
    """
    An endpoint to test the chat completion functionality with a chosen model via the LLM service.
    """
    logger.info(f"Received chat completion request for model: {request.model_id} via /testing/chat router.")
    try:
        messages_for_llm = [msg.model_dump() for msg in request.messages]
        
        response = await llm_service.call_llm_chat_completions(
            model_id=request.model_id,
            messages=messages_for_llm,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        return response
    except llm_service.LLMServiceError as e:
        logger.error(f"LLMServiceError during chat completion for /testing/chat router: {str(e)} (Status: {e.status_code})")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error during chat completion test for model {request.model_id} via /testing/chat router.")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")