import os
import logging
import json
import uuid
import re
import pathlib
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiofiles
import asyncio

logger = logging.getLogger(__name__)

class ObsidianRouter:
    def __init__(self, db, gemini_api=None):
        self.db = db
        self.gemini_api = gemini_api
        
        # Markdown link pattern (both wiki-style [[link]] and MD-style [text](link))
        self.wiki_link_pattern = re.compile(r'\[\[(.*?)\]\]')
        self.md_link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        self.tag_pattern = re.compile(r'#([a-zA-Z0-9_-]+)')
        
    async def check_connection_status(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user has Obsidian vault configured and if it's accessible
        """
        connection = await self.db.fetchrow(
            "SELECT * FROM obsidian_connections WHERE user_id = $1",
            user_id
        )
        
        if not connection:
            return {"connected": False, "message": "Obsidian vault not connected"}
        
        # Check if vault path exists and is accessible
        vault_path = connection["vault_path"]
        if not os.path.exists(vault_path) or not os.path.isdir(vault_path):
            return {
                "connected": False,
                "message": "Obsidian vault path no longer exists or is not accessible",
                "needs_reconnect": True
            }
        
        # Get settings
        settings = await self.db.fetchrow(
            "SELECT * FROM obsidian_settings WHERE user_id = $1",
            user_id
        )
        
        last_sync = None
        synced_notes = 0
        
        if connection["last_synced"]:
            last_sync = connection["last_synced"].isoformat()
            
            # Count synced notes
            synced_notes_count = await self.db.fetchval(
                "SELECT COUNT(*) FROM memory_entries WHERE user_id = $1 AND source = 'obsidian'",
                user_id
            )
            
            synced_notes = synced_notes_count or 0
        
        return {
            "connected": True,
            "vault_path": vault_path,
            "last_sync": last_sync,
            "synced_notes": synced_notes,
            "settings": settings["settings"] if settings else {}
        }
    
    async def connect_vault(self, user_id: str, vault_path: str) -> Dict[str, Any]:
        """
        Connect to Obsidian vault
        """
        # Validate vault path
        if not os.path.exists(vault_path) or not os.path.isdir(vault_path):
            return {"success": False, "message": "Vault path does not exist or is not a directory"}
        
        # Check if this looks like an Obsidian vault (has .obsidian folder)
        obsidian_config_dir = os.path.join(vault_path, ".obsidian")
        if not os.path.exists(obsidian_config_dir) or not os.path.isdir(obsidian_config_dir):
            return {"success": False, "message": "This doesn't look like an Obsidian vault (missing .obsidian folder)"}
        
        # Save connection to database
        await self.db.execute(
            """
            INSERT INTO obsidian_connections (user_id, vault_path, created_at, updated_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) 
            DO UPDATE SET vault_path = $2, updated_at = $4
            """,
            user_id, vault_path, datetime.now(), datetime.now()
        )
        
        # Create default settings if they don't exist
        default_settings = {
            "includeSubfolders": True,
            "excludeFolders": [".obsidian", ".trash", ".git"],
            "fileTypes": [".md"],
            "syncTags": True,
            "syncLinks": True,
        }
        
        await self.db.execute(
            """
            INSERT INTO obsidian_settings (user_id, settings, created_at, updated_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id, json.dumps(default_settings), datetime.now(), datetime.now()
        )
        
        return {"success": True, "message": "Obsidian vault connected successfully"}
    
    async def test_connection(self, user_id: str, vault_path: str) -> Dict[str, Any]:
        """
        Test connection to Obsidian vault
        """
        # Validate vault path
        if not os.path.exists(vault_path) or not os.path.isdir(vault_path):
            return {"success": False, "message": "Vault path does not exist or is not a directory"}
        
        # Check if this looks like an Obsidian vault (has .obsidian folder)
        obsidian_config_dir = os.path.join(vault_path, ".obsidian")
        if not os.path.exists(obsidian_config_dir) or not os.path.isdir(obsidian_config_dir):
            return {"success": False, "message": "This doesn't look like an Obsidian vault (missing .obsidian folder)"}
        
        # Count markdown files
        md_files_count = 0
        for root, _, files in os.walk(vault_path):
            for file in files:
                if file.endswith(".md"):
                    md_files_count += 1
        
        return {
            "success": True,
            "message": f"Obsidian vault looks valid with {md_files_count} markdown files"
        }
    
    async def get_settings(self, user_id: str) -> Dict[str, Any]:
        """
        Get Obsidian integration settings
        """
        # Check if vault is connected
        connection = await self.db.fetchrow(
            "SELECT * FROM obsidian_connections WHERE user_id = $1",
            user_id
        )
        
        if not connection:
            return {"success": False, "message": "Obsidian vault not connected"}
        
        # Get settings
        settings = await self.db.fetchrow(
            "SELECT * FROM obsidian_settings WHERE user_id = $1",
            user_id
        )
        
        if not settings:
            return {"success": False, "message": "Settings not found"}
        
        settings_data = settings["settings"]
        if isinstance(settings_data, str):
            settings_data = json.loads(settings_data)
        
        return {
            "success": True,
            "settings": settings_data
        }
    
    async def save_settings(self, user_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save Obsidian integration settings
        """
        # Check if vault is connected
        connection = await self.db.fetchrow(
            "SELECT * FROM obsidian_connections WHERE user_id = $1",
            user_id
        )
        
        if not connection:
            return {"success": False, "message": "Obsidian vault not connected"}
        
        # Save settings
        settings_json = json.dumps(settings)
        await self.db.execute(
            """
            INSERT INTO obsidian_settings (user_id, settings, created_at, updated_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) 
            DO UPDATE SET settings = $2, updated_at = $4
            """,
            user_id, settings_json, datetime.now(), datetime.now()
        )
        
        return {"success": True, "message": "Settings saved successfully"}
    
    async def sync(self, user_id: str) -> Dict[str, Any]:
        """
        Sync Obsidian vault
        """
        # Check if vault is connected
        connection = await self.db.fetchrow(
            "SELECT * FROM obsidian_connections WHERE user_id = $1",
            user_id
        )
        
        if not connection:
            return {"success": False, "message": "Obsidian vault not connected"}
        
        vault_path = connection["vault_path"]
        
        if not os.path.exists(vault_path) or not os.path.isdir(vault_path):
            return {"success": False, "message": "Vault path no longer exists or is not accessible"}
        
        # Get settings
        settings_record = await self.db.fetchrow(
            "SELECT * FROM obsidian_settings WHERE user_id = $1",
            user_id
        )
        
        if not settings_record:
            return {"success": False, "message": "Settings not found"}
        
        settings = settings_record["settings"]
        if isinstance(settings, str):
            settings = json.loads(settings)
        
        try:
            # Start sync process
            files_processed = 0
            notes_added = 0
            
            # Get list of files to process
            files_to_process = await self._get_files_to_process(vault_path, settings)
            
            # Process each file
            for file_path in files_to_process:
                files_processed += 1
                
                # Read file content
                note_content = await self._read_file(file_path)
                if not note_content:
                    logger.warning(f"Could not read file: {file_path}")
                    continue
                
                # Extract metadata
                rel_path = os.path.relpath(file_path, vault_path)
                title = os.path.splitext(os.path.basename(file_path))[0]
                
                # Extract tags and links
                tags = self._extract_tags(note_content) if settings.get("syncTags", True) else []
                links = self._extract_links(note_content) if settings.get("syncLinks", True) else []
                
                # Generate embedding if Gemini API is available
                embedding = None
                if self.gemini_api:
                    embedding = await self.gemini_api.generate_embedding(note_content)
                
                # Create memory entry
                memory_id = str(uuid.uuid4())
                
                # Store in database
                await self.db.execute(
                    """
                    INSERT INTO memory_entries (
                        id, user_id, title, content, source, source_id, 
                        metadata, embedding, created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (user_id, source, source_id) 
                    DO UPDATE SET 
                        title = $3, 
                        content = $4, 
                        metadata = $7, 
                        embedding = $8, 
                        updated_at = $10
                    """,
                    memory_id,
                    user_id,
                    title,
                    note_content,
                    "obsidian",
                    rel_path,
                    json.dumps({
                        "path": rel_path,
                        "tags": tags,
                        "links": links,
                        "last_modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    }),
                    json.dumps(embedding) if embedding else None,
                    datetime.now(),
                    datetime.now()
                )
                
                notes_added += 1
            
            # Update last synced timestamp
            await self.db.execute(
                """
                UPDATE obsidian_connections
                SET last_synced = $1, updated_at = $2
                WHERE user_id = $3
                """,
                datetime.now(), datetime.now(), user_id
            )
            
            return {
                "success": True,
                "message": f"Sync completed successfully. Processed {files_processed} files, added/updated {notes_added} notes."
            }
            
        except Exception as e:
            logger.error(f"Error syncing Obsidian vault: {str(e)}")
            return {"success": False, "message": f"Error syncing Obsidian vault: {str(e)}"}
    
    async def disconnect(self, user_id: str) -> Dict[str, Any]:
        """
        Disconnect Obsidian integration
        """
        # Remove Obsidian connection
        await self.db.execute(
            "DELETE FROM obsidian_connections WHERE user_id = $1",
            user_id
        )
        
        # Remove settings
        await self.db.execute(
            "DELETE FROM obsidian_settings WHERE user_id = $1",
            user_id
        )
        
        # Clean up memory entries from Obsidian
        await self.db.execute(
            "DELETE FROM memory_entries WHERE user_id = $1 AND source = 'obsidian'",
            user_id
        )
        
        return {"success": True, "message": "Obsidian disconnected successfully"}
    
    # Private helper methods
    
    async def _get_files_to_process(self, vault_path: str, settings: Dict[str, Any]) -> List[str]:
        """
        Get list of files to process based on settings
        """
        include_subfolders = settings.get("includeSubfolders", True)
        exclude_folders = settings.get("excludeFolders", [".obsidian", ".trash"])
        file_types = settings.get("fileTypes", [".md"])
        
        files_to_process = []
        
        # Helper function to check if path should be excluded
        def should_exclude(path):
            rel_path = os.path.relpath(path, vault_path)
            path_parts = pathlib.Path(rel_path).parts
            
            for exclude in exclude_folders:
                if exclude in path_parts:
                    return True
            
            return False
        
        # Walk through vault directory
        for root, dirs, files in os.walk(vault_path):
            if should_exclude(root):
                continue
                
            if not include_subfolders and root != vault_path:
                continue
                
            for file in files:
                if any(file.endswith(ext) for ext in file_types):
                    files_to_process.append(os.path.join(root, file))
        
        return files_to_process
    
    async def _read_file(self, file_path: str) -> Optional[str]:
        """
        Read file content asynchronously
        """
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                return await file.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
    
    def _extract_tags(self, content: str) -> List[str]:
        """
        Extract tags from note content
        """
        tags = set()
        
        # Find all #tag occurrences
        for match in self.tag_pattern.finditer(content):
            tag = match.group(1)
            if tag:
                tags.add(tag)
        
        return list(tags)
    
    def _extract_links(self, content: str) -> List[Dict[str, str]]:
        """
        Extract links from note content
        """
        links = []
        
        # Extract wiki-style links [[link]]
        for match in self.wiki_link_pattern.finditer(content):
            link_text = match.group(1)
            if link_text:
                # Handle aliases like [[link|alias]]
                if "|" in link_text:
                    parts = link_text.split("|", 1)
                    links.append({
                        "target": parts[0].strip(),
                        "alias": parts[1].strip(),
                        "type": "wiki"
                    })
                else:
                    links.append({
                        "target": link_text.strip(),
                        "alias": link_text.strip(),
                        "type": "wiki"
                    })
        
        # Extract Markdown links [text](link)
        for match in self.md_link_pattern.finditer(content):
            text = match.group(1)
            link = match.group(2)
            if text and link:
                # Only include internal links (not web URLs)
                if not link.startswith("http://") and not link.startswith("https://"):
                    links.append({
                        "target": link.strip(),
                        "alias": text.strip(),
                        "type": "markdown"
                    })
        
        return links 