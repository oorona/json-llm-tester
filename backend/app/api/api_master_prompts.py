# backend/app/api/api_master_prompts.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload # For eager loading
import logging
from typing import List
import json

from app.database import get_db_session
from app import db_models # SQLAlchemy models
from app import models as pydantic_models # Pydantic models
from app.services import llm_service # For calling LLM
from app.core.config import settings # For DEFAULT_ASSISTANT_MODEL_ID
from app.core.prompt_loader import load_prompt, load_and_format_prompt 

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/master-prompts",
    tags=["Master Prompts"]
)

@router.post("/", response_model=pydantic_models.MasterPromptResponse, status_code=201)
async def create_master_prompt(
    prompt_create: pydantic_models.MasterPromptCreate,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Request to create master prompt with name: {prompt_create.name}")
    
    if prompt_create.target_schema_id:
        target_schema = await db.get(db_models.JsonSchema, prompt_create.target_schema_id)
        if not target_schema:
            raise HTTPException(status_code=404, detail=f"Target JSON Schema with ID {prompt_create.target_schema_id} not found.")
    
    existing_prompt_stmt = select(db_models.MasterPrompt).filter(db_models.MasterPrompt.name == prompt_create.name)
    existing_prompt_result = await db.execute(existing_prompt_stmt)
    if existing_prompt_result.scalars().first():
        raise HTTPException(status_code=400, detail=f"Master prompt with name '{prompt_create.name}' already exists.")

    db_master_prompt = db_models.MasterPrompt(**prompt_create.model_dump())
    db.add(db_master_prompt)
    await db.commit()
    attributes_to_refresh = [
        'id', 'name', 'prompt_content', 'target_schema_id', 
        'created_at', 'updated_at' # Crucially, refresh these server-set timestamps
    ]
    if db_master_prompt.target_schema_id:
        attributes_to_refresh.append('target_schema')
    
    try:
        await db.refresh(db_master_prompt, attribute_names=attributes_to_refresh)
        if not db_master_prompt.target_schema_id: # Ensure relationship is None if ID is None
            db_master_prompt.target_schema = None
        logger.debug(f"Successfully refreshed attributes for MasterPrompt ID: {db_master_prompt.id}")
    except Exception as e_refresh:
        logger.error(f"Error during targeted refresh for MasterPrompt ID {db_master_prompt.id}: {e_refresh}", exc_info=True)
        # Decide if this is a critical failure or if we can proceed cautiously
        # For now, we'll proceed and let model_validate catch issues if attributes are missing/stale

    # 2. Simplified Debug Logging (Optional, but helpful)
    logger.debug(f"--- Debugging MasterPrompt ID: {db_master_prompt.id} before Pydantic conversion ---")
    logger.debug(f"  Name: {getattr(db_master_prompt, 'name', 'N/A')}")
    logger.debug(f"  Target Schema ID: {getattr(db_master_prompt, 'target_schema_id', 'N/A')}")
    logger.debug(f"  Created At: {getattr(db_master_prompt, 'created_at', 'N/A')}")
    logger.debug(f"  Updated At: {getattr(db_master_prompt, 'updated_at', 'N/A')}") # Important one!
    if hasattr(db_master_prompt, 'target_schema') and db_master_prompt.target_schema:
        logger.debug(f"  Target Schema loaded: ID={getattr(db_master_prompt.target_schema, 'id', 'N/A')}, Name='{getattr(db_master_prompt.target_schema, 'name', 'N/A')}'")
        # Optional: Manual validation of nested model (can be verbose)
        # try:
        #     pydantic_models.JsonSchemaResponse.model_validate(db_master_prompt.target_schema)
        #     logger.debug("    Manual validation of nested target_schema SUCCEEDED.")
        # except Exception as e_nested_validate:
        #     logger.error(f"    Manual validation of nested target_schema FAILED: {e_nested_validate}")
    elif db_master_prompt.target_schema_id:
        logger.warning("  target_schema_id is present, but target_schema object is not loaded.")
    logger.debug(f"--- End Debugging MasterPrompt ID: {db_master_prompt.id} ---")

    # 3. Explicitly convert to Pydantic model and return
    try:
        response_object = pydantic_models.MasterPromptResponse.model_validate(db_master_prompt)
        logger.info(f"Successfully created/updated/refined and validated MasterPrompt ID: {db_master_prompt.id} for response.")
        return response_object
    except Exception as e_serialize:
        logger.error(f"CRITICAL: Error during explicit Pydantic model_validate for MasterPromptResponse (ID: {db_master_prompt.id}): {e_serialize}", exc_info=True)
        # This is where the 'MissingGreenlet' error for 'updated_at' was caught before.
        # If it happens again, the explicit refresh above didn't fully solve it for Pydantic's access.
        raise HTTPException(status_code=500, detail=f"Error serializing response for master prompt ID {db_master_prompt.id} after operation.")



# backend/app/api/api_master_prompts.py
@router.get("/", response_model=List[pydantic_models.MasterPromptResponse])
async def list_master_prompts(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db_session)):
    logger.info(f"Request to list master prompts: skip={skip}, limit={limit}")
    statement = select(db_models.MasterPrompt).options(
        selectinload(db_models.MasterPrompt.target_schema) # Eager load
    ).offset(skip).limit(limit).order_by(db_models.MasterPrompt.id)
    result = await db.execute(statement)
    prompts_from_db = result.scalars().all()

    response_list = []
    for db_prompt in prompts_from_db:
        # Apply simplified debug and explicit conversion for each item
        logger.debug(f"--- Debugging MasterPrompt ID: {db_prompt.id} (from list_master_prompts) ---")
        logger.debug(f"  Name: {getattr(db_prompt, 'name', 'N/A')}")
        logger.debug(f"  Target Schema ID: {getattr(db_prompt, 'target_schema_id', 'N/A')}")
        logger.debug(f"  Updated At: {getattr(db_prompt, 'updated_at', 'N/A')}")
        if hasattr(db_prompt, 'target_schema') and db_prompt.target_schema:
            logger.debug(f"  Target Schema loaded: ID={getattr(db_prompt.target_schema, 'id', 'N/A')}")
        logger.debug(f"--- End Debugging MasterPrompt ID: {db_prompt.id} ---")
        try:
            response_list.append(pydantic_models.MasterPromptResponse.model_validate(db_prompt))
        except Exception as e_serialize:
            logger.error(f"Error during Pydantic model_validate for item in LIST MasterPromptResponse (ID: {db_prompt.id}): {e_serialize}", exc_info=True)
            # Decide how to handle: skip this item, or raise 500 for the whole list?
            # For now, let's be strict and raise if any item fails.
            raise HTTPException(status_code=500, detail=f"Error serializing item in master prompt list (ID: {db_prompt.id}).")
    return response_list

