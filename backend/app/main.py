# backend/app/main.py
from fastapi import FastAPI
import logging

from app.core.config import settings # For app-level configs
from app.database import create_db_and_tables, engine # For startup/shutdown
from fastapi.staticfiles import StaticFiles # Import StaticFiles
from fastapi.responses import FileResponse # To serve index.html for SPA routing
import os # To construct path for index.html

# Import your routers
from app.api import api_json_examples
from app.api import api_llm_operations 
from app.api import api_json_schemas 
from app.api import api_mock_data_crud
from app.api import api_master_prompts 
from app.api import api_test_runs

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLM JSON Generation Evaluator API",
    description="API for evaluating LLM JSON generation capabilities.",
    version="0.1.0",
)

# Include your routers
app.include_router(api_json_examples.router)
app.include_router(api_llm_operations.router)
app.include_router(api_json_schemas.router)
app.include_router(api_mock_data_crud.router)
app.include_router(api_master_prompts.router) 
app.include_router(api_test_runs.router)

static_files_dir = "/app/static_frontend" # Matches the COPY destination in Dockerfile
app.mount("/assets", StaticFiles(directory=os.path.join(static_files_dir, "assets")), name="spa_assets")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """
    Serves the index.html for SPA routing for any non-API, non-static file path.
    """
    index_html_path = os.path.join(static_files_dir, "index.html")
    if os.path.exists(index_html_path):
        return FileResponse(index_html_path)
    # You might want to return a 404 or another specific response if index.html is not found
    # For API routes, they should be defined before this catch-all.
    # If it's an actual static file not under /assets, this won't catch it unless you have a broader StaticFiles mount.
    # A simpler approach if all static files are in known subdirs (like /assets):
    # app.mount("/", StaticFiles(directory=static_files_dir, html=True), name="spa")
    # The 'html=True' serves index.html for directory requests.
    # However, for client-side routing, the catch-all GET route is often more robust.
    raise HTTPException(status_code=404, detail="Resource not found")





# Add other routers here as we create them (e.g., for api_json_schemas)

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup.")
    logger.info(f"Running in {settings.PYTHON_ENV} mode.")
    logger.info(f"LLM Service URL configured: {settings.LLM_SERVICE_URL}")
    if settings.LLM_SERVICE_API_KEY:
        logger.info(f"LLM Service API Key is set (masked): ****{settings.LLM_SERVICE_API_KEY[-4:] if len(settings.LLM_SERVICE_API_KEY) > 4 else '****'}")
    else:
        logger.info("LLM Service API Key is not set (or empty).")
    
    logger.info("Initializing database...")
    await create_db_and_tables()
    logger.info("Database initialization complete.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown.")
    await engine.dispose()
    logger.info("Database engine disposed.")

@app.get("/")
async def read_root():
    """
    Root path for the API.
    """
    logger.info("Root endpoint was called.")
    return {"message": "Welcome to the LLM JSON Generation Evaluator API!"}

# --- All other specific API endpoints (like /models, /testing/chat, /json-examples/*)
# --- should now be REMOVED from this file and live in their respective router files. ---