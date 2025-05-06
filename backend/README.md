# JEAN Backend

This directory contains the core backend logic for the JEAN system.

## Overview

The backend implements the JEAN service, acting as a Model Context Protocol (MCP) server. Its primary responsibilities include:

1.  **Handling MCP Requests:** Implementing the `store` and `retrieve` operations defined by the MCP specification.
2.  **Context Routing:** Analyzing incoming queries to determine the appropriate context type(s) required.
3.  **Specialized Processing:** Utilizing specialized routers, each integrated with the Gemini API, to process context relevant to specific domains (GitHub, Notes, Values, Conversations).
4.  **Data Management:** Interacting with the database to fetch raw context data and store processed information or user metadata.
5.  **User Authentication:** Handling user authentication (likely via tokens validated from the frontend Google Sign-In) and associating data with specific users.
6.  **External Integrations:** Managing connections to external APIs (e.g., GitHub API) to fetch raw context data when not available in the cache/database.

## Directory Structure

-   `app/`: Contains the main FastAPI application setup, entry points (`main.py`), and MCP endpoint definitions (`app.py`).
-   `routers/`: Holds the core context routing logic (`context_router.py`) and implementations for each specialized router (`github_router.py`, `notes_router.py`, etc.).
-   `services/`: Contains clients and wrappers for interacting with external services like the Gemini API (`gemini_api.py`) and potentially others (e.g., `github_client.py`).
-   `database/`: Handles all database interactions, including schema definition, connection management, and data access objects/functions (`context_storage.py`).
-   `models/`: (Optional) Defines data structures and Pydantic models used throughout the application for validation and consistency.

## Key Technologies

-   **Framework:** FastAPI
-   **AI:** Google Generative AI (Gemini 1.5 Pro)
-   **Database:** PostgreSQL (using `asyncpg`)
-   **Language:** Python

## Next Steps

1.  Set up the basic FastAPI application in `app/`.
2.  Define the database schema and implement initialization logic in `database/`.
3.  Implement the core MCP endpoint in `app/app.py`.
4.  Develop the basic structure of the `ContextRouter` in `routers/`.
5.  Implement the `GeminiAPI` service wrapper in `services/`. 