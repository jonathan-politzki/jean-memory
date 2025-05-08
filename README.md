# Jean Technologieswe are  - Personal Memory Layer for AI Assistants

> **Note**: Comprehensive documentation is now available in the [docs directory](docs/). Check [docs/README.md](docs/README.md) for a guide to all documentation.

Jean is a personal memory layer for AI assistants that implements the [Model Context Protocol (MCP)](https://www.anthropic.com/news/model-context-protocol).

## Current Status

### Frontend (Port 3005)
- Modern, AI-styled UI with responsive design
- Google OAuth integration for authentication
- Dashboard for displaying MCP configuration
- Placeholder UI for context source connections (GitHub, Twitter, Google Docs, Notion)
- Basic note creation interface

### Backend (Port 8080)
- FastAPI implementation with CORS support
- API key middleware for authentication
- Basic MCP endpoint (`/mcp`) implementing:
  - `retrieve` operation for fetching context
  - `store` operation for saving context
- Context router system for different types of data
- Ready for database integration (currently using placeholder data)

### Authentication Flow
- Google OAuth integration for sign-in
- Token exchange via frontend proxy
- API key generation for MCP configuration

## MCP Implementation

Our current MCP implementation follows the basic Model Context Protocol pattern but is more simplified than the full specification:

### Current Capabilities
- HTTP transport for MCP communication
- JSON-RPC based request/response format
- Support for `retrieve` and `store` methods
- Context type routing for different data sources
- API key validation

### Not Yet Implemented
- Tool registration system (like `@mcp.tool()` decorators)
- Resource handling for file-like data
- Prompt templates
- Multiple transport options (currently HTTP only)
- Full SDK compliance

## Roadmap

### Short-term Goals
1. **Database Integration**
   - Set up PostgreSQL for real data storage
   - Implement user accounts and API key management
   - Create schema for context storage

2. **Context Source Integration**
   - Complete GitHub integration for repository access
   - Implement note storage and retrieval functionality

3. **MCP Enhancement**
   - Expand MCP implementation to include tools
   - Add support for more advanced context retrieval

### Mid-term Goals
1. **Additional Context Sources**
   - Twitter/X integration
   - Google Docs integration
   - Notion integration

2. **Improved Context Processing**
   - Implement vector embeddings for better context retrieval
   - Add summarization capabilities for large context

3. **User Management**
   - User settings and preferences
   - Usage metrics and limitations

### Long-term Goals
1. **Enterprise Features**
   - Multi-user teams and sharing
   - Role-based access control
   - Audit logging

2. **Advanced MCP Features**
   - Custom prompt templates
   - Context history management
   - Cross-source context integration

## Getting Started

### Prerequisites
- Node.js 16+ for the frontend
- Python 3.10+ and [Poetry](https://python-poetry.org/) for the backend
- Docker and Docker Compose for running local database/services
- Google Cloud account for OAuth integration

### Running the Frontend
```bash
cd frontend
node server.js
```
Frontend will be available at http://localhost:3005

### Running the Backend (Local Development Server)

This runs the standard FastAPI backend, typically used for frontend interaction during development.

```bash
# Navigate to backend directory
cd backend
# Install dependencies if you haven't already
poetry install
# Run the development server
poetry run uvicorn app.main:app --reload --port 8000
```
Backend API will be available at http://localhost:8000

### Running the Backend (MCP Server for Claude Desktop)

This method runs the `jean_mcp_server.py` script directly, which is what the MCP client configuration often points to.

**Important:** Ensure you have installed dependencies locally using Poetry:
```bash
cd backend
poetry install
```

You can run the MCP server manually for testing using Poetry's virtual environment:
```bash
cd backend
# Example: Run in stdio mode
poetry run python jean_mcp_server.py --mode stdio
# Example: Run in http mode
poetry run python jean_mcp_server.py --mode http --port 8001
```

### Testing the MCP Endpoint
Once both frontend and backend are running:
1. Go to http://localhost:3005
2. Sign in with Google
3. View your MCP configuration on the dashboard
4. Test the MCP endpoint by using the configuration in an MCP-compatible client

## Integration with MCP Clients

To use JEAN with an MCP-compatible client (like Claude Desktop):

1.  **Ensure Local Dependencies:** Make sure you have run `poetry install` within the `backend` directory locally to create a virtual environment and install all necessary packages.
2.  **Find Python Path:** In the `backend` directory, run `poetry env info --path`. This will give you the path to the virtual environment (e.g., `/path/to/your/project/backend/.venv`). Construct the full path to the Python executable within this environment (e.g., `/path/to/your/project/backend/.venv/bin/python`).
3.  **Configure MCP Client:**
    *   Copy the MCP configuration template (see below or obtain from a running instance if the frontend provides it).
    *   **Crucially, set the `"command"` value in the configuration to the full Python path you found in step 2.**
    *   Set the necessary `env` variables in the configuration (DATABASE_URL pointing to local Docker Postgres `localhost:5433`, API keys, etc.).
4.  **Add Config to Client:** Add the modified configuration JSON to your MCP client's settings.
5.  **Restart Client:** Restart your MCP client (e.g., Claude Desktop). The client will now use the correct Python environment to run `jean_mcp_server.py` and should have access to your personal context via the tools.

**Example MCP Configuration Snippet (Modify `"command"` and `env`):**
```json
{
  "mcpServers": {
    "jean-memory-stdio": {
      "command": "/path/to/your/project/backend/.venv/bin/python", // <-- UPDATE THIS PATH
      "args": [
        "/path/to/your/project/backend/jean_mcp_server.py", // <-- Ensure this points to the script
        "--mode", "stdio"
      ],
      "env": {
        "JEAN_USER_ID": "1",
        "JEAN_API_KEY": "local-dev-key", // Use a suitable key for local dev
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5433/postgres", // Assumes Docker Compose DB
        "GEMINI_API_KEY": "YOUR_GEMINI_KEY_HERE"
      }
    }
  }
}
```

**Note on macOS SSL Issues:** If you encounter `SSL: CERTIFICATE_VERIFY_FAILED` errors when installing Poetry or Python packages, you may need to run the `Install Certificates.command` script located in your Python installation's Applications folder (e.g., `/Applications/Python 3.10/`).

## Docker Deployment (Future)

Docker deployment instructions will be added as the project matures.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Environment Variables

This application requires several environment variables to be set for proper operation:

### Required Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `GEMINI_API_KEY`: Google Gemini API key

### Google OAuth Environment Variables

For Google authentication to work, you need to set up the following:

- `GOOGLE_CLIENT_ID`: Your Google OAuth Client ID 
- `GOOGLE_CLIENT_SECRET`: Your Google OAuth Client Secret
- `GOOGLE_REDIRECT_URI`: Redirect URI (default: http://localhost:3005/auth/google/callback)

### Optional Environment Variables

- `JEAN_API_KEY`: API key for authentication (defaults to allowing any non-empty key in dev)
- `JEAN_USER_ID`: Default user ID (default: "1")
- `JEAN_TENANT_ID`: Default tenant ID (default: "default")
- `JEAN_API_BASE_URL`: Base URL for the API (default: http://localhost:8000)
- `MCP_LOG_LEVEL`: Logging level for MCP server (default: INFO)
- `MCP_LOG_TO_STDERR`: Whether to log to stderr (default: true)

## Setup Instructions

1.  Clone the repository.
2.  **Backend Setup:**
    *   Navigate to the `backend` directory: `cd backend`
    *   Install dependencies using Poetry: `poetry install`
3.  **Environment:** Create a `.env` file in the project root (or configure environment variables directly) with the required values (see "Environment Variables" section). Minimally, `DATABASE_URL` (for local tools) and `GEMINI_API_KEY` are needed. Google OAuth keys are needed for frontend login.
4.  **Run Services:** Start the local database and other services: `docker-compose up -d`
5.  **Configure MCP Client (Crucial for Tools):** Follow the steps in the "Integration with MCP Clients" section above to configure your client (e.g., Claude Desktop) to use the correct Python environment via the full path from `poetry env info --path`.
6.  **Optional: Run Frontend:** If needed, `cd frontend && node server.js`.
7.  **Optional: Run Backend API:** If needed, `cd backend && poetry run uvicorn app.main:app --reload --port 8000`.
