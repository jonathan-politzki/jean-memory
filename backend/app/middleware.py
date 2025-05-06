import logging
from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from typing import Optional

# Import the database singleton
import database
from database.context_storage import ContextDatabase

logger = logging.getLogger(__name__)

# Set up API key extraction from headers
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def verify_api_key(
    request: Request, 
    api_key_header_val: Optional[str] = Depends(api_key_header)
):
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
        logger.debug("Skipping API key check for /health")
        return True

    # Log incoming headers for debugging
    logger.debug(f"Middleware received headers: {dict(request.headers)}")
    logger.debug(f"Middleware received api_key_header_val (Authorization): {api_key_header_val}")

    # For testing, allow a special test API key
    # TODO: Remove this in production
    if api_key_header_val == "TEST_API_KEY" or request.headers.get("x-api-key") == "TEST_API_KEY":
        request.state.user_id = 999  # Test user ID
        request.state.tenant_id = request.headers.get("X-Tenant-ID", "default")
        logger.warning(f"Using test API key. Setting user_id=999, tenant={request.state.tenant_id}")
        return True

    # Extract API key from Authorization header
    api_key = None
    if api_key_header_val and api_key_header_val.startswith("Bearer "):
        api_key = api_key_header_val.replace("Bearer ", "")
        logger.debug(f"Extracted API key from Authorization header: {api_key[:5]}...")

    # Also check for x-api-key header as fallback
    if not api_key and "x-api-key" in request.headers:
        api_key = request.headers["x-api-key"]
        logger.debug(f"Extracted API key from x-api-key header: {api_key[:5]}...")

    # Get tenant ID from header or default to "default"
    tenant_id = request.headers.get("X-Tenant-ID", "default")
    logger.debug(f"Tenant ID set to: {tenant_id}")

    if not api_key:
        logger.warning(f"No API key found in headers for path {request.url.path}")
        raise HTTPException(status_code=401, detail="API key required")

    # Get database from singleton - never creates separate pools
    db = database.get_db()
    
    if db:
        logger.debug(f"Attempting to validate API key: {api_key[:5]}... against DB instance from singleton")
        try:
            user_id = await db.validate_api_key(api_key)
            logger.debug(f"db.validate_api_key returned user_id: {user_id}")
        except Exception as e:
            logger.exception(f"Exception calling db.validate_api_key for key {api_key[:5]}...: {e}")
            user_id = None # Treat exception as validation failure
            
        if user_id:
            # Store user_id and tenant_id in request state for use in endpoints
            request.state.user_id = user_id
            request.state.tenant_id = tenant_id
            logger.info(f"Middleware successfully authenticated user_id={user_id} tenant={tenant_id} for path {request.url.path}")
            return True
        else:
            logger.warning(f"Invalid API key provided (db.validate_api_key returned {user_id}): {api_key[:5]}... for path {request.url.path}")
            raise HTTPException(status_code=401, detail="Invalid API key")
    else:
        # If no database is configured, use test mode
        logger.warning(f"No database configured (db singleton is None), allowing API key {api_key[:5]}... in test mode for path {request.url.path}")
        request.state.user_id = 999  # Test user ID
        request.state.tenant_id = tenant_id
        return True 