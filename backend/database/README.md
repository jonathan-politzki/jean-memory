# Backend Database (`database/`)

This directory handles all interactions with the persistent data store (PostgreSQL).

## Overview

JEAN needs to store user information, cached raw context fetched from external sources, and potentially processed context or metadata. This module provides the necessary database access logic.

## Files

-   `context_storage.py`: Contains the `ContextDatabase` class (or equivalent data access functions). This class is responsible for:
    -   Managing the database connection pool (`asyncpg.create_pool`).
    -   Initializing the database, including creating tables (`raw_context`, potentially `users`, etc.) if they don't exist.
    -   Providing asynchronous methods for CRUD (Create, Read, Update, Delete) operations on the database tables.
    -   Specific methods mentioned in the guide:
        -   `initialize()`: Sets up the pool and creates tables.
        -   `store_context(user_id, context_type, content)`: Inserts or updates raw context data (using `JSONB` for content).
        -   `get_context(user_id, context_type)`: Retrieves raw context data.
        -   Potentially methods like `store_github_context`, `fetch_github_context` if specific tables are used per context type, or if logic differs slightly.
        -   Methods for user profile management (e.g., `create_user`, `get_user_by_google_id`).
-   `schema.sql` (Optional): Could contain the raw SQL `CREATE TABLE` statements for documentation or manual setup.

## Responsibilities

-   **Connection Management:** Establish and manage the connection pool to the PostgreSQL database.
-   **Schema Management:** Define and create the necessary database tables.
-   **Data Access:** Provide functions/methods to interact with the database (store, retrieve, update, delete data).
-   **Data Transformation:** Handle serialization/deserialization of data (e.g., `json.dumps`/`json.loads` for `JSONB` fields).
-   **Asynchronous Operations:** Ensure all database operations are non-blocking using `asyncpg`.

## Next Steps

1.  Implement the `ContextDatabase` class structure in `context_storage.py`.
2.  Implement the `initialize` method, including connection pool creation and the `CREATE TABLE IF NOT EXISTS raw_context` statement.
3.  Implement the `store_context` method using the `INSERT ... ON CONFLICT ... DO UPDATE` pattern.
4.  Implement the `get_context` method to fetch and deserialize context.
5.  Define and implement methods for user profile storage and retrieval, linking to Google ID. 