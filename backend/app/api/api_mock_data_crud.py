# backend/app/api/api_mock_data_crud.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import logging
from typing import List

from app.database import get_db_session
from app import db_models # SQLAlchemy models
from app import models as pydantic_models # Pydantic models

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mock-data", # Prefix for all routes in this module
    tags=["Mock Data Management (CRUD)"]
)

# --- Manage MockDataPrompt records ---
@router.get("/prompts/", response_model=List[pydantic_models.MockDataPromptResponse], summary="List All Mock Data Generation Prompts")
async def list_all_mock_data_prompts(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Request to list all mock data prompts: skip={skip}, limit={limit}")
    statement = select(db_models.MockDataPrompt).options(
        selectinload(db_models.MockDataPrompt.generated_items) # Eager load items
    ).offset(skip).limit(limit).order_by(db_models.MockDataPrompt.id.desc())
    result = await db.execute(statement)
    prompts = result.scalars().unique().all() # Use .unique() if selectinload causes duplicates
    return prompts

@router.get("/prompts/{prompt_id}", response_model=pydantic_models.MockDataPromptResponse, summary="Get a Specific Mock Data Prompt")
async def get_specific_mock_data_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Request to get mock data prompt ID: {prompt_id}")
    # Use options to load related items
    prompt = await db.get(
        db_models.MockDataPrompt, 
        prompt_id, 
        options=[selectinload(db_models.MockDataPrompt.generated_items)]
    )
    if not prompt:
        raise HTTPException(status_code=404, detail=f"MockDataPrompt with ID {prompt_id} not found.")
    return prompt

@router.delete("/prompts/{prompt_id}", status_code=204, summary="Delete a Mock Data Prompt and All Its Items")
async def delete_specific_mock_data_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Request to delete mock data prompt ID: {prompt_id}")
    prompt = await db.get(db_models.MockDataPrompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"MockDataPrompt with ID {prompt_id} not found.")
    await db.delete(prompt) # Cascade delete is configured in db_models.py
    await db.commit()
    logger.info(f"MockDataPrompt ID: {prompt_id} and its items deleted.")
    return None

# --- Manage MockDataItem records ---
@router.get("/prompts/{prompt_id}/items/", response_model=List[pydantic_models.MockDataItemResponse], summary="List Mock Data Items for a Specific Prompt")
async def list_items_for_prompt(
    prompt_id: int,
    skip: int = 0,
    limit: int = 1000, 
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Request to list items for mock data prompt ID: {prompt_id}")
    prompt_exists = await db.get(db_models.MockDataPrompt, prompt_id)
    if not prompt_exists:
        raise HTTPException(status_code=404, detail=f"MockDataPrompt with ID {prompt_id} not found.")
    
    statement = select(db_models.MockDataItem).filter(db_models.MockDataItem.prompt_id == prompt_id).offset(skip).limit(limit).order_by(db_models.MockDataItem.id)
    result = await db.execute(statement)
    items = result.scalars().all()
    return items

@router.post("/prompts/{prompt_id}/items/", response_model=pydantic_models.MockDataItemResponse, status_code=201, summary="Manually Add a Mock Data Item to a Prompt's Set")
async def manually_add_item_to_prompt_set(
    prompt_id: int,
    item_payload: pydantic_models.MockDataItemCreate,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Request to manually add item to mock data prompt ID: {prompt_id}")
    prompt_exists = await db.get(db_models.MockDataPrompt, prompt_id)
    if not prompt_exists:
        raise HTTPException(status_code=404, detail=f"MockDataPrompt with ID {prompt_id} not found.")
    
    db_item = db_models.MockDataItem(
        item_content=item_payload.item_content,
        prompt_id=prompt_id
    )
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    logger.info(f"Manually added MockDataItem ID: {db_item.id} to prompt ID: {prompt_id}")
    return db_item

@router.get("/items/{item_id}", response_model=pydantic_models.MockDataItemResponse, summary="Get a Specific Mock Data Item by Its ID")
async def get_specific_mock_data_item(
    item_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Request to get mock data item ID: {item_id}")
    item = await db.get(db_models.MockDataItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"MockDataItem with ID {item_id} not found.")
    return item

@router.put("/items/{item_id}", response_model=pydantic_models.MockDataItemResponse, summary="Update a Specific Mock Data Item")
async def update_specific_mock_data_item(
    item_id: int,
    item_payload: pydantic_models.MockDataItemUpdate, # Using specific update model
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Request to update mock data item ID: {item_id}")
    db_item = await db.get(db_models.MockDataItem, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail=f"MockDataItem with ID {item_id} not found.")
    
    update_data = item_payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
        
    await db.commit()
    await db.refresh(db_item)
    logger.info(f"MockDataItem ID: {item_id} updated.")
    return db_item

@router.delete("/items/{item_id}", status_code=204, summary="Delete a Specific Mock Data Item")
async def delete_specific_mock_data_item(
    item_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    logger.info(f"Request to delete mock data item ID: {item_id}")
    db_item = await db.get(db_models.MockDataItem, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail=f"MockDataItem with ID {item_id} not found.")
    
    await db.delete(db_item)
    await db.commit()
    logger.info(f"MockDataItem ID: {item_id} deleted.")
    return None