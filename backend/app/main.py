import uvicorn
import logging
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file before other imports
load_dotenv()

from app.app import app # Import the app instance created by the factory
from app.config import settings
from app.app import ContextDatabase # Import db class from app where it was defined

logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize database and other resources on startup."""
    logger.info("Starting JEAN MCP Server...")
    try:
        # Properly initialize the database instance stored in app state
        db_instance: ContextDatabase = app.state.db
        await db_instance.initialize()
        logger.info("Database initialization complete.")
        # Initialize other services if needed
        # gemini_api_instance: GeminiAPI = app.state.gemini_api
        # router_instance: ContextRouter = app.state.context_router
        logger.info("Application startup sequence finished.")
    except Exception as e:
        logger.exception(f"FATAL: Error during application startup: {e}")
        # Optionally, exit the application if critical components fail
        # import sys
        # sys.exit(1)

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down JEAN MCP Server...")
    db_instance: ContextDatabase = app.state.db
    await db_instance.close()
    logger.info("Database pool closed.")
    logger.info("Application shutdown sequence finished.")

if __name__ == "__main__":
    logger.info(f"Starting server with Uvicorn on host 0.0.0.0 port 8000")
    # Note: Uvicorn handles the asyncio event loop when run this way.
    uvicorn.run(
        "app.main:app", # Reference the app object created in this file
        host="0.0.0.0",
        port=8000,
        reload=True # Enable reload for development (requires watchfiles)
        # Consider adding log_level="info" or other uvicorn settings
    ) 