# JEAN Memory MCP Implementation

This package implements the Model Context Protocol (MCP) for the JEAN Memory system, allowing AI assistants like Claude to access user context, notes, GitHub activity, and other personal data.

## Features

- **Complete MCP Server**: Implementation using the official Anthropic MCP SDK
- **Authentication**: Secure access with API key validation
- **Multiple Context Types**: Notes, GitHub data, and more
- **Tools and Resources**: Both direct tool calls and resource URI access
- **Prompts**: Guide LLMs in effective interaction with the system
- **Value Extraction**: Gemini-powered analysis of user preferences
- **Claude Desktop Integration**: Easy configuration UI

## Architecture

The JEAN MCP implementation follows this structure:

```
jean_mcp/
├── server/
│   ├── mcp_server.py      # Core MCP server setup
│   ├── middleware.py      # Authentication middleware
│   └── mcp_config.py      # Claude Desktop configuration
├── tools/
│   ├── note_tools.py      # Note management tools
│   ├── github_tools.py    # GitHub integration
│   ├── auth_tools.py      # Authentication utilities
│   └── value_extraction_tools.py  # Gemini-powered analysis
├── resources/
│   └── prompts.py         # MCP prompts for LLMs
```

## Usage

### MCP Protocol

The Model Context Protocol (MCP) allows AI models like Claude to access external tools and data in a standardized way. Our implementation supports:

1. **JSON-RPC 2.0**: Standard protocol for remote procedure calls
2. **SSE Transport**: Server-Sent Events for stateful connections
3. **Tools and Resources**: Both direct tool calls and resource references

### Configuring Claude Desktop

To use JEAN Memory with Claude Desktop:

1. Visit `/mcp-config` in your browser
2. Enter your API key and user ID
3. Copy the generated configuration to Claude Desktop settings
4. Restart Claude Desktop

### Key Tools

- `create_note`: Create a new note with optional tags
- `search_notes`: Search for notes by content
- `get_recent_notes`: List most recent notes
- `get_github_repos`: List your GitHub repositories
- `get_github_activity`: Show recent GitHub activity
- `extract_user_values`: Analyze user values on a topic
- `summarize_user_preference_history`: Track preference evolution

## Development

### Requirements

- Python 3.10+
- MCP SDK (`pip install "mcp[cli]"`)
- Google Gemini API key (for value extraction)

### Running the Server

The MCP server is integrated into the main FastAPI application and runs automatically. For standalone testing:

```bash
python backend/run_mcp_server.py --api-key YOUR_API_KEY --user-id 1
```

### Testing

Use the MCP CLI for testing:

```bash
mcp dev --port 8080 --stdin
```

Also try using Claude Desktop with the `/mcp-config` generated settings.

### Environment Variables

- `GEMINI_API_KEY`: Required for value extraction tools
- `JEAN_API_BASE_URL`: Base URL for configuration generation
- `DATABASE_URL`: Required for database access 