@router.get("/{prompt_id}", response_model=pydantic_models.MasterPromptResponse)
async def get_master_prompt(prompt_id: int, db: AsyncSession = Depends(get_db_session)):
    logger.info(f"Request to get master prompt ID: {prompt_id}")
    db_prompt = await db.get(
        db_models.MasterPrompt, 
        prompt_id, 
        options=[selectinload(db_models.MasterPrompt.target_schema)] # Eager load
    )
    if not db_prompt:
        raise HTTPException(status_code=404, detail=f"MasterPrompt with ID {prompt_id} not found.")

    # Apply simplified debug and explicit conversion
    logger.debug(f"--- Debugging MasterPrompt ID: {db_prompt.id} (from get_master_prompt) ---")
    logger.debug(f"  Name: {getattr(db_prompt, 'name', 'N/A')}")
    logger.debug(f"  Target Schema ID: {getattr(db_prompt, 'target_schema_id', 'N/A')}")
    logger.debug(f"  Updated At: {getattr(db_prompt, 'updated_at', 'N/A')}")
    if hasattr(db_prompt, 'target_schema') and db_prompt.target_schema:
        logger.debug(f"  Target Schema loaded: ID={getattr(db_prompt.target_schema, 'id', 'N/A')}")
    logger.debug(f"--- End Debugging MasterPrompt ID: {db_prompt.id} ---")
    try:
        return pydantic_models.MasterPromptResponse.model_validate(db_prompt)
    except Exception as e_serialize:
        logger.error(f"Error during Pydantic model_validate for GET MasterPromptResponse (ID: {db_prompt.id}): {e_serialize}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error serializing master prompt response.")


