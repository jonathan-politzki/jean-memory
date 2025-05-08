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
- Python 3.10+ for the backend
- Google Cloud account for OAuth integration

### Running the Frontend
```bash
cd frontend
node server.js
```
Frontend will be available at http://localhost:3005

### Running the Backend
```bash
cd backend
python3 -m uvicorn app.main:app --reload --port 8080
```
Backend API will be available at http://localhost:8080

### Testing the MCP Endpoint
Once both frontend and backend are running:
1. Go to http://localhost:3005
2. Sign in with Google
3. View your MCP configuration on the dashboard
4. Test the MCP endpoint by using the configuration in an MCP-compatible client

## Integration with MCP Clients

To use JEAN with an MCP-compatible client (like Claude Desktop):

1. Copy the MCP configuration from your dashboard
2. Add it to your MCP client's settings
3. The client will now have access to your personal context

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

1. Create a `.env` file in the project root with the required environment variables.
2. Run the application using Docker Compose: `docker-compose up`
