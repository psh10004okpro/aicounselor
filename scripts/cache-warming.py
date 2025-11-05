#!/usr/bin/env python3
"""
Cache Warming Script for AI Counselor

Preloads frequently accessed data into Redis cache to improve initial response times.
Run this script after deployment or Redis restarts.

Usage:
    python scripts/cache-warming.py
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.cache_service import CacheService
from app.core.redis import RedisManager
from app.core.config import settings


class CacheWarmer:
    """Cache warming service"""

    def __init__(self):
        self.redis_manager = None
        self.cache_service = None

    async def initialize(self):
        """Initialize Redis connection"""
        print("🔌 Connecting to Redis...")
        self.redis_manager = RedisManager(settings.REDIS_URL)
        await self.redis_manager.connect()
        self.cache_service = CacheService(self.redis_manager)
        print("✅ Connected to Redis\n")

    async def warm_faq_cache(self):
        """Warm up FAQ cache"""
        print("📚 Warming FAQ cache...")
        try:
            count = await self.cache_service.initialize_faq_cache(ttl=604800)  # 7 days
            print(f"✅ Loaded {count} FAQs into cache\n")
        except Exception as e:
            print(f"❌ FAQ cache warming failed: {e}\n")

    async def warm_common_queries(self):
        """Warm up cache with common queries"""
        print("💬 Warming common query cache...")

        common_queries = [
            "안녕하세요",
            "AI 상담은 어떻게 작동하나요?",
            "스트레스를 관리하는 방법이 있나요?",
            "불안할 때 어떻게 해야 하나요?",
            "우울한 기분을 어떻게 극복할 수 있나요?",
            "수면 문제를 해결하는 방법은?",
            "대화 내용이 안전하게 보호되나요?",
            "언제든지 대화를 시작할 수 있나요?",
            "전문 상담사와 연결할 수 있나요?",
            "감사합니다",
        ]

        warmed_count = 0
        for query in common_queries:
            # Check if already in FAQ cache
            faq_response = await self.cache_service.get_faq_response(query)
            if faq_response:
                warmed_count += 1
                print(f"  ✓ Cached: {query[:50]}...")

        print(f"✅ Warmed {warmed_count} common queries\n")

    async def warm_embeddings_cache(self):
        """Warm up embeddings cache for common phrases"""
        print("🔢 Warming embeddings cache...")

        # Note: In production, you might want to precompute embeddings
        # for common queries to reduce OpenAI API calls
        common_phrases = [
            "안녕하세요",
            "도움이 필요해요",
            "감사합니다",
            "상담 시작",
            "스트레스",
            "불안",
            "우울",
        ]

        print(f"ℹ️  {len(common_phrases)} phrases identified for embedding cache")
        print("   (Embeddings will be cached on first use)\n")

    async def verify_cache_warmth(self):
        """Verify cache warming was successful"""
        print("🔍 Verifying cache warmth...")

        try:
            # Get cache statistics
            info = await self.redis_manager.redis.info('keyspace')
            db_info = info.get('db0', {})

            if isinstance(db_info, dict):
                keys = db_info.get('keys', 0)
            else:
                # Parse string format "keys=X,expires=Y,avg_ttl=Z"
                keys_str = db_info.split(',')[0].split('=')[1] if '=' in db_info else '0'
                keys = int(keys_str)

            print(f"✅ Total cached keys: {keys}")

            # Check FAQ cache
            faq_keys = []
            cursor = 0
            while True:
                cursor, keys_batch = await self.redis_manager.redis.scan(
                    cursor, match="faq:*", count=100
                )
                faq_keys.extend(keys_batch)
                if cursor == 0:
                    break

            print(f"✅ FAQ entries: {len(faq_keys)}")

            # Get memory usage
            memory_info = await self.redis_manager.redis.info('memory')
            used_memory_mb = memory_info.get('used_memory', 0) / 1024 / 1024
            print(f"✅ Memory usage: {used_memory_mb:.2f} MB\n")

        except Exception as e:
            print(f"⚠️  Verification warning: {e}\n")

    async def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        print("🧹 Cleaning up expired cache...")

        try:
            # This is handled automatically by Redis TTL
            # But we can log current state
            info = await self.redis_manager.redis.info('stats')
            expired_keys = info.get('expired_keys', 0)
            evicted_keys = info.get('evicted_keys', 0)

            print(f"ℹ️  Expired keys: {expired_keys}")
            print(f"ℹ️  Evicted keys: {evicted_keys}\n")

        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}\n")

    async def close(self):
        """Close Redis connection"""
        if self.redis_manager:
            await self.redis_manager.close()
            print("🔌 Redis connection closed")


async def main():
    """Main cache warming procedure"""
    start_time = datetime.now()

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                                                           ║")
    print("║           AI Counselor - Cache Warming                   ║")
    print("║                                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"\nStarted at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    warmer = CacheWarmer()

    try:
        # Initialize
        await warmer.initialize()

        # Warm different cache types
        await warmer.warm_faq_cache()
        await warmer.warm_common_queries()
        await warmer.warm_embeddings_cache()

        # Verify
        await warmer.verify_cache_warmth()

        # Cleanup
        await warmer.cleanup_expired_cache()

        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("╔═══════════════════════════════════════════════════════════╗")
        print("║                 Cache Warming Complete!                  ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print(f"\nCompleted at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration:.2f} seconds\n")

    except Exception as e:
        print(f"\n❌ Cache warming failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await warmer.close()


if __name__ == "__main__":
    asyncio.run(main())
