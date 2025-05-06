from fastapi import FastAPI, Request, HTTPException, Depends
import logging
from typing import Any, Optional
from fastapi.middleware.cors import CORSMiddleware  # Add CORS middleware

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
                db = ContextDatabase(settings.database_url)
                await db.initialize()
                app.state.db = db
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
        
        logger.info("Application startup complete.")

    # Cleanup on shutdown
    @app.on_event("shutdown")
    async def shutdown_db_client():
        logger.info("Shutting down application...")
        if hasattr(app.state, "db") and app.state.db is not None:
            logger.info("Closing database connection...")
            await app.state.db.close()

    # --- API Endpoints ---
    @app.get("/health", tags=["System"])
    async def health_check():
        """Simple health check endpoint."""
        health_status = {
            "status": "ok",
            "db_connected": hasattr(app.state, "db") and app.state.db is not None
        }
        return health_status

    @app.options("/cors-test", tags=["System"])
    @app.get("/cors-test", tags=["System"])
    async def cors_test():
        """Endpoint specifically for testing CORS."""
        return {"cors": "enabled", "status": "ok"}

    @app.post("/mcp",
              response_model=MCPResponse,
              tags=["MCP"],
              summary="Main MCP Endpoint")
    async def mcp_endpoint(request: Request, mcp_request: MCPRequest) -> MCPResponse:
        """Handles MCP store and retrieve operations."""
        user_id = getattr(request.state, 'user_id', None)
        tenant_id = getattr(request.state, 'tenant_id', 'default')  # Default tenant if not specified
        
        if not user_id:
            # This should theoretically be caught by middleware, but double-check
            logger.error("MCP endpoint reached without user_id in request state.")
            return MCPResponse(error={"code": -32000, "message": "Authentication failed"})

        logger.info(f"MCP request received: Method='{mcp_request.method}' for User='{user_id}' (Tenant: {tenant_id})")

        method = mcp_request.method
        params = mcp_request.params

        try:
            if method == "retrieve":
                retrieve_params = MCPRetrieveParams(**params)
                router: ContextRouter = request.app.state.context_router
                
                # Pass context_type to router if provided
                result_data = await router.route(
                    user_id=user_id, 
                    tenant_id=tenant_id,
                    query=retrieve_params.query, 
                    context_type=retrieve_params.context_type
                )
                
                # Log the routing decision for debugging
                if retrieve_params.context_type:
                    logger.info(f"Used explicit context_type '{retrieve_params.context_type}' for query: {retrieve_params.query[:30]}...")
                else:
                    logger.info(f"Used autonomous routing for query: {retrieve_params.query[:30]}... (resulted in context_type: {result_data['type']})")
                
                return MCPResponse(result=MCPResult(**result_data))

            elif method == "store":
                store_params = MCPStoreParams(**params)
                db: Optional[ContextDatabase] = request.app.state.db
                if db:
                     await db.store_context(
                         user_id=user_id,
                         tenant_id=tenant_id,
                         context_type=store_params.context_type,
                         content=store_params.content,
                         source_identifier=store_params.source_identifier
                     )
                     logger.info(f"Context stored successfully for user {user_id}, type '{store_params.context_type}'")
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
                return {"message": "Authentication failed", "error": "Invalid token format"}
                
            # Decode the payload (middle part of JWT)
            padded = token_parts[1] + '=' * (4 - len(token_parts[1]) % 4)
            try:
                payload = json.loads(base64url_decode(padded))
                logger.info(f"Successfully parsed token payload")
                
                # Extract user information
                google_id = payload.get('sub')
                email = payload.get('email')
                name = payload.get('name')
                tenant_id = payload.get('hd', 'default')  # Use domain as tenant or default
                
                logger.info(f"Extracted user info - Google ID: {google_id}, Email: {email}, Domain: {tenant_id}")
                
                if not google_id or not email:
                    logger.error("Missing required user information in token")
                    return {"message": "Authentication failed", "error": "Missing user information"}
                    
            except Exception as e:
                logger.error(f"Error parsing token payload: {e}")
                return {"message": "Authentication failed", "error": "Token parsing error"}
        
            # Store or update user in database
            db: Optional[ContextDatabase] = request.app.state.db
            if db:
                try:
                    user_id, api_key = await db.create_or_get_user(tenant_id, google_id, email)
                    api_key_display = api_key[:5]+"..."
                    logger.info(f"User authenticated: ID={user_id}, Email={email}")
                except Exception as e:
                    logger.error(f"Database error during user creation: {e}")
                    user_id = 999  # Fallback to placeholder
                    api_key_display = "TEST_API_KEY"
            else:
                logger.warning("DB not available, using placeholder user data.")
                user_id = 999  # Placeholder
                api_key_display = "TEST_API_KEY"
            
            # In a real app, we'd redirect to the frontend with user info
            return {
                "message": "Authentication successful", 
                "user_id": user_id, 
                "api_key": api_key_display,
                "user_info": {
                    "name": name,
                    "email": email
                }
            }
            
        except Exception as e:
            logger.exception(f"Error during authentication: {e}")
            return {"message": "Authentication failed", "error": str(e)}

    return app

# Create the app instance using the factory
app = create_app() 