#!/usr/bin/env python3
"""
Simple HTTP test for the JEAN Memory MCP server.
"""

import httpx
import json
import asyncio
import uuid
import time

# Connection details
MCP_URL = "http://localhost:8001/messages/"  # Standalone MCP server with correct endpoint path
API_KEY = "test-key"
USER_ID = "1"

# Create headers
HEADERS = {
    "X-API-Key": API_KEY,
    "X-User-ID": USER_ID,
    "Content-Type": "application/json"
}

async def test_mcp():
    """Test the MCP server with direct HTTP requests."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Generate a unique session ID
        session_id = f"test-session-{int(time.time())}"
        print(f"Using session ID: {session_id}")
        
        # Test initialize method
        print("Testing initialize method...")
        initialize_payload = {
            "jsonrpc": "2.0",
            "id": "test1",
            "method": "initialize",
            "params": {
                "session_id": session_id
            }
        }
        
        response = await client.post(MCP_URL, json=initialize_payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        
        # Safely try to parse JSON response
        try:
            json_response = response.json()
            print(f"Response: {json.dumps(json_response, indent=2)}")
            
            # Check if initialization failed
            if json_response.get("error"):
                print(f"Error initializing session: {json_response.get('error')}")
                return
                
        except Exception as e:
            print(f"Not JSON: {response.text[:200]}...")
            return
        
        # Test list_tools method
        print("\nTesting list_tools method...")
        list_tools_payload = {
            "jsonrpc": "2.0",
            "id": "test2",
            "method": "list_tools",
            "params": {
                "session_id": session_id
            }
        }
        
        response = await client.post(MCP_URL, json=list_tools_payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        
        # Safely try to parse JSON response
        try:
            json_response = response.json()
            print(f"Response: {json.dumps(json_response, indent=2)}")
            
            # Check if we got tools
            if json_response.get("result") and json_response.get("result").get("tools"):
                tools = json_response.get("result").get("tools")
                print(f"Found {len(tools)} tools")
            
        except Exception as e:
            print(f"Not JSON: {response.text[:200]}...")
        
        # Test create_note tool
        print("\nTesting create_note tool...")
        create_note_payload = {
            "jsonrpc": "2.0",
            "id": "test3",
            "method": "call_tool",
            "params": {
                "session_id": session_id,
                "tool_name": "create_note",
                "tool_params": {
                    "content": "This is a test note created via HTTP request",
                    "tags": ["test", "http"]
                }
            }
        }
        
        response = await client.post(MCP_URL, json=create_note_payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        
        # Safely try to parse JSON response
        try:
            json_response = response.json()
            print(f"Response: {json.dumps(json_response, indent=2)}")
        except Exception as e:
            print(f"Not JSON: {response.text[:200]}...")
            
        # Search for notes
        print("\nTesting search_notes tool...")
        search_notes_payload = {
            "jsonrpc": "2.0",
            "id": "test4",
            "method": "call_tool",
            "params": {
                "session_id": session_id,
                "tool_name": "search_notes",
                "tool_params": {
                    "query": "test",
                    "limit": 5
                }
            }
        }
        
        response = await client.post(MCP_URL, json=search_notes_payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        
        # Safely try to parse JSON response
        try:
            json_response = response.json()
            print(f"Response: {json.dumps(json_response, indent=2)}")
        except Exception as e:
            print(f"Not JSON: {response.text[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_mcp()) 