@router.put("/{prompt_id}", response_model=pydantic_models.MasterPromptResponse)
async def update_master_prompt(
    prompt_id: int,
    prompt_update: pydantic_models.MasterPromptUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Request to update master prompt ID: {prompt_id}")
    
    # Fetch with selectinload to ensure target_schema is available if needed for response
    statement = select(db_models.MasterPrompt).options(
        selectinload(db_models.MasterPrompt.target_schema)
    ).filter(db_models.MasterPrompt.id == prompt_id)
    result = await db.execute(statement)
    db_master_prompt = result.scalars().first() # Changed from db.get for options

    if not db_master_prompt:
        raise HTTPException(status_code=404, detail=f"MasterPrompt with ID {prompt_id} not found.")

    update_data = prompt_update.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] != db_master_prompt.name:
        # ... (unique name check) ...
        existing_prompt_stmt = select(db_models.MasterPrompt).filter(db_models.MasterPrompt.name == update_data["name"])
        existing_prompt_result = await db.execute(existing_prompt_stmt)
        if existing_prompt_result.scalars().first():
            raise HTTPException(status_code=400, detail=f"Master prompt with name '{update_data['name']}' already exists.")

    
    target_schema_id_in_update = update_data.get("target_schema_id")
    if "target_schema_id" in update_data: # Check if target_schema_id is part of the update payload
        if target_schema_id_in_update is not None:
            target_schema = await db.get(db_models.JsonSchema, target_schema_id_in_update)
            if not target_schema:
                raise HTTPException(status_code=404, detail=f"Target JSON Schema with ID {target_schema_id_in_update} not found.")
            # If we change target_schema_id, the relationship object also needs to be updated or reloaded.
            # Forcing a reload/refresh after setting the ID is safer.
        else: # target_schema_id is being set to None
             pass # db_master_prompt.target_schema will become None due to db_master_prompt.target_schema_id = None

    for key, value in update_data.items():
        setattr(db_master_prompt, key, value)
    
    await db.commit()
    
    attributes_to_refresh = [
        'id', 'name', 'prompt_content', 'target_schema_id', 
        'created_at', 'updated_at' # Crucially, refresh these server-set timestamps
    ]
    if db_master_prompt.target_schema_id:
        attributes_to_refresh.append('target_schema')
    
    try:
        await db.refresh(db_master_prompt, attribute_names=attributes_to_refresh)
        if not db_master_prompt.target_schema_id: # Ensure relationship is None if ID is None
            db_master_prompt.target_schema = None
        logger.debug(f"Successfully refreshed attributes for MasterPrompt ID: {db_master_prompt.id}")
    except Exception as e_refresh:
        logger.error(f"Error during targeted refresh for MasterPrompt ID {db_master_prompt.id}: {e_refresh}", exc_info=True)
        # Decide if this is a critical failure or if we can proceed cautiously
        # For now, we'll proceed and let model_validate catch issues if attributes are missing/stale

    logger.debug(f"-------------------------------------------------------------------------------")
    logger.debug(f"--- Debugging MasterPrompt ID: {db_master_prompt.id} before Pydantic conversion ---")
    logger.debug(f"  Name: {getattr(db_master_prompt, 'name', 'N/A')}")
    logger.debug(f"  Target Schema ID: {getattr(db_master_prompt, 'target_schema_id', 'N/A')}")
    logger.debug(f"  Created At: {getattr(db_master_prompt, 'created_at', 'N/A')}")
    logger.debug(f"  Updated At: {getattr(db_master_prompt, 'updated_at', 'N/A')}") # Important one!
    logger.debug(f"-------------------------------------------------------------------------------")

    if hasattr(db_master_prompt, 'target_schema') and db_master_prompt.target_schema:
        logger.debug(f"  Target Schema loaded: ID={getattr(db_master_prompt.target_schema, 'id', 'N/A')}, Name='{getattr(db_master_prompt.target_schema, 'name', 'N/A')}'")
        # Optional: Manual validation of nested model (can be verbose)
        # try:
        #     pydantic_models.JsonSchemaResponse.model_validate(db_master_prompt.target_schema)
        #     logger.debug("    Manual validation of nested target_schema SUCCEEDED.")
        # except Exception as e_nested_validate:
        #     logger.error(f"    Manual validation of nested target_schema FAILED: {e_nested_validate}")
    elif db_master_prompt.target_schema_id:
        logger.warning("  target_schema_id is present, but target_schema object is not loaded.")
    logger.debug(f"--- End Debugging MasterPrompt ID: {db_master_prompt.id} ---")

    # 3. Explicitly convert to Pydantic model and return
    try:
        response_object = pydantic_models.MasterPromptResponse.model_validate(db_master_prompt)
        logger.info(f"Successfully created/updated/refined and validated MasterPrompt ID: {db_master_prompt.id} for response.")
        return response_object
    except Exception as e_serialize:
        logger.error(f"CRITICAL: Error during explicit Pydantic model_validate for MasterPromptResponse (ID: {db_master_prompt.id}): {e_serialize}", exc_info=True)
        # This is where the 'MissingGreenlet' error for 'updated_at' was caught before.
        # If it happens again, the explicit refresh above didn't fully solve it for Pydantic's access.
        raise HTTPException(status_code=500, detail=f"Error serializing response for master prompt ID {db_master_prompt.id} after operation.")


