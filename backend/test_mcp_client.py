#!/usr/bin/env python3
"""
Simple test client for the JEAN Memory MCP server.

This script connects to the MCP server and tests basic functionality.
"""

import sys
import asyncio
import json
from mcp.client.session import HTTPClient
from rich import print

# Connection details
MCP_URL = "http://localhost:8000/mcp"
API_KEY = "test-key"
USER_ID = "1"

async def test_mcp_server():
    """Test basic MCP server functionality."""
    print(f"[bold green]Connecting to MCP server at {MCP_URL}...[/bold green]")
    
    # Create MCP client with headers for authentication
    headers = {
        "X-API-Key": API_KEY,
        "X-User-ID": USER_ID
    }
    
    try:
        client = HTTPClient(MCP_URL, headers=headers)
        
        # Initialize client
        print("[yellow]Initializing MCP session...[/yellow]")
        response = await client.initialize()
        print(f"[green]Initialization response: {json.dumps(response, indent=2)}[/green]")
        
        # List available tools
        print("[yellow]Listing available tools...[/yellow]")
        tools = await client.list_tools()
        print(f"[green]Tools: {json.dumps(tools, indent=2)}[/green]")
        
        # Try to create a test note
        print("[yellow]Creating a test note...[/yellow]")
        create_note_response = await client.call_tool("create_note", {
            "content": "This is a test note created by the MCP client",
            "tags": ["test", "mcp"]
        })
        print(f"[green]Create note response: {json.dumps(create_note_response, indent=2)}[/green]")
        
        # Search for notes
        print("[yellow]Searching for notes...[/yellow]")
        search_response = await client.call_tool("search_notes", {
            "query": "test",
            "limit": 5
        })
        print(f"[green]Search response: {json.dumps(search_response, indent=2)}[/green]")
        
        # Try to get GitHub repos
        print("[yellow]Getting GitHub repositories...[/yellow]")
        github_response = await client.call_tool("get_github_repos", {
            "limit": 3
        })
        print(f"[green]GitHub repos response: {json.dumps(github_response, indent=2)}[/green]")
        
        # Try to extract user values (may fail if Gemini API key not configured)
        print("[yellow]Extracting user values...[/yellow]")
        values_response = await client.call_tool("extract_user_values", {
            "topic": "programming",
            "context_limit": 5
        })
        print(f"[green]Values extraction response: {json.dumps(values_response, indent=2)}[/green]")
        
        print("[bold green]All tests completed![/bold green]")
    
    except Exception as e:
        print(f"[bold red]Error: {str(e)}[/bold red]")
    finally:
        # Clean up
        if 'client' in locals():
            await client.close()

if __name__ == "__main__":
    asyncio.run(test_mcp_server()) 