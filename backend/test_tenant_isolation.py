#!/usr/bin/env python3
"""
Test script for JEAN's multi-tenant isolation.

This script tests the tenant isolation functionality by:
1. Creating users in multiple tenants
2. Storing context data for each tenant
3. Verifying data isolation between tenants
4. Testing cross-tenant requests
"""

import asyncio
import json
import sys
import os
import uuid
from typing import Dict, Any, Tuple

# Add the current directory to the path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from database.context_storage import ContextDatabase

async def setup_test_database():
    """Create a test database and return the connection."""
    # Use localhost for testing outside of Docker
    database_url = "postgresql://jean:jean_password@localhost:5432/jean"
    
    print(f"Using database URL: {database_url}")
    
    # Initialize the database
    db = ContextDatabase(database_url)
    await db.initialize()
    
    print(f"Test database initialized")
    return db

async def create_test_users(db: ContextDatabase) -> Dict[str, Tuple[int, str]]:
    """Create test users in multiple tenants and return their IDs and API keys."""
    tenants = ["tenant1", "tenant2", "tenant3"]
    users = {}
    
    for tenant in tenants:
        # Create two users per tenant
        for i in range(1, 3):
            google_id = f"google_{tenant}_{i}_{uuid.uuid4()}"
            email = f"user{i}@{tenant}.example.com"
            
            user_id, api_key = await db.create_or_get_user(
                tenant_id=tenant,
                google_id=google_id,
                email=email
            )
            
            user_key = f"{tenant}_user{i}"
            users[user_key] = (user_id, api_key)
            print(f"Created {user_key}: ID={user_id}, API Key={api_key[:10]}...")
    
    return users

async def store_test_data(db: ContextDatabase, users: Dict[str, Tuple[int, str]]):
    """Store test context data for each user in different tenants."""
    # For each user, store data in multiple context types
    for user_key, (user_id, _) in users.items():
        tenant_id = user_key.split("_")[0]  # Extract tenant from user_key
        
        # Store GitHub context
        await db.store_context(
            user_id=user_id,
            tenant_id=tenant_id,
            context_type="github",
            content={
                "repos": [
                    {"name": f"repo_{user_key}", "description": f"Test repo for {user_key}"}
                ]
            },
            source_identifier="github_main"
        )
        
        # Store Notes context
        await db.store_context(
            user_id=user_id,
            tenant_id=tenant_id,
            context_type="notes",
            content={
                "notes": [
                    {"title": f"Note for {user_key}", "content": f"This is a test note for {user_key}"}
                ]
            },
            source_identifier="notes_main"
        )
        
        print(f"Stored test data for {user_key} in tenant {tenant_id}")

async def test_data_isolation(db: ContextDatabase, users: Dict[str, Tuple[int, str]]):
    """Test that data is properly isolated between tenants."""
    print("\n=== Testing Tenant Isolation ===")
    
    # Get all tenant1 users
    tenant1_users = {k: v for k, v in users.items() if k.startswith("tenant1")}
    # Get all tenant2 users
    tenant2_users = {k: v for k, v in users.items() if k.startswith("tenant2")}
    
    # Test user in tenant1
    for user_key, (user_id, _) in tenant1_users.items():
        # Get this user's data in correct tenant
        github_data = await db.get_context(
            user_id=user_id,
            tenant_id="tenant1",
            context_type="github"
        )
        
        if github_data:
            print(f"✅ User {user_key} can access their data in tenant1")
        else:
            print(f"❌ User {user_key} cannot access their data in tenant1")
        
        # Try to get this user's data with wrong tenant
        wrong_tenant_data = await db.get_context(
            user_id=user_id,
            tenant_id="tenant2",  # Wrong tenant
            context_type="github"
        )
        
        if not wrong_tenant_data:
            print(f"✅ User {user_key} cannot access data with wrong tenant ID")
        else:
            print(f"❌ ISOLATION FAILURE: User {user_key} can access data with wrong tenant ID")
    
    # Cross-tenant test: tenant2 user trying to access tenant1 user's data
    tenant1_user = list(tenant1_users.values())[0]
    tenant2_user = list(tenant2_users.values())[0]
    
    # Store specific test data for tenant1 user
    await db.store_context(
        user_id=tenant1_user[0],
        tenant_id="tenant1",
        context_type="test",
        content={"secret": "tenant1_secret_value"},
        source_identifier="isolation_test"
    )
    
    # Try to access tenant1's data from tenant2 user
    cross_tenant_data = await db.get_context(
        user_id=tenant1_user[0],  # tenant1 user's ID
        tenant_id="tenant2",      # But with tenant2
        context_type="test"
    )
    
    if not cross_tenant_data:
        print("✅ Cross-tenant isolation test passed: Cannot access other tenant's data")
    else:
        print("❌ ISOLATION FAILURE: Cross-tenant data access possible!")
    
    # Try using tenant2 user's ID with tenant1
    mismatched_user_data = await db.get_context(
        user_id=tenant2_user[0],  # tenant2 user's ID
        tenant_id="tenant1",      # But with tenant1
        context_type="github"
    )
    
    if not mismatched_user_data:
        print("✅ User-tenant mismatch test passed: Cannot access with wrong tenant")
    else:
        print("❌ ISOLATION FAILURE: User-tenant mismatch allows data access!")

async def cleanup_test_data(db: ContextDatabase, users: Dict[str, Tuple[int, str]]):
    """Clean up the test data."""
    print("\n=== Cleaning Up Test Data ===")
    
    for user_key, (user_id, _) in users.items():
        tenant_id = user_key.split("_")[0]
        success = await db.delete_user_data(user_id, tenant_id)
        if success:
            print(f"Cleaned up data for {user_key}")
        else:
            print(f"Failed to clean up data for {user_key}")

async def main():
    """Run the tenant isolation tests."""
    print("=== JEAN Multi-Tenant Isolation Test ===\n")
    
    # Set up test database
    db = None
    try:
        db = await setup_test_database()
        
        # Create test users
        users = await create_test_users(db)
        
        # Store test data
        await store_test_data(db, users)
        
        # Test data isolation
        await test_data_isolation(db, users)
        
        # Clean up
        await cleanup_test_data(db, users)
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
    finally:
        # Close database connection
        if db:
            await db.close()
            print("Database connection closed")

if __name__ == "__main__":
    asyncio.run(main()) 