@router.delete("/{prompt_id}", status_code=204)
async def delete_master_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete a master prompt.
    """
    logger.info(f"Request to delete master prompt ID: {prompt_id}")
    db_prompt = await db.get(db_models.MasterPrompt, prompt_id)
    if not db_prompt:
        raise HTTPException(status_code=404, detail=f"MasterPrompt with ID {prompt_id} not found.")
    
    await db.delete(db_prompt)
    await db.commit()
    logger.info(f"Master prompt ID: {prompt_id} deleted.")
    return None

@router.post(
    "/{prompt_id}/refine-with-llm",
    response_model=pydantic_models.MasterPromptResponse,
    summary="Refine Master Prompt with LLM Assistance"
)
async def refine_master_prompt_with_llm(
    prompt_id: int,
    refine_request: pydantic_models.MasterPromptRefineRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Refines an existing Master Prompt using textual feedback sent to an assistant LLM.
    Context like an associated JSON schema can be provided to the assistant.
   
    """
    logger.info(f"Request to refine Master Prompt ID: {prompt_id} with LLM feedback.")

    # 1. Retrieve the current MasterPrompt
    # Eagerly load target_schema if it exists and we want to use its content
    db_master_prompt = await db.get(
        db_models.MasterPrompt, 
        prompt_id, 
        options=[selectinload(db_models.MasterPrompt.target_schema)]
    )
    if not db_master_prompt:
        logger.warning(f"MasterPrompt with ID {prompt_id} not found for refinement.")
        raise HTTPException(status_code=404, detail=f"MasterPrompt with ID {prompt_id} not found.")

    logger.info(f"Found Master Prompt ID: {db_master_prompt.id}, Name: {db_master_prompt.name}")

    current_prompt_content = db_master_prompt.prompt_content
    user_feedback = refine_request.feedback
    
    # 2. Prepare context (e.g., associated schema)
    context_parts = []
    if db_master_prompt.target_schema and db_master_prompt.target_schema.schema_content:
        try:
            schema_content_str = json.dumps(db_master_prompt.target_schema.schema_content, indent=2)
            context_parts.append(f"The master prompt is intended to be used with the following JSON schema (for context on desired output structure):\n```json\n{schema_content_str}\n```")
            logger.info(f"Including target schema (ID: {db_master_prompt.target_schema_id}) in context for LLM refinement.")
        except TypeError:
            logger.warning(f"Could not serialize target schema content for Master Prompt ID {prompt_id}.")


    # 3. Construct a prompt for the assistant LLM
    prompt_instruction = load_prompt("master_prompt_refinement/system.txt")

    optional_schema_context_str = ""
    if db_master_prompt.target_schema and db_master_prompt.target_schema.schema_content:
        try:
            schema_content_str = json.dumps(db_master_prompt.target_schema.schema_content, indent=2)
            optional_schema_context_str = (
                f"The master prompt is intended to be used with the following JSON schema "
                f"(for context on desired output structure):\n```json\n{schema_content_str}\n```\n"
            )
            logger.info(f"Including target schema (ID: {db_master_prompt.target_schema_id}) in context for LLM refinement.")
        except TypeError:
            logger.warning(f"Could not serialize target schema content for Master Prompt ID {prompt_id}.")


    full_user_prompt = load_and_format_prompt(
        "master_prompt_refinement/user_template.txt",
        current_prompt_content=current_prompt_content,
        optional_schema_context=optional_schema_context_str,
        user_feedback=user_feedback
    )

    prompt_messages = [
        {"role": "system", "content": prompt_instruction},
        {"role": "user", "content": full_user_prompt}
    ]
    # 4. Call the LLM service
    assistant_model_id = settings.DEFAULT_ASSISTANT_MODEL_ID
    if not assistant_model_id or assistant_model_id == "default_assistant_model_from_code":
        logger.error("DEFAULT_ASSISTANT_MODEL_ID is not configured for master prompt refinement.")
        raise HTTPException(status_code=500, detail="Assistant LLM for prompt refinement is not configured.")

    logger.info(f"Calling assistant LLM ({assistant_model_id}) to refine master prompt ID: {prompt_id}...")
    try:
        llm_response = await llm_service.call_llm_chat_completions(
            model_id=assistant_model_id,
            messages=prompt_messages,
            temperature=0.5 # Temperature can be moderate for creative refinement
        )
    except llm_service.LLMServiceError as e:
        logger.error(f"LLM service error during master prompt refinement for ID {prompt_id}: {str(e)}")
        raise HTTPException(status_code=e.status_code or 503, detail=f"LLM service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error calling LLM service for master prompt ID {prompt_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error calling LLM service: {str(e)}")

    # 5. Parse the LLM's response
    revised_prompt_content = None
    if llm_response and "choices" in llm_response and llm_response["choices"]:
        choice = llm_response["choices"][0]
        if "message" in choice and "content" in choice["message"]:
            revised_prompt_content = choice["message"]["content"]

    if not revised_prompt_content:
        logger.error(f"LLM response did not contain expected revised prompt content for master prompt ID {prompt_id}.")
        raise HTTPException(status_code=500, detail="LLM did not return revised prompt content.")

    logger.info(f"Received refined prompt content from LLM for master prompt ID {prompt_id}.")
    logger.debug(f"Refined prompt snippet: {revised_prompt_content[:300]}...")

    # 6. Update the existing MasterPrompt record
    db_master_prompt.prompt_content = revised_prompt_content.strip() # Store the cleaned text
    
    # We are not versioning master prompts in this iteration, just updating in place.
    # db_master_prompt.updated_at will be set automatically by the DB on update.

    await db.commit()
    # Explicitly list all attributes that are in MasterPromptResponse AND might be stale/DB-generated
    # or are relationships.
    attributes_to_refresh = ['id', 'name', 'prompt_content', 'target_schema_id', 'created_at', 'updated_at']
    if db_master_prompt.target_schema_id: # Only add 'target_schema' if there's an ID for it
        attributes_to_refresh.append('target_schema')
    
    await db.refresh(db_master_prompt, attribute_names=attributes_to_refresh)
    # If target_schema_id is None, ensure target_schema is also None on the instance
    if not db_master_prompt.target_schema_id:
        db_master_prompt.target_schema = None
    # --- END REVISED REFRESH ---    
    # --- Add the same debugging block here as in get_master_prompt ---
    
    logger.debug(f"-------------------------------------------------------------------------------")
    # --- Corrected Debugging block ---
    logger.debug(f"--- Debugging db_master_prompt before returning from refine_master_prompt_with_llm (ID: {db_master_prompt.id}) ---")
    logger.debug(f"Name: {db_master_prompt.name}") # Use db_master_prompt
    logger.debug(f"Target Schema ID: {db_master_prompt.target_schema_id}") # Use db_master_prompt
    
    if db_master_prompt.target_schema_id and db_master_prompt.target_schema:
        logger.debug(f"TargetSchema for Prompt ID {db_master_prompt.id}: ID={db_master_prompt.target_schema.id}, Name='{db_master_prompt.target_schema.name}'")
        logger.debug(f"Attempting manual Pydantic validation of db_master_prompt.target_schema (ID: {db_master_prompt.target_schema.id}) against JsonSchemaResponse...")
        try:
            # For Pydantic V2
            validated_nested_schema = pydantic_models.JsonSchemaResponse.model_validate(db_master_prompt.target_schema) # Use db_master_prompt
            logger.debug(f"MANUAL VALIDATION of target_schema (ID: {db_master_prompt.target_schema.id}) SUCCEEDED. Validated name: {validated_nested_schema.name}")
        except Exception as e_pydantic:
            logger.error(f"MANUAL PYDANTIC VALIDATION of target_schema (ID: {db_master_prompt.target_schema.id}) FAILED: {e_pydantic}", exc_info=True)
    elif db_master_prompt.target_schema_id and not db_master_prompt.target_schema:
        logger.warning(f"TargetSchema for Prompt ID {db_master_prompt.id} is None in refine_master_prompt_with_llm despite target_schema_id ({db_master_prompt.target_schema_id}) being present.")
    
    logger.debug("--- End Debugging refine_master_prompt_with_llm ---")
    # --- End Corrected Debugging block ---
    logger.debug(f"-------------------------------------------------------------------------------")
    logger.info(f"Successfully refined and updated Master Prompt ID: {db_master_prompt.id}. Preparing Pydantic response.")
    try:
        # Explicitly convert to Pydantic model before returning
        response_object = pydantic_models.MasterPromptResponse.model_validate(db_master_prompt)
        return response_object
    except Exception as e_serialize:
        logger.error(f"Error during explicit Pydantic model_validate for MasterPromptResponse (ID: {db_master_prompt.id}): {e_serialize}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error serializing master prompt response after refinement.")
