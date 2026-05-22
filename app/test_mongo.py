import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from database.mongodb_client import mongodb_client
from datetime import datetime

async def create_test_data():
    """Insert test data into MongoDB"""
    print("="*60)
    print("Testing MongoDB Connection")
    print("="*60)
    
    # Connect to MongoDB
    print("\n📡 Connecting to MongoDB...")
    db = await mongodb_client.connect()
    
    if db is None or not mongodb_client.is_connected:
        print("❌ Failed to connect to MongoDB")
        print("   Make sure MongoDB is running:")
        print("   - Docker: docker run -d -p 27017:27017 --name mongodb mongo:latest")
        return
    
    print("✅ Connected to MongoDB successfully")
    
    # Try to insert a test document directly
    try:
        test_collection = mongodb_client.db.reviews
        
        test_doc = {
            "review_id": "test_123",
            "pr_number": 999,
            "pr_title": "Test Document",
            "repository": "test/repo",
            "author": "testuser",
            "action": "test",
            "commit_sha": "test123",
            "files_reviewed": 1,
            "total_findings": 0,
            "has_issues": False,
            "merge_blocked": False,
            "status": "test_completed",
            "created_at": datetime.utcnow(),
            "completed_at": datetime.utcnow()
        }
        
        print("\n💾 Inserting test document...")
        result = await test_collection.insert_one(test_doc)
        print(f"✅ Inserted test document with ID: {result.inserted_id}")
        
        # Verify
        print("\n🔍 Verifying insertion...")
        doc = await test_collection.find_one({"review_id": "test_123"})
        if doc:
            print(f"✅ Document found in database!")
            print(f"   PR Number: {doc.get('pr_number')}")
            print(f"   Repository: {doc.get('repository')}")
        else:
            print("❌ Document not found")
            
    except Exception as e:
        print(f"❌ Error inserting document: {e}")
    
    # List all collections
    print("\n📚 Available collections:")
    collections = await mongodb_client.db.list_collection_names()
    if collections:
        for collection in collections:
            count = await mongodb_client.db[collection].count_documents({})
            print(f"   - {collection}: {count} document(s)")
    else:
        print("   No collections found yet")
    
    # Disconnect
    await mongodb_client.disconnect()
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(create_test_data())