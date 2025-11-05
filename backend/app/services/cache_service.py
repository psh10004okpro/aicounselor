"""Caching and rate limiting service"""

from typing import Optional, Any
import json
import hashlib
from datetime import datetime, timedelta

from app.core.redis import RedisManager
from app.core.config import settings


class CacheService:
    """Service for caching and rate limiting using Redis"""

    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager

    # ===========================================================================
    # General Caching
    # ===========================================================================

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value with optional TTL"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        elif not isinstance(value, str):
            value = str(value)

        return await self.redis.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        return await self.redis.delete(key)

    # ===========================================================================
    # Rate Limiting
    # ===========================================================================

    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int,
        namespace: str = "rate_limit",
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit.

        Args:
            identifier: User identifier (user_id, IP, etc.)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            namespace: Rate limit namespace

        Returns:
            Tuple of (is_allowed, info_dict)
            info_dict contains: requests_made, requests_remaining, reset_time
        """
        key = f"{namespace}:{identifier}"

        # Get current count
        current = await self.redis.client.get(key)

        if current is None:
            # First request in window
            await self.redis.client.setex(key, window_seconds, 1)
            return True, {
                "requests_made": 1,
                "requests_remaining": max_requests - 1,
                "reset_time": datetime.utcnow() + timedelta(seconds=window_seconds),
            }

        current_count = int(current)

        if current_count >= max_requests:
            # Rate limit exceeded
            ttl = await self.redis.client.ttl(key)
            return False, {
                "requests_made": current_count,
                "requests_remaining": 0,
                "reset_time": datetime.utcnow() + timedelta(seconds=ttl),
            }

        # Increment counter
        new_count = await self.redis.client.incr(key)
        ttl = await self.redis.client.ttl(key)

        return True, {
            "requests_made": new_count,
            "requests_remaining": max_requests - new_count,
            "reset_time": datetime.utcnow() + timedelta(seconds=ttl),
        }

    async def rate_limit_per_minute(
        self, identifier: str, max_requests: int = 10
    ) -> tuple[bool, dict]:
        """Check rate limit per minute"""
        return await self.check_rate_limit(
            identifier, max_requests, 60, "rate_limit_minute"
        )

    async def rate_limit_per_hour(
        self, identifier: str, max_requests: int = 100
    ) -> tuple[bool, dict]:
        """Check rate limit per hour"""
        return await self.check_rate_limit(
            identifier, max_requests, 3600, "rate_limit_hour"
        )

    # ===========================================================================
    # Conversation History Caching
    # ===========================================================================

    async def cache_conversation_history(
        self, conversation_id: str, messages: list[dict], ttl: int = 3600
    ) -> bool:
        """Cache conversation history"""
        key = f"conversation:{conversation_id}:history"
        return await self.set(key, messages, ttl)

    async def get_conversation_history(
        self, conversation_id: str
    ) -> Optional[list[dict]]:
        """Get cached conversation history"""
        key = f"conversation:{conversation_id}:history"
        return await self.get(key)

    async def invalidate_conversation_history(self, conversation_id: str) -> bool:
        """Invalidate cached conversation history"""
        key = f"conversation:{conversation_id}:history"
        return await self.delete(key)

    # ===========================================================================
    # User Session Caching
    # ===========================================================================

    async def cache_user_session(
        self, session_token: str, user_data: dict, ttl: int = 86400
    ) -> bool:
        """Cache user session data (24 hours default)"""
        key = f"session:{session_token}"
        return await self.set(key, user_data, ttl)

    async def get_user_session(self, session_token: str) -> Optional[dict]:
        """Get cached user session"""
        key = f"session:{session_token}"
        return await self.get(key)

    async def invalidate_user_session(self, session_token: str) -> bool:
        """Invalidate user session"""
        key = f"session:{session_token}"
        return await self.delete(key)

    # ===========================================================================
    # Semantic Caching (Wrapper)
    # ===========================================================================

    async def semantic_cache_get(
        self, query_embedding: list[float], threshold: float = None
    ) -> Optional[dict]:
        """Get semantically similar cached response"""
        return await self.redis.semantic_cache_search(query_embedding, threshold)

    async def semantic_cache_set(
        self,
        query_id: str,
        query_embedding: list[float],
        response: dict,
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache response with semantic embedding"""
        return await self.redis.semantic_cache_set(
            query_id, query_embedding, response, ttl
        )

    # ===========================================================================
    # Crisis Event Tracking
    # ===========================================================================

    async def track_crisis_event(
        self, user_id: str, severity: int, ttl: int = 86400
    ) -> None:
        """Track crisis event for monitoring (24 hours)"""
        key = f"crisis:recent:{user_id}"
        events = await self.get(key) or []

        events.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "severity": severity,
            }
        )

        # Keep only last 10 events
        events = events[-10:]

        await self.set(key, events, ttl)

    async def get_recent_crisis_events(self, user_id: str) -> list[dict]:
        """Get recent crisis events for user"""
        key = f"crisis:recent:{user_id}"
        return await self.get(key) or []

    async def has_recent_crisis(
        self, user_id: str, minutes: int = 60, min_severity: int = 5
    ) -> bool:
        """Check if user had recent crisis event"""
        events = await self.get_recent_crisis_events(user_id)

        if not events:
            return False

        cutoff = datetime.utcnow() - timedelta(minutes=minutes)

        for event in events:
            event_time = datetime.fromisoformat(event["timestamp"])
            if event_time > cutoff and event["severity"] >= min_severity:
                return True

        return False

    # ===========================================================================
    # Memory Cache
    # ===========================================================================

    async def cache_user_memories(
        self, user_id: str, memories: list[dict], ttl: int = 3600
    ) -> bool:
        """Cache user memories (1 hour)"""
        key = f"memories:{user_id}"
        return await self.set(key, memories, ttl)

    async def get_cached_user_memories(self, user_id: str) -> Optional[list[dict]]:
        """Get cached user memories"""
        key = f"memories:{user_id}"
        return await self.get(key)

    async def invalidate_user_memories(self, user_id: str) -> bool:
        """Invalidate cached user memories"""
        key = f"memories:{user_id}"
        return await self.delete(key)

    # ===========================================================================
    # Statistics
    # ===========================================================================

    async def increment_counter(self, key: str, amount: int = 1) -> int:
        """Increment a counter"""
        return await self.redis.client.incrby(key, amount)

    async def get_counter(self, key: str) -> int:
        """Get counter value"""
        value = await self.redis.client.get(key)
        return int(value) if value else 0

    async def track_api_call(self, endpoint: str, user_id: str = None) -> None:
        """Track API call for analytics"""
        # Daily stats
        today = datetime.utcnow().strftime("%Y-%m-%d")
        await self.increment_counter(f"stats:api:{endpoint}:{today}")

        if user_id:
            await self.increment_counter(f"stats:user:{user_id}:{today}")

    async def get_daily_stats(self, date: str = None) -> dict:
        """Get daily API statistics"""
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        # Get all stats for the day
        pattern = f"stats:api:*:{date}"
        stats = {}

        async for key in self.redis.client.scan_iter(match=pattern):
            key_str = key.decode("utf-8")
            endpoint = key_str.split(":")[2]
            count = await self.get_counter(key_str)
            stats[endpoint] = count

        return stats
