from fastapi import FastAPI, Request, HTTPException, Depends
import logging
from typing import Any, Optional

# Use absolute imports from the 'backend' root directory
from .config import settings
from .models import MCPRequest, MCPResponse, MCPResult, MCPStoreParams, MCPRetrieveParams
from .middleware import verify_api_key
from routers.context_router import ContextRouter # Changed from ..routers
from database.context_storage import ContextDatabase # Changed from ..database
from services.gemini_api import GeminiAPI # Changed from ..services

# --- Logging Setup ---
# Basic logging config - customize as needed
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
def create_app():
    app = FastAPI(
        title="JEAN MCP Server",
        description="JEAN Personal Memory Layer via Model Context Protocol.",
        version="0.1.0",
        dependencies=[Depends(verify_api_key)] # Apply API key verification globally
    )

    # --- TEMPORARY: Skip real DB/Gemini initialization for testing ---
    app.state.db = None # No database connection
    app.state.gemini_api = None # No Gemini client
    # Pass None for dependencies; the router/endpoints will need to handle this
    # Use the imported classes directly now
    app.state.context_router = ContextRouter(db=None, gemini_api=None)
    logger.warning("!!! Using placeholder dependencies (No DB, No Gemini) !!!")
    # --- END TEMPORARY SECTION ---

    # --- API Endpoints ---
    @app.get("/health", tags=["System"])
    async def health_check():
        """Simple health check endpoint."""
        # In the future, could add checks for DB and Gemini connectivity
        return {"status": "ok"}

    @app.post("/mcp",
              response_model=MCPResponse,
              tags=["MCP"],
              summary="Main MCP Endpoint")
    async def mcp_endpoint(request: Request, mcp_request: MCPRequest) -> MCPResponse:
        """Handles MCP store and retrieve operations."""
        user_id = getattr(request.state, 'user_id', None)
        if not user_id:
            # This should theoretically be caught by middleware, but double-check
            logger.error("MCP endpoint reached without user_id in request state.")
            return MCPResponse(error={"code": -32000, "message": "Authentication failed"})

        logger.info(f"MCP request received: Method='{mcp_request.method}' for User='{user_id}'")

        method = mcp_request.method
        params = mcp_request.params

        try:
            if method == "retrieve":
                retrieve_params = MCPRetrieveParams(**params)
                router: ContextRouter = request.app.state.context_router
                result_data = await router.route(user_id, retrieve_params.query)
                return MCPResponse(result=MCPResult(**result_data))

            elif method == "store":
                store_params = MCPStoreParams(**params)
                db: Optional[ContextDatabase] = request.app.state.db
                if db:
                     await db.store_context(
                         user_id=user_id,
                         context_type=store_params.context_type,
                         content=store_params.content,
                         source_identifier=store_params.source_identifier
                     )
                     logger.info("Context stored (if DB was connected).")
                     stored_status = True
                else:
                     logger.warning("DB not available, skipping context storage.")
                     stored_status = False
                return MCPResponse(result=MCPResult(type="success", content={"stored": stored_status}))
            else:
                logger.warning(f"Unsupported MCP method received: {method}")
                return MCPResponse(error={"code": -32601, "message": f"Method '{method}' not found"})

        except Exception as e:
            logger.exception(f"Error processing MCP request (Method: {method}) for user {user_id}: {e}")
            # Pydantic validation errors could be caught separately for 400 errors
            return MCPResponse(error={"code": -32000, "message": f"Internal server error: {str(e)}"})

    # Placeholder for Google Auth Callback - to be implemented fully later
    @app.get("/auth/google/callback", tags=["Authentication"])
    async def auth_google_callback(request: Request, code: str):
         logger.info(f"Received Google OAuth callback with code: {code[:10]}...")
         # 1. Exchange code for tokens with Google
         # 2. Get user info (google_id, email) from Google
         # 3. Call db.create_or_get_user(google_id, email)
         # --- TEMPORARY: Skip DB interaction ---
         db: Optional[ContextDatabase] = request.app.state.db
         if db:
             user_id, api_key = await db.create_or_get_user(google_id, email)
             api_key_display = api_key[:5]+"..."
         else:
             logger.warning("DB not available, using placeholder user data.")
             user_id = 999 # Placeholder
             api_key_display = "TEST_API_KEY..."
         # --- END TEMPORARY SECTION ---

         # In a real app, redirect to frontend with user info/status
         return {"message": "Authentication placeholder successful", "user_id": user_id, "api_key": api_key_display}

    return app

# Create the app instance using the factory
app = create_app() 