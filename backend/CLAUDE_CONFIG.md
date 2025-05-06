# Claude Desktop MCP Configuration

To set up Claude Desktop to use JEAN Memory as an MCP server, follow these steps:

## Setup

1. Start the standalone MCP server on port 8001:
   ```bash
   cd backend
   python standalone_mcp_server.py
   ```

2. Configure Claude Desktop with the following settings:

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
   - "Create a note with the content 'This is a test note'"
   - "Search for notes with the keyword 'test'"
   - "Show me my recent GitHub activity"
   - "Extract my values related to programming"

## Troubleshooting

If you encounter any issues:

1. Check that the standalone MCP server is running on port 8001
2. Verify that the database is properly initialized
3. Check that you've set the GEMINI_API_KEY environment variable if you want to use value extraction
4. Look at the server logs for any error messages

## API Key Setup

For production use, you should generate a proper API key and assign it to a real user account. For testing purposes, the standalone server accepts any API key and maps it to user ID 1. 