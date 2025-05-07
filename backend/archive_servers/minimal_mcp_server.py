from mcp.server.fastmcp import FastMCP, Context
import logging

# Configure basic logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp_minimal = FastMCP(
    "Minimal Echo Server Stdio", # Renamed for clarity
    version="0.0.2",
    description="A very simple MCP server for testing Claude Desktop (stdio)."
)

@mcp_minimal.tool()
async def echo(text_to_echo: str, ctx: Context = None) -> str:
    """Echoes back the provided text.
    
    Args:
        text_to_echo: The text to be echoed back.
        ctx: MCP Context (not used in this simple tool)
    
    Returns:
        The same text that was provided.
    """
    logger.info(f"Echo tool called with: {text_to_echo}")
    return text_to_echo

if __name__ == "__main__":
    logger.info(f"Starting MINIMAL MCP server with STDIO transport")
    # Run the server with stdio transport, as per documentation for Claude Desktop launched servers
    mcp_minimal.run(transport='stdio')
