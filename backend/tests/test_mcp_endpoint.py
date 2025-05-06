#!/usr/bin/env python3
"""
Test script for validating MCP endpoint conformance.

This script sends various MCP requests to test:
1. MCP retrieve operation
2. MCP store operation 
3. MCP standard compliance
4. Error handling
"""

import asyncio
import json
import sys
import os
import argparse
import aiohttp

# Parse arguments
parser = argparse.ArgumentParser(description='Test MCP endpoint compliance')
parser.add_argument('--url', type=str, default='http://localhost:8000/mcp', 
                    help='URL of the MCP endpoint to test')
parser.add_argument('--api-key', type=str, default='TEST_API_KEY',
                    help='API key to use for testing')
args = parser.parse_args()

# Standard MCP requests based on spec
RETRIEVE_REQUEST = {
    "method": "retrieve",
    "params": {
        "query": "What GitHub repositories am I working on?"
    }
}

RETRIEVE_WITH_CONTEXT_TYPE_REQUEST = {
    "method": "retrieve",
    "params": {
        "query": "What GitHub repositories am I working on?",
        "context_type": "github"
    }
}

STORE_REQUEST = {
    "method": "store",
    "params": {
        "context_type": "notes",
        "content": {
            "title": "Test Note",
            "body": "This is a test note for MCP compliance testing."
        },
        "source_identifier": "test-note-1"
    }
}

INVALID_METHOD_REQUEST = {
    "method": "invalid_method",
    "params": {
        "query": "This should return a method not found error"
    }
}

MALFORMED_REQUEST = {
    "invalid_key": "invalid_value"
}

async def test_mcp_endpoint():
    """Test the MCP endpoint for standard compliance."""
    print(f"Testing MCP endpoint at {args.url}")
    
    api_key = args.api_key
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Basic retrieve request
        print("\n=== Test 1: Standard Retrieve Request ===")
        async with session.post(args.url, json=RETRIEVE_REQUEST, headers=headers) as response:
            print(f"Status: {response.status}")
            result = await response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            success = "result" in result and result.get("result", {}).get("type")
            print(f"Test passed: {success}")
        
        # Test 2: Retrieve with explicit context type
        print("\n=== Test 2: Retrieve With Context Type ===")
        async with session.post(args.url, json=RETRIEVE_WITH_CONTEXT_TYPE_REQUEST, headers=headers) as response:
            print(f"Status: {response.status}")
            result = await response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            success = "result" in result and result.get("result", {}).get("type") == "github"
            print(f"Test passed: {success}")
        
        # Test 3: Store request
        print("\n=== Test 3: Store Request ===")
        async with session.post(args.url, json=STORE_REQUEST, headers=headers) as response:
            print(f"Status: {response.status}")
            result = await response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            success = "result" in result and result.get("result", {}).get("type") == "success"
            print(f"Test passed: {success}")
        
        # Test 4: Invalid method (should return method not found error)
        print("\n=== Test 4: Invalid Method Error Handling ===")
        async with session.post(args.url, json=INVALID_METHOD_REQUEST, headers=headers) as response:
            print(f"Status: {response.status}")
            result = await response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            success = "error" in result and "code" in result["error"]
            print(f"Test passed: {success}")
        
        # Test 5: Malformed request (should return parser error)
        print("\n=== Test 5: Malformed Request Error Handling ===")
        async with session.post(args.url, json=MALFORMED_REQUEST, headers=headers) as response:
            print(f"Status: {response.status}")
            try:
                result = await response.json()
                print(f"Response: {json.dumps(result, indent=2)}")
                success = "error" in result
            except:
                result = await response.text()
                print(f"Response: {result}")
                success = "error" in result.lower()
            print(f"Test passed: {success}")
        
        print("\n=== MCP Compliance Test Summary ===")
        print("These tests verify that the MCP endpoint correctly implements:")
        print("1. Standard retrieve operation")
        print("2. Retrieve with explicit context type (extension)")
        print("3. Standard store operation")
        print("4. Proper error handling for invalid methods")
        print("5. Proper error handling for malformed requests")

if __name__ == "__main__":
    asyncio.run(test_mcp_endpoint()) 