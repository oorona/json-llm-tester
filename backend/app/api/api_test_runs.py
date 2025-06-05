# backend/app/api/api_test_runs.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload,sessionmaker
import logging
import json
import time as pytime # To avoid conflict with 'time' module if used differently
from datetime import datetime
from typing import List, Dict, Any 
from collections import defaultdict

from app.database import get_db_session, AsyncSessionFactory # Import your session management
from app import db_models # SQLAlchemy models
from app import models as pydantic_models # Pydantic models
from app.services import llm_service # For calling LLM
from app.core.config import settings
from jsonschema import validate, ValidationError # For schema validation

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/test-runs",
    tags=["Test Runs & Results"]
)

# Helper function to perform a single test evaluation (can be run in background)
async def run_single_test_case(
    db: AsyncSession, # Pass a new session or handle session scope carefully for background tasks
    test_run_id: int,
    master_prompt_content: str,
    mock_data_item: db_models.MockDataItem,
    target_llm_id: str,
    master_schema_content: Dict[Any, Any]
):
    start_time = pytime.monotonic()
    llm_raw_output = None
    parse_status = None
    schema_compliance_status = None
    validation_errors_list = []
    error_message_str = None
    tokens_used_val = None # Placeholder

    try:
        # 1. Inject mock data into master prompt
        # Simple replacement, consider more robust templating if {{INPUT_DATA}} can vary
        final_prompt_content = master_prompt_content.replace("{{INPUT_DATA}}", json.dumps(mock_data_item.item_content))
        
        prompt_messages = [{"role": "user", "content": final_prompt_content}] # Assuming user role for master prompt

        # 2. Call the target LLM
        llm_response = await llm_service.call_llm_chat_completions(
            model_id=target_llm_id,
            messages=prompt_messages,
            temperature=0.5 # Or make configurable per test run
        )
        
        if llm_response and llm_response.get("choices") and llm_response["choices"][0].get("message"):
            llm_raw_output = llm_response["choices"][0]["message"].get("content")
            # Potentially extract token usage if available in llm_response.usage.total_tokens

        # 3. Validate the output
        if llm_raw_output:
            try:
                # Clean potential markdown
                if llm_raw_output.strip().startswith("```json"):
                    llm_raw_output = llm_raw_output.strip()[7:-3] if llm_raw_output.strip().endswith("```") else llm_raw_output.strip()[7:]
                elif llm_raw_output.strip().startswith("```"):
                    llm_raw_output = llm_raw_output.strip()[3:-3] if llm_raw_output.strip().endswith("```") else llm_raw_output.strip()[3:]

                parsed_output = json.loads(llm_raw_output)
                parse_status = True
                logger.info(f"TestRun {test_run_id}, LLM {target_llm_id}, Item {mock_data_item.id}: Output parsed successfully.")
                
                try:
                    validate(instance=parsed_output, schema=master_schema_content)
                    schema_compliance_status = "Pass"
                    logger.info(f"TestRun {test_run_id}, LLM {target_llm_id}, Item {mock_data_item.id}: Schema validation passed.")
                except ValidationError as ve:
                    schema_compliance_status = "Fail"
                    # Capture multiple errors if possible, or simplify
                    validation_errors_list.append({
                        "message": ve.message,
                        "path": list(str(p) for p in ve.path),
                        "validator": ve.validator
                    })
                    logger.warning(f"TestRun {test_run_id}, LLM {target_llm_id}, Item {mock_data_item.id}: Schema validation failed: {ve.message}")
                except Exception as sve: # Other schema validation library errors
                    schema_compliance_status = "Fail"
                    validation_errors_list.append({"message": str(sve), "path": [], "validator": "schema_error"})
                    logger.error(f"TestRun {test_run_id}, LLM {target_llm_id}, Item {mock_data_item.id}: Schema itself is invalid or other validation error: {sve}")

            except json.JSONDecodeError as je:
                parse_status = False
                schema_compliance_status = "N/A (not valid JSON)"
                logger.warning(f"TestRun {test_run_id}, LLM {target_llm_id}, Item {mock_data_item.id}: Failed to parse LLM output as JSON: {je}")
        else:
            error_message_str = "LLM did not return any content."
            logger.warning(f"TestRun {test_run_id}, LLM {target_llm_id}, Item {mock_data_item.id}: {error_message_str}")


    except llm_service.LLMServiceError as lse:
        error_message_str = f"LLM Service Error: {str(lse)}"
        logger.error(f"TestRun {test_run_id}, LLM {target_llm_id}, Item {mock_data_item.id}: {error_message_str}")
    except Exception as e:
        error_message_str = f"Unexpected error during test case: {str(e)}"
        logger.error(f"TestRun {test_run_id}, LLM {target_llm_id}, Item {mock_data_item.id}: {error_message_str}", exc_info=True)
    
    end_time = pytime.monotonic()
    execution_time_ms = (end_time - start_time) * 1000

    # 4. Store TestResult (important: this db session is for the background task)
    async with AsyncSessionFactory() as task_session: # Create a new session for this task
        db_test_result = db_models.TestResult(
            test_run_id=test_run_id,
            target_llm_model_id=target_llm_id,
            mock_input_data_used=mock_data_item.item_content, # Store copy of the input
            llm_raw_output=llm_raw_output,
            parse_status=parse_status,
            schema_compliance_status=schema_compliance_status,
            validation_errors=validation_errors_list if validation_errors_list else None,
            execution_time_ms=execution_time_ms,
            tokens_used=tokens_used_val, # Placeholder
            error_message=error_message_str
        )
        task_session.add(db_test_result)
        await task_session.commit()
        logger.info(f"Stored TestResult for TestRun {test_run_id}, LLM {target_llm_id}, Item {mock_data_item.id}")

