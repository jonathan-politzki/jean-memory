import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class GitHubRouter:
    """Router for GitHub context."""

    def __init__(self, db = None, gemini_api = None):
        self.db = db
        self.gemini_api = gemini_api
        # TODO: Initialize GitHubClient service if needed
        logger.info("GitHubRouter initialized.")

    async def get_raw_context(self, user_id: int) -> List[Dict[str, Any]]:
        """Get raw GitHub context from database or external API."""
        logger.info(f"Fetching raw GitHub context for user {user_id}...")
        # 1. Check database (implement specific method in ContextDatabase if desired)
        # db_context = await self.db.get_all_context_by_type(user_id, "github")
        # if db_context:
        #    logger.info(f"Found {len(db_context)} GitHub context items in DB for user {user_id}.")
        #    return db_context

        # 2. Fetch from GitHub API (Placeholder)
        logger.warning(f"GitHub API fetching not implemented yet. Returning placeholder data.")
        # github_client = GitHubClient(user_id) # Requires GitHubClient service
        # context = await github_client.get_repositories()
        context = [
            {"name": "jean-memory", "description": "This repo", "files": [{"path": "README.md", "content": "# JEAN..."}]},
            {"name": "other-project", "description": "Another project"}
        ]

        # 3. Store for future use (Placeholder - needs proper data structure)
        # for repo_context in context:
        #    source_id = repo_context.get("name") # Or URL?
        #    if source_id:
        #        await self.db.store_context(user_id, "github", repo_context, source_identifier=source_id)

        return context

    async def get_context(self, user_id: int, query: str) -> Dict[str, Any]:
        """Get and process GitHub context for a user and query."""
        logger.info(f"Processing GitHub context for user {user_id} query: '{query[:50]}...'")
        # 1. Get raw context
        raw_context = await self.get_raw_context(user_id)
        if not raw_context:
            return {"type": "github", "content": "No GitHub context found."}

        # 2. Process with Gemini
        # processed_context = await self.gemini_api.process(
        #     "github",
        #     raw_context,
        #     query
        # )
        # Placeholder:
        processed_context = f"[Processed GitHub context for query: {query}]"

        return {
            "type": "github",
            "content": processed_context
        } 