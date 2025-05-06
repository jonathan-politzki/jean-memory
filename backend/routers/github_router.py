import logging
from typing import Dict, Any, List, Optional
import asyncio

logger = logging.getLogger(__name__)

class GitHubRouter:
    """
    Router for handling GitHub and code-related context.
    """

    def __init__(self, db=None, gemini_api=None):
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

    async def get_context(self, user_id: int, tenant_id: str, query: str) -> Dict[str, Any]:
        """
        Get GitHub-related context for a user's query, with tenant isolation
        
        Args:
            user_id: The user ID requesting context
            tenant_id: The tenant/organization ID for data isolation
            query: The user's query about GitHub repositories or code
            
        Returns:
            Dict with context information
        """
        logger.info(f"Getting GitHub context for user {user_id} (tenant: {tenant_id}) query: {query[:30]}...")
        
        # 1. Try to get context from database first (cached data)
        if self.db:
            try:
                cached_data = await self.db.get_context(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    context_type="github"
                )
                if cached_data:
                    logger.info(f"Found cached GitHub data for user {user_id} (tenant: {tenant_id})")
                    
                    # 2. Process with Gemini if available
                    if self.gemini_api:
                        processed_response = await self.gemini_api.process(
                            context_type="github", 
                            context_data=cached_data, 
                            query=query
                        )
                        return {"type": "github", "content": processed_response}
                    
                    # If no Gemini, return raw data
                    return {"type": "github", "content": str(cached_data)}
            except Exception as e:
                logger.error(f"Error retrieving GitHub context from database: {e}")
                # Continue to fetch from API as fallback
        
        # 3. If not in DB or DB error, fetch from GitHub API
        # This is a placeholder - in a real implementation, we would:
        # - Get the user's GitHub token from settings/DB
        # - Call GitHub API to fetch repositories, PRs, issues, etc.
        # - Store results in DB for future use
        # - Process with Gemini
        
        logger.warning("GitHub API fetching not implemented yet. Returning placeholder data.")
        
        # Placeholder data - would be real GitHub data in production
        github_data = [
            {
                "name": "sample-repo",
                "description": "A sample repository",
                "files": [
                    {"path": "main.py", "content": "print('Hello, world!')"},
                    {"path": "README.md", "content": "# Sample Repository\n\nThis is a sample."}
                ]
            }
        ]
        
        # Process with Gemini if available
        if self.gemini_api:
            try:
                processed_response = await self.gemini_api.process(
                    context_type="github", 
                    context_data=github_data, 
                    query=query
                )
                return {"type": "github", "content": processed_response}
            except Exception as e:
                logger.error(f"Error processing GitHub data with Gemini: {e}")
                # Fall back to returning raw data
        
        # Return raw data if Gemini processing failed or is unavailable
        return {"type": "github", "content": "[GitHub context placeholder]"} 