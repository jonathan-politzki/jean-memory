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
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        metadata JSONB DEFAULT '{}'::JSONB,
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
                           content: Dict[str, Any], source_identifier: Optional[str] = None) -> bool:
        """Store context data for a user with tenant isolation."""
        if not self.pool:
            raise ConnectionError("Database not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                # Convert dict to JSONB for storage
                content_json = json.dumps(content)
                
                # Insert or update context record
                await conn.execute('''
                    INSERT INTO context 
                    (user_id, tenant_id, context_type, source_identifier, content, updated_at)
                    VALUES ($1, $2, $3, $4, $5::jsonb, NOW())
                    ON CONFLICT (tenant_id, user_id, context_type, source_identifier) 
                    DO UPDATE SET content = $5::jsonb, updated_at = NOW()
                ''', user_id, tenant_id, context_type, source_identifier, content_json)
                
                return True
        except Exception as e:
            logger.exception(f"Error storing context: {e}")
            return False
    
    async def get_context(self, user_id: int, tenant_id: str, context_type: str, 
                         source_identifier: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve context data for a user with tenant isolation."""
        if not self.pool:
            raise ConnectionError("Database not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                # Query with or without source_identifier
                if source_identifier:
                    rows = await conn.fetch('''
                        SELECT context_type, source_identifier, content, updated_at
                        FROM context
                        WHERE user_id = $1 AND tenant_id = $2 AND context_type = $3 
                        AND source_identifier = $4
                        ORDER BY updated_at DESC
                    ''', user_id, tenant_id, context_type, source_identifier)
                else:
                    rows = await conn.fetch('''
                        SELECT context_type, source_identifier, content, updated_at
                        FROM context
                        WHERE user_id = $1 AND tenant_id = $2 AND context_type = $3
                        ORDER BY updated_at DESC
                    ''', user_id, tenant_id, context_type)
                
                # Convert database rows to Python dicts
                result = []
                for row in rows:
                    result.append({
                        'context_type': row['context_type'],
                        'source_identifier': row['source_identifier'],
                        'content': row['content'],
                        'timestamp': row['updated_at'].isoformat()
                    })
                
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
        if not self.pool:
            raise ConnectionError("Database not initialized")
        
        async with self.pool.acquire() as conn:
            user_id = await conn.fetchval("SELECT id FROM users WHERE api_key = $1", api_key)
            return user_id

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