"""
Test script for the MCP implementation.

This script tests the MCP server functionality to ensure it works correctly.
"""

import asyncio
import json
import httpx
import argparse
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MCP RPC request template
def create_mcp_request(method: str, params: Dict[str, Any], request_id: int = 1) -> Dict[str, Any]:
    """Create a JSON-RPC request for the MCP server."""
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": request_id
    }

# Test functions
async def test_call_tool(url: str, api_key: str, user_id: int, tool_name: str, arguments: Dict[str, Any]):
    """Test calling an MCP tool."""
    logger.info(f"Testing tool: {tool_name}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key,
                "X-User-ID": str(user_id)
            },
            json=create_mcp_request("call_tool", {
                "name": tool_name,
                "arguments": arguments
            })
        )
        
        if response.status_code != 200:
            logger.error(f"HTTP Error: {response.status_code}, {response.text}")
            return False
        
        try:
            result = response.json()
            
            if "error" in result:
                logger.error(f"MCP Error: {result['error']}")
                return False
            
            logger.info(f"Success: {tool_name}")
            logger.info(f"Result: {json.dumps(result['result'], indent=2)}")
            return True
        
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return False

async def test_list_tools(url: str, api_key: str, user_id: int):
    """Test listing available MCP tools."""
    logger.info("Testing list_tools")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key,
                "X-User-ID": str(user_id)
            },
            json=create_mcp_request("list_tools", {})
        )
        
        if response.status_code != 200:
            logger.error(f"HTTP Error: {response.status_code}, {response.text}")
            return False
        
        try:
            result = response.json()
            
            if "error" in result:
                logger.error(f"MCP Error: {result['error']}")
                return False
            
            tools = result["result"]
            logger.info(f"Available tools: {len(tools)}")
            for tool in tools:
                logger.info(f"  - {tool['name']}: {tool['description']}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return False

async def test_list_resources(url: str, api_key: str, user_id: int):
    """Test listing available MCP resources."""
    logger.info("Testing list_resources")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key,
                "X-User-ID": str(user_id)
            },
            json=create_mcp_request("list_resources", {})
        )
        
        if response.status_code != 200:
            logger.error(f"HTTP Error: {response.status_code}, {response.text}")
            return False
        
        try:
            result = response.json()
            
            if "error" in result:
                logger.error(f"MCP Error: {result['error']}")
                return False
            
            resources = result["result"]
            logger.info(f"Available resources: {len(resources)}")
            for resource in resources:
                logger.info(f"  - {resource['uri']}: {resource.get('description', 'No description')}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return False

async def test_read_resource(url: str, api_key: str, user_id: int, resource_uri: str):
    """Test reading an MCP resource."""
    logger.info(f"Testing read_resource: {resource_uri}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key,
                "X-User-ID": str(user_id)
            },
            json=create_mcp_request("read_resource", {
                "uri": resource_uri
            })
        )
        
        if response.status_code != 200:
            logger.error(f"HTTP Error: {response.status_code}, {response.text}")
            return False
        
        try:
            result = response.json()
            
            if "error" in result:
                logger.error(f"MCP Error: {result['error']}")
                return False
            
            logger.info(f"Successfully read resource: {resource_uri}")
            # Only show preview of content to avoid overwhelming logs
            content = result["result"]["content"]
            if isinstance(content, str):
                logger.info(f"Content preview: {content[:100]}...")
            else:
                logger.info(f"Content type: {type(content)}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return False

async def run_all_tests(url: str, api_key: str, user_id: int):
    """Run all MCP tests."""
    logger.info("Starting MCP test suite")
    
    # Test listing tools
    tools_success = await test_list_tools(url, api_key, user_id)
    
    # Test listing resources
    resources_success = await test_list_resources(url, api_key, user_id)
    
    # Test specific tools
    notes_success = await test_call_tool(
        url, api_key, user_id, 
        "get_recent_notes", 
        {"limit": 5}
    )
    
    github_success = await test_call_tool(
        url, api_key, user_id, 
        "get_repositories", 
        {"limit": 5}
    )
    
    config_success = await test_call_tool(
        url, api_key, user_id, 
        "get_mcp_config", 
        {}
    )
    
    # Test specific resources
    recent_notes_success = await test_read_resource(
        url, api_key, user_id,
        "notes://recent/5"
    )
    
    github_repos_success = await test_read_resource(
        url, api_key, user_id,
        "github://repositories"
    )
    
    mcp_config_success = await test_read_resource(
        url, api_key, user_id,
        "config://mcp"
    )
    
    # Summarize results
    total_tests = 8
    passed_tests = sum([
        tools_success, resources_success,
        notes_success, github_success, config_success,
        recent_notes_success, github_repos_success, mcp_config_success
    ])
    
    logger.info(f"Tests completed: {passed_tests}/{total_tests} passed")
    if passed_tests == total_tests:
        logger.info("✅ All tests passed! MCP implementation is working correctly.")
    else:
        logger.warning(f"❌ {total_tests - passed_tests} tests failed. Check the logs for details.")
    
    return passed_tests == total_tests

async def main():
    """Main function to run the test script."""
    parser = argparse.ArgumentParser(description="Test the MCP implementation")
    parser.add_argument("--url", default="http://localhost:8080/mcp", help="MCP server URL")
    parser.add_argument("--api-key", required=True, help="API key for authentication")
    parser.add_argument("--user-id", required=True, type=int, help="User ID for authentication")
    args = parser.parse_args()
    
    try:
        success = await run_all_tests(args.url, args.api_key, args.user_id)
        exit(0 if success else 1)
    except Exception as e:
        logger.exception(f"Test suite failed with error: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 