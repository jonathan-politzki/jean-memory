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
        # This is where you'd actually get the DB instance
        # For now, we assume a function get_db exists or it's attached elsewhere
        # db: ContextDatabase = request.app.state.db # Example if stored in app state

        # Placeholder for validation logic - replace with actual DB call
        # user_id = await db.validate_api_key(api_key)
        async def _placeholder_validate(key):
             # Replace with actual DB call using request.app.state.db.validate_api_key(key)
             if key == "TEST_API_KEY": return 1
             return None
        user_id = await _placeholder_validate(api_key)

        if not user_id:
            logger.warning(f"Invalid API key received: {api_key[:5]}...")
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