async def execute_test_run_background(
    db_session_maker: sessionmaker, # Pass the session factory
    test_run_id: int,
    master_prompt_content: str,
    mock_data_item_ids: List[int], # Pass IDs to fetch items in background task
    target_llm_ids: List[str],
    master_schema_content: Dict[Any, Any]
):
    logger.info(f"Background task started for TestRun ID: {test_run_id}")
    async with db_session_maker() as db: # Create a new session for this background task
        try:
            # Fetch mock data items within the task using their IDs
            mock_data_items_stmt = select(db_models.MockDataItem).filter(db_models.MockDataItem.id.in_(mock_data_item_ids))
            mock_data_items_result = await db.execute(mock_data_items_stmt)
            mock_data_items = mock_data_items_result.scalars().all()

            if not mock_data_items:
                raise ValueError("No mock data items found for the provided IDs in background task.")

            # Update TestRun status to "running"
            test_run_obj = await db.get(db_models.TestRun, test_run_id)
            if not test_run_obj:
                logger.error(f"TestRun ID {test_run_id} not found in background task. Exiting.")
                return
            test_run_obj.status = "running"
            test_run_obj.started_at = datetime.utcnow() # Use UTC for consistency
            await db.commit()

            test_cases_count = 0
            for target_llm_id in target_llm_ids:
                for mock_item in mock_data_items:
                    await run_single_test_case(
                        db=db, # Pass the current session
                        test_run_id=test_run_id,
                        master_prompt_content=master_prompt_content,
                        mock_data_item=mock_item,
                        target_llm_id=target_llm_id,
                        master_schema_content=master_schema_content
                    )
                    test_cases_count += 1
            
            logger.info(f"Completed {test_cases_count} test cases for TestRun ID: {test_run_id}")
            test_run_obj.status = "completed"
        except Exception as e:
            logger.error(f"Error in background task for TestRun ID {test_run_id}: {e}", exc_info=True)
            if 'test_run_obj' in locals() and test_run_obj: # Check if test_run_obj was fetched
                test_run_obj.status = "failed"
                test_run_obj.error_message = str(e) # Add error message to TestRun if you add such a field
        finally:
            if 'test_run_obj' in locals() and test_run_obj:
                test_run_obj.completed_at = datetime.utcnow()
                await db.commit()
    logger.info(f"Background task finished for TestRun ID: {test_run_id}")


