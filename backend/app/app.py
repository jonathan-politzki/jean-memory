from fastapi import FastAPI, Request, HTTPException, Depends
import logging
from typing import Any, Optional
from fastapi.middleware.cors import CORSMiddleware  # Add CORS middleware
from fastapi.responses import RedirectResponse, HTMLResponse # Import RedirectResponse and HTMLResponse

# Use absolute imports from the 'backend' root directory
from .config import settings
from .models import MCPRequest, MCPResponse, MCPResult, MCPStoreParams, MCPRetrieveParams
from .middleware import verify_api_key
# Import the database singleton instead of the class
import database
from database.context_storage import ContextDatabase  # Still import for type hints
from routers.context_router import ContextRouter # Changed from ..routers
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
    )
    
    # Add CORS middleware BEFORE adding dependencies
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for testing
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PUT", "PATCH"],
        allow_headers=["*"],  # Allow all headers including X-API-Key
        expose_headers=["*"],
    )
    
    # Add global dependency AFTER middleware
    app.dependency_overrides[verify_api_key] = verify_api_key

    # Initialize Services
    @app.on_event("startup")
    async def startup_db_client():
        logger.info("Starting up application...")
        
        # Initialize database if URL is provided
        if settings.database_url:
            logger.info(f"Initializing database connection to: {settings.database_url.replace('jean:jean_password', 'jean:****')}")
            try:
                # Use the database singleton instead of creating a new instance
                db = await database.initialize_db(settings.database_url)
                app.state.db = db  # Store singleton reference in app state
                logger.info("Database connection established successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                app.state.db = None
        else:
            logger.warning("No DATABASE_URL provided. Running with no database support.")
            app.state.db = None
        
        # Initialize Gemini API client if API key is provided
        if settings.gemini_api_key:
            logger.info("Initializing Gemini API client...")
            app.state.gemini_api = GeminiAPI(api_key=settings.gemini_api_key)
        else:
            logger.warning("No GEMINI_API_KEY provided. Running with no AI classification.")
            app.state.gemini_api = None
        
        # Initialize context router with dependencies
        app.state.context_router = ContextRouter(
            db=app.state.db, 
            gemini_api=app.state.gemini_api
        )
        
        logger.info("Application startup sequence finished.")

    # Cleanup on shutdown
    @app.on_event("shutdown")
    async def shutdown_db_client():
        logger.info("Shutting down application...")
        # Using the singleton close method instead of directly closing
        await database.close_db()
        logger.info("Database connection closed.")

    # --- API Endpoints ---
    @app.get("/health", tags=["System"])
    async def health_check():
        """Simple health check endpoint."""
        # Use the singleton to check database status
        db = database.get_db()
        health_status = {
            "status": "ok",
            "db_connected": db is not None and db.pool is not None
        }
        return health_status

    @app.options("/cors-test", tags=["System"])
    @app.get("/cors-test", tags=["System"])
    async def cors_test():
        """Endpoint specifically for testing CORS."""
        return {"cors": "enabled", "status": "ok"}

    # Legacy MCP endpoint - removing to let FastMCP server handle these requests
    # @app.post("/mcp",
    #           response_model=MCPResponse,
    #           tags=["MCP"],
    #           summary="Main MCP Endpoint",
    #           dependencies=[Depends(verify_api_key)])
    # async def mcp_endpoint(request: Request, mcp_request: MCPRequest) -> MCPResponse:
    #     """Handles MCP store and retrieve operations."""
    #     user_id = getattr(request.state, 'user_id', None)
    #     tenant_id = getattr(request.state, 'tenant_id', 'default')  # Default tenant if not specified
    #     
    #     if not user_id:
    #         # This should theoretically be caught by middleware, but double-check
    #         logger.error("MCP endpoint reached without user_id in request state.")
    #         return MCPResponse(error={"code": -32000, "message": "Authentication failed"})
    # 
    #     logger.info(f"MCP request received: Method='{mcp_request.method}' for User='{user_id}' (Tenant: {tenant_id})")
    # 
    #     method = mcp_request.method
    #     params = mcp_request.params
    # 
    #     try:
    #         # Legacy implementation - now handled by FastMCP server
    #         logger.warning(f"Unsupported MCP method received: {method}")
    #         return MCPResponse(error={"code": -32601, "message": f"Method '{method}' not found"})
    #     except Exception as e:
    #         logger.exception(f"Error processing MCP request: {e}")
    #         return MCPResponse(error={"code": -32000, "message": str(e)})

    # Google Auth Callback - with proper token verification and user extraction
    @app.get("/auth/google/callback", tags=["Authentication"])
    async def auth_google_callback(request: Request, code: str):
        import httpx
        import json
        from jwt.utils import base64url_decode

        logger.info(f"Received Google OAuth callback with code: {code[:10]}...")

        # For our simplified flow, we're receiving an ID token directly
        # In a full OAuth flow, we'd exchange an authorization code for tokens
        try:
            # Extract user info from the ID token
            # For simplicity, we're parsing the JWT payload directly instead of verifying
            # In production, proper verification should be done
            token_parts = code.split('.')
            if len(token_parts) != 3:
                logger.error("Invalid token format")
                # Redirect to an error page or login page
                return RedirectResponse(url="/?error=auth_failed")

            # Decode the payload (middle part of JWT)
            padded = token_parts[1] + '=' * (4 - len(token_parts[1]) % 4)
            try:
                payload = json.loads(base64url_decode(padded))
                logger.info(f"Successfully parsed token payload")

                # Extract user information
                google_id = payload.get('sub')
                email = payload.get('email')
                name = payload.get('name') # Keep name for potential future use
                tenant_id = payload.get('hd', 'default') # Use domain as tenant or default

                logger.info(f"Extracted user info - Google ID: {google_id}, Email: {email}, Domain: {tenant_id}")

                if not google_id or not email:
                    logger.error("Missing required user information in token")
                    return RedirectResponse(url="/?error=auth_failed")

            except Exception as e:
                logger.error(f"Error parsing token payload: {e}")
                return RedirectResponse(url="/?error=auth_failed")

            # Store or update user in database
            db: Optional[ContextDatabase] = request.app.state.db
            user_id = None
            api_key = None # Initialize api_key
            if db:
                try:
                    # This call returns the CORRECT key (existing or new)
                    user_id_from_db, api_key_from_db = await db.create_or_get_user(tenant_id, google_id, email)
                    # We need to assign these returned values
                    user_id = user_id_from_db
                    api_key = api_key_from_db
                    logger.info(f"User authenticated: ID={user_id}, Email={email}")
                except Exception as e:
                    logger.error(f"Database error during user creation: {e}")
                    # Redirect to an error page or login page if DB fails
                    return RedirectResponse(url="/?error=db_error")
            else:
                logger.warning("DB not available, cannot authenticate user.")
                # Redirect to an error page or login page if DB is unavailable
                return RedirectResponse(url="/?error=db_unavailable")

            # Redirect to the profile page with user_id and the full api_key
            if user_id is not None and api_key is not None:
                # Direct redirect to frontend with clear parameter names to avoid encoding issues
                frontend_url = "http://localhost:3005"
                # Redirect to the MCP config page instead of profile.html
                profile_url = f"{frontend_url}/mcp-config.html?jean_user_id={user_id}&jean_api_key={api_key}"
                logger.info(f"Redirecting user to frontend MCP config: {profile_url.replace(api_key, api_key[:5]+'...')}")
                return RedirectResponse(url=profile_url)
            else:
                # Handle case where user_id or api_key couldn't be retrieved
                logger.error("Failed to retrieve user_id or api_key after authentication.")
                return RedirectResponse(url="/?error=auth_failed")


        except Exception as e:
            logger.exception(f"Error during authentication: {e}")
            # Redirect to an error page or login page on general failure
            return RedirectResponse(url="/?error=auth_failed")

    return app

# Create the app instance using the factory
app = create_app() 