# JEAN Memory Backend

This directory contains the core backend logic for the JEAN Memory system.

## Overview

The backend implements the JEAN Memory service, acting as a Model Context Protocol (MCP) server. Its primary responsibilities include:

1. **Memory Storage:** Storing user memories, notes, and context information in a structured database.
2. **Memory Retrieval:** Using semantic search to find relevant memories based on user queries.
3. **MCP Implementation:** Providing tools for Claude to create and access memory entries through the Model Context Protocol.
4. **User Authentication:** Handling user authentication and associating data with specific users.
5. **Multi-tenant Support:** Isolating data between different users and organizations.

## Directory Structure

- `jean_mcp/`: Core MCP server implementation containing tools, resources, and server configuration.
- `app/`: Contains the main FastAPI application setup and API endpoints.
- `routers/`: API route handlers for different functionality areas.
- `services/`: Contains clients and wrappers for interacting with external services like the Gemini API.
- `database/`: Handles all database interactions, schema definition, and migrations.
- `tests/`: Unit and integration tests for the application.

## Running the Server

The backend can be run in several modes using the unified `jean_mcp_server.py` script:

### Claude Desktop Integration (stdio mode)

```bash
python jean_mcp_server.py --mode stdio
```

Environment variables:
- `JEAN_USER_ID`: Current user ID for memory storage/retrieval
- `JEAN_API_KEY`: API key for authentication
- `DATABASE_URL`: PostgreSQL connection string
- `GEMINI_API_KEY`: Google Gemini API key for memory processing

### HTTP API Server

```bash
python jean_mcp_server.py --mode http --port 8001
```

### Test/Minimal Server

```bash
python jean_mcp_server.py --mode minimal
```

## Key Technologies

- **Framework:** FastAPI
- **AI:** Google Generative AI (Gemini)
- **Database:** PostgreSQL
- **MCP Implementation:** Model Context Protocol
- **Language:** Python

## Next Steps

1. Complete the frontend integration with Obsidian and GitHub.
2. Deploy to Google Cloud Run following the deployment plan.
3. Implement robust authentication and user management.
4. Expand memory types and context sources. 