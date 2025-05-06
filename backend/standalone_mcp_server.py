#!/usr/bin/env python3
"""
Standalone MCP server for JEAN Memory, designed to be launched by Claude Desktop via stdio.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables from .env file, if present
# Claude Desktop can also pass environment variables via its config.
load_dotenv()

# Configure logging
# When run via stdio by Claude Desktop, stderr is usually captured in Claude's logs.
logging.basicConfig(
    level=os.getenv("MCP_LOG_LEVEL", "INFO").upper(), # Allow log level override via env
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr # Important for stdio transport with FastMCP
)
logger = logging.getLogger(__name__)

# Environment variables will be primarily managed by Claude Desktop's config
# but we can set fallbacks or ensure they are present if needed.
logger.info(f"JEAN_USER_ID from env: {os.getenv('JEAN_USER_ID')}")
logger.info(f"JEAN_API_KEY from env: {os.getenv('JEAN_API_KEY')}")
logger.info(f"GEMINI_API_KEY loaded: {'present' if os.getenv('GEMINI_API_KEY') else 'not present'}")
logger.info(f"DATABASE_URL loaded: {'present' if os.getenv('DATABASE_URL') else 'not present'}")


# Import the fully configured mcp_server instance 
# This mcp_server instance has all tools, resources, and lifespan events registered.
from jean_mcp.server.mcp_server import mcp_server as jean_memory_mcp

if __name__ == "__main__":
    logger.info("Starting JEAN Memory MCP server with STDIO transport...")
    try:
        # The jean_memory_mcp is the FastMCP instance from mcp_server.py
        # It already has the app_lifespan, tools, resources, and middleware configured.
        # The FastMCP.run() method handles the stdio transport internally.
        jean_memory_mcp.run(transport='stdio')
        logger.info("JEAN Memory MCP server with STDIO transport stopped.")
    except Exception as e:
        logger.exception("JEAN Memory MCP server crashed during stdio run")
        # Exiting with an error code might help Claude Desktop identify issues.
        sys.exit(1) 