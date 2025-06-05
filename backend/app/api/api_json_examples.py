# backend/app/api/api_json_examples.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import json # For parsing LLM response

from typing import List
from sqlalchemy.future import select # Import select
from app.database import get_db_session
from app import db_models # SQLAlchemy models
from app import models as pydantic_models # Pydantic models
from app.services import llm_service # For calling LLM
from app.core.config import settings # For DEFAULT_ASSISTANT_MODEL_ID
from app.core.prompt_loader import load_prompt, load_and_format_prompt

logger = logging.getLogger(__name__)

# Create an APIRouter instance
router = APIRouter(
    prefix="/json-examples", # All routes in this router will start with /json-examples
    tags=["JSON Examples"]    # Tag for OpenAPI documentation
)

@router.post("/", response_model=pydantic_models.JsonExampleResponse, status_code=201)
async def create_json_example(
    example_in: pydantic_models.JsonExampleCreate, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new JSON example.
    
    Users can submit an example of the target JSON structure they want LLMs to generate.
    """
    logger.info(f"Received request to create JSON example: {example_in.description or 'No description'}")
    
    db_example = db_models.JsonExample(
        content=example_in.content,
        description=example_in.description
    )
    
    db.add(db_example)
    await db.commit()
    await db.refresh(db_example)
    
    logger.info(f"Successfully created JSON example with ID: {db_example.id}")
    return db_example

@router.post(
    "/{example_id}/generate-schema",
    response_model=pydantic_models.JsonSchemaResponse, # Assuming JsonSchemaResponse is defined in pydantic_models
    status_code=201,
    summary="Generate JSON Schema from Example"
)
async def generate_schema_from_example(
    example_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Generates an initial JSON schema from a given JSON example using the assistant LLM.
    """
    logger.info(f"Request to generate schema for JsonExample ID: {example_id}")

    db_example = await db.get(db_models.JsonExample, example_id)
    if not db_example:
        logger.warning(f"JsonExample with ID {example_id} not found.")
        raise HTTPException(status_code=404, detail=f"JsonExample with ID {example_id} not found.")

    logger.info(f"Found JsonExample: {db_example.description or db_example.id}")

    try:
        json_example_content_str = json.dumps(db_example.content, indent=2)
    except TypeError as e:
        logger.error(f"Could not serialize JsonExample content to JSON string for example ID {example_id}: {e}")
        raise HTTPException(status_code=500, detail="Error processing example content.")

    system_prompt_str = load_prompt("schema_generation/system.txt")
    user_prompt_str = load_and_format_prompt(
        "schema_generation/user_template.txt",
        json_example_content_str=json_example_content_str
    )

    prompt_messages = [
        {"role": "system", "content": system_prompt_str},
        {"role": "user", "content": user_prompt_str}
    ]
    
    assistant_model_id = settings.DEFAULT_ASSISTANT_MODEL_ID
    if not assistant_model_id or assistant_model_id == "default_assistant_model_from_code":
        logger.error("DEFAULT_ASSISTANT_MODEL_ID is not configured correctly in .env file.")
        raise HTTPException(status_code=500, detail="Assistant LLM is not configured.")
    
    logger.info(f"Calling assistant LLM ({assistant_model_id}) to generate schema...")
    try:
        llm_response = await llm_service.call_llm_chat_completions(
            model_id=assistant_model_id,
            messages=prompt_messages,
            temperature=0.2
        )
    except llm_service.LLMServiceError as e:
        logger.error(f"LLM service error during schema generation: {str(e)}")
        raise HTTPException(status_code=e.status_code or 503, detail=f"LLM service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error calling LLM service: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error calling LLM service: {str(e)}")

    generated_schema_content_str = None
    if llm_response and "choices" in llm_response and llm_response["choices"]:
        choice = llm_response["choices"][0]
        if "message" in choice and "content" in choice["message"]:
            generated_schema_content_str = choice["message"]["content"]
    
    if not generated_schema_content_str:
        logger.error("LLM response did not contain expected schema content.")
        raise HTTPException(status_code=500, detail="LLM did not return schema content.")

    logger.debug(f"Raw schema string from LLM: {generated_schema_content_str[:500]}...")
    try:
        if generated_schema_content_str.strip().startswith("```json"):
            generated_schema_content_str = generated_schema_content_str.strip()[7:]
            if generated_schema_content_str.strip().endswith("```"):
                 generated_schema_content_str = generated_schema_content_str.strip()[:-3]
        elif generated_schema_content_str.strip().startswith("```"):
            generated_schema_content_str = generated_schema_content_str.strip()[3:]
            if generated_schema_content_str.strip().endswith("```"):
                generated_schema_content_str = generated_schema_content_str.strip()[:-3]
        
        generated_schema_dict = json.loads(generated_schema_content_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON schema. Error: {e}. Response: {generated_schema_content_str[:500]}...")
        raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON for schema. Parse error: {e}")

    schema_name = f"Schema_for_Example_{example_id}_v1"
    db_schema = db_models.JsonSchema(
        name=schema_name,
        schema_content=generated_schema_dict,
        json_example_id=example_id,
        status="draft_assistant_generated",
        version=1
    )

    db.add(db_schema)
    await db.commit()
    await db.refresh(db_schema)

    logger.info(f"Successfully generated and stored new JSON schema with ID: {db_schema.id}")
    return db_schema
    
    
@router.get("/", response_model=List[pydantic_models.JsonExampleResponse], summary="List All JSON Examples")
async def list_json_examples(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve a list of all submitted JSON examples, with pagination.
    """
    logger.info(f"Request to list JSON examples with skip: {skip}, limit: {limit}")
    
    statement = select(db_models.JsonExample).offset(skip).limit(limit).order_by(db_models.JsonExample.id)
    result = await db.execute(statement)
    db_examples = result.scalars().all()
    
    logger.info(f"Retrieved {len(db_examples)} JSON examples.")
    return db_examples

# Add other JsonExample related endpoints here (e.g., GET by ID, GET all)