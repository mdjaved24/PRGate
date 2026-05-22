import hashlib
from functools import lru_cache
from typing import Optional
from datetime import datetime, timedelta
from schemas.findings import CodeReviewResponse

class ReviewCache:
    """Cache for code review results"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def _get_cache_key(self, code: str) -> str:
        """Generate cache key from code"""
        return hashlib.md5(code.encode()).hexdigest()
    
    def get(self, code: str) -> Optional[CodeReviewResponse]:
        """Get cached review result"""
        key = self._get_cache_key(code)
        
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                return result
            else:
                # Remove expired entry
                del self.cache[key]
        
        return None
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics for monitoring"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "hit_rate": "unknown"  # Could track hits/misses
        }
    
    def set(self, code: str, result: CodeReviewResponse):
        """Cache review result"""
        key = self._get_cache_key(code)
        
        # Manage cache size
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (result, datetime.now())
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()

# Global cache instance
review_cache = ReviewCache(max_size=100, ttl_seconds=3600)