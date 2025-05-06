# JEAN - Personal Memory Layer via MCP

JEAN is a personal memory layer designed to seamlessly enhance AI assistants like Claude Desktop or Cursor by providing relevant, personalized context through the Model Context Protocol (MCP).

## Overview

JEAN acts as a background MCP service that intelligently gathers, processes, and provides context without requiring explicit user commands. It leverages the large context windows of models like Gemini 1.5 Pro through a specialized routing architecture, offering an alternative to traditional RAG systems.

**Core Principles:**

-   **Silent Operation:** Works in the background via MCP.
-   **Contextual Relevance:** Uses specialized routers and Gemini to extract *relevant* information from broad context sources.
-   **User Simplicity:** Easy onboarding via Google Auth and a simple configuration URL.
-   **Privacy Focused:** User control over data, encryption at rest.
-   **Specialized Routing:** Avoids vector databases, instead routing queries to domain-specific Gemini processing pipelines.

## Architecture

1.  **Frontend (`frontend/`):** A minimal web interface for Google Sign-In. Its sole purpose is to authenticate the user and provide them with their unique MCP server configuration URL.
2.  **Backend (`backend/`):** A FastAPI application implementing the JEAN MCP server.
    -   **MCP Endpoint (`backend/app/`):** Handles `store` and `retrieve` requests.
    -   **Context Router (`backend/routers/context_router.py`):** Analyzes queries and dispatches to specialized routers.
    -   **Specialized Routers (`backend/routers/`):** Domain-specific routers (GitHub, Notes, Values, Conversations) that fetch raw data, format it, and process it using dedicated Gemini API calls (`backend/services/gemini_api.py`).
    -   **Database (`backend/database/`):** PostgreSQL database storing user info and cached raw context, accessed via `asyncpg`.

(See the architecture diagrams and detailed implementation guide in the original documents/design files for more.)

## Getting Started (Development)

**Prerequisites:**

-   Python 3.10+
-   Poetry (or `pip` with `requirements.txt`)
-   PostgreSQL server
-   Google Cloud Project for OAuth and Gemini API Key

**Setup:**

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd jean-memory 
    ```
2.  **Set up Backend Environment:**
    ```bash
    cd backend
    # Using Poetry (Recommended)
    poetry install 
    # OR using pip
    # pip install -r requirements.txt 
    ```
3.  **Configure Environment Variables:** Create a `.env` file in the `backend` directory based on `.env.example` (to be created) with your `DATABASE_URL` and `GEMINI_API_KEY`.
    ```dotenv
    # .env (in backend/)
    DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname
    GEMINI_API_KEY=your_google_gemini_api_key
    # Add Google OAuth Client ID/Secret later for frontend/auth
    ```
4.  **Set up Database:** Ensure your PostgreSQL server is running and the database/user specified in `DATABASE_URL` exists.
5.  **Run Database Migrations/Initialization (First Time):** The backend startup should handle table creation.
6.  **Run the Backend Server:**
    ```bash
    # From the backend/ directory
    poetry run uvicorn app.main:app --reload 
    # Or: python -m uvicorn app.main:app --reload
    ```
7.  **Frontend Setup (TBD):** Follow instructions in `frontend/README.md` once implemented.

## Immediate Next Steps (Code Implementation)

1.  **Backend - Database:** Implement `ContextDatabase` class in `backend/database/context_storage.py` with `initialize`, `store_context`, `get_context`, and basic user methods.
2.  **Backend - Services:** Implement `GeminiAPI` class in `backend/services/gemini_api.py` with initialization, prompt formatting, and the asynchronous `process` method.
3.  **Backend - App:** Set up basic FastAPI app in `backend/app/app.py` and startup logic in `backend/app/main.py` (including DB initialization).
4.  **Backend - Routers:** Implement basic `determine_context_type` and `ContextRouter` structure in `backend/routers/context_router.py`.
5.  **Backend - MCP Endpoint:** Implement the `/mcp` endpoint in `backend/app/app.py` to parse requests and call the `ContextRouter` (for retrieve) or database methods (for store - TBD).
6.  **Frontend - Basic UI:** Implement the Google Sign-In flow and display of the MCP URL.
