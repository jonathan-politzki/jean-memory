#!/usr/bin/env python3
"""
Unified MCP server for JEAN Memory.

This script provides a unified interface to run the JEAN Memory MCP server
in different modes:
- stdio: For Claude Desktop integration via stdio
- http: For HTTP API access
- minimal: A minimal echo server for testing

Usage:
    python jean_mcp_server.py --mode stdio
    python jean_mcp_server.py --mode http --port 8001
    python jean_mcp_server.py --mode minimal --user-id 1 --api-key YOUR_KEY
"""

import os
import sys
import logging
import argparse
import uvicorn
from dotenv import load_dotenv

# Load environment variables before other imports
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("MCP_LOG_LEVEL", "INFO").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr if os.getenv("MCP_LOG_TO_STDERR", "true").lower() == "true" else sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_stdio_server():
    """Run the MCP server with stdio transport for Claude Desktop integration."""
    # Import the fully configured mcp_server instance 
    from jean_mcp.server.mcp_server import mcp_server as jean_memory_mcp

    logger.info("Starting JEAN Memory MCP server with STDIO transport...")
    try:
        # The jean_memory_mcp is the FastMCP instance from mcp_server.py
        # It already has the app_lifespan, tools, resources, and middleware configured.
        jean_memory_mcp.run(transport='stdio')
        logger.info("JEAN Memory MCP server with STDIO transport stopped.")
    except Exception as e:
        logger.exception("JEAN Memory MCP server crashed during stdio run")
        sys.exit(1)

def run_minimal_server():
    """Run a minimal MCP server with stdio transport for testing."""
    try:
        from mcp.server.fastmcp import FastMCP, Context
    except ImportError:
        logger.error("Could not import FastMCP. Make sure mcp package is installed.")
        sys.exit(1)

    # Initialize minimal FastMCP server
    mcp_minimal = FastMCP(
        "Minimal Echo Server",
        version="0.0.2",
        description="A very simple MCP server for testing."
    )

    @mcp_minimal.tool()
    async def echo(text_to_echo: str, ctx: Context = None) -> str:
        """Echoes back the provided text."""
        logger.info(f"Echo tool called with: {text_to_echo}")
        return text_to_echo

    logger.info("Starting MINIMAL MCP server with STDIO transport")
    mcp_minimal.run(transport='stdio')

def run_http_server(host="0.0.0.0", port=8001):
    """Run the MCP server with HTTP transport."""
    # Make sure environment variables are set before running
    api_key = os.getenv("JEAN_API_KEY")
    user_id = os.getenv("JEAN_USER_ID")
    tenant_id = os.getenv("JEAN_TENANT_ID", "default")
    
    if not api_key:
        logger.warning("JEAN_API_KEY environment variable not set.")
    if not user_id:
        logger.warning("JEAN_USER_ID environment variable not set.")
    
    logger.info(f"Starting MCP server on {host}:{port}")
    logger.info(f"Using tenant ID: {tenant_id}")
    
    # Run the MCP server using uvicorn
    uvicorn.run(
        "jean_mcp.server.mcp_server:mcp.sse_app()",
        host=host,
        port=port,
        reload=True
    )

def main():
    """Parse arguments and run the appropriate server mode."""
    parser = argparse.ArgumentParser(description="Unified JEAN Memory MCP Server")
    parser.add_argument("--mode", choices=["stdio", "http", "minimal"], default="stdio",
                       help="Server mode: stdio for Claude Desktop, http for API access, minimal for testing")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--user-id", help="User ID for authentication")
    parser.add_argument("--tenant-id", default="default", help="Tenant ID for authentication")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the HTTP server on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the HTTP server to")
    args = parser.parse_args()

    # Set environment variables for authentication if provided
    if args.api_key:
        os.environ["JEAN_API_KEY"] = args.api_key
        logger.info(f"Using API key from command line: {args.api_key[:4]}...")
    
    if args.user_id:
        os.environ["JEAN_USER_ID"] = args.user_id
        logger.info(f"Using user ID from command line: {args.user_id}")
    
    if args.tenant_id:
        os.environ["JEAN_TENANT_ID"] = args.tenant_id
        logger.info(f"Using tenant ID from command line: {args.tenant_id}")

    # Run the appropriate server mode
    if args.mode == "stdio":
        run_stdio_server()
    elif args.mode == "minimal":
        run_minimal_server()
    elif args.mode == "http":
        run_http_server(args.host, args.port)
    else:
        logger.error(f"Unknown mode: {args.mode}")
        sys.exit(1)

if __name__ == "__main__":
    main() 