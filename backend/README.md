# JEAN Memory Backend

This directory houses the core backend logic for the JEAN Memory system. It acts as a Model Context Protocol (MCP) server, enabling AI models like Claude to store and retrieve information.

## Core Functionality

The backend is responsible for:

*   **Memory Storage:** Persisting user memories, notes, and various contextual information in a structured database (PostgreSQL).
*   **Memory Retrieval:** Employing semantic search and an intelligent routing system to find relevant memories based on user queries or AI model requests.
*   **MCP Implementation:** Exposing tools for AI models to interact with the memory system, primarily `create_jean_memory_entry` and `access_jean_memory`.
*   **User Management:** Designed to handle user-specific data, ensuring information is associated with and isolated to the correct user.

## Key Components and Technologies

*   **Framework:** FastAPI (Python)
*   **AI/NLP:** Google Generative AI (Gemini) for tasks like query classification and semantic understanding.
*   **Database:** PostgreSQL
*   **MCP Server:** Implemented using `jean_mcp_server.py`, which can run in different modes (stdio for Claude Desktop, HTTP for general API access).
*   **Autonomous Router System:** An advanced system that intelligently classifies user queries or AI model requests to determine the most relevant type of context (e.g., GitHub, notes, values, conversations). This allows for more targeted and effective information retrieval. Models can rely on this automatic classification or explicitly specify a context type.

## Directory Structure

*   `app/`: Contains the main FastAPI application setup, API endpoints, and high-level application logic.
*   `database/`: Manages all database interactions, including schema definitions (e.g., using SQLAlchemy) and data access layers.
*   `jean_mcp/`: Contains the core MCP server implementation, including tool definitions and server configuration. This is where the `jean_mcp_server.py` script likely resides.
*   `routers/`: Defines API route handlers for different functionalities. This likely includes the specialized routers for various context types (GitHub, notes, etc.).
*   `services/`: Houses clients and wrappers for interacting with external services, such as the Google Gemini API.
*   `tests/`: Contains unit and integration tests for the backend application.

## Running the Server

The backend is typically run using the `jean_mcp_server.py` script.

**1. Stdio Mode (for Claude Desktop Integration):**

   This mode allows Claude Desktop to communicate with the JEAN Memory backend directly.

   ```bash
   # From the 'backend' directory
   python jean_mcp_server.py --mode stdio
   ```

   **Required Environment Variables:**
    *   `JEAN_USER_ID`: Identifier for the current user.
    *   `JEAN_API_KEY`: API key for authenticating requests to the backend.
    *   `DATABASE_URL`: Connection string for the PostgreSQL database (e.g., `postgresql://user:password@host:port/dbname`).
    *   `GEMINI_API_KEY`: API key for Google Gemini services.

   Claude Desktop needs to be configured to point to this script. See `CLAUDE_CONFIG.md` (to be deleted, content incorporated here) for details on the JSON configuration structure for `mcpServers` in Claude Desktop, including setting the command, arguments, and environment variables.

**2. HTTP API Server Mode:**

   This mode exposes the backend as an HTTP API, allowing other services or frontends to interact with it.

   ```bash
   # From the 'backend' directory
   python jean_mcp_server.py --mode http --port 8001
   ```
   (The port can be configured as needed).

   When configuring Claude Desktop for HTTP mode, the `serverType` would be "HTTP", `serverUrl` would point to `http://localhost:8001` (or the configured URL), and headers like `X-API-Key` and `X-User-ID` would be used for authentication.

## Autonomous Router System In-Depth

The backend features an advanced routing system to enhance context retrieval. It categorizes information into domains like:

*   GitHub (code, issues)
*   Notes (personal knowledge)
*   Values (preferences, principles)
*   Conversations (meeting notes, chats)
*   Tasks (to-dos, project plans)
*   And others like Work, Media, Locations.

When a query comes in (e.g., via `access_jean_memory`), the system can:

1.  **Autonomously Classify:** Use Gemini to determine which category the query best fits.
2.  **Route:** Direct the query to a specialized router for that category.
3.  **Retrieve:** The specialized router fetches the most relevant information.

AI models can also bypass automatic classification by explicitly stating the `context_type` in their requests if they already know where to look. This system is detailed in the (now incorporated) `ROUTER_SYSTEM.md`.

## Purpose in the JEAN Memory Project

The backend is the heart of the JEAN Memory system. It manages the storage, retrieval, and intelligent processing of all information that constitutes a user's "memory." It provides the necessary APIs and MCP tools for AI agents and frontend applications to interact with this memory, enabling them to recall past information, understand user preferences, and access relevant context for various tasks.

## Next Steps

1. Complete the frontend integration with Obsidian and GitHub.
2. Deploy to Google Cloud Run following the deployment plan.
3. Implement robust authentication and user management.
4. Expand memory types and context sources. 