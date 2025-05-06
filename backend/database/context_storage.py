import logging
import asyncpg
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

class ContextDatabase:
    """Database interface for JEAN context storage."""
    
    def __init__(self, connection_string: str):
        # Convert SQLAlchemy format URL if necessary
        if "+asyncpg" in connection_string:
            connection_string = connection_string.replace("+asyncpg", "")
        
        self.connection_string = connection_string
        self.pool = None
        logger.info("ContextDatabase instance created (not yet connected)")
    
    async def initialize(self):
        """Initialize the database connection and tables."""
        logger.info("Initializing database connection and tables...")
        
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(self.connection_string)
            logger.info("Database connection pool created successfully")
            
            # Create tables if they don't exist
            async with self.pool.acquire() as conn:
                # Create users table with tenant isolation in mind
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        tenant_id VARCHAR(50) NOT NULL, -- Organization/team isolation
                        google_id VARCHAR(255) UNIQUE,
                        email VARCHAR(255) UNIQUE,
                        api_key VARCHAR(255) UNIQUE,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_active TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        settings JSONB DEFAULT '{}'::JSONB,
                        UNIQUE(tenant_id, google_id)
                    )
                ''')
                
                # Create context table with separate partitions by context_type
                # and strong user isolation
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS context (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        tenant_id VARCHAR(50) NOT NULL, -- For stronger isolation
                        context_type VARCHAR(50) NOT NULL,
                        source_identifier VARCHAR(255),
                        content JSONB NOT NULL,
                        metadata JSONB DEFAULT '{}'::JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        -- Composite index for efficient querying by user within tenant
                        -- This ensures data isolation between tenants
                        UNIQUE(tenant_id, user_id, context_type, source_identifier)
                    )
                ''')
                
                # Create indices for fast lookups
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_context_user_type 
                    ON context(user_id, context_type);
                ''')
                
                await conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_context_tenant 
                    ON context(tenant_id);
                ''')
                
                logger.info("Database tables and indices created or verified")
        except Exception as e:
            logger.exception(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def create_or_get_user(self, tenant_id: str, google_id: str, email: str) -> Tuple[int, str]:
        """Create a new user or get existing user by Google ID."""
        if not self.pool:
            raise ConnectionError("Database not initialized")
        
        async with self.pool.acquire() as conn:
            # Generate a unique API key if creating new user
            api_key = str(uuid.uuid4())
            
            # Try to find existing user or create a new one
            user = await conn.fetchrow('''
                INSERT INTO users (tenant_id, google_id, email, api_key)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (google_id) DO UPDATE
                SET last_active = NOW(), email = $3
                RETURNING id, api_key
            ''', tenant_id, google_id, email, api_key)
            
            return user['id'], user['api_key']
    
    async def store_context(self, user_id: int, tenant_id: str, context_type: str, 
                           content: Dict[str, Any], source_identifier: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store context data for a user with tenant isolation."""
        if not self.pool:
            raise ConnectionError("Database not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                # Convert dict to JSONB for storage
                content_json = json.dumps(content)
                metadata_json = json.dumps(metadata) if metadata else json.dumps({})
                
                # Insert or update context record
                await conn.execute('''
                    INSERT INTO context 
                    (user_id, tenant_id, context_type, source_identifier, content, metadata, updated_at)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, NOW())
                    ON CONFLICT (tenant_id, user_id, context_type, source_identifier) 
                    DO UPDATE SET content = $5::jsonb, metadata = $6::jsonb, updated_at = NOW()
                ''', user_id, tenant_id, context_type, source_identifier, content_json, metadata_json)
                
                return True
        except Exception as e:
            logger.exception(f"Error storing context: {e}")
            return False
    
    async def get_context(self, user_id: int, tenant_id: str, context_type: str, 
                         source_identifier: Optional[str] = None,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve context data for a user with tenant isolation."""
        if not self.pool:
            raise ConnectionError("Database not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                # Query with or without source_identifier
                if source_identifier:
                    query = '''
                        SELECT id, context_type, source_identifier, content, metadata, created_at, updated_at
                        FROM context
                        WHERE user_id = $1 AND tenant_id = $2 AND context_type = $3 
                        AND source_identifier = $4
                        ORDER BY updated_at DESC
                    '''
                    params = [user_id, tenant_id, context_type, source_identifier]
                else:
                    query = '''
                        SELECT id, context_type, source_identifier, content, metadata, created_at, updated_at
                        FROM context
                        WHERE user_id = $1 AND tenant_id = $2 AND context_type = $3
                        ORDER BY updated_at DESC
                    '''
                    params = [user_id, tenant_id, context_type]

                if limit is not None:
                    query += f" LIMIT ${len(params) + 1}"
                    params.append(limit)
                
                rows = await conn.fetch(query, *params)
                
                # Convert database rows to Python dicts
                result = []
                for row in rows:
                    result.append({
                        'id': row['id'],
                        'context_type': row['context_type'],
                        'source_identifier': row['source_identifier'],
                        'content': row['content'],
                        'metadata': row['metadata'],
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                    })
                
                logger.info(f"Retrieved {len(result)} context items for user {user_id}, type '{context_type}'")
                return result
        except Exception as e:
            logger.exception(f"Error retrieving context: {e}")
            return []
    
    async def delete_user_data(self, user_id: int, tenant_id: str) -> bool:
        """Delete all context data for a user (for GDPR/privacy compliance)."""
        if not self.pool:
            raise ConnectionError("Database not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                # Delete all context for this user
                await conn.execute('''
                    DELETE FROM context 
                    WHERE user_id = $1 AND tenant_id = $2
                ''', user_id, tenant_id)
                
                return True
        except Exception as e:
            logger.exception(f"Error deleting user data: {e}")
            return False

    async def validate_api_key(self, api_key: str) -> Optional[int]:
        """Validate an API key and return the corresponding user_id if valid."""
        # For development purposes, accept anything and use a default user ID
        logger.debug(f"validate_api_key called with api_key (first 10 chars): '{api_key[:10] if api_key else 'None'}...', length: {len(api_key) if api_key else 0}")
        
        # DEVELOPMENT MODE: Always accept ANY key and map to user ID 1
        # In production, you'd want to remove this and only use the database check
        if not api_key or api_key.lower() == "undefined" or api_key == "null":
            logger.warning(f"⚠️ DEVELOPMENT MODE: Using user_id=1 for empty/invalid API key: '{api_key}'")
            return 1
            
        if not self.pool:
            logger.error("Database pool not initialized in validate_api_key")
            logger.warning("⚠️ DEVELOPMENT MODE: Using user_id=1 due to missing database connection")
            return 1
        
        try:
            async with self.pool.acquire() as conn:
                # First check the actual database
                logger.debug(f"Checking database for api_key: '{api_key[:10] if api_key else 'None'}...'")
                user_id = await conn.fetchval("SELECT id FROM users WHERE api_key = $1", api_key)
                
                # If found in database, use that user_id
                if user_id is not None:
                    logger.debug(f"Found valid API key in database, user_id={user_id}")
                    return user_id
                
                # DEVELOPMENT MODE: Return the first user in the database as a fallback
                first_user_id = await conn.fetchval("SELECT id FROM users ORDER BY id LIMIT 1")
                if first_user_id:
                    logger.warning(f"⚠️ DEVELOPMENT MODE: Using first user (ID={first_user_id}) for unrecognized API key")
                    return first_user_id
                
                # If there are no users in the database, create one
                logger.warning("⚠️ DEVELOPMENT MODE: No users in database, creating test user...")
                test_user_id = await conn.fetchval("""
                    INSERT INTO users (tenant_id, google_id, email, api_key)
                    VALUES ('default', 'dev_user', 'dev@example.com', 'DEV_API_KEY')
                    ON CONFLICT (google_id) DO UPDATE SET last_active = NOW()
                    RETURNING id
                """)
                logger.warning(f"⚠️ DEVELOPMENT MODE: Created test user ID={test_user_id}")
                return test_user_id
                
        except Exception as e:
            logger.exception(f"Error during API key validation: {e}")
            logger.warning("⚠️ DEVELOPMENT MODE: Using user_id=1 after database exception")
            return 1
        
        # Should never reach here in development mode, but just in case
        logger.warning("⚠️ DEVELOPMENT MODE: Using default user_id=1 as final fallback")
        return 1

    async def get_all_context_by_type(self, user_id: int, context_type: str) -> list[Dict[str, Any]]:
        """Retrieve all raw context of a specific type for a user."""
        if not self.pool:
            raise ConnectionError("Database not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                query = 'SELECT content FROM context WHERE user_id = $1 AND context_type = $2 ORDER BY updated_at DESC NULLS LAST'
                params = [user_id, context_type]
                records = await conn.fetch(query, *params)
                results = []
                for record in records:
                    if record and record['content']:
                        results.append(json.loads(record['content']))

            logger.info(f"Retrieved {len(results)} context items for user {user_id}, type '{context_type}'")
            return results
        except Exception as e:
            logger.exception(f"Error retrieving context: {e}")
            return []

    async def get_user_settings_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the settings JSONB for a specific user."""
        if not self.pool:
            logger.error("Database pool not initialized in get_user_settings_by_id")
            return None
        
        try:
            async with self.pool.acquire() as conn:
                settings_json = await conn.fetchval("SELECT settings FROM users WHERE id = $1", user_id)
                if settings_json:
                    # asyncpg returns JSONB as a string, so parse it
                    return json.loads(settings_json) if isinstance(settings_json, str) else settings_json
                return {}
        except Exception as e:
            logger.exception(f"Error retrieving user settings for user_id {user_id}: {e}")
            return None

    async def update_user_settings_by_id(self, user_id: int, new_settings: Dict[str, Any]) -> bool:
        """Update the settings JSONB for a specific user."""
        if not self.pool:
            logger.error("Database pool not initialized in update_user_settings_by_id")
            return False
        
        try:
            async with self.pool.acquire() as conn:
                settings_json_str = json.dumps(new_settings)
                await conn.execute("UPDATE users SET settings = $1 WHERE id = $2", settings_json_str, user_id)
                return True
        except Exception as e:
            logger.exception(f"Error updating user settings for user_id {user_id}: {e}")
            return False

    async def search_context(self, user_id: int, tenant_id: str, context_type: str, 
                            query: str, limit: Optional[int] = 10) -> List[Dict[str, Any]]:
        """Search context data for a user based on a query string (simple ILIKE search on content)."""
        if not self.pool:
            raise ConnectionError("Database not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                # Perform a simple ILIKE search on the content field (cast to text)
                # This is a basic search. For more advanced search, consider full-text search capabilities.
                sql_query = '''
                    SELECT id, context_type, source_identifier, content, metadata, created_at, updated_at
                    FROM context
                    WHERE user_id = $1 AND tenant_id = $2 AND context_type = $3
                    AND content::text ILIKE $4  -- Search within the JSONB content as text
                    ORDER BY updated_at DESC
                '''
                params = [user_id, tenant_id, context_type, f"%{query}%"]

                if limit is not None:
                    sql_query += f" LIMIT ${len(params) + 1}"
                    params.append(limit)
                
                rows = await conn.fetch(sql_query, *params)
                
                results = []
                for row in rows:
                    results.append({
                        'id': row['id'],
                        'context_type': row['context_type'],
                        'source_identifier': row['source_identifier'],
                        'content': row['content'], # This is JSONB, might need specific key access in tool
                        'metadata': row['metadata'],
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                    })
                
                logger.info(f"Found {len(results)} items matching query '{query}' for user {user_id}, type '{context_type}'")
                return results
        except Exception as e:
            logger.exception(f"Error searching context for query '{query}': {e}")
            return [] 