# backend/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings # We'll add a DATABASE_URL to settings

# Define the SQLite database URL.
# For SQLite, it will be like: "sqlite+aiosqlite:///./llm_evaluator.db"
# This means a file named llm_evaluator.db will be created in the root of the `backend` directory (or wherever the app is run from).
DATABASE_URL = f"sqlite+aiosqlite:///./{settings.PYTHON_ENV}_llm_evaluator.db"
# Using PYTHON_ENV in the DB name allows for separate dev/test databases if needed.

# Create an async SQLAlchemy engine.
# `echo=True` is useful for debugging, it logs all SQL statements. Set to False for production.
engine = create_async_engine(DATABASE_URL, echo=(settings.PYTHON_ENV == "development"))

# Create a session factory for creating AsyncSession instances.
# expire_on_commit=False is often recommended for FastAPI use cases
# to allow objects to be accessed after the session is committed.
AsyncSessionFactory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for declarative SQLAlchemy models.
# Our database models will inherit from this.
Base = declarative_base()

# Dependency to get a DB session in path operations
async def get_db_session() -> AsyncSession:
    """
    FastAPI dependency that provides a database session.
    It ensures the session is closed after the request.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit() # Commit changes if no exceptions
        except Exception:
            await session.rollback() # Rollback on error
            raise
        finally:
            await session.close() # Ensure session is closed

async def create_db_and_tables():
    """
    Creates all database tables defined by models inheriting from Base.
    This is typically called on application startup.
    """
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Uncomment to drop all tables on startup (for dev)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if they didn't exist).")

from . import db_models 

# Add a logger for database operations if not already configured globally
import logging
logger = logging.getLogger(__name__)
if not logger.handlers: # Avoid adding multiple handlers if already configured
    # Basic configuration if this module is used standalone or logger isn't set up
    logging.basicConfig(level=logging.INFO)


