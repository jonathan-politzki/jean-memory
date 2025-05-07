# Backend Database (`backend/database`)

This directory is responsible for all interactions with the persistent data store for the JEAN Memory system, which is PostgreSQL. It provides an abstraction layer for database operations, focusing on asynchronous communication and a structured approach to data storage.

## Core Functionality

*   **Database Connection Management:** Establishes and manages an asynchronous connection pool to PostgreSQL using `asyncpg`.
*   **Schema Definition and Initialization:** Defines and creates the necessary database tables (`users`, `context`) and their associated indexes upon application startup.
*   **Data Access Layer:** Provides a comprehensive set of asynchronous methods for Creating, Reading, Updating, and Deleting (CRUD) user data and context entries.
*   **User and Tenant Management:** Handles user creation (often linked to Google OAuth identity), API key generation and validation, and supports a `tenant_id` for data isolation.
*   **Context Storage:** Stores various types of user-specific context information, where the actual content is stored in `JSONB` format, allowing for flexible data structures.
*   **Singleton Pattern:** Ensures that a single, shared instance of the database connection pool is used throughout the application, managed via functions in `__init__.py`.

## Key Files

*   **`context_storage.py`:**
    *   Defines the `ContextDatabase` class, which encapsulates all database logic.
    *   Handles the PostgreSQL connection string (adapting from SQLAlchemy format if needed).
    *   Manages an `asyncpg` connection pool.
    *   Contains methods for:
        *   `initialize()`: Connects to the DB, creates the pool, and executes DDL statements to create `users` and `context` tables if they don't exist, along with relevant indexes.
        *   `close()`: Closes the connection pool.
        *   `create_or_get_user()`: Creates a new user (with a new API key) or retrieves an existing one based on `tenant_id` and `google_id`.
        *   `validate_api_key()`: Checks if an API key is valid by querying the `users` table. Includes development mode fallbacks where it might accept any key or default to a test user if the DB isn't fully set up or the key isn't found.
        *   `store_context()`: Inserts or updates (upserts) a context entry in the `context` table. Content and metadata are stored as `JSONB`.
        *   `get_context()`: Retrieves context entries for a user, filtered by `tenant_id`, `context_type`, and optionally `source_identifier` or a `limit`.
        *   `get_all_context_by_type()`: Retrieves all context entries for a user of a specific type.
        *   `search_context()`: Performs a basic `ILIKE` search on the `content` field (cast to text) for a given query string.
        *   `get_context_by_id()`: Retrieves a specific context entry by its primary key, ensuring it belongs to the correct user and tenant.
        *   `delete_context_by_id()`: Deletes a specific context entry by its ID, with user/tenant ownership checks.
        *   `delete_user_data()`: Deletes all context data for a specific user within a tenant.
        *   `delete_context_by_type_and_user()`: Deletes all context entries for a specific user, tenant, and context type.
        *   `get_user_settings_by_id()` and `update_user_settings_by_id()`: Manage user-specific settings stored in a `JSONB` column in the `users` table.

*   **`__init__.py`:**
    *   Implements a singleton pattern for the `ContextDatabase`.
    *   `_db_instance`: A global variable holding the single `ContextDatabase` instance.
    *   `initialize_db(connection_string)`: Creates and initializes `_db_instance` if it doesn't exist, or returns the existing one.
    *   `get_db()`: Returns the `_db_instance`.
    *   `close_db()`: Closes the connection pool of `_db_instance` and resets it to `None`.
    *   This ensures that different parts of the application (e.g., middleware, API endpoints, MCP tools) share the same database connection pool.

## Database Schema Visualization

The database primarily consists of two tables:

1.  **`users` Table:** Stores information about individual users and their tenancy.
    *   `id` (SERIAL PRIMARY KEY): Unique identifier for the user.
    *   `tenant_id` (VARCHAR(50)): Identifier for the tenant (e.g., organization, team) to which the user belongs. Crucial for data isolation.
    *   `google_id` (VARCHAR(255) UNIQUE): The user's unique Google ID, used for authentication.
    *   `email` (VARCHAR(255) UNIQUE): The user's email address.
    *   `api_key` (VARCHAR(255) UNIQUE): A unique API key generated for the user to access the JEAN Memory service.
    *   `is_active` (BOOLEAN DEFAULT TRUE): Flag indicating if the user account is active.
    *   `created_at` (TIMESTAMP WITH TIME ZONE DEFAULT NOW()): Timestamp of user creation.
    *   `last_active` (TIMESTAMP WITH TIME ZONE DEFAULT NOW()): Timestamp of the user's last activity.
    *   `settings` (JSONB DEFAULT '{}'): Stores user-specific settings and preferences in JSON format.
    *   **Unique Constraint:** `UNIQUE(tenant_id, google_id)` ensures a Google ID is unique within a specific tenant.

