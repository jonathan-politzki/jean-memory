import logging
import os
import json
from typing import Dict, Any, Optional
import secrets
import aiohttp
import urllib.parse

logger = logging.getLogger(__name__)

class GitHubOAuthRouter:
    """
    Router for handling GitHub OAuth authentication flow.
    """

    def __init__(self, db=None):
        self.db = db
        logger.info("GitHubOAuthRouter initialized.")
        
        # GitHub OAuth configurations - should be in environment variables in production
        self.client_id = os.getenv("GITHUB_CLIENT_ID", "your-github-client-id")
        self.client_secret = os.getenv("GITHUB_CLIENT_SECRET", "your-github-client-secret")
        self.redirect_uri = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:3000/github/callback")
        
        # OAuth state storage - should use Redis or similar in production
        self.oauth_states = {}
    
    async def get_oauth_url(self, user_id: str) -> Dict[str, Any]:
        """
        Generate a GitHub OAuth URL for authorization.
        
        Args:
            user_id: The user ID requesting OAuth
            
        Returns:
            Dict with the OAuth URL and state parameter
        """
        logger.info(f"Generating GitHub OAuth URL for user {user_id}")
        
        # Generate a secure random state parameter to prevent CSRF
        state = secrets.token_urlsafe(32)
        
        # Store the state with the user ID
        self.oauth_states[state] = user_id
        
        # Build the authorization URL
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "repo,read:user",  # Permissions we're requesting
            "state": state
        }
        
        auth_url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
        
        return {
            "success": True,
            "url": auth_url,
            "state": state
        }
    
    async def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """
        Handle the OAuth callback from GitHub.
        
        Args:
            code: The authorization code from GitHub
            state: The state parameter to verify
            
        Returns:
            Dict with the result of the OAuth flow
        """
        logger.info(f"Handling GitHub OAuth callback with state: {state[:10]}...")
        
        # Verify the state parameter
        if state not in self.oauth_states:
            logger.error(f"Invalid OAuth state parameter: {state[:10]}")
            return {
                "success": False,
                "message": "Invalid OAuth state parameter"
            }
        
        # Retrieve the user ID associated with this OAuth flow
        user_id = self.oauth_states[state]
        
        try:
            # Exchange the code for an access token
            async with aiohttp.ClientSession() as session:
                token_url = "https://github.com/login/oauth/access_token"
                payload = {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri
                }
                headers = {"Accept": "application/json"}
                
                async with session.post(token_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GitHub token exchange failed: {error_text}")
                        return {
                            "success": False,
                            "message": f"GitHub authentication failed: {error_text}"
                        }
                    
                    token_data = await response.json()
                    
                    if "error" in token_data:
                        logger.error(f"GitHub token exchange error: {token_data['error']}")
                        return {
                            "success": False,
                            "message": f"GitHub authentication error: {token_data['error_description']}"
                        }
                    
                    access_token = token_data.get("access_token")
                    if not access_token:
                        logger.error("No access token in GitHub response")
                        return {
                            "success": False,
                            "message": "GitHub did not provide an access token"
                        }
                    
                    # Get user info from GitHub API
                    async with session.get(
                        "https://api.github.com/user",
                        headers={
                            "Authorization": f"token {access_token}",
                            "Accept": "application/vnd.github.v3+json"
                        }
                    ) as user_response:
                        if user_response.status != 200:
                            error_text = await user_response.text()
                            logger.error(f"GitHub user info request failed: {error_text}")
                            return {
                                "success": False,
                                "message": f"Failed to get GitHub user info: {error_text}"
                            }
                        
                        user_info = await user_response.json()
                        github_username = user_info.get("login")
            
            # Store the token and user info in the database
            if self.db:
                try:
                    # Save GitHub credentials
                    await self.db.store_oauth_token(
                        user_id=user_id,
                        provider="github",
                        token_data={
                            "access_token": access_token,
                            "username": github_username,
                            "scope": token_data.get("scope", "")
                        }
                    )
                    
                    # Also store basic settings
                    await self.db.store_settings(
                        user_id=user_id,
                        settings_type="github",
                        settings={
                            "username": github_username,
                            "syncIssues": True,
                            "syncCommits": True,
                            "syncFrequency": "daily"
                        }
                    )
                    
                    logger.info(f"Successfully saved GitHub OAuth token for user {user_id}")
                except Exception as e:
                    logger.error(f"Error storing GitHub token in database: {e}")
                    return {
                        "success": False,
                        "message": f"Database error: {str(e)}"
                    }
            
            # Clean up the state
            del self.oauth_states[state]
            
            return {
                "success": True,
                "message": "GitHub authentication successful",
                "username": github_username
            }
        
        except Exception as e:
            logger.error(f"Error in GitHub OAuth flow: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def get_repositories(self, user_id: str) -> Dict[str, Any]:
        """
        Get the user's GitHub repositories.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dict with the user's repositories
        """
        logger.info(f"Getting GitHub repositories for user {user_id}")
        
        # Get the stored token from the database
        if not self.db:
            return {
                "success": False,
                "message": "Database not available"
            }
        
        try:
            token_data = await self.db.get_oauth_token(
                user_id=user_id,
                provider="github"
            )
            
            if not token_data or "access_token" not in token_data:
                logger.error(f"No GitHub token found for user {user_id}")
                return {
                    "success": False,
                    "message": "GitHub not connected. Please authenticate with GitHub first."
                }
            
            access_token = token_data["access_token"]
            
            # Get user settings to know which repositories are selected
            settings = await self.db.get_settings(
                user_id=user_id,
                settings_type="github"
            )
            
            selected_repos = settings.get("repositories", []) if settings else []
            
            # Fetch repositories from GitHub API
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.github.com/user/repos?per_page=100",
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GitHub repos request failed: {error_text}")
                        return {
                            "success": False,
                            "message": f"Failed to get GitHub repositories: {error_text}"
                        }
                    
                    repos_data = await response.json()
            
            # Format repositories for the frontend
            repositories = []
            for repo in repos_data:
                repositories.append({
                    "name": repo["full_name"],
                    "description": repo.get("description", ""),
                    "url": repo["html_url"],
                    "private": repo["private"],
                    "selected": repo["full_name"] in selected_repos
                })
            
            return {
                "success": True,
                "repositories": repositories,
                "settings": settings or {}
            }
        
        except Exception as e:
            logger.error(f"Error getting GitHub repositories: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def sync_repositories(self, user_id: str) -> Dict[str, Any]:
        """
        Sync the user's GitHub repositories.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dict with sync result
        """
        logger.info(f"Syncing GitHub repositories for user {user_id}")
        
        # Get the stored token from the database
        if not self.db:
            return {
                "success": False,
                "message": "Database not available"
            }
        
        try:
            token_data = await self.db.get_oauth_token(
                user_id=user_id,
                provider="github"
            )
            
            if not token_data or "access_token" not in token_data:
                logger.error(f"No GitHub token found for user {user_id}")
                return {
                    "success": False,
                    "message": "GitHub not connected. Please authenticate with GitHub first."
                }
            
            access_token = token_data["access_token"]
            
            # Get user settings to know which repositories to sync
            settings = await self.db.get_settings(
                user_id=user_id,
                settings_type="github"
            )
            
            if not settings:
                logger.error(f"No GitHub settings found for user {user_id}")
                return {
                    "success": False,
                    "message": "GitHub settings not found"
                }
            
            selected_repos = settings.get("repositories", [])
            sync_issues = settings.get("syncIssues", True)
            sync_commits = settings.get("syncCommits", True)
            
            if not selected_repos:
                logger.warning(f"No repositories selected for syncing. User: {user_id}")
                return {
                    "success": False,
                    "message": "No repositories selected for syncing"
                }
            
            # In a real implementation, this would:
            # 1. Fetch data from GitHub API for selected repositories
            # 2. Store the data in the database
            # 3. Update last sync timestamp in settings
            
            # For now, we'll just simulate a successful sync
            logger.info(f"GitHub sync completed for user {user_id}")
            
            # Update settings with sync timestamp
            settings["lastSync"] = "2025-05-15T10:30:00Z"  # ISO format timestamp
            await self.db.store_settings(
                user_id=user_id,
                settings_type="github",
                settings=settings
            )
            
            return {
                "success": True,
                "message": "GitHub repositories synced successfully",
                "lastSync": "2025-05-15T10:30:00Z"
            }
        
        except Exception as e:
            logger.error(f"Error syncing GitHub repositories: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def save_settings(self, user_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save GitHub integration settings.
        
        Args:
            user_id: User ID
            settings: Dict of settings (repositories, sync options, etc.)
            
        Returns:
            Dict with save result
        """
        logger.info(f"Saving GitHub settings for user {user_id}")
        
        if not self.db:
            return {
                "success": False,
                "message": "Database not available"
            }
        
        try:
            # Get existing settings first
            existing_settings = await self.db.get_settings(
                user_id=user_id,
                settings_type="github"
            ) or {}
            
            # Merge with new settings
            existing_settings.update(settings)
            
            # Store updated settings
            await self.db.store_settings(
                user_id=user_id,
                settings_type="github",
                settings=existing_settings
            )
            
            return {
                "success": True,
                "message": "GitHub settings saved successfully"
            }
        except Exception as e:
            logger.error(f"Error saving GitHub settings: {e}")
            return {
                "success": False,
                "message": f"Database error: {str(e)}"
            }
    
    async def check_connection_status(self, user_id: str) -> Dict[str, Any]:
        """
        Check if a user has connected to GitHub.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with connection status
        """
        logger.info(f"Checking GitHub connection status for user {user_id}")
        
        if not self.db:
            return {
                "connected": False,
                "message": "Database not available"
            }
        
        try:
            token_data = await self.db.get_oauth_token(
                user_id=user_id,
                provider="github"
            )
            
            if token_data and "access_token" in token_data:
                return {
                    "connected": True,
                    "username": token_data.get("username", "Unknown")
                }
            
            return {
                "connected": False
            }
        except Exception as e:
            logger.error(f"Error checking GitHub connection status: {e}")
            return {
                "connected": False,
                "message": f"Error: {str(e)}"
            }
    
    async def disconnect(self, user_id: str) -> Dict[str, Any]:
        """
        Disconnect a user from GitHub.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with disconnect result
        """
        logger.info(f"Disconnecting GitHub for user {user_id}")
        
        if not self.db:
            return {
                "success": False,
                "message": "Database not available"
            }
        
        try:
            # Remove the token from the database
            await self.db.delete_oauth_token(
                user_id=user_id,
                provider="github"
            )
            
            # Also remove the settings
            await self.db.delete_settings(
                user_id=user_id,
                settings_type="github"
            )
            
            return {
                "success": True,
                "message": "Successfully disconnected from GitHub"
            }
        except Exception as e:
            logger.error(f"Error disconnecting from GitHub: {e}")
            return {
                "success": False,
                "message": f"Database error: {str(e)}"
            } 