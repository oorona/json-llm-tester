import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Corrected base path assuming this file is in backend/app/core/
BASE_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

def load_prompt(file_path_relative: str) -> str:
    """
    Loads a prompt from a file relative to the base prompts directory.
    Example: load_prompt("schema_generation/from_example_system.txt")
    """
    full_path = BASE_PROMPT_DIR / file_path_relative
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {full_path}")
        # Consider raising a more specific custom exception or re-raising FileNotFoundError
        raise FileNotFoundError(f"Prompt file not found: {full_path}")
    except Exception as e:
        logger.error(f"Error loading prompt file {full_path}: {e}")
        raise # Re-raise the original exception

def load_and_format_prompt(file_path_relative: str, **kwargs) -> str:
    """
    Loads a prompt template from a file and formats it with provided arguments.
    """
    template_str = load_prompt(file_path_relative)
    try:
        return template_str.format(**kwargs)
    except KeyError as e:
        logger.error(f"Missing key '{e}' in format arguments for prompt template {file_path_relative}")
        raise ValueError(f"Missing key '{e}' for prompt template {file_path_relative}")