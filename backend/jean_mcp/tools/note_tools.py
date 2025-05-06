"""
MCP tools for managing user notes in the JEAN Memory system.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger(__name__)

def register_note_tools(mcp: FastMCP):
    """Register all note-related tools with the MCP server."""
    logger.info("Registering note tools with MCP server")
    
    @mcp.tool()
    async def create_note(
        content: str, 
        tags: Optional[List[str]] = None, 
        context_type: str = "notes",
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Create a new note in the user's memory.
        
        Args:
            content: The content of the note
            tags: Optional list of tags to categorize the note
            context_type: The type of context (default: notes)
            ctx: MCP context object
        
        Returns:
            Dictionary with note details and success status
        """
        if not ctx or not ctx.request_context.lifespan_context.db:
            return {"success": False, "error": "Database not available"}
        
        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        tenant_id = ctx.request_context.lifespan_context.tenant_id
        
        if not user_id:
            return {"success": False, "error": "User ID not provided"}
        
        try:
            # Convert tags list to string if provided
            tags_str = ",".join(tags) if tags else ""
            
            # Store the note in the database
            note_id = await db.store_context(
                user_id=user_id,
                tenant_id=tenant_id,
                context_type=context_type,
                content=content,
                source_identifier=f"note-{datetime.utcnow().isoformat()}",
                metadata={"tags": tags_str}
            )
            
            return {
                "success": True,
                "note_id": note_id,
                "message": "Note created successfully"
            }
            
        except Exception as e:
            logger.exception(f"Error creating note: {e}")
            return {"success": False, "error": str(e)}
    
    @mcp.tool()
    async def search_notes(
        query: str, 
        context_type: str = "notes",
        limit: int = 10,
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Search for notes based on a query.
        
        Args:
            query: The search query
            context_type: The type of context to search (default: notes)
            limit: Maximum number of results to return
            ctx: MCP context object
        
        Returns:
            Dictionary with search results
        """
        if not ctx or not ctx.request_context.lifespan_context.db:
            return {"success": False, "error": "Database not available"}
        
        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        tenant_id = ctx.request_context.lifespan_context.tenant_id
        
        if not user_id:
            return {"success": False, "error": "User ID not provided"}
        
        try:
            # For now, use simple text search
            # Later we can enhance with vector search
            results = await db.search_context(
                user_id=user_id,
                tenant_id=tenant_id,
                context_type=context_type,
                query=query,
                limit=limit
            )
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.get("id"),
                    "content": result.get("content"),
                    "created_at": result.get("created_at"),
                    "tags": result.get("metadata", {}).get("tags", "").split(",") if result.get("metadata", {}).get("tags") else []
                })
            
            return {
                "success": True,
                "count": len(formatted_results),
                "results": formatted_results
            }
            
        except Exception as e:
            logger.exception(f"Error searching notes: {e}")
            return {"success": False, "error": str(e)}
    
    @mcp.tool()
    async def get_recent_notes(
        limit: int = 10,
        context_type: str = "notes",
        ctx: Context = None
    ) -> Dict[str, Any]:
        """Get the most recent notes.
        
        Args:
            limit: Maximum number of notes to return
            context_type: The type of context to retrieve (default: notes)
            ctx: MCP context object
        
        Returns:
            Dictionary with recent notes
        """
        if not ctx or not ctx.request_context.lifespan_context.db:
            return {"success": False, "error": "Database not available"}
        
        db = ctx.request_context.lifespan_context.db
        user_id = ctx.request_context.lifespan_context.user_id
        tenant_id = ctx.request_context.lifespan_context.tenant_id
        
        if not user_id:
            return {"success": False, "error": "User ID not provided"}
        
        try:
            # Get recent notes from the database
            results = await db.get_recent_context(
                user_id=user_id,
                tenant_id=tenant_id,
                context_type=context_type,
                limit=limit
            )
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.get("id"),
                    "content": result.get("content"),
                    "created_at": result.get("created_at"),
                    "tags": result.get("metadata", {}).get("tags", "").split(",") if result.get("metadata", {}).get("tags") else []
                })
            
            return {
                "success": True,
                "count": len(formatted_results),
                "results": formatted_results
            }
            
        except Exception as e:
            logger.exception(f"Error getting recent notes: {e}")
            return {"success": False, "error": str(e)}

    # Register resource endpoints for notes
    @mcp.resource("notes://recent/{limit}")
    async def notes_recent_resource(limit: int) -> str:
        """Get recent notes as a resource.
        
        This allows clients to directly access recent notes through a resource URI.
        """
        result = await get_recent_notes(limit=int(limit), ctx=None)
        if not result.get("success"):
            return f"Error retrieving notes: {result.get('error')}"
        
        notes = result.get("results", [])
        if not notes:
            return "No recent notes found."
        
        output = "# Recent Notes\n\n"
        for note in notes:
            created_at = note.get("created_at", "Unknown date")
            tags = note.get("tags", [])
            tags_str = ", ".join(tags) if tags else "No tags"
            
            output += f"## Note from {created_at}\n\n"
            output += f"{note.get('content')}\n\n"
            output += f"*Tags: {tags_str}*\n\n---\n\n"
        
        return output
    
    @mcp.resource("notes://search/{query}")
    async def notes_search_resource(query: str) -> str:
        """Search notes and return results as a resource.
        
        This allows clients to directly search notes through a resource URI.
        """
        result = await search_notes(query=query, ctx=None)
        if not result.get("success"):
            return f"Error searching notes: {result.get('error')}"
        
        notes = result.get("results", [])
        if not notes:
            return f"No notes found matching query: '{query}'"
        
        output = f"# Search Results for '{query}'\n\n"
        for note in notes:
            created_at = note.get("created_at", "Unknown date")
            tags = note.get("tags", [])
            tags_str = ", ".join(tags) if tags else "No tags"
            
            output += f"## Note from {created_at}\n\n"
            output += f"{note.get('content')}\n\n"
            output += f"*Tags: {tags_str}*\n\n---\n\n"
        
        return output 