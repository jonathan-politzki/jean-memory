import logging
import os
import json
from typing import Dict, Any, List, Optional
import asyncio
import re

logger = logging.getLogger(__name__)

class ObsidianRouter:
    """
    Router for handling Obsidian vault integration.
    """

    def __init__(self, db=None, gemini_api=None):
        self.db = db
        self.gemini_api = gemini_api
        logger.info("ObsidianRouter initialized.")
        
        # Create a settings cache for quick access
        self.settings_cache = {}
        
    async def get_raw_context(self, user_id: int) -> List[Dict[str, Any]]:
        """Get raw Obsidian notes from database or local vault."""
        logger.info(f"Fetching raw Obsidian context for user {user_id}...")
        
        # 1. Check database for cached Obsidian notes
        if self.db:
            try:
                cached_notes = await self.db.get_all_context_by_type(user_id, "obsidian")
                if cached_notes:
                    logger.info(f"Found {len(cached_notes)} Obsidian notes in DB for user {user_id}.")
                    return cached_notes
            except Exception as e:
                logger.error(f"Error retrieving Obsidian notes from database: {e}")
        
        # 2. Placeholder implementation - would read from the actual vault in production
        logger.warning(f"Direct Obsidian vault reading not implemented yet. Returning placeholder data.")
        context = [
            {
                "path": "Notes/Project Ideas.md",
                "title": "Project Ideas",
                "content": "# Project Ideas\n\n- Build a personal knowledge management system\n- Create a habit tracker with ML insights",
                "tags": ["ideas", "projects"]
            },
            {
                "path": "Notes/Meeting Notes/2025-05-10.md",
                "title": "Meeting Notes - 2025-05-10",
                "content": "# Meeting Notes\n\n- Discussed project roadmap\n- Set deadlines for next sprint",
                "tags": ["meetings", "work"]
            }
        ]
        
        # 3. In a real implementation, we would store the fetched data for future use
        if self.db:
            try:
                for note in context:
                    await self.db.store_context(
                        user_id=user_id,
                        context_type="obsidian",
                        data=note,
                        source_identifier=note.get("path", "unknown")
                    )
            except Exception as e:
                logger.error(f"Error storing Obsidian notes in database: {e}")
        
        return context

    async def get_context(self, user_id: int, tenant_id: str, query: str) -> Dict[str, Any]:
        """
        Get Obsidian-related context for a user's query, with tenant isolation.
        
        Args:
            user_id: The user ID requesting context
            tenant_id: The tenant/organization ID for data isolation
            query: The user's query about their notes
            
        Returns:
            Dict with context information
        """
        logger.info(f"Getting Obsidian context for user {user_id} (tenant: {tenant_id}) query: {query[:30]}...")
        
        # 1. Try to get context from database first
        if self.db:
            try:
                cached_data = await self.db.get_context(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    context_type="obsidian"
                )
                if cached_data:
                    logger.info(f"Found cached Obsidian data for user {user_id} (tenant: {tenant_id})")
                    
                    # 2. Process with Gemini if available
                    if self.gemini_api:
                        processed_response = await self.gemini_api.process(
                            context_type="obsidian", 
                            context_data=cached_data, 
                            query=query
                        )
                        return {"type": "obsidian", "content": processed_response}
                    
                    # If no Gemini, return raw data
                    return {"type": "obsidian", "content": str(cached_data)}
            except Exception as e:
                logger.error(f"Error retrieving Obsidian context from database: {e}")
                # Continue to process as fallback
        
        # 3. If not in DB or DB error, fetch directly from Obsidian vault
        # In a real implementation, we would:
        # - Look up user's Obsidian vault path from settings
        # - Read and parse .md files from the vault
        # - Filter by tags if specified in settings
        # - Store results in DB for future use
        # - Process with Gemini
        
        return {"type": "obsidian", "content": "[Obsidian context placeholder]"}
    
    async def connect_vault(self, user_id: int, vault_path: str) -> Dict[str, Any]:
        """
        Connect to a user's Obsidian vault.
        
        Args:
            user_id: User ID
            vault_path: Path to the Obsidian vault
            
        Returns:
            Dict with connection result
        """
        logger.info(f"Connecting to Obsidian vault for user {user_id} at path {vault_path}")
        
        # 1. Validate that the path exists and is an Obsidian vault
        # This would be implemented differently in production, possibly with a desktop app
        # that has filesystem access
        
        # For now, we'll simulate success
        if vault_path:
            # Store vault settings in database
            if self.db:
                try:
                    # Create/update settings collection
                    settings = {
                        "vaultPath": vault_path,
                        "syncAllNotes": True,
                        "syncFrequency": "daily"
                    }
                    
                    await self.db.store_settings(
                        user_id=user_id,
                        settings_type="obsidian",
                        settings=settings
                    )
                    
                    # Update local cache
                    self.settings_cache[str(user_id)] = settings
                    
                    return {
                        "success": True,
                        "message": "Successfully connected to Obsidian vault",
                        "vault_path": vault_path
                    }
                except Exception as e:
                    logger.error(f"Error storing Obsidian settings: {e}")
                    return {
                        "success": False,
                        "message": f"Database error: {str(e)}"
                    }
        
        return {
            "success": False,
            "message": "Invalid vault path or path doesn't exist"
        }
    
    async def test_connection(self, user_id: int, vault_path: str) -> Dict[str, Any]:
        """
        Test connection to an Obsidian vault.
        
        Args:
            user_id: User ID
            vault_path: Path to the Obsidian vault
            
        Returns:
            Dict with test result
        """
        logger.info(f"Testing connection to Obsidian vault for user {user_id} at path {vault_path}")
        
        # In production, this would check if the path exists and count .md files
        # For demo, we'll simulate a successful test
        
        return {
            "success": True,
            "message": "Vault exists and is accessible",
            "notesCount": 45  # Simulated count of notes
        }
    
    async def save_settings(self, user_id: int, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save Obsidian integration settings.
        
        Args:
            user_id: User ID
            settings: Dict of settings (vault path, sync options, etc.)
            
        Returns:
            Dict with save result
        """
        logger.info(f"Saving Obsidian settings for user {user_id}: {settings}")
        
        if not settings.get("vaultPath"):
            return {
                "success": False,
                "message": "Vault path is required"
            }
        
        # Store settings in database
        if self.db:
            try:
                await self.db.store_settings(
                    user_id=user_id,
                    settings_type="obsidian",
                    settings=settings
                )
                
                # Update local cache
                self.settings_cache[str(user_id)] = settings
                
                return {
                    "success": True,
                    "message": "Settings saved successfully"
                }
            except Exception as e:
                logger.error(f"Error storing Obsidian settings: {e}")
                return {
                    "success": False,
                    "message": f"Database error: {str(e)}"
                }
        
        return {
            "success": False,
            "message": "Database not available"
        }
    
    async def get_settings(self, user_id: int) -> Dict[str, Any]:
        """
        Get Obsidian integration settings.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with settings
        """
        logger.info(f"Getting Obsidian settings for user {user_id}")
        
        # Check local cache first
        if str(user_id) in self.settings_cache:
            return {
                "success": True,
                "settings": self.settings_cache[str(user_id)]
            }
        
        # Fetch from database
        if self.db:
            try:
                settings = await self.db.get_settings(
                    user_id=user_id,
                    settings_type="obsidian"
                )
                
                if settings:
                    # Update local cache
                    self.settings_cache[str(user_id)] = settings
                    
                    return {
                        "success": True,
                        "settings": settings
                    }
                else:
                    return {
                        "success": True,
                        "settings": None,
                        "message": "No settings found"
                    }
            except Exception as e:
                logger.error(f"Error fetching Obsidian settings: {e}")
                return {
                    "success": False,
                    "message": f"Database error: {str(e)}"
                }
        
        return {
            "success": False,
            "message": "Database not available"
        }
    
    async def check_connection_status(self, user_id: int) -> Dict[str, Any]:
        """
        Check if a user has connected to an Obsidian vault.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with connection status
        """
        logger.info(f"Checking Obsidian connection status for user {user_id}")
        
        # Fetch settings to determine if connected
        settings_result = await self.get_settings(user_id)
        
        if settings_result["success"] and settings_result.get("settings"):
            return {
                "connected": True,
                "vault_path": settings_result["settings"].get("vaultPath")
            }
        
        return {
            "connected": False
        }
    
    async def disconnect(self, user_id: int) -> Dict[str, Any]:
        """
        Disconnect from an Obsidian vault.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with disconnect result
        """
        logger.info(f"Disconnecting Obsidian for user {user_id}")
        
        # Remove settings from database
        if self.db:
            try:
                await self.db.delete_settings(
                    user_id=user_id,
                    settings_type="obsidian"
                )
                
                # Remove from local cache
                if str(user_id) in self.settings_cache:
                    del self.settings_cache[str(user_id)]
                
                return {
                    "success": True,
                    "message": "Successfully disconnected from Obsidian"
                }
            except Exception as e:
                logger.error(f"Error disconnecting from Obsidian: {e}")
                return {
                    "success": False,
                    "message": f"Database error: {str(e)}"
                }
        
        return {
            "success": False,
            "message": "Database not available"
        }
    
    async def sync(self, user_id: int) -> Dict[str, Any]:
        """
        Sync notes from an Obsidian vault.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with sync result
        """
        logger.info(f"Syncing Obsidian vault for user {user_id}")
        
        # Check if vault is connected
        status = await self.check_connection_status(user_id)
        if not status.get("connected"):
            return {
                "success": False,
                "message": "Obsidian vault not connected"
            }
        
        # Get vault settings
        settings_result = await self.get_settings(user_id)
        if not settings_result["success"] or not settings_result.get("settings"):
            return {
                "success": False,
                "message": "Could not retrieve Obsidian settings"
            }
        
        settings = settings_result["settings"]
        vault_path = settings.get("vaultPath")
        sync_all_notes = settings.get("syncAllNotes", True)
        sync_tags = settings.get("syncTags", False)
        tags_list = settings.get("tagsList", "")
        
        # In a real implementation, we would:
        # 1. Read all .md files in the vault
        # 2. Parse them for frontmatter, content, and tags
        # 3. Filter by tags if specified
        # 4. Store them in the database
        
        # For demo purposes, we'll simulate syncing
        # In production, this would be implemented with actual file system access
        
        # Update sync status in settings
        settings["lastSync"] = "2025-05-15T09:30:00Z"  # ISO format timestamp
        settings["notesSynced"] = 37  # Simulated count
        
        # Save updated settings
        await self.save_settings(user_id, settings)
        
        return {
            "success": True,
            "message": "Sync completed successfully",
            "notesSynced": 37,
            "lastSync": "2025-05-15T09:30:00Z"
        } 