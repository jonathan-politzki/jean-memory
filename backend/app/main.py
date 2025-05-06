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
    """Initialize resources on startup (DB init temporarily skipped)."""
    logger.info("Starting JEAN MCP Server...")
    # --- TEMPORARY: Skip DB Initialization ---
    # try:
    #     db_instance: Optional[ContextDatabase] = getattr(app.state, 'db', None)
    #     if db_instance:
    #         await db_instance.initialize()
    #         logger.info("Database initialization complete (if DB was configured).")
    #     else:
    #         logger.warning("DB instance not found in app state during startup.")
    #     # Initialize other services if needed
    #     logger.info("Application startup sequence finished.")
    # except Exception as e:
    #     logger.exception(f"FATAL: Error during application startup: {e}")
    logger.warning("!!! Skipping Database initialization for testing !!!")
    # --- END TEMPORARY SECTION ---
    logger.info("Application startup sequence finished (without DB init).")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown (DB close temporarily skipped)."""
    logger.info("Shutting down JEAN MCP Server...")
    # --- TEMPORARY: Skip DB Close ---
    # db_instance: Optional[ContextDatabase] = getattr(app.state, 'db', None)
    # if db_instance:
    #     await db_instance.close()
    #     logger.info("Database pool closed (if DB was configured).")
    # else:
    #     logger.warning("DB instance not found in app state during shutdown.")
    logger.warning("!!! Skipping Database closing for testing !!!")
    # --- END TEMPORARY SECTION ---
    logger.info("Application shutdown sequence finished (without DB close).")

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