import asyncpg
import json
import secrets
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class ContextDatabase:
    """Database access for context storage and user management."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize database connection pool and create tables if they don't exist."""
        if self._pool:
            logger.warning("Database pool already initialized.")
            return
        try:
            self._pool = await asyncpg.create_pool(self.database_url)
            logger.info("Database connection pool created successfully.")

            async with self._pool.acquire() as conn:
                # Create users table
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id SERIAL PRIMARY KEY,
                        google_id TEXT UNIQUE NOT NULL,
                        email TEXT,
                        api_key TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
                    )
                ''')
                logger.info("Checked/created 'users' table.")

                # Create raw_context table
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS raw_context (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                        context_type TEXT NOT NULL,
                        content JSONB NOT NULL,
                        source_identifier TEXT, -- e.g., repo name, note filename
                        created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
                        updated_at TIMESTAMPTZ,
                        UNIQUE(user_id, context_type, source_identifier) -- Ensure unique context per source
                    )
                ''')
                logger.info("Checked/created 'raw_context' table.")

                # Add indexes for faster lookups
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_google_id ON users (google_id)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_api_key ON users (api_key)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_raw_context_user_type ON raw_context (user_id, context_type)')

        except Exception as e:
            logger.exception(f"Failed to initialize database pool or tables: {e}")
            self._pool = None # Ensure pool is None if init failed
            raise

    async def close(self):
        """Close the database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed.")

    def _get_pool(self) -> asyncpg.Pool:
        """Get the pool, raising an error if not initialized."""
        if not self._pool:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")
        return self._pool

    def _generate_secure_api_key(self) -> str:
        """Generate a secure random API key."""
        return secrets.token_hex(32)

    async def create_or_get_user(self, google_id: str, email: Optional[str]) -> Tuple[int, str]:
        """Create a new user or get existing user based on Google ID. Returns (user_id, api_key)."""
        pool = self._get_pool()
        async with pool.acquire() as conn:
            # Check if user exists
            user_record = await conn.fetchrow(
                "SELECT user_id, api_key FROM users WHERE google_id = $1", google_id
            )

            if user_record:
                logger.info(f"Found existing user for google_id: {google_id[:5]}...")
                return user_record['user_id'], user_record['api_key']

            # User doesn't exist, create new user with API key
            api_key = self._generate_secure_api_key()
            logger.info(f"Creating new user for google_id: {google_id[:5]}...")

            try:
                user_record = await conn.fetchrow(
                    """
                    INSERT INTO users (google_id, email, api_key)
                    VALUES ($1, $2, $3)
                    RETURNING user_id, api_key
                    """,
                    google_id, email, api_key
                )
                if user_record:
                     return user_record['user_id'], user_record['api_key']
                else:
                    # This should not happen with RETURNING clause if insert succeeds
                    raise RuntimeError("Failed to retrieve user info after insert.")
            except asyncpg.UniqueViolationError:
                # Handle rare race condition where user was created between SELECT and INSERT
                logger.warning(f"Race condition detected for google_id: {google_id[:5]}... Retrying fetch.")
                user_record = await conn.fetchrow(
                    "SELECT user_id, api_key FROM users WHERE google_id = $1", google_id
                )
                if user_record:
                    return user_record['user_id'], user_record['api_key']
                else:
                    # If still not found, something is wrong
                    raise RuntimeError("Failed to create or find user after race condition.")


    async def validate_api_key(self, api_key: str) -> Optional[int]:
        """Validate an API key and return the corresponding user_id if valid."""
        pool = self._get_pool()
        async with pool.acquire() as conn:
            user_id = await conn.fetchval("SELECT user_id FROM users WHERE api_key = $1", api_key)
            return user_id

    async def store_context(self, user_id: int, context_type: str, content: Dict[str, Any], source_identifier: Optional[str] = None):
        """Store or update raw context in the database."""
        pool = self._get_pool()
        now = datetime.utcnow()
        content_json = json.dumps(content)

        async with pool.acquire() as conn:
            # Use ON CONFLICT to handle inserts or updates
            await conn.execute(
                '''
                INSERT INTO raw_context (user_id, context_type, content, source_identifier, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $5)
                ON CONFLICT (user_id, context_type, source_identifier)
                DO UPDATE SET
                    content = EXCLUDED.content,
                    updated_at = EXCLUDED.updated_at
                ''',
                user_id, context_type, content_json, source_identifier, now
            )
        logger.info(f"Stored/updated context for user {user_id}, type '{context_type}', source '{source_identifier}'")


    async def get_context(self, user_id: int, context_type: str, source_identifier: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve specific raw context from the database."""
        pool = self._get_pool()
        query = 'SELECT content FROM raw_context WHERE user_id = $1 AND context_type = $2'
        params = [user_id, context_type]

        if source_identifier:
            query += ' AND source_identifier = $3'
            params.append(source_identifier)
        else:
             # If no specific source, maybe get the most recently updated? Or all? Decide strategy.
             # For now, let's assume source_identifier is usually provided or we fetch all of a type.
             # To get the most recent: query += ' ORDER BY updated_at DESC NULLS LAST LIMIT 1'
             # To get all: Modify return type to List[Dict] and use fetch() instead of fetchrow()
             # For this example, we require source_identifier or return None if ambiguous
             if not source_identifier:
                 logger.warning("get_context called without source_identifier, ambiguity possible.")
                 return None # Or fetch all if desired


        async with pool.acquire() as conn:
            record = await conn.fetchrow(query, *params)

            if record and record['content']:
                logger.info(f"Retrieved context for user {user_id}, type '{context_type}', source '{source_identifier}'")
                return json.loads(record['content'])
            else:
                 logger.info(f"No context found for user {user_id}, type '{context_type}', source '{source_identifier}'")
                 return None

    async def get_all_context_by_type(self, user_id: int, context_type: str) -> list[Dict[str, Any]]:
        """Retrieve all raw context of a specific type for a user."""
        pool = self._get_pool()
        query = 'SELECT content FROM raw_context WHERE user_id = $1 AND context_type = $2 ORDER BY updated_at DESC NULLS LAST'
        params = [user_id, context_type]

        results = []
        async with pool.acquire() as conn:
            records = await conn.fetch(query, *params)
            for record in records:
                if record and record['content']:
                    results.append(json.loads(record['content']))

        logger.info(f"Retrieved {len(results)} context items for user {user_id}, type '{context_type}'")
        return results 