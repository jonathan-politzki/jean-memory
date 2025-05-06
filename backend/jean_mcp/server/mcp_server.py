from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Dict, Optional

import logging
import asyncio
import json
import os
import sys

# Use the installed MCP package by its full path
sys.path.insert(0, '/usr/local/lib/python3.10/site-packages')
from mcp.server.fastmcp import FastMCP, Context, Image
from mcp.server.fastmcp.prompts import base
from starlette.middleware import Middleware

# Import our middleware
from .middleware import MCPAuthMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define application context with database access
@dataclass
class AppContext:
    """Application context with database and other dependencies."""
    db: Any  # Will be our database instance
    user_id: Optional[int] = None
    tenant_id: str = 'default'

# Initialize lifespan context manager
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with database connections."""
    logger.info("Starting Jean Memory MCP Server...")
    
    # Import here to avoid circular imports
    import database
    
    try:
        # Initialize database connection
        from app.config import settings
        db = await database.initialize_db(settings.database_url)
        logger.info("Database connection established")
        
        # Create the context with initial values
        context = AppContext(db=db)
        
        # For running directly with MCP CLI (e.g., mcp dev), get user credentials from env
        if os.getenv("JEAN_USER_ID"):
            try:
                context.user_id = int(os.getenv("JEAN_USER_ID"))
            except (ValueError, TypeError):
                logger.warning(f"Invalid JEAN_USER_ID environment variable: {os.getenv('JEAN_USER_ID')}")
        
        if os.getenv("JEAN_TENANT_ID"):
            context.tenant_id = os.getenv("JEAN_TENANT_ID")
        
        # Make the context available to middleware by storing in server.app.state
        if hasattr(server, "sse_app") and callable(server.sse_app):
            app = server.sse_app()
            if hasattr(app, "state"):
                app.state._mcp_lifespan_context = context
        
        # Yield the context to make it available to all MCP tools
        yield context
        
    except Exception as e:
        logger.exception(f"Error during MCP server startup: {e}")
        # Provide an empty context that tools can check for None values
        yield AppContext(db=None)
        
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down Jean Memory MCP Server...")
        await database.close_db()

# Create FastMCP server with lifespan and middleware
mcp = FastMCP(
    "JEAN Memory", 
    version="0.1.0",
    lifespan=app_lifespan,
    description="Personal Memory Layer for AI Assistants",
    middleware=[Middleware(MCPAuthMiddleware)]
)

# Register MCP initialization function
def initialize_mcp_server():
    """Initialize and register all tools and resources."""
    logger.info("Initializing MCP tools and resources...")
    
    # Import and register note tools
    from jean_mcp.tools.note_tools import register_note_tools
    register_note_tools(mcp)
    
    # Import and register github tools
    from jean_mcp.tools.github_tools import register_github_tools
    register_github_tools(mcp)
    
    # Import and register auth tools for configuration
    from jean_mcp.tools.auth_tools import register_auth_tools
    register_auth_tools(mcp)
    
    logger.info("MCP server initialization complete")
    return mcp

# This will be called when importing this module
mcp_server = initialize_mcp_server()

# If running directly, start the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mcp_server:mcp.sse_app()", host="0.0.0.0", port=8001, reload=True) 