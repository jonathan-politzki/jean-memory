#!/usr/bin/env python3
"""
Demonstration of JEAN's multi-tenant isolation patterns.

This script shows how JEAN implements tenant isolation without
requiring an actual database connection.
"""

import asyncio
from typing import Dict, Any, Optional, List

# Simulated database for demonstration
class MockDatabase:
    def __init__(self):
        self.data = {}  # { tenant_id: { user_id: { context_type: { source_id: content } } } }
        print("Mock database initialized")
    
    async def store_context(self, user_id: int, tenant_id: str, context_type: str, 
                           content: Dict[str, Any], source_identifier: Optional[str] = None) -> bool:
        """Store context data with tenant isolation."""
        # Create nested structure if it doesn't exist
        if tenant_id not in self.data:
            self.data[tenant_id] = {}
        
        if user_id not in self.data[tenant_id]:
            self.data[tenant_id][user_id] = {}
            
        if context_type not in self.data[tenant_id][user_id]:
            self.data[tenant_id][user_id][context_type] = {}
        
        # Store the data
        source_identifier = source_identifier or "default"
        self.data[tenant_id][user_id][context_type][source_identifier] = content
        
        print(f"Stored context for tenant={tenant_id}, user={user_id}, type={context_type}")
        return True
    
    async def get_context(self, user_id: int, tenant_id: str, context_type: str, 
                         source_identifier: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve context data with tenant isolation."""
        # Check if data exists
        if (tenant_id not in self.data or 
            user_id not in self.data[tenant_id] or 
            context_type not in self.data[tenant_id][user_id]):
            print(f"No data found for tenant={tenant_id}, user={user_id}, type={context_type}")
            return []
        
        # Get specific source or all sources
        result = []
        user_contexts = self.data[tenant_id][user_id][context_type]
        
        if source_identifier:
            if source_identifier in user_contexts:
                content = user_contexts[source_identifier]
                result.append({
                    "context_type": context_type,
                    "source_identifier": source_identifier,
                    "content": content,
                    "timestamp": "2023-08-01T12:00:00Z"  # Placeholder timestamp
                })
        else:
            # Return all sources for this context type
            for source_id, content in user_contexts.items():
                result.append({
                    "context_type": context_type,
                    "source_identifier": source_id,
                    "content": content,
                    "timestamp": "2023-08-01T12:00:00Z"  # Placeholder timestamp
                })
        
        print(f"Retrieved {len(result)} items for tenant={tenant_id}, user={user_id}, type={context_type}")
        return result

# Simplified router to demonstrate tenant isolation
class Router:
    def __init__(self, db: MockDatabase):
        self.db = db
        print("Router initialized")
    
    async def route(self, user_id: int, tenant_id: str, query: str, context_type: str) -> Dict[str, Any]:
        """
        Route a query to get context with tenant isolation.
        
        Args:
            user_id: User ID requesting context
            tenant_id: Tenant/organization ID for isolation
            query: The query text
            context_type: The type of context to retrieve
            
        Returns:
            Dict with context response
        """
        print(f"Routing query for tenant={tenant_id}, user={user_id}, type={context_type}")
        
        # Get context from database
        context_items = await self.db.get_context(
            user_id=user_id,
            tenant_id=tenant_id,
            context_type=context_type
        )
        
        if not context_items:
            return {"type": context_type, "content": "No context available"}
        
        # Process the context (simplified)
        combined_content = "\n\n".join([
            f"Item {i+1}: {item['content']}" for i, item in enumerate(context_items)
        ])
        
        return {
            "type": context_type,
            "content": f"Context for '{query}': {combined_content}"
        }

async def run_demo():
    """Run the multi-tenant demonstration."""
    print("=== JEAN Multi-Tenant Routing Demonstration ===\n")
    
    # Set up mock database
    db = MockDatabase()
    
    # Set up router
    router = Router(db)
    
    # Create test data for multiple tenants and users
    print("\n=== Storing Test Data ===")
    
    # Tenant 1, User 1
    await db.store_context(
        user_id=101,
        tenant_id="tenant1",
        context_type="github",
        content={"repos": ["tenant1-repo1", "tenant1-repo2"]},
        source_identifier="github_main"
    )
    
    # Tenant 1, User 2
    await db.store_context(
        user_id=102,
        tenant_id="tenant1",
        context_type="github",
        content={"repos": ["tenant1-user2-repo"]},
        source_identifier="github_main"
    )
    
    # Tenant 2, User 1
    await db.store_context(
        user_id=201,
        tenant_id="tenant2",
        context_type="github",
        content={"repos": ["tenant2-repo1", "tenant2-repo2"]},
        source_identifier="github_main"
    )
    
    # Test data for notes
    await db.store_context(
        user_id=101,
        tenant_id="tenant1",
        context_type="notes",
        content={"notes": ["Tenant 1 note content"]},
        source_identifier="notes_main"
    )
    
    await db.store_context(
        user_id=201,
        tenant_id="tenant2",
        context_type="notes",
        content={"notes": ["Tenant 2 note content"]},
        source_identifier="notes_main"
    )
    
    # Demonstrate tenant isolation
    print("\n=== Testing Tenant Isolation ===")
    
    # Correct access: Tenant 1, User 1
    result1 = await router.route(
        user_id=101,
        tenant_id="tenant1",
        query="Show me my repos",
        context_type="github"
    )
    print("\nTenant 1, User 1 accessing their data:")
    print(result1["content"])
    
    # Correct access: Tenant 2, User 1
    result2 = await router.route(
        user_id=201,
        tenant_id="tenant2",
        query="Show me my repos",
        context_type="github"
    )
    print("\nTenant 2, User 1 accessing their data:")
    print(result2["content"])
    
    # Incorrect tenant: User from Tenant 1 trying to access with Tenant 2
    result3 = await router.route(
        user_id=101,  # Tenant 1 user
        tenant_id="tenant2",  # But with Tenant 2
        query="Show me my repos",
        context_type="github"
    )
    print("\nTenant 1 User trying to access with Tenant 2 credentials:")
    print(result3["content"])
    
    print("\n=== Demonstration Complete ===")
    print("This demonstrates how JEAN enforces tenant isolation in the routing layer.")
    print("Each tenant's data is completely separated, preventing cross-tenant data access.")

if __name__ == "__main__":
    asyncio.run(run_demo()) 