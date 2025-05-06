from fastapi import FastAPI, Request, HTTPException, Depends
import logging
from typing import Any

from .config import settings
from .models import MCPRequest, MCPResponse, MCPResult, MCPStoreParams, MCPRetrieveParams
from .middleware import verify_api_key
from ..routers.context_router import ContextRouter # Import the router
# Assume db and gemini_api instances are created and managed in main.py
# and potentially attached to app.state or passed via dependencies.

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

    # --- Placeholder for Dependency Initialization (actual init in main.py) ---
    # In a real app, db and gemini_api would be initialized in main.py
    # and made available, e.g., via app.state or a dependency injection system.
    # For now, we'll instantiate placeholders here, but this should be refactored.
    # This is NOT production-ready dependency management.
    from ..database.context_storage import ContextDatabase
    from ..services.gemini_api import GeminiAPI
    app.state.db = ContextDatabase(settings.database_url)
    app.state.gemini_api = GeminiAPI(settings.gemini_api_key)
    app.state.context_router = ContextRouter(app.state.db, app.state.gemini_api)
    logger.info("Placeholder DB, GeminiAPI, and ContextRouter initialized in app state.")


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
                # Access router from app state (replace with proper dependency injection later)
                router: ContextRouter = request.app.state.context_router
                result_data = await router.route(user_id, retrieve_params.query)
                return MCPResponse(result=MCPResult(**result_data))

            elif method == "store":
                store_params = MCPStoreParams(**params)
                # Access db from app state (replace with proper dependency injection later)
                db: ContextDatabase = request.app.state.db
                await db.store_context(
                    user_id=user_id,
                    context_type=store_params.context_type,
                    content=store_params.content,
                    source_identifier=store_params.source_identifier
                )
                # MCP store often doesn't require a content response, just success
                return MCPResponse(result=MCPResult(type="success", content={"stored": True}))
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
         # 4. Redirect user back to frontend, potentially with a session token or status
         # Placeholder response:
         google_id = "placeholder_google_id_for_" + code
         email = "placeholder@example.com"
         db: ContextDatabase = request.app.state.db
         user_id, api_key = await db.create_or_get_user(google_id, email)

         # In a real app, redirect to frontend with user info/status
         return {"message": "Authentication placeholder successful", "user_id": user_id, "api_key": api_key[:5]+"..."}

    return app

# Create the app instance using the factory
app = create_app() 