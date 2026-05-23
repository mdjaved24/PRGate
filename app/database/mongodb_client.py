import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from datetime import datetime
from utils.logger import get_logger

# Setup logger
db_logger = get_logger("database")

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
        enabled = os.getenv('MONGODB_ENABLED', 'false').lower() == 'true'  # Default to false for production
        
        if not enabled:
            db_logger.info("ℹ️ MongoDB is disabled (MONGODB_ENABLED=false)")
            self._db = None
            return None
        
        try:
            db_logger.info(f"📡 Connecting to MongoDB...")
            self._client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=5000)
            # Test connection
            await self._client.admin.command('ping')
            self._db = self._client[db_name]
            db_logger.info(f"✅ MongoDB connected successfully to {mongodb_url}")
            db_logger.info(f"📚 Using database: {db_name}")
            await self._create_indexes()
            return self._db
        except Exception as e:
            db_logger.error(f"⚠️ MongoDB connection failed: {e}")
            db_logger.warning("⚠️ Continuing without database - some features will be disabled")
            self._client = None
            self._db = None
            return None
    
    async def _create_indexes(self):
        """Create indexes for better query performance"""
        if self._db is None:
            return
        
        try:
            db_logger.debug("Creating database indexes...")
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
            
            db_logger.info("✅ MongoDB indexes created")
        except Exception as e:
            db_logger.warning(f"⚠️ Index creation warning: {e}")
    
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
            db_logger.info("✅ MongoDB disconnected")

# Global MongoDB client instance
mongodb_client = MongoDBClient()