@router.post("/", response_model=pydantic_models.TestRunResponse, status_code=202) # 202 Accepted
async def create_and_initiate_test_run(
    test_run_create: pydantic_models.TestRunCreate,
    background_tasks: BackgroundTasks, # FastAPI's background tasks
    db: AsyncSession = Depends(get_db_session)
):
    """
    Initiates a new test run.
    - Select Target LLMs.
    - System iterates through LLMs and mock data, injects data into master prompt, sends to LLM.
    - Tests for different LLMs should run in parallel (handled by background tasks, actual parallelism per LLM not in this basic version).
    """
    logger.info(f"Request to create and initiate test run: {test_run_create.name or 'Unnamed Run'}")

    # 1. Validate foreign keys
    master_prompt = await db.get(db_models.MasterPrompt, test_run_create.master_prompt_id)
    if not master_prompt:
        raise HTTPException(status_code=404, detail=f"MasterPrompt with ID {test_run_create.master_prompt_id} not found.")

    mock_data_prompt = await db.get(
        db_models.MockDataPrompt, 
        test_run_create.mock_data_prompt_id,
        options=[selectinload(db_models.MockDataPrompt.generated_items)] # Load items
    )
    if not mock_data_prompt:
        raise HTTPException(status_code=404, detail=f"MockDataPrompt with ID {test_run_create.mock_data_prompt_id} not found.")
    if not mock_data_prompt.generated_items:
        raise HTTPException(status_code=400, detail=f"MockDataPrompt ID {test_run_create.mock_data_prompt_id} has no generated mock data items.")

    master_schema = await db.get(db_models.JsonSchema, test_run_create.master_schema_id)
    if not master_schema:
        raise HTTPException(status_code=404, detail=f"Master JsonSchema with ID {test_run_create.master_schema_id} not found.")
    if master_schema.status != "approved_master": # Or some other finalized status
         logger.warning(f"Test run initiated with schema ID {master_schema.id} which is not 'approved_master' (status: {master_schema.status}).")
         # Decide if this is a hard error or warning. For now, proceeding.
    
    # 2. Create TestRun DB record
    db_test_run = db_models.TestRun(
        name=test_run_create.name,
        master_prompt_id=test_run_create.master_prompt_id,
        mock_data_prompt_id=test_run_create.mock_data_prompt_id,
        target_llm_model_ids=test_run_create.target_llm_model_ids,
        master_schema_id=test_run_create.master_schema_id,
        status="queued" # Initial status
    )
    db.add(db_test_run)
    await db.commit()
    await db.refresh(db_test_run) # Get ID, created_at
    logger.info(f"TestRun record created with ID: {db_test_run.id}, status: {db_test_run.status}")

    # 3. Add the actual test execution to background tasks
    # Pass IDs of mock data items to avoid passing large ORM objects to background task
    mock_data_item_ids = [item.id for item in mock_data_prompt.generated_items]

    background_tasks.add_task(
        execute_test_run_background,
        db_session_maker=AsyncSessionFactory, # Pass the factory from database.py
        test_run_id=db_test_run.id,
        master_prompt_content=master_prompt.prompt_content,
        mock_data_item_ids=mock_data_item_ids,
        target_llm_ids=db_test_run.target_llm_model_ids,
        master_schema_content=master_schema.schema_content
    )
    logger.info(f"Test run ID {db_test_run.id} added to background tasks.")

    # Eagerly load results for the initial response (it will be empty as tasks run in background)
    await db.refresh(db_test_run, attribute_names=['results'])
    return db_test_run

@router.get("/", response_model=List[pydantic_models.TestRunResponse], summary="List All Test Runs")
async def list_test_runs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve a list of all test runs, with pagination.
    Each test run in the list will also include its detailed results.
    """
    logger.info(f"Request to list test runs: skip={skip}, limit={limit}")
    statement = select(db_models.TestRun).options(
        selectinload(db_models.TestRun.results), # Eager load the results for each run
        selectinload(db_models.TestRun.master_prompt), # Optionally load related master prompt
        selectinload(db_models.TestRun.mock_data_prompt), # Optionally load related mock data prompt
        selectinload(db_models.TestRun.master_schema) # Optionally load related master schema
    ).offset(skip).limit(limit).order_by(db_models.TestRun.id.desc()) # Show newest first
    
    result = await db.execute(statement)
    test_runs = result.scalars().unique().all() # Use .unique() because of multiple selectinload options
    
    logger.info(f"Retrieved {len(test_runs)} test runs.")
    return test_runs

@router.get("/{run_id}", response_model=pydantic_models.TestRunResponse, summary="Get a Specific Test Run")
async def get_test_run(
    run_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve the details of a specific test run by its ID,
    including all its associated test results and related configuration details.
    """
    logger.info(f"Request to get test run ID: {run_id}")
    
    # Fetch the TestRun and eagerly load its related results and configuration entities
    statement = select(db_models.TestRun).options(
        selectinload(db_models.TestRun.results),
        selectinload(db_models.TestRun.master_prompt),
        selectinload(db_models.TestRun.mock_data_prompt),
        selectinload(db_models.TestRun.master_schema)
    ).filter(db_models.TestRun.id == run_id)
    
    result = await db.execute(statement)
    test_run = result.scalars().unique().first() # Use .unique().first()

    if not test_run:
        logger.warning(f"TestRun with ID {run_id} not found.")
        raise HTTPException(status_code=404, detail=f"TestRun with ID {run_id} not found.")
    
    logger.info(f"Successfully retrieved TestRun ID: {test_run.id}, Status: {test_run.status}")
    return test_run

