# JEAN Memory Project Status

## Project Overview

JEAN (JSON Entity Aware Network) Memory is a personal AI memory layer that enhances AI assistants with contextual information. The system provides an interface for storing and retrieving user data and exposing it to AI assistants through the Model Context Protocol (MCP).

## Current Implementation Status

### ✅ Core Components Implemented

- **Backend API**: FastAPI-based service with PostgreSQL database for storing user context
- **Frontend UI**: Modern, responsive web interface for user interaction
- **Authentication**: Google OAuth integration for secure user access
- **Context Storage**: System for storing and retrieving notes and other user data
- **Docker Integration**: Full containerization with docker-compose for consistent deployment
- **MCP Integration**: Complete Model Context Protocol implementation with tools and resources

### ✅ MCP Implementation Progress

We've fully implemented the Model Context Protocol:

1. **Jean MCP Module**: Created a clean, structured implementation in `jean_mcp/` that follows the official MCP SDK patterns:
   - `jean_mcp/server/mcp_server.py`: Server configuration with lifespan management
   - `jean_mcp/server/middleware.py`: Authentication middleware for MCP requests
   - `jean_mcp/tools/note_tools.py`: Tools for creating, searching, and retrieving notes
   - `jean_mcp/tools/github_tools.py`: Tools for GitHub repository and activity integration
   - `jean_mcp/tools/auth_tools.py`: Tools for authentication and configuration
   - `jean_mcp/tools/value_extraction_tools.py`: Tools for analyzing user values using Gemini
   - `jean_mcp/resources/prompts.py`: MCP prompts for guiding LLM interaction
   - `jean_mcp/server/mcp_config.py`: Configuration endpoints for Claude Desktop

2. **MCP Server Integration**:
   - Created a standalone MCP server in `standalone_mcp_server.py` for dedicated MCP functionality
   - Successfully initialized server with all tools and resources
   - Verified proper logging and registration of MCP components

3. **Testing and Debugging**:
   - Identified routing conflicts between FastAPI app and MCP server
   - Found that MCP protocol requires proper session handling
   - Created test scripts for curl and Python-based HTTP testing
   - Discovered that MCP SDK version 1.7.1 expects session_id parameter for all requests

4. **Claude Desktop Integration**:
   - Created configuration documentation in `CLAUDE_CONFIG.md`
   - Generated correct configuration JSON for Claude Desktop connection
   - Prepared standalone server for proper Claude Desktop integration

## Technical Details

### MCP Implementation Architecture

- Using the official MCP SDK from Anthropic (`mcp` package v1.7.1)
- Implemented through Server-Sent Events (SSE) transport at `/messages/` endpoint
- Authentication through X-API-Key header and middleware validation
- Providing resources, tools, and context data through standardized MCP interfaces
- Structured to handle multiple users and tenants

### MCP Capabilities

1. **Note Management**:
   - Create, search, and retrieve notes with optional tags
   - Recent notes access through both tools and resources
   - Search by content or tags

2. **GitHub Integration**:
   - Repository listing and details
   - Recent activity tracking and summarization
   - Integration with user context

3. **Value Extraction**:
   - Analysis of user preferences and values
   - Identification of evolving preferences over time
   - Integration with Gemini for deep context analysis

4. **Claude Desktop Integration**:
   - Configuration UI for easy setup
   - Dynamic configuration generation
   - Clear instructions for users

### Implementation Challenges and Solutions

1. **Routing Conflicts**:
   - Identified conflict between FastAPI app's `/mcp` endpoint and MCP server
   - Resolved by creating a standalone MCP server for dedicated MCP functionality
   - Used separate port (8001) to avoid conflicts with main application

2. **Session Management**:
   - Discovered MCP protocol requires proper session lifecycle (initialize → list_tools → call_tool)
   - Session ID is required in all MCP requests
   - Testing showed it's best to use Claude Desktop which handles session management correctly

3. **Testing Approaches**:
   - Created curl and Python-based HTTP tests
   - Found direct HTTP testing challenging due to MCP protocol requirements
   - Determined Claude Desktop is the most reliable way to test the implementation

## Usage Instructions

### Claude Desktop Configuration

The correct configuration for Claude Desktop integration should be:

```json
{
  "mcpServers": {
    "jean-memory": {
      "serverType": "HTTP",
      "serverUrl": "http://localhost:8001",
      "headers": {
        "X-API-Key": "your-api-key",
        "X-User-ID": "1"
      }
    }
  }
}
```

### Preferred Claude Desktop Integration (via `stdio`)

Recent testing (May 2025) has shown that for custom MCP servers launched directly by Claude Desktop, using the `stdio` transport is more reliable and aligns with official MCP SDK documentation examples.

This involves:
1.  **Server-Side:** The Python MCP server script (e.g., `FastMCP` based) should be started using `mcp_instance.run(transport='stdio')` instead of being run as an HTTP/SSE server with Uvicorn.
2.  **Claude Desktop Configuration (`claude_desktop_config.json`):**
    *   The server entry should specify a `command` (e.g., `"python3"`) and `args` (containing the absolute path to the server script).
    *   Fields like `serverType` and `serverUrl` should be omitted for this configuration.
    *   Environment variables for the server can be passed using the `env` key within the server's configuration block in `claude_desktop_config.json`.

**Example `claude_desktop_config.json` for `stdio`:**
```json
{
  "mcpServers": {
    "jean-memory-stdio": {
      "command": "python3",
      "args": [
        "/ABSOLUTE/PATH/TO/jean-memory/backend/standalone_mcp_server.py"
      ],
      "env": {
        "JEAN_API_KEY": "your-test-key", // Or retrieved from a secure source
        "JEAN_USER_ID": "1"             // Or relevant user ID
        // Other necessary environment variables like DATABASE_URL, GEMINI_API_KEY
      }
    }
  }
}
```
This approach resolved previous issues where Claude Desktop was incorrectly expecting a `command` for HTTP server configurations and ensures that Claude Desktop can properly manage the lifecycle of the local MCP server process.

### Running the Standalone MCP Server

For testing and development, use the standalone MCP server:

```bash
python backend/standalone_mcp_server.py
```

This runs the MCP server on port 8001 without interfering with the main application.

### Environmental Variables

For complete functionality, ensure these environment variables are set:

- `DATABASE_URL`: Connection string for PostgreSQL database
- `GEMINI_API_KEY`: Google Gemini API key for context analysis
- `JEAN_API_BASE_URL`: Base URL for the deployed service

## Next Steps

1. **Enhanced Testing**:
   - Test with actual Claude Desktop deployment
   - Create comprehensive test suite for MCP functionality
   - Implement structured logging of MCP interactions

2. **Additional Data Sources**:
   - Extend beyond notes and GitHub (email, calendar, etc.)
   - Add more third-party integrations

3. **Documentation**:
   - Create detailed user documentation
   - Document the API for developers

4. **User Experience**:
   - Add more guidance on MCP usage patterns
   - Improve error handling and user feedback
   - Develop example prompts and workflows 