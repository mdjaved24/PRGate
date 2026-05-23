import json
import uvicorn
import os
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from git_hub.client import git
from llm.reviewer import review_code
from git_hub.pr_fetcher import git_router
from utils.logger import get_logger, audit_logger
from database.mongodb_client import mongodb_client

# Setup loggers
app_logger = get_logger("app")
audit_logger = get_logger("audit")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    app_logger.info("=" * 50)
    app_logger.info("🚀 PRGate Starting up...")
    app_logger.info("=" * 50)
    
    # Connect to MongoDB (don't let it crash the app)
    try:
        await mongodb_client.connect()
        if mongodb_client.is_connected:
            app_logger.info("✅ MongoDB connected successfully")
        else:
            app_logger.warning("⚠️ MongoDB not connected - running without database")
    except Exception as e:
        app_logger.error(f"❌ MongoDB connection failed: {e}")
        app_logger.warning("⚠️ Continuing without database...")
    
    app_logger.info("✅ PRGate started successfully")
    yield
    
    # Shutdown
    app_logger.info("🛑 PRGate shutting down...")
    try:
        await mongodb_client.disconnect()
    except Exception as e:
        app_logger.error(f"Error disconnecting MongoDB: {e}")
    app_logger.info("✅ PRGate stopped")

# Create app with lifespan
app = FastAPI(
    title="PRGate", 
    description="Automated Security Review Bot",
    lifespan=lifespan
)

@app.get("/")
def main():
    app_logger.debug("Health check endpoint called")
    return {'msg': 'PRGate Security Bot is running!'}

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "PRGate"}

# Include router
app.include_router(router=git_router)

if __name__ == "__main__":
    import os
    
    # Get environment
    environment = os.getenv("ENVIRONMENT", "development")
    port = int(os.getenv("PORT", 8000))
    
    if environment == "production":
        # Production settings (Render) - use single worker for stability
        app_logger.info(f"🚀 Starting PRGate in PRODUCTION mode on port {port}")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            reload=False,
            workers=1  # Use 1 worker to prevent child process death
        )
    else:
        # Development settings (local)
        app_logger.info(f"🚀 Starting PRGate in DEVELOPMENT mode on port {port}")
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=8000,
            reload=True
        )