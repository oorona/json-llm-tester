import requests
import logging
from typing import List, Dict, Any
from app.core.config import settings # Uses updated settings
from app.models import LLMModel

logger = logging.getLogger(__name__)

class LLMServiceError(Exception):
    """Custom exception for LLM service errors."""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

def get_llm_service_headers() -> Dict[str, str]:
    """Helper function to get authorization headers for the LLM service."""
    headers = {'Content-Type': 'application/json'}
    if settings.LLM_SERVICE_API_KEY: # Only add Authorization header if API key is provided
        headers['Authorization'] = f'Bearer {settings.LLM_SERVICE_API_KEY}'
    else:
        logger.info("LLM_SERVICE_API_KEY is not set, proceeding without Authorization header.")
    return headers

async def get_available_models() -> List[LLMModel]:
    """
    Fetches the list of available LLM models from the configured LLM service (e.g., LiteLLM).
    Expected LiteLLM endpoint: /v1/models
    Expected LiteLLM response format: {"data": [{"id": "model_id", ...}, ...], "object": "list"}
    """
    url = f"{settings.LLM_SERVICE_URL}/v1/models" # OpenAI standard endpoint
    logger.info(f"Fetching available models from: {url}")
    try:
        headers = get_llm_service_headers()
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        models_data_response = response.json()
        available_llms = []
        
        # LiteLLM (and OpenAI) format is typically {"data": [...]}
        if isinstance(models_data_response, dict) and "data" in models_data_response and isinstance(models_data_response["data"], list):
            model_list_to_parse = models_data_response["data"]
            logger.info(f"Parsing {len(model_list_to_parse)} model items from 'data' key.")
            
            for model_info in model_list_to_parse:
                if not isinstance(model_info, dict):
                    logger.warning(f"Skipping non-dictionary model item: {model_info}")
                    continue

                model_id = model_info.get("id")
                
                if not model_id:
                    logger.warning(f"Skipping model item due to missing 'id': {model_info}")
                    continue
                
                # For LiteLLM's /v1/models, 'id' is the primary identifier.
                # 'name' might not be present or might be same as 'id'.
                # 'description' is typically not in the basic model list from OpenAI-compatible /v1/models.
                name = model_info.get("name", model_id) # Use 'id' as name if 'name' is not present
                description = model_info.get("description") # Or None if not present

                available_llms.append(LLMModel(
                    model_id=model_id,
                    name=name,
                    description=description # Will be None if not found
                ))
        else:
            logger.warning(f"Unexpected format for models data from {url}. Expected dict with 'data' list. Received: {models_data_response}")

        logger.info(f"Successfully processed model list. Found {len(available_llms)} models.")
        return available_llms

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching models from LLM Service ({url}): {e}")
        raise LLMServiceError(f"Could not connect to LLM service: {e}", status_code=503)
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching models from {url}: {e}", exc_info=True)
        raise LLMServiceError(f"An unexpected error occurred while fetching models: {e}", status_code=500)


async def call_llm_chat_completions(model_id: str, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1024) -> Dict[str, Any]:
    """
    Calls the LLM service chat completions endpoint (OpenAI compatible).
    Expected LiteLLM endpoint: /v1/chat/completions
    """
    url = f"{settings.LLM_SERVICE_URL}/v1/chat/completions" # OpenAI standard endpoint
    headers = get_llm_service_headers()
    
    data = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        # Add other OpenAI compatible parameters as needed e.g. stream: False
    }
    
    logger.info(f"Sending chat completion request to {url} for model {model_id}")
    logger.debug(f"Request data: {data}")

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        response_json = response.json()
        logger.info(f"Received response from chat completion for model {model_id}")
        logger.debug(f"Response JSON: {response_json}")
        return response_json
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling LLM chat completions ({url}) for model {model_id}: {e}")
        if e.response is not None:
            logger.error(f"LLM service response content: {e.response.text}")
            raise LLMServiceError(f"LLM service error: {e.response.status_code} - {e.response.text}", status_code=e.response.status_code)
        raise LLMServiceError(f"Could not connect to LLM service: {e}", status_code=503)
    except Exception as e:
        logger.error(f"An unexpected error occurred during chat completion ({url}) for model {model_id}: {e}", exc_info=True)
        raise LLMServiceError(f"An unexpected error occurred during chat completion: {e}", status_code=500)