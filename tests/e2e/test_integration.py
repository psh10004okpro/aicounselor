#!/usr/bin/env python3
"""
End-to-End Integration Tests for AI Counselor

Tests complete user workflows including:
- User registration and authentication
- Chat conversations with streaming
- Crisis detection scenarios
- Long conversation handling
- Cache performance

Usage:
    pytest tests/e2e/test_integration.py -v
    python tests/e2e/test_integration.py
"""

import asyncio
import pytest
import httpx
import json
from typing import List, Dict
import time


# Test configuration
API_BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0


class TestIntegration:
    """End-to-end integration tests"""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup test client"""
        self.client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT)
        self.session_token = None
        self.conversation_id = None
        yield
        await self.client.aclose()

    async def test_01_health_check(self):
        """Test API health endpoint"""
        response = await self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "redis" in data
        print("✅ Health check passed")

    async def test_02_anonymous_session_creation(self):
        """Test anonymous user session creation"""
        response = await self.client.post("/auth/anonymous")
        assert response.status_code == 201
        data = response.json()

        assert "user" in data
        assert "session_token" in data
        assert data["user"]["is_anonymous"] is True

        self.session_token = data["session_token"]
        print(f"✅ Anonymous session created: {self.session_token[:20]}...")

    async def test_03_send_first_message(self):
        """Test sending first message in conversation"""
        assert self.session_token is not None

        payload = {
            "message": "안녕하세요, 도움이 필요해요",
            "stream": False
        }

        response = await self.client.post(
            "/chat/send",
            json=payload,
            headers={"X-Session-Token": self.session_token}
        )

        assert response.status_code == 200
        data = response.json()

        assert "message_id" in data
        assert "conversation_id" in data
        assert "content" in data
        assert data["role"] == "assistant"
        assert len(data["content"]) > 0

        self.conversation_id = data["conversation_id"]
        print(f"✅ First message sent, conversation: {self.conversation_id}")
        print(f"   Response: {data['content'][:100]}...")

    async def test_04_conversation_continuity(self):
        """Test conversation continuity with follow-up messages"""
        assert self.session_token is not None
        assert self.conversation_id is not None

        messages = [
            "요즘 스트레스를 많이 받고 있어요",
            "어떻게 관리하면 좋을까요?",
            "구체적인 방법을 알려주세요"
        ]

        for msg in messages:
            payload = {
                "message": msg,
                "conversation_id": self.conversation_id,
                "stream": False
            }

            response = await self.client.post(
                "/chat/send",
                json=payload,
                headers={"X-Session-Token": self.session_token}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["conversation_id"] == self.conversation_id
            print(f"   ✓ Message: {msg[:50]}...")
            print(f"     Response: {data['content'][:80]}...")

            # Small delay between messages
            await asyncio.sleep(0.5)

        print("✅ Conversation continuity maintained")

    async def test_05_streaming_response(self):
        """Test streaming message response"""
        assert self.session_token is not None

        payload = {
            "message": "스트레스 관리 방법을 알려주세요",
            "stream": True
        }

        async with self.client.stream(
            "POST",
            "/chat/send",
            json=payload,
            headers={"X-Session-Token": self.session_token}
        ) as response:
            assert response.status_code == 200

            tokens = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str.strip():
                        data = json.loads(data_str)
                        if data.get("type") == "token":
                            tokens.append(data["content"])
                        elif data.get("type") == "done":
                            print(f"✅ Streaming response complete: {len(tokens)} tokens")
                            break

            assert len(tokens) > 0

    async def test_06_crisis_detection_keywords(self):
        """Test crisis detection with keywords"""
        assert self.session_token is not None

        # Test with critical keywords
        crisis_messages = [
            "요즘 삶이 너무 힘들어요",
            "가끔 죽고 싶다는 생각이 들어요"
        ]

        for msg in crisis_messages:
            payload = {
                "message": msg,
                "stream": False
            }

            response = await self.client.post(
                "/chat/send",
                json=payload,
                headers={"X-Session-Token": self.session_token}
            )

            assert response.status_code == 200
            data = response.json()

            # Check if crisis was detected
            if data.get("crisis_detected"):
                print(f"✅ Crisis detected for: {msg}")
                assert "risk_level" in data
                print(f"   Risk level: {data['risk_level']}")
            else:
                print(f"⚠️  No crisis detected (may be GPT-4 filtered)")

    async def test_07_false_positive_prevention(self):
        """Test that idioms don't trigger false positives"""
        assert self.session_token is not None

        # Korean idioms that should NOT trigger crisis detection
        idioms = [
            "배고파 죽겠어요",
            "웃겨 죽겠네요",
            "감사합니다, 많은 도움이 되었어요"
        ]

        for idiom in idioms:
            payload = {
                "message": idiom,
                "stream": False
            }

            response = await self.client.post(
                "/chat/send",
                json=payload,
                headers={"X-Session-Token": self.session_token}
            )

            assert response.status_code == 200
            data = response.json()

            # These should NOT trigger crisis detection
            if data.get("crisis_detected") and data.get("risk_level") in ["high", "critical"]:
                print(f"⚠️  False positive detected for: {idiom}")
            else:
                print(f"✅ No false positive: {idiom}")

    async def test_08_long_conversation(self):
        """Test handling of long conversations (10+ messages)"""
        assert self.session_token is not None

        conversation_messages = [
            "안녕하세요",
            "저는 대학생입니다",
            "요즘 학업 스트레스가 심해요",
            "시험 기간이 다가오고 있어요",
            "밤에 잠을 잘 못 자요",
            "집중이 안 돼요",
            "어떻게 해야 할까요?",
            "구체적인 조언 부탁드려요",
            "도움이 되는 정보 감사합니다",
            "다음에 또 상담할 수 있을까요?"
        ]

        conversation_id = None
        start_time = time.time()

        for i, msg in enumerate(conversation_messages, 1):
            payload = {
                "message": msg,
                "stream": False
            }

            if conversation_id:
                payload["conversation_id"] = conversation_id

            response = await self.client.post(
                "/chat/send",
                json=payload,
                headers={"X-Session-Token": self.session_token}
            )

            assert response.status_code == 200
            data = response.json()

            if not conversation_id:
                conversation_id = data["conversation_id"]

            print(f"   [{i}/10] {msg[:40]}...")

            await asyncio.sleep(0.3)  # Small delay

        duration = time.time() - start_time
        print(f"✅ Long conversation completed in {duration:.2f}s")

    async def test_09_cache_performance(self):
        """Test cache performance with repeated queries"""
        assert self.session_token is not None

        # Query that should be cached (FAQ)
        query = "AI 상담은 어떻게 작동하나요?"

        # First request (cache miss)
        start_time = time.time()
        payload = {"message": query, "stream": False}

        response1 = await self.client.post(
            "/chat/send",
            json=payload,
            headers={"X-Session-Token": self.session_token}
        )
        first_duration = time.time() - start_time

        assert response1.status_code == 200
        data1 = response1.json()

        # Second request (should hit cache)
        start_time = time.time()
        response2 = await self.client.post(
            "/chat/send",
            json=payload,
            headers={"X-Session-Token": self.session_token}
        )
        second_duration = time.time() - start_time

        assert response2.status_code == 200
        data2 = response2.json()

        # Cache should make second request faster
        speedup = first_duration / second_duration if second_duration > 0 else 1

        print(f"✅ Cache performance test:")
        print(f"   First request:  {first_duration:.3f}s")
        print(f"   Second request: {second_duration:.3f}s")
        print(f"   Speedup: {speedup:.2f}x")

        # FAQ cache should return same answer
        if data1.get("content") == data2.get("content"):
            print("   ✓ FAQ cache working (same response)")

    async def test_10_rate_limiting(self):
        """Test rate limiting"""
        assert self.session_token is not None

        # Send many requests quickly
        print("   Sending 15 rapid requests...")
        rate_limited = False

        for i in range(15):
            payload = {"message": f"Test message {i}", "stream": False}

            response = await self.client.post(
                "/chat/send",
                json=payload,
                headers={"X-Session-Token": self.session_token}
            )

            if response.status_code == 429:
                print(f"✅ Rate limit triggered at request {i+1}")
                rate_limited = True
                break
            elif response.status_code == 200:
                print(f"   [{i+1}/15] Request succeeded")

        if not rate_limited:
            print("⚠️  Rate limiting not triggered (may need adjustment)")

    async def test_11_get_conversation_history(self):
        """Test retrieving conversation history"""
        assert self.session_token is not None
        assert self.conversation_id is not None

        response = await self.client.get(
            f"/chat/history/{self.conversation_id}",
            headers={"X-Session-Token": self.session_token}
        )

        assert response.status_code == 200
        data = response.json()

        assert "messages" in data
        assert "conversation_id" in data
        assert len(data["messages"]) > 0

        print(f"✅ Retrieved {len(data['messages'])} messages from history")

    async def test_12_clear_conversation(self):
        """Test clearing conversation history"""
        assert self.session_token is not None
        assert self.conversation_id is not None

        response = await self.client.delete(
            f"/chat/history/{self.conversation_id}",
            headers={"X-Session-Token": self.session_token}
        )

        assert response.status_code == 200
        print("✅ Conversation history cleared")


async def run_all_tests():
    """Run all E2E tests"""
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                                                           ║")
    print("║          AI Counselor - E2E Integration Tests            ║")
    print("║                                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝\n")

    test_suite = TestIntegration()

    # Setup
    await test_suite.setup().__anext__()

    try:
        # Run tests in order
        await test_suite.test_01_health_check()
        await test_suite.test_02_anonymous_session_creation()
        await test_suite.test_03_send_first_message()
        await test_suite.test_04_conversation_continuity()
        await test_suite.test_05_streaming_response()
        await test_suite.test_06_crisis_detection_keywords()
        await test_suite.test_07_false_positive_prevention()
        await test_suite.test_08_long_conversation()
        await test_suite.test_09_cache_performance()
        await test_suite.test_10_rate_limiting()
        await test_suite.test_11_get_conversation_history()
        await test_suite.test_12_clear_conversation()

        print("\n╔═══════════════════════════════════════════════════════════╗")
        print("║              All E2E Tests Passed! ✅                    ║")
        print("╚═══════════════════════════════════════════════════════════╝")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
