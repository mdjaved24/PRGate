import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from datetime import datetime

class MongoDBClient:
    """MongoDB client manager for CodeSentry"""
    
    _instance = None
    _client: Optional[AsyncIOMotorClient] = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Establish MongoDB connection"""
        mongodb_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
        db_name = os.getenv('MONGODB_DB_NAME', 'pr_gate')
        enabled = os.getenv('MONGODB_ENABLED', 'true').lower() == 'true'
        
        if not enabled:
            print("ℹ️ MongoDB is disabled (MONGODB_ENABLED=false)")
            return None
        
        try:
            self._client = AsyncIOMotorClient(mongodb_url)
            # Test connection
            await self._client.admin.command('ping')
            self._db = self._client[db_name]
            print(f"✅ MongoDB connected successfully to {mongodb_url}")
            print(f"📚 Using database: {db_name}")
            await self._create_indexes()
            return self._db
        except Exception as e:
            print(f"⚠️ MongoDB connection failed: {e}")
            self._client = None
            self._db = None
            return None
    
    async def _create_indexes(self):
        """Create indexes for better query performance"""
        if self._db is None:
            return
        
        try:
            # Reviews collection indexes
            await self._db.reviews.create_index("pr_number")
            await self._db.reviews.create_index("repository")
            await self._db.reviews.create_index("created_at")
            await self._db.reviews.create_index([("repository", 1), ("created_at", -1)])
            
            # Findings collection indexes
            await self._db.findings.create_index("review_id")
            await self._db.findings.create_index("severity")
            await self._db.findings.create_index("category")
            await self._db.findings.create_index("cwe_id")
            
            # Developers collection indexes
            await self._db.developers.create_index("username", unique=True)
            await self._db.developers.create_index("email")
            
            # Repositories collection indexes
            await self._db.repositories.create_index("full_name", unique=True)
            
            print("✅ MongoDB indexes created")
        except Exception as e:
            print(f"⚠️ Index creation warning: {e}")
    
    @property
    def db(self):
        """Get database instance"""
        return self._db
    
    @property
    def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._db is not None
    
    async def disconnect(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            print("✅ MongoDB disconnected")

# Global MongoDB client instance
mongodb_client = MongoDBClient()