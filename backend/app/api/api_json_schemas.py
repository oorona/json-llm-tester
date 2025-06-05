# backend/app/api/api_json_schemas.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select # For select statements if needed for more complex queries
import logging
from typing import List # For potential future list endpoint
import json

from app.database import get_db_session
from app import db_models # SQLAlchemy models
from app import models as pydantic_models # Pydantic models
from app.services import llm_service # For calling LLM
from app.core.config import settings # For DEFAULT_ASSISTANT_MODEL_ID
from jsonschema import validate, ValidationError, SchemaError # Import for jsonschema validation
from app.core.prompt_loader import load_prompt, load_and_format_prompt

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/json-schemas",
    tags=["JSON Schemas"]
)

@router.get("/{schema_id}", response_model=pydantic_models.JsonSchemaResponse)
async def get_json_schema(
    schema_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve a specific JSON schema by its ID.
    This allows the UI to fetch and display a schema for review or editing.
    """
    logger.info(f"Request to retrieve JSON schema with ID: {schema_id}")
    db_schema = await db.get(db_models.JsonSchema, schema_id)
    if db_schema is None:
        logger.warning(f"JSON schema with ID {schema_id} not found.")
        raise HTTPException(status_code=404, detail=f"JSON schema with ID {schema_id} not found.")
    logger.info(f"Successfully retrieved JSON schema ID: {db_schema.id}, Name: {db_schema.name}")
    return db_schema

@router.put("/{schema_id}", response_model=pydantic_models.JsonSchemaResponse)
async def update_json_schema(
    schema_id: int,
    schema_update_payload: pydantic_models.JsonSchemaUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update an existing JSON schema (e.g., its content, name, or status).
    This supports direct editing of the schema by the user.
    """
    logger.info(f"Request to update JSON schema with ID: {schema_id}")
    db_schema = await db.get(db_models.JsonSchema, schema_id)
    if db_schema is None:
        logger.warning(f"JSON schema with ID {schema_id} not found for update.")
        raise HTTPException(status_code=404, detail=f"JSON schema with ID {schema_id} not found.")

    update_data = schema_update_payload.model_dump(exclude_unset=True) # Pydantic V2
    # For Pydantic V1, it would be: update_data = schema_update_payload.dict(exclude_unset=True)
    
    updated_fields_count = 0
    for key, value in update_data.items():
        if hasattr(db_schema, key):
            setattr(db_schema, key, value)
            updated_fields_count +=1
    
    if updated_fields_count > 0:
        # If version is not being manually updated, and content changes, consider incrementing it.
        # For now, we allow manual version update via payload or leave it as is.
        # If 'schema_content' is updated and 'version' is not in update_data,
        # you might want to increment db_schema.version here.
        # Example:
        # if "schema_content" in update_data and "version" not in update_data:
        #     db_schema.version += 1
        #     logger.info(f"Schema content changed, auto-incrementing version to {db_schema.version} for schema ID {schema_id}")

        await db.commit()
        await db.refresh(db_schema)
        logger.info(f"Successfully updated JSON schema ID: {db_schema.id}. Fields updated: {updated_fields_count}")
    else:
        logger.info(f"No fields to update for JSON schema ID: {schema_id}. Returning current state.")

    return db_schema
@router.post(
    "/{schema_id}/refine-with-llm",
    response_model=pydantic_models.JsonSchemaResponse,
    summary="Refine JSON Schema with LLM Assistance"
)
async def refine_json_schema_with_llm(
    schema_id: int,
    refine_request: pydantic_models.JsonSchemaRefineRequest, # New Pydantic model for feedback
    db: AsyncSession = Depends(get_db_session)
):
    """
    Refines an existing JSON schema using textual feedback sent to an assistant LLM.
    The system sends this feedback (along with the current schema and optionally the original example)
    to the assistant LLM to generate a revised schema.
    """
    logger.info(f"Request to refine JSON schema ID: {schema_id} with LLM feedback.")

    # 1. Retrieve the current JsonSchema
    db_schema = await db.get(db_models.JsonSchema, schema_id)
    if not db_schema:
        logger.warning(f"JSON schema with ID {schema_id} not found for refinement.")
        raise HTTPException(status_code=404, detail=f"JSON schema with ID {schema_id} not found.")

    logger.info(f"Found JSON schema ID: {db_schema.id}, Name: {db_schema.name}, Version: {db_schema.version}")

    current_schema_content_str = json.dumps(db_schema.schema_content, indent=2)
    user_feedback = refine_request.feedback

    # 2. Optionally, retrieve the original JsonExample if it exists and might provide context
    original_example_content_str = None
    if db_schema.json_example_id:
        db_example = await db.get(db_models.JsonExample, db_schema.json_example_id)
        if db_example and db_example.content:
            original_example_content_str = json.dumps(db_example.content, indent=2)
            logger.info(f"Including original JSON example (ID: {db_schema.json_example_id}) content in prompt for context.")

    # 3. Construct a prompt for the assistant LLM
    system_prompt_instruction = load_prompt("schema_refinement/system.txt") # System prompt is now simpler

    optional_example_context_str = ""
    if original_example_content_str:
        optional_example_context_str = (
            f"\nThis schema was originally derived from or related to the "
            f"following JSON example (for context):\n```json\n{original_example_content_str}\n```"
        )

    user_prompt_content = load_and_format_prompt(
        "schema_refinement/user_template.txt",
        current_schema_content_str=current_schema_content_str,
        optional_original_example_context=optional_example_context_str,
        user_feedback=user_feedback
    )

    prompt_messages = [
        # System prompt can be directly loaded if it's static, or constructed if needed
        {"role": "system", "content": system_prompt_instruction},
        {"role": "user", "content": user_prompt_content}
    ]

    # 4. Call the LLM service
    assistant_model_id = settings.DEFAULT_ASSISTANT_MODEL_ID
    if not assistant_model_id or assistant_model_id == "default_assistant_model_from_code":
        logger.error("DEFAULT_ASSISTANT_MODEL_ID is not configured correctly in .env file for schema refinement.")
        raise HTTPException(status_code=500, detail="Assistant LLM for schema refinement is not configured.")

    logger.info(f"Calling assistant LLM ({assistant_model_id}) to refine schema ID: {schema_id}...")
    try:
        llm_response = await llm_service.call_llm_chat_completions(
            model_id=assistant_model_id,
            messages=prompt_messages,
            temperature=0.3 # Slightly higher temp than initial generation, but still focused
        )
    except llm_service.LLMServiceError as e:
        logger.error(f"LLM service error during schema refinement for schema ID {schema_id}: {str(e)}")
        raise HTTPException(status_code=e.status_code or 503, detail=f"LLM service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error calling LLM service for schema ID {schema_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error calling LLM service: {str(e)}")

    # 5. Parse the LLM's response
    revised_schema_content_str = None
    if llm_response and "choices" in llm_response and llm_response["choices"]:
        choice = llm_response["choices"][0]
        if "message" in choice and "content" in choice["message"]:
            revised_schema_content_str = choice["message"]["content"]

    if not revised_schema_content_str:
        logger.error(f"LLM response did not contain expected revised schema content for schema ID {schema_id}.")
        raise HTTPException(status_code=500, detail="LLM did not return revised schema content.")

    logger.debug(f"Raw revised schema string from LLM for schema ID {schema_id}: {revised_schema_content_str[:500]}...")
    try:
        # Basic cleanup for markdown code blocks
        if revised_schema_content_str.strip().startswith("```json"):
            revised_schema_content_str = revised_schema_content_str.strip()[7:]
            if revised_schema_content_str.strip().endswith("```"):
                 revised_schema_content_str = revised_schema_content_str.strip()[:-3]
        elif revised_schema_content_str.strip().startswith("```"):
            revised_schema_content_str = revised_schema_content_str.strip()[3:]
            if revised_schema_content_str.strip().endswith("```"):
                revised_schema_content_str = revised_schema_content_str.strip()[:-3]

        revised_schema_dict = json.loads(revised_schema_content_str)
        logger.info(f"Successfully parsed revised schema string to JSON object for schema ID {schema_id}.")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as revised JSON schema for schema ID {schema_id}. Error: {e}. Response: {revised_schema_content_str[:500]}...")
        raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON for revised schema. Parse error: {e}")

    # 6. Update the existing JsonSchema record
    db_schema.schema_content = revised_schema_dict
    db_schema.version += 1 # Increment version
    db_schema.status = "draft_llm_refined" # Update status
    # db_schema.name could also be updated if refine_request.new_name was provided

    await db.commit()
    await db.refresh(db_schema)

    logger.info(f"Successfully refined and updated JSON schema ID: {db_schema.id} to version {db_schema.version}.")
    return db_schema

@router.post(
    "/{schema_id}/validate-object",
    response_model=pydantic_models.SchemaValidationResponse,
    summary="Validate JSON Object Against Schema"
)
async def validate_object_against_schema(
    schema_id: int,
    object_to_validate: pydantic_models.JsonObjectToValidate, # User provides JSON object
    db: AsyncSession = Depends(get_db_session)
):
    """
    Validates a given JSON object against a specified JSON schema.
    The user pastes a sample JSON object to validate it against the current version of the schema.
    The system shows "Pass" or "Fail" with specific error messages.
    """
    logger.info(f"Request to validate object against JSON schema ID: {schema_id}")

    # 1. Retrieve the JsonSchema from the database
    db_schema = await db.get(db_models.JsonSchema, schema_id)
    if not db_schema:
        logger.warning(f"JSON schema with ID {schema_id} not found for validation.")
        raise HTTPException(status_code=404, detail=f"JSON schema with ID {schema_id} not found.")

    if not isinstance(db_schema.schema_content, dict):
        logger.error(f"Schema content for schema ID {schema_id} is not a valid dictionary structure.")
        raise HTTPException(status_code=500, detail="Stored schema content is not in a valid format for validation.")

    logger.info(f"Validating object against schema ID: {db_schema.id}, Name: {db_schema.name}")

    # 2. Perform validation using the jsonschema library
    instance_to_validate = object_to_validate.json_object
    schema_definition = db_schema.schema_content

    validation_errors: List[pydantic_models.SchemaValidationErrorDetail] = []
    is_valid = True

    try:
        # jsonschema.validate will raise ValidationError if validation fails
        # or SchemaError if the schema itself is invalid
        validate(instance=instance_to_validate, schema=schema_definition)
        logger.info(f"Validation successful for object against schema ID: {schema_id}")
    except ValidationError as e:
        is_valid = False
        # More detailed error, good for a list of errors
        # The jsonschema library's 'iter_errors' can be useful for collecting all errors
        # For simplicity, let's capture the main error and its context.
        # We can refine this to capture multiple errors from e.context or by using Draft202012Validator(schema).iter_errors(instance)
        logger.warning(f"Validation failed for object against schema ID: {schema_id}. Error: {e.message}")
        
        # A single error example (can be expanded to iterate through e.context for multiple errors)
        error_path = list(str(p) for p in e.path) # Convert deque to list of strings
        validation_errors.append(pydantic_models.SchemaValidationErrorDetail(
            message=e.message,
            path=error_path,
            validator=e.validator
            # schema_path=list(str(sp) for sp in e.schema_path) # Also available
        ))
        # To get all errors, you'd typically do:
        # from jsonschema import Draft7Validator # Or your preferred validator version
        # validator = Draft7Validator(schema_definition)
        # for error in sorted(validator.iter_errors(instance_to_validate), key=str):
        #     validation_errors.append(pydantic_models.SchemaValidationErrorDetail(
        #         message=error.message,
        #         path=list(str(p) for p in error.path),
        #         validator=error.validator
        #     ))

    except SchemaError as e:
        # This means the schema itself stored in the database is invalid
        logger.error(f"Invalid schema (SchemaError) for schema ID: {schema_id}. Error: {e.message}")
        raise HTTPException(status_code=500, detail=f"The stored schema (ID: {schema_id}) is invalid: {e.message}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during validation for schema ID: {schema_id}. Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during validation: {str(e)}")
        
    return pydantic_models.SchemaValidationResponse(is_valid=is_valid, errors=validation_errors if not is_valid else None)

@router.get("/", response_model=List[pydantic_models.JsonSchemaResponse], summary="List All JSON Schemas")
async def list_json_schemas(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve a list of all stored JSON schemas, with pagination.
    """
    logger.info(f"Request to list JSON schemas with skip: {skip}, limit: {limit}")
    
    statement = select(db_models.JsonSchema).offset(skip).limit(limit).order_by(db_models.JsonSchema.id)
    result = await db.execute(statement)
    db_schemas = result.scalars().all()
    
    logger.info(f"Retrieved {len(db_schemas)} JSON schemas.")
    return db_schemas

@router.post(
    "/{schema_id}/generate-mock-data",
    response_model=pydantic_models.MockDataGenerationInitiatedResponse,
    status_code=201,
    summary="Generate Mock Data for a JSON Schema"
)
async def generate_mock_data_for_schema(
    schema_id: int,
    prompt_request: pydantic_models.MockDataPromptRequest, # Using the new request model
    db: AsyncSession = Depends(get_db_session)
):
    """
    Creates a mock data generation prompt and triggers an LLM to generate mock data items
    for a specific JSON schema.
    - User writes a textual prompt.
    - User specifies the desired number of items.
    - Assistant LLM generates mock data.
    """
    logger.info(f"Request to generate {prompt_request.desired_item_count} mock data items for schema ID: {schema_id} using prompt: '{prompt_request.prompt_text[:50]}...'")

    db_schema = await db.get(db_models.JsonSchema, schema_id)
    if not db_schema:
        raise HTTPException(status_code=404, detail=f"JSON Schema with ID {schema_id} not found.")
    # Consider checking if db_schema.status is "approved_master"
    # if db_schema.status != "approved_master":
    #     raise HTTPException(status_code=400, detail=f"Mock data can only be generated for 'approved_master' schemas. Schema ID {schema_id} has status '{db_schema.status}'.")

    db_mock_data_prompt = db_models.MockDataPrompt(
        prompt_text=prompt_request.prompt_text,
        desired_item_count=prompt_request.desired_item_count,
        target_schema_id=schema_id
    )
    db.add(db_mock_data_prompt)
    await db.commit() # Commit here to get an ID for db_mock_data_prompt
    await db.refresh(db_mock_data_prompt)
    logger.info(f"MockDataPrompt created with ID: {db_mock_data_prompt.id}")

    schema_content_str = json.dumps(db_schema.schema_content, indent=2)
    llm_system_prompt = load_and_format_prompt(
        "mock_data_generation/system_template.txt",
        desired_item_count=db_mock_data_prompt.desired_item_count
    )
    llm_user_prompt = load_and_format_prompt(
        "mock_data_generation/user_template.txt",
        prompt_text=db_mock_data_prompt.prompt_text, # Corrected variable name
        schema_content_str=schema_content_str,
        desired_item_count=db_mock_data_prompt.desired_item_count
    )
    prompt_messages = [{"role": "system", "content": llm_system_prompt}, {"role": "user", "content": llm_user_prompt}]

    assistant_model_id = settings.DEFAULT_ASSISTANT_MODEL_ID
    if not assistant_model_id or assistant_model_id == "default_assistant_model_from_code":
        # No rollback of prompt needed here, just fail the operation. User can retry.
        raise HTTPException(status_code=500, detail="Assistant LLM for mock data generation is not configured.")

    llm_output_str = None
    generated_items_list_from_llm = []
    try:
        llm_response = await llm_service.call_llm_chat_completions(
            model_id=assistant_model_id, messages=prompt_messages, temperature=0.7)
        
        if llm_response and llm_response.get("choices") and llm_response["choices"][0].get("message"):
            llm_output_str = llm_response["choices"][0]["message"].get("content")
        
        if not llm_output_str:
            raise ValueError("LLM did not return content.")

        if llm_output_str.strip().startswith("```json"):
            llm_output_str = llm_output_str.strip()[7:-3] if llm_output_str.strip().endswith("```") else llm_output_str.strip()[7:]
        elif llm_output_str.strip().startswith("```"):
            llm_output_str = llm_output_str.strip()[3:-3] if llm_output_str.strip().endswith("```") else llm_output_str.strip()[3:]
        
        generated_items_list_from_llm = json.loads(llm_output_str)
        if not isinstance(generated_items_list_from_llm, list):
            raise ValueError("LLM output was not a JSON list as expected.")
        logger.info(f"LLM generated {len(generated_items_list_from_llm)} raw items.")

    except Exception as e: # Catch LLM call errors, parsing errors, or ValueErrors
        logger.error(f"Failed during LLM call or parsing for mock data generation (prompt ID {db_mock_data_prompt.id}): {str(e)}", exc_info=True)
        # Update prompt to indicate failure, but keep the prompt record
        db_mock_data_prompt.prompt_text += f"\n\n[SYSTEM NOTE: LLM failed to generate valid items or an error occurred. Error: {str(e)}]"
        await db.commit()
        await db.refresh(db_mock_data_prompt) # Refresh to get updated text
        # Return the prompt info with empty items list
        prompt_response = pydantic_models.MockDataPromptResponse.from_orm(db_mock_data_prompt)
        return pydantic_models.MockDataGenerationInitiatedResponse(
            prompt_details=prompt_response,
            message=f"Mock data prompt created, but LLM generation failed or returned unexpected data: {str(e)}"
        )

    created_db_items_count = 0
    for item_content in generated_items_list_from_llm:
        if isinstance(item_content, dict):
            db_item = db_models.MockDataItem(item_content=item_content, prompt_id=db_mock_data_prompt.id)
            db.add(db_item)
            created_db_items_count += 1
        else:
            logger.warning(f"Skipping an item from LLM that was not a dictionary: {type(item_content)}")
    
    if created_db_items_count > 0:
        await db.commit()
        logger.info(f"Successfully stored {created_db_items_count} mock data items for prompt ID {db_mock_data_prompt.id}.")
    
    # Eagerly load generated_items for the response
    await db.refresh(db_mock_data_prompt, attribute_names=['generated_items']) 
    prompt_response = pydantic_models.MockDataPromptResponse.from_orm(db_mock_data_prompt)

    return pydantic_models.MockDataGenerationInitiatedResponse(
        prompt_details=prompt_response,
        message=f"Successfully generated and stored {len(prompt_response.generated_items)} mock data items."
    )


# @router.post(
#     "/json-schemas/{schema_id}/generate-mock-data",
#     response_model=pydantic_models.MockDataGenerationResponse, # Custom response
#     status_code=201,
#     summary="Generate Mock Data for a JSON Schema"
# )
# async def generate_mock_data_for_schema(
#     schema_id: int,
#     prompt_request: pydantic_models.MockDataPromptCreate,
#     db: AsyncSession = Depends(get_db_session)
# ):
#     """
#     Creates a mock data generation prompt and triggers an LLM to generate mock data items
#     - User writes a textual prompt describing the type of input data scenarios.
#     - User specifies the desired number of mock data items to generate.
#     - The system sends the user's prompt and quantity to the assistant LLM.
#     """
#     logger.info(f"Request to generate {prompt_request.desired_item_count} mock data items for schema ID: {schema_id} using prompt: '{prompt_request.prompt_text[:50]}...'")

#     # 1. Verify target schema exists
#     db_schema = await db.get(db_models.JsonSchema, schema_id)
#     if not db_schema:
#         raise HTTPException(status_code=404, detail=f"JSON Schema with ID {schema_id} not found.")
#     if db_schema.status != "approved_master": # Or some other "finalized" status
#         logger.warning(f"Attempt to generate mock data for schema ID {schema_id} which is not an 'approved_master' schema (status: {db_schema.status}).")
#         # Decide if this should be a hard error or just a warning. For now, proceeding.

#     # 2. Create and store the MockDataPrompt
#     db_mock_data_prompt = db_models.MockDataPrompt(
#         prompt_text=prompt_request.prompt_text,
#         desired_item_count=prompt_request.desired_item_count,
#         target_schema_id=schema_id
#     )
#     db.add(db_mock_data_prompt)
#     await db.commit()
#     await db.refresh(db_mock_data_prompt)
#     logger.info(f"MockDataPrompt created with ID: {db_mock_data_prompt.id}")

#     # 3. Construct prompt for LLM to generate mock data items
#     # The LLM should be asked to return a JSON array of JSON objects.
#     schema_content_str = json.dumps(db_schema.schema_content, indent=2)
#     llm_system_prompt = load_and_format_prompt(
#         "mock_data_generation/system_template.txt",
#         desired_item_count=db_mock_data_prompt.desired_item_count
#     )
#     llm_user_prompt = load_and_format_prompt(
#         "mock_data_generation/user_template.txt",
#         prompt_text=db_mock_data_prompt.prompt_text, # Corrected variable name
#         schema_content_str=schema_content_str,
#         desired_item_count=db_mock_data_prompt.desired_item_count
#     )
#     prompt_messages = [{"role": "system", "content": llm_system_prompt}, {"role": "user", "content": llm_user_prompt}]

#     # 4. Call LLM service
#     assistant_model_id = settings.DEFAULT_ASSISTANT_MODEL_ID
#     if not assistant_model_id or assistant_model_id == "default_assistant_model_from_code":
#         # Rollback MockDataPrompt creation if LLM is not configured
#         await db.delete(db_mock_data_prompt)
#         await db.commit()
#         raise HTTPException(status_code=500, detail="Assistant LLM for mock data generation is not configured.")

#     logger.info(f"Calling assistant LLM ({assistant_model_id}) to generate mock data items for prompt ID: {db_mock_data_prompt.id}...")
#     generated_items_list = []
#     try:
#         llm_response = await llm_service.call_llm_chat_completions(
#             model_id=assistant_model_id,
#             messages=prompt_messages,
#             temperature=0.7 # Higher temperature for more varied mock data
#         )
        
#         llm_output_str = None
#         if llm_response and "choices" in llm_response and llm_response["choices"]:
#             choice = llm_response["choices"][0]
#             if "message" in choice and "content" in choice["message"]:
#                 llm_output_str = choice["message"]["content"]
        
#         if not llm_output_str:
#             raise HTTPException(status_code=500, detail="LLM did not return content for mock data.")

#         # Basic cleanup for markdown code blocks
#         if llm_output_str.strip().startswith("```json"):
#             llm_output_str = llm_output_str.strip()[7:]
#             if llm_output_str.strip().endswith("```"):
#                  llm_output_str = llm_output_str.strip()[:-3]
#         elif llm_output_str.strip().startswith("```"):
#             llm_output_str = llm_output_str.strip()[3:]
#             if llm_output_str.strip().endswith("```"):
#                 llm_output_str = llm_output_str.strip()[:-3]
        
#         generated_items_list = json.loads(llm_output_str)
#         if not isinstance(generated_items_list, list):
#             raise ValueError("LLM output for mock data was not a JSON list.")
#         logger.info(f"LLM generated {len(generated_items_list)} items. Expected {db_mock_data_prompt.desired_item_count}.")

#     except json.JSONDecodeError as e:
#         logger.error(f"Failed to parse LLM response as JSON array for mock data. Error: {e}. Response: {llm_output_str[:500]}...")
#         # Store the prompt but indicate failure to generate items
#         db_mock_data_prompt.prompt_text += "\n\n[SYSTEM NOTE: LLM failed to generate valid JSON data for items.]" # Append a note
#         await db.commit()
#         await db.refresh(db_mock_data_prompt)
#         # Return the prompt details with empty items, client can decide how to handle
#         return pydantic_models.MockDataGenerationResponse(prompt_details=db_mock_data_prompt, generated_items=[])

#     except llm_service.LLMServiceError as e:
#         # Rollback MockDataPrompt creation or mark it as failed
#         await db.delete(db_mock_data_prompt)
#         await db.commit()
#         raise HTTPException(status_code=e.status_code or 503, detail=f"LLM service error: {str(e)}")
#     except Exception as e:
#         # Rollback or mark as failed
#         await db.delete(db_mock_data_prompt)
#         await db.commit()
#         logger.error(f"Unexpected error during mock data generation: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

#     # 5. Store generated MockDataItems
#     created_db_items = []
#     for item_content in generated_items_list:
#         # Now, item_content can be a string, number, boolean, dict, or list.
#         # All are valid JSON values that can be stored in the JSON db column.
#         # You might add a log if you want to track the types being stored:
#         logger.info(f"Processing mock data item of type: {type(item_content)}")
#         db_item = db_models.MockDataItem(
#             item_content=item_content, # This will correctly store strings, numbers, etc.
#             prompt_id=db_mock_data_prompt.id
#         )
#         db.add(db_item)
#         created_db_items.append(db_item)
    
#     if created_db_items:
#         await db.commit()
#         for db_item in created_db_items: # Refresh each item to get its ID, created_at etc.
#             await db.refresh(db_item)
#         logger.info(f"Successfully stored {len(created_db_items)} mock data items for prompt ID {db_mock_data_prompt.id}.")
    
#     # Refresh the prompt to get its generated_items relationship populated for the response
#     await db.refresh(db_mock_data_prompt, attribute_names=['generated_items'])

#     return pydantic_models.MockDataGenerationResponse(prompt_details=db_mock_data_prompt)