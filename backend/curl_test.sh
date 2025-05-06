#!/bin/bash
# Simple curl-based test for the JEAN Memory MCP server

# Connection details
MCP_URL="http://localhost:8001/messages/"
API_KEY="test-key"
USER_ID="1"

# Generate a random session ID
SESSION_ID="test-session-$(date +%s)"
echo "Using session ID: $SESSION_ID"

# Initialize session
echo -e "\n\033[1;32mInitializing session...\033[0m"
INIT_PAYLOAD='{
  "jsonrpc": "2.0",
  "id": "test1",
  "method": "initialize",
  "params": {
    "session_id": "'"$SESSION_ID"'"
  }
}'
echo "Request: $INIT_PAYLOAD"

INIT_RESPONSE=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-User-ID: $USER_ID" \
  -d "$INIT_PAYLOAD")

echo "Response: $INIT_RESPONSE"

# List available tools
echo -e "\n\033[1;32mListing available tools...\033[0m"
TOOLS_PAYLOAD='{
  "jsonrpc": "2.0",
  "id": "test2",
  "method": "list_tools",
  "params": {
    "session_id": "'"$SESSION_ID"'"
  }
}'
echo "Request: $TOOLS_PAYLOAD"

TOOLS_RESPONSE=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-User-ID: $USER_ID" \
  -d "$TOOLS_PAYLOAD")

echo "Response: $TOOLS_RESPONSE"

# Create a test note
echo -e "\n\033[1;32mCreating a test note...\033[0m"
CREATE_PAYLOAD='{
  "jsonrpc": "2.0",
  "id": "test3",
  "method": "call_tool",
  "params": {
    "session_id": "'"$SESSION_ID"'",
    "tool_name": "create_note",
    "tool_params": {
      "content": "This is a test note created via curl",
      "tags": ["test", "curl"]
    }
  }
}'
echo "Request: $CREATE_PAYLOAD"

CREATE_RESPONSE=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-User-ID: $USER_ID" \
  -d "$CREATE_PAYLOAD")

echo "Response: $CREATE_RESPONSE"

# Search for notes
echo -e "\n\033[1;32mSearching for notes...\033[0m"
SEARCH_PAYLOAD='{
  "jsonrpc": "2.0",
  "id": "test4",
  "method": "call_tool",
  "params": {
    "session_id": "'"$SESSION_ID"'",
    "tool_name": "search_notes",
    "tool_params": {
      "query": "test",
      "limit": 5
    }
  }
}'
echo "Request: $SEARCH_PAYLOAD"

SEARCH_RESPONSE=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-User-ID: $USER_ID" \
  -d "$SEARCH_PAYLOAD")

echo "Response: $SEARCH_RESPONSE" 