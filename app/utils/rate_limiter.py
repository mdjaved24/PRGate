from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

class RateLimiter:
    """Simple rate limiter for GitHub API calls"""
    
    def __init__(self, max_requests: int = 5, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.time_window)
        
        # Clean old entries
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if req_time > window_start
        ]
        
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        self.requests[key].append(now)
        return True
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests allowed"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.time_window)
        
        self.requests[key] = [
            req_time for req_time in self.requests[key] 
            if req_time > window_start
        ]
        
        return max(0, self.max_requests - len(self.requests[key]))

# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=10, time_window=60)