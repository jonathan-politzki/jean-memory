#!/usr/bin/env python3
"""
Test script for validating CORS is properly configured.
This script tests that the backend allows cross-origin requests from the frontend.
"""

import asyncio
import argparse
import aiohttp
import json

# Parse arguments
parser = argparse.ArgumentParser(description='Test CORS configuration')
parser.add_argument('--backend-url', type=str, default='http://localhost:8080', 
                    help='URL of the backend server')
parser.add_argument('--frontend-url', type=str, default='http://localhost:3003',
                    help='URL of the frontend server (origin)')
args = parser.parse_args()

async def test_cors():
    """Test CORS configuration between frontend and backend."""
    print(f"Testing CORS from {args.frontend_url} to {args.backend_url}")
    
    # Endpoints to test
    endpoints = [
        '/health',  # Health endpoint
        '/mcp',     # The MCP endpoint
        '/cors-test'  # Dedicated CORS test endpoint
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            url = f"{args.backend_url}{endpoint}"
            
            # Set Origin header to simulate cross-origin request
            headers = {
                "Origin": args.frontend_url
            }
            
            print(f"\n=== Testing CORS for {url} ===")
            
            # First, perform OPTIONS request (preflight)
            try:
                async with session.options(url, headers=headers) as response:
                    print(f"OPTIONS Status: {response.status}")
                    print(f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
                    print(f"Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods')}")
                    print(f"Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Headers')}")
                    
                    cors_enabled = response.headers.get('Access-Control-Allow-Origin') is not None
                    print(f"CORS enabled: {cors_enabled}")
            except Exception as e:
                print(f"OPTIONS request failed: {e}")
            
            # Then perform actual GET request
            try:
                async with session.get(url, headers=headers) as response:
                    print(f"GET Status: {response.status}")
                    print(f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
                    
                    cors_enabled = response.headers.get('Access-Control-Allow-Origin') is not None
                    print(f"CORS enabled: {cors_enabled}")
            except Exception as e:
                print(f"GET request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_cors()) 