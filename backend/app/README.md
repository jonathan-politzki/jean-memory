# Backend Application Core (`backend/app`)

This directory forms the heart of the JEAN Memory backend, housing the main FastAPI application, its configuration, core services, and entry points.

## Overview

The `app` directory is responsible for:

*   **FastAPI Application Instance:** Initializing and configuring the main FastAPI application.
*   **Server Lifecycle:** Managing startup and shutdown events, including initializing database connections and other services.
*   **Configuration Management:** Loading application settings, primarily using Pydantic models and environment variables.
*   **API Endpoints:** Defining core API endpoints, middleware, and request/response models.
*   **Authentication & Authorization:** Handling API key verification and user identification.
*   **External Service Integration:** Providing clients or wrappers for external services, notably the Google Gemini API.

## Key Files and Their Roles

*   **`app.py`:**
    *   Defines the FastAPI application factory `create_app()`.
    *   Instantiates the FastAPI `app` object.
    *   Configures Cross-Origin Resource Sharing (CORS) middleware.
    *   Sets up global dependencies, like API key verification.
    *   Manages application startup (`@app.on_event("startup")`) and shutdown (`@app.on_event("shutdown")`) events. This includes initializing the database connection (via the singleton pattern from the `database` directory) and the `GeminiAPI` client, storing them in `app.state`.
    *   Initializes and stores the `ContextRouter` in `app.state`.
    *   Defines some core API endpoints like `/health` and `/auth/google/callback`.
    *   Previously, it might have contained the main `/mcp` endpoint, but recent versions might delegate this to a dedicated MCP server component (e.g., within `jean_mcp` or via `standalone_mcp_server.py`).

*   **`main.py`:**
    *   Imports the `app` instance from `app.py`.
    *   Loads environment variables using `dotenv`.
    *   Handles application startup (e.g., initializing the database via `database.initialize_db()` and storing it in `app.state.db`) and shutdown events (e.g., `database.close_db()`).
    *   Initializes instances of various routers (e.g., `GitHubOAuthRouter`, `ObsidianRouter`, `GoogleAuthRouter`) and the `GeminiAPI` client.
    *   **Defines a significant number of API routes directly within this file.** This includes routes for:
        *   Health checks (`/health`).
        *   MCP configuration retrieval (`/api/mcp-config`).
        *   GitHub integration (OAuth flow, status, data, settings, sync, disconnect).
        *   Obsidian integration (status, connect, test, settings, sync, disconnect).
        *   Google Authentication integration (OAuth flow, callback, status, disconnect).
        *   A placeholder for a knowledge graph API (`/api/knowledge/graph`).
    *   Includes the `if __name__ == "__main__":` block to run the application using `uvicorn` for development, making it an executable entry point for the server.

*   **`config.py`:**
    *   Defines a Pydantic `Settings` class to manage application configuration.
    *   Loads settings from environment variables and `.env` files.
    *   Includes settings like `database_url`, `gemini_api_key`, and `jean_api_base_url`.

*   **`auth.py`:**
    *   Defines functions for API key-based authentication.
    *   `api_key_header`: Defines how to extract the API key (`X-API-Key`) from request headers.
    *   `user_id_header`: Defines how to extract the User ID (`X-User-ID`) from request headers.
    *   `verify_api_key()`: Validates the provided API key (e.g., against an environment variable or by allowing any non-empty key in development).
    *   `get_user_id()`: Retrieves the user ID from headers after API key validation, with a fallback to an environment variable or a default value.

*   **`middleware.py`:**
    *   Contains FastAPI middleware, primarily for request processing and authentication.
    *   `verify_api_key()` (as middleware): Verifies the API key from the `Authorization` (Bearer token) or `x-api-key` header.
    *   Validates the API key against the database (using `db.validate_api_key()` from the `database` singleton).
    *   Sets `request.state.user_id` and `request.state.tenant_id` upon successful authentication.
    *   Includes special handling for test API keys and scenarios where no database is configured (fallback to a test mode).

*   **`models.py`:**
    *   Defines Pydantic models for structuring API request and response data.
    *   Includes models for MCP operations like `MCPRequest`, `MCPStoreParams`, `MCPRetrieveParams`, `MCPResult`, and `MCPResponse`.
    *   May also contain other data models, such as `UserInfo` for authentication-related responses.

*   **`gemini_api.py`:**
    *   Provides a `GeminiAPI` class to interact with Google's Gemini services.
    *   Handles embedding generation (`generate_embedding`) using the `embedding-001` model via HTTP requests to the `generativelanguage.googleapis.com` endpoint.
    *   Includes methods for calculating similarity scores (`similarity_score`) between embeddings and searching for similar texts (`search_similar_texts`).
    *   Requires a `GEMINI_API_KEY` for its operations.

*   **`__init__.py`:** Standard Python package marker.

## Interaction and Dependencies

*   **Database (`../database`):** The `app` module heavily relies on the `database` directory (specifically `context_storage.py`) for all data persistence tasks, including user creation/validation and context storage/retrieval. It uses a singleton pattern for database connections, initialized at startup.
*   **Routers (`../routers` and Routers defined in `main.py`):** While `main.py` defines many routes, it also initializes router classes (like `GitHubOAuthRouter`). The application structure suggests that more complex routing logic or route groups might be intended for the dedicated `../routers` directory.
*   **Services (`../services`, e.g., `gemini_api.py` within `app`):** External service interactions, like with the Gemini API, are encapsulated in client classes.
*   **MCP Components (`../jean_mcp`):** While `main.py` and `app.py` have references to MCP, the core MCP server logic and tool definitions are expected to reside primarily in the `jean_mcp` directory or be launched via a script like `standalone_mcp_server.py`.

## Noteworthy Observations

*   **Route Definitions:** A significant number of specific API routes (GitHub, Obsidian, Google Auth) are defined directly in `app/main.py`. In larger applications, these are often organized into separate files within a `routers` directory and included in the main app using `app.include_router()`.
*   **App State:** The FastAPI `app.state` is used to store shared resources like the database connection (`app.state.db`), Gemini API client (`app.state.gemini_api`), and context router (`app.state.context_router`), making them accessible throughout the application.

This `app` directory serves as the central nervous system of the backend, orchestrating various components to deliver the JEAN Memory service. 