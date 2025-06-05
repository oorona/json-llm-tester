# backend/app/core/config.py
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path # Ensure Path is imported

class Settings(BaseSettings):
    # Backend settings
    PYTHON_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = '%(levelname)s:     %(asctime)s - %(name)s - %(message)s' # Adjusted format slightly for clarity

    # LLM Service (e.g., LiteLLM proxy) settings
    LLM_SERVICE_URL: str = "http://localhost:4000"  # Default if not in .env
    LLM_SERVICE_API_KEY: str | None = None 
    DEFAULT_ASSISTANT_MODEL_ID: str = "default_assistant_model_in_code" # Default if not in .env

    @staticmethod
    def get_env_file_path() -> Path | None:
        # Assuming WORKDIR in Docker is /app 
        # And backend/app/* (where config.py lives) is copied to /app/app/*
        # So, __file__ for config.py would be /app/app/core/config.py
        # .parent -> /app/app/core
        # .parent.parent -> /app/app
        # .parent.parent.parent -> /app
        # Thus, it looks for /app/.env
        env_path_calculated = Path(__file__).resolve().parent.parent.parent / ".env"
        
        print(f"DEBUG [config.py - get_env_file_path]: __file__ is {Path(__file__).resolve()}")
        print(f"DEBUG [config.py - get_env_file_path]: Calculated env_path for .env: {env_path_calculated}")
        
        if env_path_calculated.exists():
            print(f"DEBUG [config.py - get_env_file_path]: {env_path_calculated} EXISTS.")
            return env_path_calculated
        else:
            # This else block will be hit if /app/.env is not found by the exists() check
            print(f"DEBUG [config.py - get_env_file_path]: {env_path_calculated} DOES NOT EXIST.")
            return None # Pydantic will then try CWD or only actual env vars

    model_config = SettingsConfigDict(
        env_file=get_env_file_path(), 
        env_file_encoding='utf-8',
        extra='ignore', # Ignore extra fields from .env not defined in Settings
        case_sensitive=False 
    )

@lru_cache()
def get_settings() -> Settings:
    print("DEBUG [config.py - get_settings]: Instantiating Settings...")
    return Settings()

settings = get_settings()

# --- Debug prints after Settings instantiation ---
print(f"DEBUG [config.py - post_settings_instantiation]: Attempted .env path via Settings.get_env_file_path(): {Settings.get_env_file_path()}") # Will re-run get_env_file_path if not cached properly by Pydantic for this call.
print(f"DEBUG [config.py - post_settings_instantiation]: Loaded LLM_SERVICE_URL from settings object: {settings.LLM_SERVICE_URL}")
print(f"DEBUG [config.py - post_settings_instantiation]: Loaded PYTHON_ENV from settings object: {settings.PYTHON_ENV}")
print(f"DEBUG [config.py - post_settings_instantiation]: Loaded LOG_LEVEL from settings object: {settings.LOG_LEVEL}")
# --- End Debug prints ---

# --- Basic logging configuration using loaded settings ---
# Convert string log level from settings to logging level int
numeric_log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(level=numeric_log_level, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__) # Logger for this module

# Log initial settings loaded by the application
logger.info(f"Application environment (PYTHON_ENV): {settings.PYTHON_ENV}")
logger.info(f"Logging level set to: {settings.LOG_LEVEL}")
logger.info(f"LLM Service URL configured: {settings.LLM_SERVICE_URL}")
if settings.LLM_SERVICE_API_KEY:
    logger.info(f"LLM Service API Key is set (masked): ****{settings.LLM_SERVICE_API_KEY[-4:] if len(settings.LLM_SERVICE_API_KEY) > 4 else '****'}")
else:
    logger.info("LLM Service API Key is not set (or empty).")
logger.info(f"Default Assistant Model ID: {settings.DEFAULT_ASSISTANT_MODEL_ID}")