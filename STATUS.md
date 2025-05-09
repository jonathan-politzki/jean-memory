# JEAN Project Status

## Deployment Status (as of May 2025)
- ✅ **Web Frontend (`app.jeantechnologies.com`)**: Deployed to Google Cloud Run, accessible via `https://app.jeantechnologies.com`.
    - Secured by Google Cloud Load Balancer and Identity-Aware Proxy (IAP).
    - User authentication via Google OAuth managed by IAP.
- ✅ **Backend (`jean-memory-api`)**: Deployed to Google Cloud Run, connected to Cloud SQL (PostgreSQL).
    - Accessed by the deployed frontend.
    - MCP endpoint also available for local/desktop client integration (see below).

## Current Functionality
- ✅ **Frontend UI**: Modern AI-style interface with responsive design
- ✅ **Authentication**: Google OAuth integration working properly.
- ✅ **CORS & API Communication**: Frontend-backend communication properly configured.
- ✅ **Containerization**: Full application (frontend, backend, postgres, redis) containerized with Docker Compose.
- ✅ **MCP Endpoint**: Robust Model Context Protocol implementation via `stdio` for Claude Desktop.
    - ✅ Core memory tools (`create_jean_memory_entry`, `access_jean_memory` with Gemini synthesis, `clear_jean_memory_bank`, `diagnose_list_gemini_models`).
    - ✅ GitHub integration tools (pending token setup).
    - ✅ Value extraction tools (using Gemini).
    - ✅ Auth tools for MCP config.
    - ✅ MCP Prompts defined for tool guidance.
- ✅ **Context Banks**: System supports storing and retrieving data from different "context banks" using `context_type`.
- ✅ **Database Integration**: PostgreSQL connection stable; schema for users and context established and working.
- ✅ **Memory Storage & Retrieval**: Core functions for creating, retrieving, searching, and clearing memory entries are functional.
- ✅ **Gemini Integration**: `access_jean_memory` tool successfully calls Gemini API for context synthesis (using `models/gemini-1.5-pro-latest`). Gemini error handling for model availability is improved.
- ✅ **Error Handling**: Graceful error handling in tools and database interactions.

## Working Flow
1. Run `docker-compose up -d` to start backend services (PostgreSQL).
2. Configure `claude_desktop_config.json` to launch `backend/standalone_mcp_server.py` via `python3` with `stdio` transport, providing necessary `env` vars (`DATABASE_URL` pointing to `localhost:5433`, `GEMINI_API_KEY`, `JEAN_USER_ID`).
3. Restart Claude Desktop.
4. MCP tools for JEAN Memory populate in Claude Desktop.
5. User can interact with Claude to:
    - Store new memories in various context banks using `create_jean_memory_entry`.
    - Access and synthesize memories using `access_jean_memory` (which internally uses Gemini).
    - Clear memory banks using `clear_jean_memory_bank`.
    - Other tools (GitHub, value extraction) are available but may depend on further setup (e.g., GitHub token).

### Local Development Database Note:
- When running the MCP server locally (e.g., via Claude Desktop), ensure it uses the correct `DATABASE_URL` for the local Dockerized PostgreSQL (e.g., `postgresql://postgres:postgres@localhost:5433/postgres`).
- This is typically set in the `env` block of your `claude_desktop_config.json`.
- If you encounter database connection errors referencing incorrect hostnames, credentials, or Cloud SQL paths, your shell environment might have an overriding `DATABASE_URL`. Prefixing the server command can resolve this: `DATABASE_URL="postgresql://postgres:postgres@localhost:5433/postgres" poetry run python jean_mcp_server.py --mode stdio`.

## Architecture Improvements
- ✅ **Database Singleton Pattern**: Ensures all app components use the same database connection.
- ✅ **API Key Validation (Development Mode)**: Robust validation with development mode fallbacks for `stdio` context.
- ✅ **Refactored MCP Tools**: Moved from specific "note" tools to a more generalized `core_memory_tools.py` (`create_jean_memory_entry`, `access_jean_memory`) and a `clear_jean_memory_bank` tool.
- ✅ **`stdio` for Claude Desktop**: MCP server now uses `stdio` transport when launched by Claude Desktop, resolving previous connection and configuration issues.
- ✅ **Gemini Model Name Corrected**: Successfully diagnosed and fixed Gemini API calls to use an available model (`models/gemini-1.5-pro-latest`).
- ✅ **Asynchronous Operations**: Ensured Gemini API calls within async MCP tools are non-blocking.