2.  **`context` Table:** Stores the actual memory entries and contextual data for users.
    *   `id` (SERIAL PRIMARY KEY): Unique identifier for the context entry.
    *   `user_id` (INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE): Foreign key linking to the `users` table. Ensures that if a user is deleted, their context data is also removed.
    *   `tenant_id` (VARCHAR(50) NOT NULL): Copied from the user record for stronger data isolation and potentially for direct querying by tenant without joining `users`.
    *   `context_type` (VARCHAR(50) NOT NULL): A string identifying the type of context (e.g., "note", "github_commit", "conversation_summary"). Used for organizing and retrieving specific kinds of memories.
    *   `source_identifier` (VARCHAR(255)): An optional unique identifier for the source of this memory entry (e.g., a specific file path, URL, message ID).
    *   `content` (JSONB NOT NULL): The main data for this memory entry, stored in a flexible JSONB format. This allows storing complex, structured data.
    *   `metadata` (JSONB DEFAULT '{}'): Additional, type-specific metadata about the context entry (e.g., tags, priority, source URL), also in JSONB format.
    *   `created_at` (TIMESTAMP WITH TIME ZONE DEFAULT NOW()): Timestamp of context entry creation.
    *   `updated_at` (TIMESTAMP WITH TIME ZONE DEFAULT NOW()): Timestamp of the last update to the context entry.
    *   **Unique Constraint:** `UNIQUE(tenant_id, user_id, context_type, source_identifier)` ensures that for a given user within a tenant, a specific `source_identifier` within a `context_type` is unique. This helps prevent duplicate entries for the same item.
    *   **Indexes:**
        *   `idx_context_user_type` ON `context(user_id, context_type)`: For efficient querying of context entries by user and type.
        *   `idx_context_tenant` ON `context(tenant_id)`: For efficient querying by tenant.

## How It Works (Data Flow and Interaction)

1.  **Initialization:** When the FastAPI application starts (in `backend/app/app.py` or `main.py`), `initialize_db()` from `backend/database/__init__.py` is called.
    *   This creates a `ContextDatabase` instance if one doesn't exist.
    *   The `ContextDatabase.initialize()` method establishes a connection pool to PostgreSQL and executes `CREATE TABLE IF NOT EXISTS` statements for `users` and `context`.
    *   The initialized `ContextDatabase` instance is stored globally (as `_db_instance`) and often also in `app.state.db` for easy access within FastAPI request handlers.

2.  **User Authentication/Creation:**
    *   When a user logs in (e.g., via Google OAuth, handled in `backend/app/app.py` or a dedicated auth router), their `google_id` and `email` are obtained.
    *   `ContextDatabase.create_or_get_user(tenant_id, google_id, email)` is called.
        *   This attempts to insert a new user. If a user with that `google_id` (within the `tenant_id`) already exists (due to the `ON CONFLICT` clause), it updates their `last_active` time and `email`.
        *   It returns the user's internal `id` and their `api_key` (either newly generated or existing).
    *   API key validation (e.g., in `backend/app/middleware.py`) calls `ContextDatabase.validate_api_key(api_key)` to check if the provided key exists in the `users` table and retrieve the associated `user_id`.

3.  **Storing Context:**
    *   When an MCP tool (e.g., `create_jean_memory_entry`) or an internal process needs to save information:
    *   It calls `ContextDatabase.store_context(user_id, tenant_id, context_type, content, source_identifier, metadata)`.
    *   The `content` and `metadata` (Python dictionaries) are serialized to JSON strings.
    *   An `INSERT ... ON CONFLICT ... DO UPDATE` statement is used to either create a new record in the `context` table or update an existing one (based on the unique constraint `tenant_id, user_id, context_type, source_identifier`).

4.  **Retrieving Context:**
    *   When an MCP tool (e.g., `access_jean_memory`) or another part of the system needs to fetch memories:
    *   It calls methods like `ContextDatabase.get_context()`, `get_all_context_by_type()`, or `search_context()` with the `user_id`, `tenant_id`, and relevant filters (`context_type`, query string, etc.).
    *   These methods construct and execute `SELECT` queries against the `context` table.
    *   JSONB content is retrieved and typically deserialized back into Python dictionaries before being returned.

This `database` module provides a robust and isolated way to manage all persistent data for the JEAN Memory system, ensuring data integrity and enabling efficient access for the rest of the backend application. 