@router.get("/{run_id}/summary-by-llm", response_model=pydantic_models.TestRunOverallSummaryResponse, summary="Get Summary Statistics for a Test Run by LLM")
async def get_test_run_summary_by_llm(
    run_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieve aggregated summary statistics for a specific test run, broken down by each target LLM.
    Provides data for summary tables and visualizations.
    """
    logger.info(f"Request for summary by LLM for TestRun ID: {run_id}")

    # 1. Fetch the TestRun to confirm it exists and get its name
    db_test_run = await db.get(db_models.TestRun, run_id)
    if not db_test_run:
        raise HTTPException(status_code=404, detail=f"TestRun with ID {run_id} not found.")

    # 2. Fetch all TestResult records for this TestRun
    results_statement = select(db_models.TestResult).filter(db_models.TestResult.test_run_id == run_id)
    results_result = await db.execute(results_statement)
    all_test_results_for_run = results_result.scalars().all()

    if not all_test_results_for_run:
        logger.info(f"No test results found for TestRun ID: {run_id}. Returning empty summary.")
        return pydantic_models.TestRunOverallSummaryResponse(
            test_run_id=run_id,
            test_run_name=db_test_run.name,
            overall_total_tests=0,
            llm_summaries=[]
        )

    # 3. Aggregate results by target_llm_model_id
    llm_stats_temp = defaultdict(lambda: {
        "total_tests": 0,
        "successful_parses": 0,
        "schema_compliant_tests": 0,
        "execution_times": [],
        "tokens": []
    })

    for result in all_test_results_for_run:
        stats = llm_stats_temp[result.target_llm_model_id]
        stats["total_tests"] += 1
        if result.parse_status is True:
            stats["successful_parses"] += 1
        if result.schema_compliance_status == "Pass": # Assuming "Pass" string literal
            stats["schema_compliant_tests"] += 1
        if result.execution_time_ms is not None:
            stats["execution_times"].append(result.execution_time_ms)
        if result.tokens_used is not None:
            stats["tokens"].append(result.tokens_used)

    # 4. Prepare the response
    llm_summaries_response = []
    overall_total_tests = 0
    for llm_id, stats in llm_stats_temp.items():
        overall_total_tests += stats["total_tests"]
        avg_exec_time = sum(stats["execution_times"]) / len(stats["execution_times"]) if stats["execution_times"] else None
        total_tokens = sum(stats["tokens"]) if stats["tokens"] else None
        compliance_percentage = (stats["schema_compliant_tests"] / stats["total_tests"]) * 100 if stats["total_tests"] > 0 else 0.0
        
        llm_summaries_response.append(pydantic_models.LLMRunSummary(
            target_llm_model_id=llm_id,
            total_tests=stats["total_tests"],
            successful_parses=stats["successful_parses"],
            schema_compliant_tests=stats["schema_compliant_tests"],
            schema_compliance_percentage=round(compliance_percentage, 2),
            average_execution_time_ms=round(avg_exec_time, 2) if avg_exec_time is not None else None,
            total_tokens_used=total_tokens
        ))
    
    logger.info(f"Generated summary for TestRun ID: {run_id} with {len(llm_summaries_response)} LLM summaries.")
    return pydantic_models.TestRunOverallSummaryResponse(
        test_run_id=run_id,
        test_run_name=db_test_run.name,
        overall_total_tests=overall_total_tests,
        llm_summaries=llm_summaries_response
    )