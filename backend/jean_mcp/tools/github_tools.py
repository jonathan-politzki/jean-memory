"""
MCP tools for integrating with GitHub in the JEAN Memory system.
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger(__name__)

async def fetch_github_data(endpoint: str, token: str) -> Dict:
    """Fetch data from GitHub API."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.github.com/{endpoint}", headers=headers)
        response.raise_for_status()
        return response.json()

def register_github_tools(mcp: FastMCP):
    """Register all GitHub-related tools with the MCP server."""
    logger.info("Registering GitHub tools with MCP server")
    
    @mcp.tool()
    async def get_github_repos(
        limit: int = 5,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Get the user's GitHub repositories.
        
        Args:
            limit: Maximum number of repositories to return
            ctx: MCP context object
        
        Returns:
            Dictionary with GitHub repositories
        """
        if not ctx or not ctx.request_context.lifespan_context.db:
            return {"success": False, "error": "Database not available"}
        
        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        
        if not user_id:
            return {"success": False, "error": "User ID not provided"}
        
        try:
            # Get GitHub token from user settings
            user_settings = await db.get_user_settings_by_id(user_id)
            github_token = user_settings.get("github_token") if user_settings else None
            
            if not github_token:
                return {"success": False, "error": "GitHub token not configured"}
            
            # Fetch repositories from GitHub API
            repos = await fetch_github_data("user/repos?sort=updated&per_page=" + str(limit), github_token)
            
            formatted_repos = []
            for repo in repos:
                formatted_repos.append({
                    "name": repo.get("name"),
                    "full_name": repo.get("full_name"),
                    "description": repo.get("description"),
                    "url": repo.get("html_url"),
                    "stars": repo.get("stargazers_count"),
                    "forks": repo.get("forks_count"),
                    "updated_at": repo.get("updated_at")
                })
            
            return {
                "success": True,
                "count": len(formatted_repos),
                "repos": formatted_repos
            }
            
        except httpx.HTTPStatusError as e:
            logger.exception(f"GitHub API error: {e}")
            return {"success": False, "error": f"GitHub API error: {e.response.status_code}"}
        except Exception as e:
            logger.exception(f"Error fetching GitHub repositories: {e}")
            return {"success": False, "error": str(e)}
    
    @mcp.tool()
    async def get_github_activity(
        days: int = 7,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Get the user's recent GitHub activity.
        
        Args:
            days: Number of days to look back
            ctx: MCP context object
        
        Returns:
            Dictionary with GitHub activity
        """
        if not ctx or not ctx.request_context.lifespan_context.db:
            return {"success": False, "error": "Database not available"}
        
        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        
        if not user_id:
            return {"success": False, "error": "User ID not provided"}
        
        try:
            # Get GitHub token from user settings
            user_settings = await db.get_user_settings_by_id(user_id)
            github_token = user_settings.get("github_token") if user_settings else None
            
            if not github_token:
                return {"success": False, "error": "GitHub token not configured"}
            
            # Fetch user events from GitHub API
            events = await fetch_github_data("users/me/events", github_token)
            
            # Filter events by date
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            recent_events = []
            
            for event in events:
                event_date = datetime.fromisoformat(event.get("created_at").replace("Z", "+00:00"))
                if event_date >= cutoff_date:
                    recent_events.append({
                        "type": event.get("type"),
                        "repo": event.get("repo", {}).get("name"),
                        "created_at": event.get("created_at"),
                        "payload": {
                            key: value for key, value in event.get("payload", {}).items()
                            if key in ["ref", "ref_type", "description", "action"]
                        }
                    })
            
            return {
                "success": True,
                "count": len(recent_events),
                "events": recent_events
            }
            
        except httpx.HTTPStatusError as e:
            logger.exception(f"GitHub API error: {e}")
            return {"success": False, "error": f"GitHub API error: {e.response.status_code}"}
        except Exception as e:
            logger.exception(f"Error fetching GitHub activity: {e}")
            return {"success": False, "error": str(e)}

    # Register resource endpoint for GitHub activity
    @mcp.resource("github://activity/{days}")
    async def github_activity_resource(days: int) -> str:
        """Get GitHub activity as a resource.
        
        This allows clients to directly access GitHub activity through a resource URI.
        """
        result = await get_github_activity(days=int(days), ctx=None)
        if not result.get("success"):
            return f"Error retrieving GitHub activity: {result.get('error')}"
        
        events = result.get("events", [])
        if not events:
            return "No recent GitHub activity found."
        
        output = f"# GitHub Activity (Past {days} Days)\n\n"
        
        for event in events:
            event_type = event.get("type", "Unknown")
            repo = event.get("repo", "Unknown repository")
            created_at = event.get("created_at", "Unknown date")
            
            output += f"## {event_type} on {repo}\n"
            output += f"*{created_at}*\n\n"
            
            payload = event.get("payload", {})
            for key, value in payload.items():
                output += f"**{key}**: {value}\n"
            
            output += "\n---\n\n"
        
        return output 