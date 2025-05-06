#!/bin/bash
# Test the standalone MCP server using the MCP CLI tool

# Set up environment variables
export JEAN_USER_ID=1
export JEAN_API_KEY=test-key
export GEMINI_API_KEY=${GEMINI_API_KEY:-""}

# Start the server in the background
echo "Starting MCP server on port 8001..."
python3 backend/standalone_mcp_server.py 8001 > mcp_server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 3

# Use mcp dev command to test the server
echo "Testing server with MCP CLI..."
docker exec -it jean-memory-backend-1 mcp dev test \
  --host http://host.docker.internal:8001/messages/ \
  --headers X-API-Key:test-key,X-User-ID:1

# Kill the server
echo "Stopping server..."
kill $SERVER_PID

echo "Done!" 