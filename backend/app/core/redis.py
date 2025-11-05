"""Redis connection and caching utilities"""

import json
from typing import Optional, Any
from redis.asyncio import Redis, ConnectionPool
import numpy as np

from app.core.config import settings


class RedisManager:
    """Redis connection manager with semantic caching support"""

    def __init__(self):
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[Redis] = None

    async def connect(self) -> None:
        """Initialize Redis connection pool"""
        self.pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=False,  # We'll handle encoding ourselves
            max_connections=50,
        )
        self.client = Redis(connection_pool=self.pool)

    async def disconnect(self) -> None:
        """Close Redis connections"""
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.client:
            return None

        value = await self.client.get(key)
        if value:
            return value.decode("utf-8")
        return None

    async def set(
        self, key: str, value: str, ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL"""
        if not self.client:
            return False

        ttl = ttl or settings.CACHE_TTL_SECONDS
        return await self.client.setex(key, ttl, value)

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.client:
            return False

        return await self.client.delete(key) > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.client:
            return False

        return await self.client.exists(key) > 0

    async def semantic_cache_search(
        self, query_embedding: list[float], threshold: float = None
    ) -> Optional[dict[str, Any]]:
        """
        Search for similar cached queries using embeddings.

        Args:
            query_embedding: Query embedding vector
            threshold: Similarity threshold (default from settings)

        Returns:
            Cached response if similar query found, None otherwise
        """
        if not self.client:
            return None

        threshold = threshold or settings.SIMILARITY_THRESHOLD

        # Get all cache keys with embeddings
        pattern = "cache:embedding:*"
        cursor = 0
        best_match = None
        best_similarity = threshold

        async for key in self.client.scan_iter(match=pattern):
            try:
                # Get embedding
                cached_embedding_bytes = await self.client.get(key)
                if not cached_embedding_bytes:
                    continue

                cached_embedding = json.loads(cached_embedding_bytes.decode("utf-8"))

                # Calculate cosine similarity
                similarity = self._cosine_similarity(
                    query_embedding, cached_embedding
                )

                # Update best match if similarity is higher
                if similarity > best_similarity:
                    best_similarity = similarity
                    # Get the response key (remove "cache:embedding:" prefix)
                    response_key = key.decode("utf-8").replace(
                        "cache:embedding:", "cache:response:"
                    )
                    response_bytes = await self.client.get(response_key)
                    if response_bytes:
                        best_match = {
                            "response": json.loads(response_bytes.decode("utf-8")),
                            "similarity": similarity,
                        }

            except Exception as e:
                # Log error but continue searching
                print(f"Error checking cache key {key}: {e}")
                continue

        return best_match

    async def semantic_cache_set(
        self,
        query_id: str,
        query_embedding: list[float],
        response: dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store query embedding and response in cache.

        Args:
            query_id: Unique identifier for the query
            query_embedding: Query embedding vector
            response: Response to cache
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False

        ttl = ttl or settings.CACHE_TTL_SECONDS

        try:
            # Store embedding
            embedding_key = f"cache:embedding:{query_id}"
            await self.client.setex(
                embedding_key, ttl, json.dumps(query_embedding)
            )

            # Store response
            response_key = f"cache:response:{query_id}"
            await self.client.setex(
                response_key, ttl, json.dumps(response)
            )

            return True
        except Exception as e:
            print(f"Error setting semantic cache: {e}")
            return False

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        arr1 = np.array(vec1)
        arr2 = np.array(vec2)

        dot_product = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))


# Global Redis manager instance
redis_manager = RedisManager()


async def get_redis() -> RedisManager:
    """Dependency for getting Redis manager"""
    return redis_manager
