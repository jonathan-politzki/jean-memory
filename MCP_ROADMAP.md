# MCP Implementation Roadmap

Based on the [Model Context Protocol documentation](https://docs.anthropic.com/mcp/), this roadmap outlines the steps needed to enhance our current basic MCP implementation to a fully-compliant MCP server with advanced features.

## Current Implementation Status

Our server currently implements a subset of the MCP specification:

- ✅ Basic `/mcp` HTTP endpoint 
- ✅ JSON-RPC based request/response format
- ✅ Support for `retrieve` and `store` methods
- ✅ Context type routing for different data sources
- ✅ API key authentication
- ✅ Cross-origin resource sharing (CORS) support

## Phase 1: Core MCP Server Compliance

1. **Install MCP SDK**
   - Install the Python MCP SDK: `pip install "mcp[cli]"`
   - Restructure code to use the SDK classes and decorators

2. **Refactor Current MCP Endpoint**
   - Replace custom implementation with SDK-based FastMCP server
   - Implement proper error handling and response formatting
   - Example:
     ```python
     from mcp.server.fastmcp import FastMCP
     
     # Initialize FastMCP server
     mcp = FastMCP("jean-memory")
     ```

3. **Convert Existing Functions to MCP Tools**
   - Adapt the retrieve/store operations using the `@mcp.tool()` decorator
   - Example:
     ```python
     @mcp.tool()
     async def get_notes(query: str) -> str:
         """Get user notes based on a query.
         
         Args:
             query: The search query to find relevant notes
         """
         # Implementation here
         return formatted_notes
     ```

4. **Implement Multiple Transport Options**
   - Add support for stdio transport alongside HTTP
   - Configure transport options in server startup
   - Example:
     ```python
     if __name__ == "__main__":
         # Initialize and run the server with selected transport
         mcp.run(transport=transport_option)  # 'stdio' or 'http'
     ```

## Phase 2: Advanced MCP Features

1. **Resource Implementation**
   - Add support for file-like resources that can be read by clients
   - Implement caching and efficient data delivery
   - Example:
     ```python
     @mcp.resource("user_documents")
     async def get_user_documents(user_id: str):
         """Retrieve documents belonging to a user."""
         # Implementation here
         return documents
     ```

2. **Prompt Templates**
   - Create pre-written templates for common tasks
   - Implement prompt registration system
   - Example:
     ```python
     @mcp.prompt("github_summary")
     def github_summary():
         """Create a summary of GitHub activity."""
         return """
         Please summarize my recent GitHub activity including:
         1. Recent commits
         2. Open pull requests
         3. Issues assigned to me
         ... additional prompt details ...
         """
     ```

3. **Context Management**
   - Implement proper context session management
   - Add support for context history and state
   - Handle context limits and truncation strategies

## Phase 3: Integration with Claude Desktop and Other Clients

1. **Claude Desktop Configuration**
   - Create configuration file for Claude Desktop
   - Example:
     ```json
     {
         "mcpServers": {
             "jean-memory": {
                 "command": "python3",
                 "args": [
                     "-m",
                     "uvicorn",
                     "app.main:app",
                     "--port",
                     "8080"
                 ]
             }
         }
     }
     ```

2. **Tool Registration and Discovery**
   - Ensure tools are properly registered and discoverable
   - Implement proper tool metadata and documentation
   - Test with Claude Desktop tool discovery

3. **Testing and Debugging**
   - Implement the MCP Inspector for debugging
   - Create test suite for all MCP functionality
   - End-to-end testing with actual MCP clients

## Phase 4: Enhanced Context Features

1. **Context Source Integration**
   - Implement GitHub tools for repository access
   - Add Twitter/X content retrieval
   - Integrate with Google Docs and other sources

2. **Improved Context Retrieval**
   - Implement vector embeddings for semantic search
   - Add support for context ranking and filtering
   - Integrate with large language models for context processing

3. **Context Composition**
   - Develop tools for combining multiple context sources
   - Implement context summarization tools
   - Create context visualization utilities

## Implementation Notes

### MCP Server Structure Comparison

| Feature | Documentation Example | Our Current Implementation | Planned Implementation |
|---------|----------------------|---------------------------|------------------------|
| Server Base | `FastMCP` | Custom FastAPI | `FastMCP` from SDK |
| Tool Definition | `@mcp.tool()` decorator | Manual route handling | `@mcp.tool()` decorator |
| Error Handling | SDK-provided | Custom JSON-RPC | SDK-provided |
| Transport | stdio and HTTP | HTTP only | stdio and HTTP |
| Resources | `@mcp.resource()` | Not implemented | `@mcp.resource()` |
| Prompts | `@mcp.prompt()` | Not implemented | `@mcp.prompt()` |

### Integration Testing

To test the MCP server with Claude Desktop:

1. Make sure the server is running
2. Configure Claude Desktop's `claude_desktop_config.json`:
   ```json
   {
       "mcpServers": {
           "jean-memory": {
               "command": "python3",
               "args": [
                   "-m",
                   "uvicorn",
                   "app.main:app",
                   "--port",
                   "8080"
               ]
           }
       }
   }
   ```
3. Restart Claude Desktop
4. Check if the tool icon appears
5. Test with queries that should trigger your tools

For other MCP clients, refer to their specific configuration requirements.

### Dependencies

- Python 3.10+
- MCP SDK: `pip install "mcp[cli]"`
- FastAPI: `pip install fastapi uvicorn`
- Additional libraries as needed for specific integrations

### Testing and Debugging

- Use the MCP Inspector for debugging tool executions
- Follow logging best practices to trace request flow
- Create unit tests for each tool and integration test for the entire server 