## Next Steps

### 1. Frontend Feature Implementation & Testing
- Implement UI functionalities on `https://app.jeantechnologies.com` for:
    - Viewing/managing MCP configuration.
    - Basic note creation/management (if intended beyond MCP).
    - Connecting to and managing context sources (GitHub, etc.).
- Thoroughly test the deployed frontend and its interaction with the deployed backend API.

### 2. Thorough Testing & Refinement (MCP Tools)
- Rigorously test `access_jean_memory` with various scenarios of relevant, partially relevant, and conflicting memories to evaluate Gemini synthesis quality and adherence to "honesty" in prompts.
- Iteratively refine the Gemini prompt in `access_jean_memory` for optimal synthesis.
- Test `value_extraction_tools`.
- Implement a way to set the GitHub token (e.g., a new MCP tool `update_github_token` or manual DB entry) and then test `github_tools`.

### 3. Enhance Context Functionality (Backend)
- Consider UI implications for managing different context banks if a frontend is to interact directly (beyond MCP).
- Further develop the "intelligent" aspects of `access_jean_memory`:
    - Smarter `context_type` selection if `target_context_types` is not provided.
    - More advanced query generation for `db.search_context`.

### 4. Full MCP Compliance & Features (Backend)
- Review and test all defined MCP Prompts for utility.
- Evaluate if specific resource URIs (like `notes://search/{query}`) are still needed or if `access_jean_memory` covers these use cases adequately.

### 5. Security & Production Readiness (Overall)
- Review and potentially remove/refine `MCPAuthMiddleware` in the backend if IAP and frontend authentication cover necessary scenarios for the deployed API.
- Remove any remaining development mode fallbacks if moving towards production.
- Consider API key rotation strategies for services like Gemini if the key is bundled.

## How to Run (for MCP with Claude Desktop)
1. Ensure Docker is running.
2. In the project root, run `docker-compose up -d` (primarily for the `postgres` service).
3. **Local Backend Setup:** Navigate to the `backend` directory (`cd backend`) and run `poetry install` to ensure dependencies are installed in the local virtual environment.
4. **Find Python Path:** In the `backend` directory, run `poetry env info --path` and note the full path to the virtual environment.
5. Configure `~/Library/Application Support/Claude/claude_desktop_config.json` as per documentation:
    - Use the **full path to the Python executable** from the Poetry virtual environment (e.g., `/path/from/step4/bin/python`) as the `"command"`.
    - Set the `"args"` to point to `backend/jean_mcp_server.py` (using its full path) with `--mode stdio`.
    - Set the correct `env` vars (`DATABASE_URL` pointing to `localhost:5433`, `GEMINI_API_KEY`, `JEAN_USER_ID`).
6. Completely quit and restart Claude Desktop.

## MCP Integration
JEAN is an "MCP first" application. The `stdio`-based integration with Claude Desktop is now the primary local development and testing method. The system provides:
- Core tools: `create_jean_memory_entry`, `access_jean_memory`, `clear_jean_memory_bank`, `diagnose_list_gemini_models`.
- Specialized tools: GitHub integration, value extraction, MCP configuration.
- MCP Prompts for guiding LLM interaction.

## Development Mode Notes
- `JEAN_USER_ID` and `JEAN_API_KEY` in `claude_desktop_config.json`'s `env` block provide context for the `stdio` launched server.
- `validate_api_key` in `context_storage.py` has development fallbacks; review for production.
- **Poetry Setup:** Ensure the `poetry` command works in your local terminal. If you encounter `ModuleNotFoundError: No module named 'poetry'`, you may need to fix the shebang line in the `poetry` script or reinstall Poetry. If you get SSL errors during installation, run `Install Certificates.command` from your Python Application folder. 