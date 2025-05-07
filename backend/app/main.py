import uvicorn
import logging
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Optional, Dict, Any, List
import os
import json
import uuid
from datetime import datetime

# Load environment variables from .env file before other imports
load_dotenv()

from app.app import app # Import the app instance created by the factory
from app.config import settings
# Use the database singleton pattern
import database
from database.context_storage import ContextDatabase # Only for typing

# Import MCP server from our jean_mcp package
# from jean_mcp.server.mcp_server import mcp
# from jean_mcp.server.mcp_config import router as mcp_config_router

from .auth import verify_api_key, get_user_id
from .routers.github_oauth_router import GitHubOAuthRouter
from .routers.obsidian_router import ObsidianRouter
from .routers.google_auth_router import GoogleAuthRouter
from .gemini_api import GeminiAPI

logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("Starting JEAN MCP Server...")
    try:
        # Get the database singleton from app state
        db_instance = getattr(app.state, 'db', None)
        # If not found in app state, ensure it's initialized using the singleton
        if db_instance is None:
            if settings.database_url:
                logger.info("Database not found in app state, initializing from singleton...")
                db_instance = await database.initialize_db(settings.database_url)
                app.state.db = db_instance
            else:
                logger.warning("No DATABASE_URL provided. Running with no database support.")
        logger.info("Database initialization complete.")
        # Initialize other services if needed
        logger.info("Application startup sequence finished.")
    except Exception as e:
        logger.exception(f"FATAL: Error during application startup: {e}")
        logger.warning("Falling back to test mode due to database error.")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down JEAN MCP Server...")
    # Use the database singleton to close the connection
    await database.close_db()
    logger.info("Application shutdown sequence finished.")

# Mount the MCP server at the /mcp path
logger.info("MCP server integration temporarily disabled")

# Include MCP configuration routes
logger.info("MCP configuration routes temporarily disabled")

# Initialize database
# db = Database()

# Initialize API services
gemini_api = GeminiAPI(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize routers
github_router = GitHubOAuthRouter()
obsidian_router = ObsidianRouter(gemini_api=gemini_api)
google_auth_router = GoogleAuthRouter()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/mcp-config")
async def get_mcp_config(api_key: str = None):
    """Get MCP configuration for Claude Desktop"""
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")
    
    # In a production system, you would validate the API key here
    # and possibly retrieve user-specific configuration
    
    # Basic MCP configuration for now
    config = {
        "mcpServers": {
            "jean-memory": {
                "serverType": "HTTP",
                "serverUrl": os.getenv("JEAN_API_BASE_URL", "http://localhost:8001"),
                "headers": {
                    "X-API-Key": api_key,
                    "X-User-ID": "1"  # In production, this would be a real user ID
                }
            }
        }
    }
    
    return config

# GitHub Integration Routes
@app.get("/api/integrations/github/oauth/url")
async def get_github_oauth_url(request: Request, user_id: str = None):
    """Get GitHub OAuth URL for authorization"""
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    result = await github_router.get_oauth_url(user_id)
    return result

@app.get("/api/integrations/github/oauth/callback")
async def handle_github_oauth_callback(code: str, state: str):
    """Handle GitHub OAuth callback"""
    result = await github_router.handle_oauth_callback(code, state)
    if not result.get("success"):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": result.get("message", "Authentication failed")}
        )
    
    # In a real app, you might redirect to the frontend with a success message
    # For now, we'll just return the success response
    return result

@app.get("/api/integrations/github/status")
async def check_github_status(user_id: str):
    """Check GitHub connection status"""
    result = await github_router.check_connection_status(user_id)
    return result

@app.get("/api/integrations/github/data")
async def get_github_data(user_id: str):
    """Get GitHub repositories and settings"""
    result = await github_router.get_repositories(user_id)
    return result

@app.post("/api/integrations/github/settings")
async def save_github_settings(request: Request):
    """Save GitHub integration settings"""
    data = await request.json()
    user_id = data.get("userId")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    # Remove userId from settings before storing
    settings = {k: v for k, v in data.items() if k != "userId"}
    
    result = await github_router.save_settings(user_id, settings)
    return result

@app.post("/api/integrations/github/sync")
async def sync_github_repositories(request: Request):
    """Sync GitHub repositories"""
    data = await request.json()
    user_id = data.get("userId")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    result = await github_router.sync_repositories(user_id)
    return result

@app.post("/api/integrations/github/disconnect")
async def disconnect_github(request: Request):
    """Disconnect GitHub integration"""
    data = await request.json()
    user_id = data.get("userId")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    result = await github_router.disconnect(user_id)
    return result

