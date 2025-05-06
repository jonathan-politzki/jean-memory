import logging
from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from typing import Optional

# Assume ContextDatabase is available via dependency injection or global state
# from ..database.context_storage import ContextDatabase
# from .dependencies import get_db

logger = logging.getLogger(__name__)

# Set up API key extraction from headers
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def verify_api_key(request: Request, api_key_header: Optional[str] = Depends(api_key_header)):
    """
    Middleware to verify API key and set user_id and tenant_id in request state.
    
    Extracts API key from Authorization header (using Bearer token format)
    and tenant ID from X-Tenant-ID header (or defaults to "default").
    
    If API key is valid, sets:
    - request.state.user_id: User ID for the request
    - request.state.tenant_id: Tenant ID for multi-tenant isolation
    """
    # Skip API key check for health endpoint
    if request.url.path == "/health":
        return True
    
    # For testing, allow a special test API key
    # TODO: Remove this in production
    if api_key_header == "TEST_API_KEY" or request.headers.get("x-api-key") == "TEST_API_KEY":
        request.state.user_id = 999  # Test user ID
        request.state.tenant_id = request.headers.get("X-Tenant-ID", "default")
        logger.warning(f"Using test API key with user_id=999, tenant={request.state.tenant_id}")
        return True
    
    # Extract API key from Authorization header
    api_key = None
    if api_key_header and api_key_header.startswith("Bearer "):
        api_key = api_key_header.replace("Bearer ", "")
    
    # Also check for x-api-key header as fallback
    if not api_key and "x-api-key" in request.headers:
        api_key = request.headers["x-api-key"]
    
    # Get tenant ID from header or default to "default"
    tenant_id = request.headers.get("X-Tenant-ID", "default")
    
    if not api_key:
        logger.warning("No API key provided in request")
        raise HTTPException(status_code=401, detail="API key required")
    
    # Verify API key in database
    db: Optional[ContextDatabase] = request.app.state.db
    if db:
        user_id = await db.validate_api_key(api_key)
        if user_id:
            # Store user_id and tenant_id in request state for use in endpoints
            request.state.user_id = user_id
            request.state.tenant_id = tenant_id
            logger.info(f"Authenticated user_id={user_id} tenant={tenant_id}")
            return True
        else:
            logger.warning(f"Invalid API key provided: {api_key[:5]}...")
            raise HTTPException(status_code=401, detail="Invalid API key")
    else:
        # If no database is configured, use test mode
        logger.warning("No database configured, allowing all API keys in test mode")
        request.state.user_id = 999  # Test user ID
        request.state.tenant_id = tenant_id
        return True 