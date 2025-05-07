import asyncio
import json
import sys
import os
from unittest.mock import MagicMock, patch

# Add the current directory to the path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app.models import MCPRequest, MCPRetrieveParams
from routers.context_router import ContextRouter

# Mock for GeminiAPI
class MockGeminiAPI:
    async def determine_context_type(self, query: str) -> str:
        """Mock implementation that simulates classification based on keywords."""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ["github", "code", "repository"]):
            return "github"
        elif any(term in query_lower for term in ["notes", "write", "wrote"]):
            return "notes"
        elif any(term in query_lower for term in ["values", "prefer", "like"]):
            return "values"
        elif any(term in query_lower for term in ["meeting", "discussion", "conversation"]):
            return "conversations" 
        elif any(term in query_lower for term in ["task", "project", "deadline"]):
            return "tasks"
        elif any(term in query_lower for term in ["work", "professional", "career"]):
            return "work"
        elif any(term in query_lower for term in ["video", "watch", "podcast"]):
            return "media"
        elif any(term in query_lower for term in ["place", "travel", "restaurant"]):
            return "locations"
        else:
            return "notes"  # Default

    async def process(self, context_type: str, context_data: any, query: str) -> str:
        """Mock implementation that returns a simple response."""
        return f"Processed {context_type} context for query: {query}"

async def test_autonomous_routing():
    """Test the autonomous routing functionality with different query types using mocks."""
    
    print("Initializing mock Gemini API...")
    gemini_api = MockGeminiAPI()
    
    # Initialize context router with mock
    context_router = ContextRouter(db=None, gemini_api=gemini_api)
    
    # Test queries for different context types
    test_queries = [
        "What's in my GitHub repository about machine learning?",
        "What did I write in my notes about quantum physics?",
        "What are my personal values regarding environmental sustainability?",
        "What was discussed in my meeting with John last week?",
        "When is my deadline for the marketing project?",
        "What certifications do I need for my career advancement?",
        "Send me a link to that YouTube video about cooking pasta",
        "What restaurants did I like in Paris?",
    ]
    
    print("\n=== Testing Autonomous Context Type Classification (Mock) ===\n")
    
    # Test direct classification
    for query in test_queries:
        print(f"Query: {query}")
        
        # Test direct classification via mocked Gemini
        context_type = await gemini_api.determine_context_type(query)
        print(f"  Direct mock classification: {context_type}")
        
        # Test classification via router
        router_type = await context_router.determine_context_type(query)
        print(f"  Router classification: {router_type}")
        
        print()
    
    print("\n=== Testing Full Query Routing (Mock) ===\n")
    
    # Test full routing
    for query in test_queries[:4]:  # Just use a subset for brevity
        print(f"Query: {query}")
        
        # Auto-determine context type
        result = await context_router.route(user_id=999, query=query)
        print(f"  Auto-determined context type: {result['type']}")
        print(f"  Result content: {result['content']}")
        
        print()
    
    # Test explicit context type
    query = "Tell me about my recent work"
    print(f"Query with explicit context type: {query}")
    result = await context_router.route(user_id=999, query=query, context_type="notes")
    print(f"  Forced context type 'notes' result: {result['content']}")
    print()

async def test_mcp_structure():
    """Test the structure of an MCP request with explicit context type."""
    
    # Test an MCP request with explicit context type
    retrieve_request = MCPRequest(
        method="retrieve",
        params={
            "query": "What did I write about quantum computing?",
            "context_type": "notes"  # Explicitly providing context type
        }
    )
    
    # Parse into specific model
    retrieve_params = MCPRetrieveParams(**retrieve_request.params)
    
    print("\n=== Testing MCP Request Structure ===\n")
    print(f"Query: {retrieve_params.query}")
    print(f"Explicit context type: {retrieve_params.context_type}")
    
    # Show how this would look in an actual request
    print("\nExample MCP Request JSON:")
    print(json.dumps({
        "method": "retrieve",
        "params": {
            "query": "What did I write about quantum computing?",
            "context_type": "notes"
        }
    }, indent=2))
    
    print("\nExample MCP Request JSON with autonomous routing (no context_type):")
    print(json.dumps({
        "method": "retrieve",
        "params": {
            "query": "What did I write about quantum computing?"
        }
    }, indent=2))

if __name__ == "__main__":
    asyncio.run(test_autonomous_routing())
    asyncio.run(test_mcp_structure()) 