# Obsidian Integration Routes
@app.get("/api/integrations/obsidian/status")
async def check_obsidian_status(user_id: str):
    """Check Obsidian connection status"""
    result = await obsidian_router.check_connection_status(user_id)
    return result

@app.post("/api/integrations/obsidian/connect")
async def connect_obsidian_vault(request: Request):
    """Connect to Obsidian vault"""
    data = await request.json()
    user_id = data.get("userId")
    vault_path = data.get("vaultPath")
    
    if not user_id or not vault_path:
        raise HTTPException(status_code=400, detail="User ID and vault path are required")
    
    result = await obsidian_router.connect_vault(user_id, vault_path)
    return result

@app.post("/api/integrations/obsidian/test")
async def test_obsidian_connection(request: Request):
    """Test connection to Obsidian vault"""
    data = await request.json()
    user_id = data.get("userId")
    vault_path = data.get("vaultPath")
    
    if not user_id or not vault_path:
        raise HTTPException(status_code=400, detail="User ID and vault path are required")
    
    result = await obsidian_router.test_connection(user_id, vault_path)
    return result

@app.get("/api/integrations/obsidian/settings")
async def get_obsidian_settings(user_id: str):
    """Get Obsidian integration settings"""
    result = await obsidian_router.get_settings(user_id)
    return result

@app.post("/api/integrations/obsidian/settings")
async def save_obsidian_settings(request: Request):
    """Save Obsidian integration settings"""
    data = await request.json()
    user_id = data.get("userId")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    # Remove userId from settings before storing
    settings = {k: v for k, v in data.items() if k != "userId"}
    
    result = await obsidian_router.save_settings(user_id, settings)
    return result

@app.post("/api/integrations/obsidian/sync")
async def sync_obsidian_vault(request: Request):
    """Sync Obsidian vault"""
    data = await request.json()
    user_id = data.get("userId")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    result = await obsidian_router.sync(user_id)
    return result

@app.post("/api/integrations/obsidian/disconnect")
async def disconnect_obsidian(request: Request):
    """Disconnect Obsidian integration"""
    data = await request.json()
    user_id = data.get("userId")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    result = await obsidian_router.disconnect(user_id)
    return result

# Google Auth Integration Routes
@app.get("/api/auth/google/url")
async def get_google_oauth_url(user_id: str = None):
    """Get Google OAuth URL for authorization"""
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    result = await google_auth_router.get_oauth_url(user_id)
    return result

@app.get("/api/auth/google/callback")
async def handle_google_oauth_callback(code: str, state: str):
    """Handle Google OAuth callback"""
    result = await google_auth_router.handle_oauth_callback(code, state)
    if not result.get("success"):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": result.get("message", "Authentication failed")}
        )
    
    if "redirect" in result:
        return RedirectResponse(url=result["redirect"])
    
    # Return the result as JSON if no redirect
    return result

@app.get("/api/auth/google/status")
async def check_google_status(user_id: str):
    """Check Google connection status"""
    result = await google_auth_router.check_connection_status(user_id)
    return result

@app.post("/api/auth/google/disconnect")
async def disconnect_google(request: Request):
    """Disconnect Google integration"""
    data = await request.json()
    user_id = data.get("userId")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    result = await google_auth_router.disconnect(user_id)
    return result

# Knowledge Graph API
@app.get("/api/knowledge/graph")
async def get_knowledge_graph(user_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Get knowledge graph data for visualization"""
    # In a real implementation, we would:
    # 1. Get notes from database based on filters
    # 2. Generate graph connections based on tags, links, etc
    # 3. Return formatted data for the visualization
    
    # For now, return sample data
    return {
        "success": True,
        "nodes": [
            {"id": "node1", "name": "Project Ideas", "type": "note", "source": "Obsidian"},
            {"id": "node2", "name": "Meeting Notes", "type": "note", "source": "Obsidian"},
            {"id": "node3", "name": "JEAN Memory Project", "type": "note", "source": "GitHub"}
        ],
        "links": [
            {"source": "node1", "target": "node3", "value": 2},
            {"source": "node2", "target": "node3", "value": 1}
        ]
    }

if __name__ == "__main__":
    logger.info(f"Starting server with Uvicorn on host 0.0.0.0 port 8080")
    # Note: Uvicorn handles the asyncio event loop when run this way.
    uvicorn.run(
        "app.main:app", # Reference the app object created in this file
        host="0.0.0.0",
        port=8080,
        reload=True # Enable reload for development (requires watchfiles)
        # Consider adding log_level="info" or other uvicorn settings
    ) 