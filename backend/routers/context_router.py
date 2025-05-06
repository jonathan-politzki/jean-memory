import asyncio
import logging
from typing import Dict, Any, Optional, List

# Assuming specialized routers are defined in other files in this directory
# from .github_router import GitHubRouter
# from .notes_router import NotesRouter
# ... etc

# Placeholder classes until implemented
class GitHubRouter:
    async def get_context(self, user_id: int, query: str) -> Dict[str, Any]: return {"type": "github", "content": "[GitHub context placeholder]"}
class NotesRouter:
    async def get_context(self, user_id: int, query: str) -> Dict[str, Any]: return {"type": "notes", "content": "[Notes context placeholder]"}
class ValuesRouter:
    async def get_context(self, user_id: int, query: str) -> Dict[str, Any]: return {"type": "values", "content": "[Values context placeholder]"}
class ConversationsRouter:
    async def get_context(self, user_id: int, query: str) -> Dict[str, Any]: return {"type": "conversations", "content": "[Conversations context placeholder]"}


logger = logging.getLogger(__name__)

def determine_context_type(query: str) -> str:
    """Analyze query to determine the most relevant context type(s)."""
    query_lower = query.lower()

    # Simple keyword matching (replace/enhance with NLP/LLM later)
    if any(term in query_lower for term in ["code", "repository", "github", "commit", "repo", "pr", "issue"]):
        return "github"
    elif any(term in query_lower for term in ["note", "notes", "wrote", "writing", "document", "obsidian"]):
        return "notes"
    elif any(term in query_lower for term in ["value", "preference", "important to me", "i like", "i dislike"]):
        return "values"
    elif any(term in query_lower for term in ["conversation", "discussed", "said", "told me", "meeting"]):
        return "conversations"
    else:
        # If no specific keywords, maybe default to a broader search or combination
        # For now, defaulting to comprehensive, but could also return None or a default type
        logger.info(f"Query did not match specific keywords, defaulting to comprehensive search.")
        return "comprehensive"

class ContextRouter:
    """Router that determines which specialized context to use and retrieves it."""

    def __init__(self, db, gemini_api):
        # TODO: Inject dependencies (db connection/pool, gemini api client)
        # self.db = db
        # self.gemini_api = gemini_api

        # Initialize specialized routers (passing dependencies)
        self.specialized_routers = {
            # "github": GitHubRouter(db, gemini_api),
            # "notes": NotesRouter(db, gemini_api),
            # "values": ValuesRouter(db, gemini_api),
            # "conversations": ConversationsRouter(db, gemini_api)
            # Using placeholders for now:
            "github": GitHubRouter(),
            "notes": NotesRouter(),
            "values": ValuesRouter(),
            "conversations": ConversationsRouter(),
        }
        logger.info("ContextRouter initialized with specialized routers.")

    async def route(self, user_id: int, query: str) -> Dict[str, Any]:
        """Route a query to the appropriate specialized router(s) and return context."""
        context_type = determine_context_type(query)
        logger.info(f"Determined context type '{context_type}' for query: '{query[:50]}...'")

        results: List[Dict[str, Any]] = []

        if context_type == "comprehensive":
            # Get context from multiple routers concurrently
            tasks = [
                router.get_context(user_id, query)
                for router_name, router in self.specialized_routers.items()
                # Optional: Add logic here to exclude certain routers based on query
            ]
            results = await asyncio.gather(*tasks)

        elif context_type in self.specialized_routers:
            # Use the specific router
            router = self.specialized_routers[context_type]
            result = await router.get_context(user_id, query)
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