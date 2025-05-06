#!/usr/bin/env python3
"""
Example MCP Client - Simulates how an AI model like Claude would use JEAN via MCP
"""

import json
import asyncio
import argparse
import sys
import os
import requests
from typing import Dict, Any, Optional

# Parse arguments
parser = argparse.ArgumentParser(description='Example MCP client for JEAN')
parser.add_argument('--query', type=str, default="What did I write in my notes about quantum computing?", 
                    help='Query to send to JEAN')
parser.add_argument('--context_type', type=str, default=None, 
                    help='Optional explicit context type (github, notes, values, conversations, tasks, work, media, locations)')
parser.add_argument('--url', type=str, default="http://localhost:8000/mcp", 
                    help='URL of the JEAN MCP endpoint')
parser.add_argument('--api_key', type=str, default="TEST_API_KEY", 
                    help='API key for authentication')
args = parser.parse_args()

def call_mcp(query: str, context_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Call the JEAN MCP endpoint with a query.
    
    Args:
        query: The query to send
        context_type: Optional explicit context type
        
    Returns:
        The MCP response
    """
    # Prepare the MCP request
    params = {"query": query}
    if context_type:
        params["context_type"] = context_type
        
    mcp_request = {
        "method": "retrieve",
        "params": params
    }
    
    # Print the request
    print("\n=== MCP Request ===")
    print(json.dumps(mcp_request, indent=2))
    
    # Send the request
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {args.api_key}"
    }
    
    try:
        response = requests.post(args.url, json=mcp_request, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return {"error": f"HTTP Error: {response.status_code}"}
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

def simulate_ai_assistant():
    """Simulate an AI assistant using JEAN via MCP."""
    # Print a banner
    print("\n" + "=" * 50)
    print("JEAN MCP Client Example - Simulating an AI Assistant")
    print("=" * 50)
    
    # Get the user query from arguments
    query = args.query
    context_type = args.context_type
    
    print(f"\nUser Query: {query}")
    
    # Mode description
    if context_type:
        print(f"Mode: Explicit context_type '{context_type}'")
    else:
        print("Mode: Autonomous routing (Gemini will classify the query)")
    
    # Call the MCP endpoint
    response = call_mcp(query, context_type)
    
    # Print the response
    print("\n=== MCP Response ===")
    print(json.dumps(response, indent=2))
    
    # Simulate AI model using the context
    if "result" in response and response["result"]:
        result = response["result"]
        context_type = result.get("type")
        content = result.get("content")
        
        print("\n=== AI Assistant Processing ===")
        print(f"Context type: {context_type}")
        print(f"Using context: {content}")
        
        # Simulate the assistant's response
        print("\n=== AI Assistant Response to User ===")
        print(f"Based on your {context_type} information, I found this: {content}")
    else:
        print("\n=== AI Assistant Response to User ===")
        print("I couldn't find any relevant information to answer your question.")

if __name__ == "__main__":
    simulate_ai_assistant() 