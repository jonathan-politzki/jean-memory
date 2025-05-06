import asyncio
import logging
from typing import Dict, Any, Optional, List

# Import the specialized router classes
from .github_router import GitHubRouter
from .notes_router import NotesRouter
from .values_router import ValuesRouter
from .conversations_router import ConversationsRouter
from .tasks_router import TasksRouter
from .work_router import WorkRouter
from .media_router import MediaRouter
from .locations_router import LocationsRouter

logger = logging.getLogger(__name__)

# This function is kept for backward compatibility or manual classification if needed
def determine_context_type_simple(query: str) -> str:
    """Basic keyword matching to determine context type - fallback method."""
    query_lower = query.lower()

    # Simple keyword matching 
    if any(term in query_lower for term in ["code", "repository", "github", "commit", "repo", "pr", "issue"]):
        return "github"
    elif any(term in query_lower for term in ["note", "notes", "wrote", "writing", "document", "obsidian"]):
        return "notes"
    elif any(term in query_lower for term in ["value", "preference", "important to me", "i like", "i dislike"]):
        return "values"
    elif any(term in query_lower for term in ["conversation", "discussed", "said", "told me", "meeting"]):
        return "conversations"
    elif any(term in query_lower for term in ["task", "todo", "project", "goal", "deadline", "schedule"]):
        return "tasks"
    elif any(term in query_lower for term in ["work", "job", "professional", "career", "industry"]):
        return "work"
    elif any(term in query_lower for term in ["video", "article", "podcast", "read", "watch", "book", "movie"]):
        return "media"
    elif any(term in query_lower for term in ["place", "travel", "location", "city", "country", "visit"]):
        return "locations"
    else:
        # If no specific keywords, default to comprehensive search
        logger.info(f"Query did not match specific keywords, defaulting to comprehensive search.")
        return "comprehensive"

class ContextRouter:
    """Router that determines which specialized context to use and retrieves it."""

    def __init__(self, db, gemini_api):
        # Store dependencies
        self.db = db
        self.gemini_api = gemini_api

        # Initialize specialized routers (passing dependencies)
        self.specialized_routers = {
            # Using placeholders for now:
            "github": GitHubRouter(),
            "notes": NotesRouter(),
            "values": ValuesRouter(),
            "conversations": ConversationsRouter(),
            "tasks": TasksRouter(),
            "work": WorkRouter(),
            "media": MediaRouter(),
            "locations": LocationsRouter(),
        }
        logger.info("ContextRouter initialized with specialized routers.")

    async def determine_context_type(self, query: str) -> str:
        """
        Determine the context type for a query using AI classification.
        Falls back to basic keyword matching if Gemini API is not available.
        """
        if self.gemini_api:
            try:
                # Use AI to classify the query
                context_type = await self.gemini_api.determine_context_type(query)
                logger.info(f"AI classified query as '{context_type}'")
                return context_type
            except Exception as e:
                logger.warning(f"Error using Gemini to classify query: {e}. Falling back to keyword matching.")
                return determine_context_type_simple(query)
        else:
            # Fall back to simple keyword matching if Gemini API isn't available
            logger.warning("Gemini API not available, using simple keyword matching for context type.")
            return determine_context_type_simple(query)

    async def route(self, user_id: int, tenant_id: str, query: str, context_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Route a query to the appropriate specialized router(s) and return context.
        
        Args:
            user_id: The user ID for which to retrieve context
            tenant_id: The tenant/organization ID for isolation
            query: The query to route
            context_type: Optional explicit context type (if not provided, will be determined autonomously)
        """
        # If context_type is not explicitly provided, determine it
        if not context_type:
            context_type = await self.determine_context_type(query)
            
        logger.info(f"Using context type '{context_type}' for query: '{query[:50]}...' (User: {user_id}, Tenant: {tenant_id})")

        results: List[Dict[str, Any]] = []

        if context_type == "comprehensive":
            # Get context from multiple routers concurrently
            tasks = [
                router.get_context(user_id, tenant_id, query)
                for router_name, router in self.specialized_routers.items()
                # Optional: Add logic here to exclude certain routers based on query
            ]
            results = await asyncio.gather(*tasks)

        elif context_type in self.specialized_routers:
            # Use the specific router
            router = self.specialized_routers[context_type]
            result = await router.get_context(user_id, tenant_id, query)
            results.append(result)
        else:
            logger.warning(f"No specialized router found for determined context type '{context_type}'.")
            # Maybe return an error or a default response
            return {"type": "error", "content": f"Could not handle context type: {context_type}"}

        # Combine results (simple merge for now, could be more sophisticated)
        if not results:
             return {"type": "no_context", "content": "No relevant context found for the query."}

        # If comprehensive, maybe combine content differently?
        # For now, just return the list of results or the single result.
        if context_type == "comprehensive" and len(results) > 1:
            # Filter out potential errors or placeholders if needed
            valid_results = [r for r in results if r.get("type") != "error"]
            # Simple combination: Join content strings? Or return structured list?
            # Returning structured list is likely more useful for the client/MCP response
            combined_content = "\n\n---\n\n".join([res.get('content', '') for res in valid_results])
            return {
                "type": "comprehensive",
                "content": combined_content, # Or maybe return the list: "details": valid_results
                "sources": [res.get("type") for res in valid_results]
            }
        elif results:
             return results[0] # Return the single result
        else:
             # Should be covered by the check above, but just in case
             return {"type": "no_context", "content": "No relevant context found for the query."}

    # This method might be better placed within the specialized routers themselves
    # async def get_raw_context(self, user_id, context_type, source_identifier=None):
    #     """Helper to get raw context, checking cache/DB first, then external API."""
    #     # 1. Check DB
    #     # db_context = await self.db.get_context(user_id, context_type, source_identifier)
    #     # if db_context:
    #     #     return db_context
    #     # 2. Fetch from external source (e.g., GitHub API via GitHubClient service)
    #     # client = self._get_external_client(context_type)
    #     # raw_context = await client.fetch_data(user_id, ...)
    #     # 3. Store in DB for future use
    #     # await self.db.store_context(user_id, context_type, raw_context, source_identifier)
    #     # return raw_context
    #     pass 