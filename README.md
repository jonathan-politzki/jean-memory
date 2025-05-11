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

**Note on `DATABASE_URL` for Local Development:** When running the MCP server locally for clients like Claude Desktop, it's crucial that the server uses the `DATABASE_URL` for your local PostgreSQL instance (e.g., `postgresql://postgres:postgres@localhost:5433/postgres` if using the provided Docker Compose setup).
The MCP client configuration's `env` block (shown above) is the primary place to set this. However, if the server still fails to connect to the local database (e.g., with errors mentioning a Cloud SQL path or incorrect credentials), your local shell environment might have a conflicting `DATABASE_URL` set.
In such cases, you can explicitly set it when running the server:
`cd backend && DATABASE_URL="postgresql://postgres:postgres@localhost:5433/postgres" poetry run python jean_mcp_server.py --mode stdio`
This ensures the correct local database URL is used, overriding any conflicting environment variables.

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

### Running in Production

For production deployment, use Docker Compose with the production configuration:

```bash
# First, create a .env file with your production settings
# (See scripts/production-env-example.env for required variables)

# Then run the full stack in production mode
docker-compose up -d

# To view logs
docker-compose logs -f

# To stop all services
docker-compose down
```

Before running in production, ensure you've configured:
1. Real OAuth credentials for Google/GitHub
2. Production API keys for Gemini/Claude 
3. Proper database credentials
4. SSL/TLS if deploying publicly

The docker-compose.yml is configured to run in production mode with DEV_MODE=false, which disables mock authentication and test fallbacks.
