"""Caching and rate limiting service"""

from typing import Optional, Any
import json
import hashlib
from datetime import datetime, timedelta

from app.core.redis import RedisManager
from app.core.config import settings


# ===========================================================================
# FAQ Data for Korean Counseling Chatbot
# ===========================================================================

KOREAN_FAQ_DATA = [
    {
        "question": "AI 상담은 어떻게 작동하나요?",
        "answer": "안녕하세요! 저는 마음이입니다. 인지행동치료(CBT) 기반의 AI 상담사로, 여러분의 고민을 경청하고 공감하며 건강한 관점을 찾도록 돕습니다. 단, 저는 전문 상담사를 대체할 수 없으며, 심각한 증상이 있으시다면 전문가 상담을 권장드립니다.",
        "keywords": ["ai 상담", "작동", "어떻게", "마음이", "소개"],
    },
    {
        "question": "자살예방 상담전화는 어디인가요?",
        "answer": "⚠️ **긴급 자살예방 상담전화**\n\n• 자살예방상담전화: **1393** (24시간 무료)\n• 청소년전화: **1388** (24시간)\n• 정신건강위기상담: **1577-0199** (24시간)\n• 응급: **119**\n\n힘든 시간을 보내고 계신다면 지금 바로 전화주세요. 전문가들이 항상 대기하고 있습니다.",
        "keywords": ["자살", "상담전화", "긴급", "1393", "위기"],
    },
    {
        "question": "우울증 증상은 무엇인가요?",
        "answer": "우울증의 주요 증상으로는 지속적인 우울감, 흥미 상실, 에너지 감소, 수면 문제, 식욕 변화, 집중력 저하 등이 있습니다. 2주 이상 이런 증상이 지속되고 일상생활에 지장이 있다면 전문가 상담을 권장드립니다. 정신건강의학과나 상담센터를 방문해보세요.",
        "keywords": ["우울증", "증상", "우울", "우울한"],
    },
    {
        "question": "불안을 어떻게 관리하나요?",
        "answer": "불안 관리에 도움이 되는 방법들:\n\n1. **호흡법**: 4-7-8 호흡 (4초 들이쉬고, 7초 멈추고, 8초 내쉬기)\n2. **그라운딩**: 5-4-3-2-1 기법 (5가지 보이는 것, 4가지 만질 수 있는 것 등)\n3. **운동**: 규칙적인 신체활동\n4. **수면**: 충분한 휴식\n5. **전문가 상담**: 지속적인 불안은 상담이 필요합니다\n\n불안이 일상생활에 큰 지장을 준다면 정신건강의학과 방문을 권장드립니다.",
        "keywords": ["불안", "관리", "걱정", "초조"],
    },
    {
        "question": "개인정보는 안전한가요?",
        "answer": "네, 여러분의 개인정보는 안전하게 보호됩니다. 익명 세션을 사용하며, 모든 대화는 암호화되어 저장됩니다. 대화 기록은 24시간 후 자동 삭제되며, 위기 감지를 위한 최소한의 정보만 처리됩니다. 자세한 내용은 개인정보처리방침을 참고해주세요.",
        "keywords": ["개인정보", "안전", "프라이버시", "보안", "익명"],
    },
    {
        "question": "무료로 사용할 수 있나요?",
        "answer": "네, 이 AI 상담 서비스는 완전히 무료입니다. 별도의 가입이나 결제 없이 익명으로 상담을 받으실 수 있습니다. 다만, 하루 이용 횟수에 제한이 있을 수 있습니다.",
        "keywords": ["무료", "비용", "가격", "요금"],
    },
    {
        "question": "스트레스를 어떻게 해소하나요?",
        "answer": "스트레스 해소 방법:\n\n1. **신체 활동**: 산책, 요가, 스트레칭\n2. **이완 기법**: 심호흡, 명상, 근육 이완\n3. **취미 활동**: 음악 감상, 독서, 그림 그리기\n4. **사회적 지지**: 가족, 친구와 대화\n5. **충분한 수면**: 규칙적인 수면 패턴\n\n스트레스가 지속되거나 과도하다면 전문가 상담을 고려해보세요.",
        "keywords": ["스트레스", "해소", "관리", "피로"],
    },
]


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

    # ===========================================================================
    # FAQ Caching
    # ===========================================================================

    async def initialize_faq_cache(self, ttl: int = 604800) -> int:
        """
        Initialize FAQ cache with pre-defined Korean FAQs.

        Args:
            ttl: Time to live in seconds (default: 7 days)

        Returns:
            Number of FAQs cached
        """
        cached_count = 0

        for faq in KOREAN_FAQ_DATA:
            # Create unique key from question
            question_hash = hashlib.md5(
                faq["question"].encode("utf-8")
            ).hexdigest()
            key = f"faq:{question_hash}"

            # Cache FAQ data
            faq_data = {
                "question": faq["question"],
                "answer": faq["answer"],
                "keywords": faq["keywords"],
                "cached_at": datetime.utcnow().isoformat(),
            }

            success = await self.set(key, faq_data, ttl)
            if success:
                cached_count += 1

                # Also cache by keywords for fast lookup
                for keyword in faq["keywords"]:
                    keyword_key = f"faq:keyword:{keyword.lower()}"
                    await self.redis.client.sadd(keyword_key, question_hash)
                    await self.redis.client.expire(keyword_key, ttl)

        return cached_count

    async def get_faq_response(self, question: str, similarity_threshold: float = 0.7) -> Optional[dict]:
        """
        Get cached FAQ response by question text or keywords.

        Args:
            question: User's question
            similarity_threshold: Minimum similarity for keyword matching

        Returns:
            FAQ data dict or None if not found
        """
        # Try exact match first
        question_hash = hashlib.md5(question.encode("utf-8")).hexdigest()
        key = f"faq:{question_hash}"
        faq_data = await self.get(key)

        if faq_data:
            return faq_data

        # Try keyword matching
        question_lower = question.lower()

        for faq in KOREAN_FAQ_DATA:
            # Check if any keyword is in the question
            keyword_matches = sum(
                1 for keyword in faq["keywords"]
                if keyword.lower() in question_lower
            )

            # If enough keywords match, return this FAQ
            if keyword_matches >= 1:
                # Create cached response
                faq_hash = hashlib.md5(faq["question"].encode("utf-8")).hexdigest()
                cached_faq = await self.get(f"faq:{faq_hash}")

                if cached_faq:
                    return cached_faq

                # Return fresh data if not cached
                return {
                    "question": faq["question"],
                    "answer": faq["answer"],
                    "keywords": faq["keywords"],
                    "cached_at": datetime.utcnow().isoformat(),
                }

        return None

    async def get_all_faqs(self) -> list[dict]:
        """Get all cached FAQs"""
        faqs = []

        for faq in KOREAN_FAQ_DATA:
            question_hash = hashlib.md5(faq["question"].encode("utf-8")).hexdigest()
            key = f"faq:{question_hash}"
            cached_faq = await self.get(key)

            if cached_faq:
                faqs.append(cached_faq)
            else:
                # Return fresh data if not cached
                faqs.append({
                    "question": faq["question"],
                    "answer": faq["answer"],
                    "keywords": faq["keywords"],
                })

        return faqs

    # ===========================================================================
    # Usage and Cost Tracking
    # ===========================================================================

    async def track_usage(
        self,
        user_id: str,
        tokens: int,
        cost: float,
        model: str = "gpt-4o-mini",
    ) -> bool:
        """
        Track API usage and costs for a user.

        Args:
            user_id: User identifier
            tokens: Number of tokens used
            cost: Cost in USD
            model: Model name

        Returns:
            Success status
        """
        now = datetime.utcnow()
        today = now.strftime("%Y-%m-%d")
        month = now.strftime("%Y-%m")

        # Daily usage
        daily_key = f"usage:daily:{user_id}:{today}"
        await self.redis.client.hincrby(daily_key, "tokens", tokens)
        await self.redis.client.hincrbyfloat(daily_key, "cost", cost)
        await self.redis.client.hincrby(daily_key, "requests", 1)
        await self.redis.client.hset(daily_key, "model", model)
        await self.redis.client.expire(daily_key, 86400 * 31)  # Keep for 31 days

        # Monthly usage
        monthly_key = f"usage:monthly:{user_id}:{month}"
        await self.redis.client.hincrby(monthly_key, "tokens", tokens)
        await self.redis.client.hincrbyfloat(monthly_key, "cost", cost)
        await self.redis.client.hincrby(monthly_key, "requests", 1)
        await self.redis.client.expire(monthly_key, 86400 * 365)  # Keep for 1 year

        # Global stats
        global_daily = f"usage:global:daily:{today}"
        await self.redis.client.hincrby(global_daily, "tokens", tokens)
        await self.redis.client.hincrbyfloat(global_daily, "cost", cost)
        await self.redis.client.hincrby(global_daily, "requests", 1)
        await self.redis.client.expire(global_daily, 86400 * 365)

        return True

    async def get_usage_stats(
        self,
        user_id: str,
        period: str = "day",
        date: str = None,
    ) -> dict:
        """
        Get usage statistics for a user.

        Args:
            user_id: User identifier
            period: "day" or "month"
            date: Specific date (YYYY-MM-DD for day, YYYY-MM for month)

        Returns:
            Usage stats dict with tokens, cost, requests
        """
        now = datetime.utcnow()

        if period == "day":
            if not date:
                date = now.strftime("%Y-%m-%d")
            key = f"usage:daily:{user_id}:{date}"
        elif period == "month":
            if not date:
                date = now.strftime("%Y-%m")
            key = f"usage:monthly:{user_id}:{date}"
        else:
            raise ValueError("Period must be 'day' or 'month'")

        # Get all fields from hash
        data = await self.redis.client.hgetall(key)

        if not data:
            return {
                "tokens": 0,
                "cost": 0.0,
                "requests": 0,
                "model": None,
                "period": period,
                "date": date,
            }

        # Decode bytes to strings
        decoded = {k.decode("utf-8"): v.decode("utf-8") for k, v in data.items()}

        return {
            "tokens": int(decoded.get("tokens", 0)),
            "cost": float(decoded.get("cost", 0.0)),
            "requests": int(decoded.get("requests", 0)),
            "model": decoded.get("model"),
            "period": period,
            "date": date,
        }

    async def get_global_usage_stats(self, date: str = None) -> dict:
        """
        Get global usage statistics for all users.

        Args:
            date: Date in YYYY-MM-DD format (default: today)

        Returns:
            Global usage stats
        """
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        key = f"usage:global:daily:{date}"
        data = await self.redis.client.hgetall(key)

        if not data:
            return {
                "tokens": 0,
                "cost": 0.0,
                "requests": 0,
                "date": date,
            }

        decoded = {k.decode("utf-8"): v.decode("utf-8") for k, v in data.items()}

        return {
            "tokens": int(decoded.get("tokens", 0)),
            "cost": float(decoded.get("cost", 0.0)),
            "requests": int(decoded.get("requests", 0)),
            "date": date,
        }

    async def get_cache_hit_rate(self, date: str = None) -> dict:
        """
        Calculate cache hit rate for semantic caching.

        Args:
            date: Date in YYYY-MM-DD format (default: today)

        Returns:
            Cache statistics with hit rate
        """
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        hits_key = f"cache:hits:{date}"
        misses_key = f"cache:misses:{date}"

        hits = await self.get_counter(hits_key)
        misses = await self.get_counter(misses_key)
        total = hits + misses

        hit_rate = (hits / total * 100) if total > 0 else 0

        return {
            "hits": hits,
            "misses": misses,
            "total": total,
            "hit_rate": round(hit_rate, 2),
            "date": date,
        }

    async def track_cache_hit(self, date: str = None) -> None:
        """Track a cache hit"""
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        key = f"cache:hits:{date}"
        await self.increment_counter(key)
        await self.redis.client.expire(key, 86400 * 31)  # Keep for 31 days

    async def track_cache_miss(self, date: str = None) -> None:
        """Track a cache miss"""
        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        key = f"cache:misses:{date}"
        await self.increment_counter(key)
        await self.redis.client.expire(key, 86400 * 31)  # Keep for 31 days

    # ===========================================================================
    # Message History (24-hour TTL)
    # ===========================================================================

    async def save_message(
        self,
        session_id: str,
        message: dict,
        ttl: int = 86400,
    ) -> bool:
        """
        Save a message to conversation history.

        Args:
            session_id: Session identifier
            message: Message dict with role, content, timestamp
            ttl: Time to live in seconds (default: 24 hours)

        Returns:
            Success status
        """
        key = f"messages:{session_id}"

        # Get existing messages
        messages = await self.get(key) or []

        # Add new message
        messages.append({
            **message,
            "saved_at": datetime.utcnow().isoformat(),
        })

        # Keep last 50 messages only
        messages = messages[-50:]

        # Save with TTL
        return await self.set(key, messages, ttl)

    async def get_history(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get message history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return

        Returns:
            List of messages (most recent first)
        """
        key = f"messages:{session_id}"
        messages = await self.get(key) or []

        # Return last N messages
        return messages[-limit:] if messages else []

    async def clear_history(self, session_id: str) -> bool:
        """Clear message history for a session"""
        key = f"messages:{session_id}"
        return await self.delete(key)
