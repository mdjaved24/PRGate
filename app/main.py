import json
import uvicorn
from fastapi import FastAPI, Request
from git_hub.client import git
from llm.reviewer import review_code
from git_hub.pr_fetcher import git_router
from utils.logger import get_logger, audit_logger
from database.mongodb_client import mongodb_client

# Setup loggers
app_logger = get_logger("app")
audit_logger = get_logger("audit")

app = FastAPI(title="PRGate", description="Automated Security Review Bot")

@app.on_event("startup")
async def startup_event():
    """Log application startup"""
    app_logger.info("=" * 50)
    app_logger.info("🚀 PRGate Starting up...")
    app_logger.info("=" * 50)
    
    # Connect to MongoDB
    await mongodb_client.connect()
    
    app_logger.info("✅ PRGate started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown"""
    app_logger.info("🛑 PRGate shutting down...")
    await mongodb_client.disconnect()
    app_logger.info("✅ PRGate stopped")

@app.get("/")
def main():
    app_logger.debug("Health check endpoint called")
    return {'msg': 'PRGate Security Bot is running!'}

# Include router
app.include_router(router=git_router)

if __name__ == "__main__":
    import os
    
    # Get environment
    environment = os.getenv("ENVIRONMENT", "development")
    
    if environment == "production":
        # Production settings (Render)
        port = int(os.getenv("PORT", 8000))
        uvicorn.run(
            "main:app",
            host="0.0.0.0",  # Listen on all interfaces
            port=port,
            reload=False,     # No auto-reload in production
            workers=4         # Multiple workers for production
        )
    else:
        # Development settings (local)
        uvicorn.run(
            "main:app",
            host="127.0.0.1",  # Local only
            port=8000,
            reload=True        # Auto-reload on code changes
        )