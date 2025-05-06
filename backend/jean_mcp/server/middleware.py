"""
Middleware for the MCP server to handle authentication and request processing.
"""

import logging
import os
from typing import Optional, Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import database

logger = logging.getLogger(__name__)

class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle authentication for MCP requests."""
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process each request to authenticate and set user context."""
        # Extract authentication info from headers or environment variables
        api_key = self._get_api_key(request)
        user_id = self._get_user_id(request)
        tenant_id = self._get_tenant_id(request)
        
        # If no API key or user ID is provided, try to use environment variables
        # This is useful for local development and Claude Desktop integration
        if not api_key:
            api_key = os.getenv("JEAN_API_KEY")
        
        if not user_id:
            user_id_env = os.getenv("JEAN_USER_ID")
            if user_id_env:
                try:
                    user_id = int(user_id_env)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid JEAN_USER_ID environment variable: {user_id_env}")
        
        if not tenant_id:
            tenant_id = os.getenv("JEAN_TENANT_ID", "default")
        
        # If API key is provided but user ID is not, try to get user ID from database
        if api_key and not user_id:
            try:
                # Get the database instance
                db = await self._get_db()
                if db:
                    # Verify API key and get user ID
                    user = await db.get_user_by_api_key(api_key)
                    if user:
                        user_id = user.get("id")
                        if not tenant_id or tenant_id == "default":
                            tenant_id = user.get("tenant_id", "default")
            except Exception as e:
                logger.exception(f"Error verifying API key: {e}")
        
        # Store user info in request state
        request.state.user_id = user_id
        request.state.tenant_id = tenant_id
        request.state.api_key = api_key
        
        # Log authentication status (but mask the API key for security)
        if api_key:
            masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
            logger.debug(f"MCP request: API Key={masked_key}, User ID={user_id}, Tenant ID={tenant_id}")
        
        # Update the lifespan context with user ID and tenant ID
        # This makes them available to all MCP tools via ctx.request_context.lifespan_context
        try:
            # Get the existing lifespan context from the app state
            if hasattr(request.app, "state") and hasattr(request.app.state, "_mcp_lifespan_context"):
                lifespan_context = request.app.state._mcp_lifespan_context
                
                # Update user_id and tenant_id
                lifespan_context.user_id = user_id
                lifespan_context.tenant_id = tenant_id
        except Exception as e:
            logger.exception(f"Error updating lifespan context: {e}")
        
        # Continue processing the request
        response = await call_next(request)
        return response
    
    def _get_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request headers."""
        # Check various header formats
        headers = request.headers
        api_key = (
            headers.get("X-API-Key") or
            headers.get("x-api-key") or
            headers.get("Authorization")
        )
        
        # If Authorization header is used with Bearer format, extract the token
        if api_key and api_key.startswith("Bearer "):
            api_key = api_key[7:]
        
        return api_key
    
    def _get_user_id(self, request: Request) -> Optional[int]:
        """Extract user ID from request headers."""
        headers = request.headers
        user_id_str = (
            headers.get("X-User-ID") or
            headers.get("x-user-id")
        )
        
        # Convert to integer if possible
        if user_id_str:
            try:
                return int(user_id_str)
            except (ValueError, TypeError):
                logger.warning(f"Invalid user ID in request headers: {user_id_str}")
        
        return None
    
    def _get_tenant_id(self, request: Request) -> str:
        """Extract tenant ID from request headers."""
        headers = request.headers
        tenant_id = (
            headers.get("X-Tenant-ID") or
            headers.get("x-tenant-id") or
            "default"
        )
        
        return tenant_id
    
    async def _get_db(self):
        """Get the database instance."""
        try:
            # Get the database singleton
            return database.get_db()
        except Exception as e:
            logger.exception(f"Error getting database instance: {e}")
            return None 