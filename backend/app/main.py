import uvicorn
import logging
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file before other imports
load_dotenv()

from app.app import app # Import the app instance created by the factory
from app.config import settings
# Use the database singleton pattern
import database
from database.context_storage import ContextDatabase # Only for typing

logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("Starting JEAN MCP Server...")
    try:
        # Get the database singleton from app state
        db_instance = getattr(app.state, 'db', None)
        # If not found in app state, ensure it's initialized using the singleton
        if db_instance is None:
            if settings.database_url:
                logger.info("Database not found in app state, initializing from singleton...")
                db_instance = await database.initialize_db(settings.database_url)
                app.state.db = db_instance
            else:
                logger.warning("No DATABASE_URL provided. Running with no database support.")
        logger.info("Database initialization complete.")
        # Initialize other services if needed
        logger.info("Application startup sequence finished.")
    except Exception as e:
        logger.exception(f"FATAL: Error during application startup: {e}")
        logger.warning("Falling back to test mode due to database error.")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down JEAN MCP Server...")
    # Use the database singleton to close the connection
    await database.close_db()
    logger.info("Application shutdown sequence finished.")

if __name__ == "__main__":
    logger.info(f"Starting server with Uvicorn on host 0.0.0.0 port 8080")
    # Note: Uvicorn handles the asyncio event loop when run this way.
    uvicorn.run(
        "app.main:app", # Reference the app object created in this file
        host="0.0.0.0",
        port=8080,
        reload=True # Enable reload for development (requires watchfiles)
        # Consider adding log_level="info" or other uvicorn settings
    ) 