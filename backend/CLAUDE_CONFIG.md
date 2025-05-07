# Claude Desktop MCP Configuration

To set up Claude Desktop to use JEAN Memory as an MCP server, follow these steps:

## Setup

1. Start the JEAN Memory MCP server in stdio mode:
   ```bash
   cd backend
   python jean_mcp_server.py --mode stdio
   ```

   Or set environment variables directly:
   ```bash
   JEAN_USER_ID=1 JEAN_API_KEY=test-key DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres GEMINI_API_KEY=your_gemini_api_key python jean_mcp_server.py --mode stdio
   ```

2. Configure Claude Desktop with the following settings:

```json
{
  "mcpServers": {
    "jean-memory-stdio": {
      "command": "python3",
      "args": [
        "/path/to/jean-memory/backend/jean_mcp_server.py",
        "--mode", "stdio"
      ],
      "env": {
        "JEAN_USER_ID": "1", 
        "JEAN_API_KEY": "test-key",
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5433/postgres", 
        "GEMINI_API_KEY": "your_gemini_api_key"
      }
    }
  }
}
```

Replace `/path/to/jean-memory/` with your actual project path.

## Alternative HTTP Configuration

If you prefer using the HTTP server mode:

1. Start the HTTP server:
   ```bash
   python jean_mcp_server.py --mode http --port 8001
   ```

2. Configure Claude Desktop with HTTP settings:

```json
{
  "mcpServers": {
    "jean-memory": {
      "serverType": "HTTP",
      "serverUrl": "http://localhost:8001",
      "headers": {
        "X-API-Key": "test-key",
        "X-User-ID": "1"
      }
    }
  }
}
```

## Testing

1. Start a conversation with Claude in Claude Desktop
2. Verify the MCP connection by asking Claude to use one of the JEAN Memory tools:
   - "Create a memory entry about my preferences"
   - "Access my memory to find information about X"
   - "What do you remember about me?"

## Troubleshooting

If you encounter any issues:

1. Check that the JEAN Memory MCP server is running correctly
2. Verify that the database is properly initialized and accessible
3. Ensure all required environment variables are set (JEAN_USER_ID, JEAN_API_KEY, DATABASE_URL, GEMINI_API_KEY)
4. Look at the server logs for any error messages
5. If using stdio mode, make sure the file path in the configuration is correct

## Environment Variables

- `JEAN_USER_ID`: The user ID for memory storage/retrieval (e.g., "1")
- `JEAN_API_KEY`: The API key for authentication (e.g., "test-key")
- `DATABASE_URL`: PostgreSQL connection string
- `GEMINI_API_KEY`: Google Gemini API key for memory processing 