import logging
from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader

# Assume ContextDatabase is available via dependency injection or global state
# from ..database.context_storage import ContextDatabase
# from .dependencies import get_db

logger = logging.getLogger(__name__)

# Define the header for the API key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False) # auto_error=False to handle missing key manually

async def verify_api_key(request: Request, api_key: str = Depends(api_key_header)):
    """Dependency to verify API key from header and attach user_id to request state."""
    # Allow unauthenticated access to docs, health checks, etc.
    # Adjust the path check as needed for your routes
    allowed_paths = ["/docs", "/openapi.json", "/health", "/auth/google/callback"] # Add auth callback
    if request.url.path in allowed_paths or request.url.path.startswith("/frontend") or request.method == "OPTIONS":
        logger.debug(f"Skipping API key verification for path: {request.url.path}")
        return

    if not api_key:
        logger.warning("API key missing from request header.")
        raise HTTPException(status_code=401, detail="API key required")

    try:
        # --- TEMPORARY: Use placeholder validation directly ---
        # db: Optional[ContextDatabase] = getattr(request.app.state, 'db', None)
        # if db:
        #     user_id = await db.validate_api_key(api_key)
        # else:
        #     logger.warning("DB not available for API key validation, using placeholder.")
        #     if api_key == "TEST_API_KEY":
        #         user_id = 1 # Placeholder user ID
        #     else:
        #         user_id = None
        # Simplified placeholder check:
        if api_key == "TEST_API_KEY":
             user_id = 1 # Placeholder user ID
             logger.info("Using placeholder API Key validation.")
        else:
             user_id = None
             logger.warning("Placeholder validation failed for key: %s", api_key[:5]+"...")
        # --- END TEMPORARY SECTION ---

        if not user_id:
            logger.warning(f"Invalid API key received (placeholder check): {api_key[:5]}...")
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Attach user_id to request state for use in endpoint handlers
        request.state.user_id = user_id
        logger.debug(f"API key validated successfully for user_id: {user_id}")

    except HTTPException as e:
        # Re-raise HTTPExceptions directly
        raise e
    except Exception as e:
        logger.exception(f"Authentication error during API key validation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during authentication") 