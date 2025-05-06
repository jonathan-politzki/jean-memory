"""
Script to run the MCP server independently for testing and development.

Usage:
    python run_mcp_server.py --api-key YOUR_API_KEY --user-id YOUR_USER_ID

This starts the MCP server on port 8001 for direct testing.
"""

import asyncio
import logging
import argparse
import os
import sys
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Run the MCP server for testing and development."""
    parser = argparse.ArgumentParser(description="Run MCP server for testing")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--user-id", type=int, help="User ID for authentication")
    parser.add_argument("--tenant-id", default="default", help="Tenant ID for authentication")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the server on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    args = parser.parse_args()

    # Set environment variables for authentication if provided
    if args.api_key:
        os.environ["JEAN_API_KEY"] = args.api_key
        logger.info(f"Using API key from command line: {args.api_key[:4]}...")
    
    if args.user_id:
        os.environ["JEAN_USER_ID"] = str(args.user_id)
        logger.info(f"Using user ID from command line: {args.user_id}")
    
    if args.tenant_id:
        os.environ["JEAN_TENANT_ID"] = args.tenant_id
        logger.info(f"Using tenant ID from command line: {args.tenant_id}")

    # Run the MCP server using uvicorn
    logger.info(f"Starting MCP server on {args.host}:{args.port}")
    uvicorn.run(
        "jean_mcp.server.mcp_server:mcp.sse_app()",
        host=args.host,
        port=args.port,
        reload=True
    )

if __name__ == "__main__":
    main() 