import os
import logging
import aiohttp
import json
import uuid
from typing import Dict, Any, Optional, List
import base64
from datetime import datetime

logger = logging.getLogger(__name__)

class GitHubOAuthRouter:
    def __init__(self, db):
        self.db = db
        self.client_id = os.getenv("GITHUB_CLIENT_ID")
        self.client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/api/integrations/github/oauth/callback")
        self.oauth_url = "https://github.com/login/oauth/authorize"
        self.token_url = "https://github.com/login/oauth/access_token"
        self.api_base = "https://api.github.com"
        
        # Ensure environment variables are set
        if not self.client_id or not self.client_secret:
            logger.warning("GitHub OAuth credentials not set. Integration will not work properly.")
    
    async def get_oauth_url(self, user_id: str) -> Dict[str, Any]:
        """
        Generate GitHub OAuth URL for authorization
        """
        if not self.client_id:
            return {"success": False, "message": "GitHub OAuth client ID not configured"}
        
        # Generate a random state for CSRF protection
        state = f"{user_id}:{uuid.uuid4().hex}"
        
        # Store state in database for verification during callback
        await self.db.execute(
            "INSERT INTO github_oauth_states (user_id, state, created_at) VALUES ($1, $2, $3)",
            user_id, state, datetime.now()
        )
        
        # Build OAuth URL
        oauth_url = f"{self.oauth_url}?client_id={self.client_id}&redirect_uri={self.redirect_uri}&scope=repo&state={state}"
        
        return {
            "success": True,
            "oauth_url": oauth_url
        }
    
    async def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """
        Handle GitHub OAuth callback and exchange code for access token
        """
        # Verify state to prevent CSRF attacks
        state_parts = state.split(":")
        if len(state_parts) != 2:
            return {"success": False, "message": "Invalid state format"}
        
        user_id = state_parts[0]
        
        # Check if state exists in database
        state_record = await self.db.fetchrow(
            "SELECT * FROM github_oauth_states WHERE user_id = $1 AND state = $2",
            user_id, state
        )
        
        if not state_record:
            return {"success": False, "message": "Invalid or expired state"}
        
        # Exchange code for access token
        async with aiohttp.ClientSession() as session:
            headers = {"Accept": "application/json"}
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
                "state": state
            }
            
            async with session.post(self.token_url, headers=headers, data=data) as response:
                if response.status != 200:
                    return {"success": False, "message": "Failed to exchange code for access token"}
                
                response_data = await response.json()
                
                if "error" in response_data:
                    return {"success": False, "message": response_data.get("error_description", "Unknown error")}
                
                access_token = response_data.get("access_token")
                token_type = response_data.get("token_type", "bearer")
                scope = response_data.get("scope", "")
                
                # Store access token in database
                await self.db.execute(
                    """
                    INSERT INTO github_connections (user_id, access_token, token_type, scope, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET access_token = $2, token_type = $3, scope = $4, updated_at = $6
                    """,
                    user_id, access_token, token_type, scope, datetime.now(), datetime.now()
                )
                
                # Clean up state
                await self.db.execute(
                    "DELETE FROM github_oauth_states WHERE user_id = $1",
                    user_id
                )
                
                # Fetch user information
                user_info = await self._fetch_github_user(access_token)
                
                return {
                    "success": True,
                    "message": "GitHub connected successfully",
                    "user_info": user_info
                }
    
    async def check_connection_status(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user has GitHub connected and token is valid
        """
        connection = await self.db.fetchrow(
            "SELECT * FROM github_connections WHERE user_id = $1",
            user_id
        )
        
        if not connection:
            return {"connected": False, "message": "GitHub not connected"}
        
        # Verify token is valid by making a test API call
        user_info = await self._fetch_github_user(connection["access_token"])
        
        if user_info is None:
            return {
                "connected": False,
                "message": "GitHub token is invalid or expired",
                "needs_reauth": True
            }
        
        # Get settings for the connection
        settings = await self.db.fetchrow(
            "SELECT * FROM github_settings WHERE user_id = $1",
            user_id
        )
        
        return {
            "connected": True,
            "user_info": user_info,
            "settings": settings or {}
        }
    
    async def save_settings(self, user_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save GitHub integration settings
        """
        # Check if user has GitHub connected
        connection = await self.db.fetchrow(
            "SELECT * FROM github_connections WHERE user_id = $1",
            user_id
        )
        
        if not connection:
            return {"success": False, "message": "GitHub not connected"}
        
        # Save settings
        settings_json = json.dumps(settings)
        await self.db.execute(
            """
            INSERT INTO github_settings (user_id, settings, created_at, updated_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) 
            DO UPDATE SET settings = $2, updated_at = $4
            """,
            user_id, settings_json, datetime.now(), datetime.now()
        )
        
        return {"success": True, "message": "Settings saved successfully"}
    
    async def get_repositories(self, user_id: str) -> Dict[str, Any]:
        """
        Get GitHub repositories for the user
        """
        connection = await self.db.fetchrow(
            "SELECT * FROM github_connections WHERE user_id = $1",
            user_id
        )
        
        if not connection:
            return {"success": False, "message": "GitHub not connected"}
        
        repos = await self._fetch_repositories(connection["access_token"])
        
        if repos is None:
            return {"success": False, "message": "Failed to fetch repositories"}
        
        # Get settings
        settings = await self.db.fetchrow(
            "SELECT * FROM github_settings WHERE user_id = $1",
            user_id
        )
        
        # Get list of synchronized repositories
        synced_repos = await self.db.fetch(
            "SELECT * FROM github_synced_repos WHERE user_id = $1",
            user_id
        )
        
        synced_repo_ids = [repo["repo_id"] for repo in synced_repos]
        
        return {
            "success": True,
            "repositories": repos,
            "settings": settings["settings"] if settings else {},
            "synced_repositories": synced_repo_ids
        }
    
    async def sync_repositories(self, user_id: str) -> Dict[str, Any]:
        """
        Sync GitHub repositories for the user
        """
        connection = await self.db.fetchrow(
            "SELECT * FROM github_connections WHERE user_id = $1",
            user_id
        )
        
        if not connection:
            return {"success": False, "message": "GitHub not connected"}
        
        # Get settings to determine which repos to sync
        settings = await self.db.fetchrow(
            "SELECT * FROM github_settings WHERE user_id = $1",
            user_id
        )
        
        if not settings:
            return {"success": False, "message": "No settings configured for GitHub integration"}
        
        try:
            settings_data = settings["settings"]
            if isinstance(settings_data, str):
                settings_data = json.loads(settings_data)
            
            # Get repositories to sync
            selected_repos = settings_data.get("selectedRepositories", [])
            access_token = connection["access_token"]
            
            # Start sync process
            for repo_id in selected_repos:
                # Fetch repository info and content
                repo_info = await self._fetch_repository(access_token, repo_id)
                
                if not repo_info:
                    logger.warning(f"Could not fetch info for repository {repo_id}")
                    continue
                
                # Get repository contents
                contents = await self._fetch_repository_contents(access_token, repo_info["full_name"], "")
                
                if not contents:
                    logger.warning(f"Could not fetch contents for repository {repo_id}")
                    continue
                
                # Process repository contents and store in memory database
                await self._process_repository_contents(user_id, repo_info, contents, access_token)
                
                # Mark repository as synced
                await self.db.execute(
                    """
                    INSERT INTO github_synced_repos (user_id, repo_id, repo_name, last_synced)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id, repo_id) 
                    DO UPDATE SET last_synced = $4
                    """,
                    user_id, repo_id, repo_info["full_name"], datetime.now()
                )
            
            return {"success": True, "message": f"Synced {len(selected_repos)} repositories"}
            
        except Exception as e:
            logger.error(f"Error syncing GitHub repositories: {str(e)}")
            return {"success": False, "message": f"Error syncing repositories: {str(e)}"}
    
    async def disconnect(self, user_id: str) -> Dict[str, Any]:
        """
        Disconnect GitHub integration
        """
        # Remove GitHub connection
        await self.db.execute(
            "DELETE FROM github_connections WHERE user_id = $1",
            user_id
        )
        
        # Remove settings
        await self.db.execute(
            "DELETE FROM github_settings WHERE user_id = $1",
            user_id
        )
        
        # Remove synced repositories
        await self.db.execute(
            "DELETE FROM github_synced_repos WHERE user_id = $1",
            user_id
        )
        
        # Clean up memory entries from GitHub
        await self.db.execute(
            "DELETE FROM memory_entries WHERE user_id = $1 AND source = 'github'",
            user_id
        )
        
        return {"success": True, "message": "GitHub disconnected successfully"}
    
    # Private helper methods
    
    async def _fetch_github_user(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Fetch GitHub user information
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                async with session.get(f"{self.api_base}/user", headers=headers) as response:
                    if response.status != 200:
                        return None
                    
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching GitHub user: {str(e)}")
            return None
    
    async def _fetch_repositories(self, access_token: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch GitHub repositories for the user
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                async with session.get(f"{self.api_base}/user/repos?per_page=100", headers=headers) as response:
                    if response.status != 200:
                        return None
                    
                    repos = await response.json()
                    
                    # Simplify repository information
                    return [{
                        "id": repo["id"],
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "description": repo["description"],
                        "private": repo["private"],
                        "url": repo["html_url"],
                        "language": repo["language"],
                        "created_at": repo["created_at"],
                        "updated_at": repo["updated_at"]
                    } for repo in repos]
        except Exception as e:
            logger.error(f"Error fetching GitHub repositories: {str(e)}")
            return None
    
    async def _fetch_repository(self, access_token: str, repo_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch specific repository information
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                async with session.get(f"{self.api_base}/repositories/{repo_id}", headers=headers) as response:
                    if response.status != 200:
                        return None
                    
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching GitHub repository: {str(e)}")
            return None
    
    async def _fetch_repository_contents(self, access_token: str, repo_full_name: str, path: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch contents of a repository path
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                url = f"{self.api_base}/repos/{repo_full_name}/contents/{path}"
                
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return None
                    
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching GitHub repository contents: {str(e)}")
            return None
    
    async def _fetch_file_content(self, access_token: str, repo_full_name: str, path: str) -> Optional[str]:
        """
        Fetch content of a specific file
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                url = f"{self.api_base}/repos/{repo_full_name}/contents/{path}"
                
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return None
                    
                    content = await response.json()
                    
                    if content.get("type") != "file":
                        return None
                    
                    if content.get("encoding") == "base64":
                        return base64.b64decode(content["content"]).decode("utf-8")
                    
                    return content["content"]
        except Exception as e:
            logger.error(f"Error fetching GitHub file content: {str(e)}")
            return None
    
    async def _process_repository_contents(self, user_id: str, repo_info: Dict[str, Any], contents: List[Dict[str, Any]], access_token: str):
        """
        Process repository contents recursively and store in memory database
        """
        for item in contents:
            if item["type"] == "file":
                # Check if file should be processed based on extension
                if self._should_process_file(item["name"]):
                    content = await self._fetch_file_content(access_token, repo_info["full_name"], item["path"])
                    
                    if content:
                        # Store content in memory database
                        memory_id = str(uuid.uuid4())
                        await self.db.execute(
                            """
                            INSERT INTO memory_entries (
                                id, user_id, title, content, source, source_id, 
                                metadata, created_at, updated_at
                            )
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                            """,
                            memory_id,
                            user_id,
                            f"{repo_info['name']} - {item['path']}",
                            content,
                            "github",
                            f"{repo_info['id']}:{item['path']}",
                            json.dumps({
                                "repo_name": repo_info["name"],
                                "repo_full_name": repo_info["full_name"],
                                "path": item["path"],
                                "sha": item["sha"],
                                "url": item["html_url"],
                                "language": self._detect_language(item["name"])
                            }),
                            datetime.now(),
                            datetime.now()
                        )
            
            elif item["type"] == "dir":
                # Recursively process directories
                subcontents = await self._fetch_repository_contents(
                    access_token, repo_info["full_name"], item["path"]
                )
                
                if subcontents:
                    await self._process_repository_contents(
                        user_id, repo_info, subcontents, access_token
                    )
    
    def _should_process_file(self, filename: str) -> bool:
        """
        Determine if a file should be processed based on extension
        """
        # List of extensions to process
        extensions = [
            ".md", ".txt", ".py", ".js", ".ts", ".jsx", ".tsx", 
            ".html", ".css", ".json", ".yml", ".yaml", ".toml",
            ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rb",
            ".rs", ".swift", ".kt", ".sh", ".bat", ".ps1"
        ]
        
        # Check if file has a relevant extension
        return any(filename.lower().endswith(ext) for ext in extensions)
    
    def _detect_language(self, filename: str) -> str:
        """
        Detect programming language based on file extension
        """
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        
        language_map = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "jsx": "React",
            "tsx": "React TypeScript",
            "html": "HTML",
            "css": "CSS",
            "json": "JSON",
            "yml": "YAML",
            "yaml": "YAML",
            "toml": "TOML",
            "java": "Java",
            "c": "C",
            "cpp": "C++",
            "h": "C/C++ Header",
            "hpp": "C++ Header",
            "go": "Go",
            "rb": "Ruby",
            "rs": "Rust",
            "swift": "Swift",
            "kt": "Kotlin",
            "sh": "Shell",
            "bat": "Batch",
            "ps1": "PowerShell",
            "md": "Markdown",
            "txt": "Text"
        }
        
        return language_map.get(ext, "Unknown") 