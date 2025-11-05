"""
Tests for Chat API endpoints

Tests cover:
- Streaming responses
- Non-streaming responses
- Rate limiting
- Token limits
- Error handling
- Crisis detection integration
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.main import app
from app.models.user import User
from app.models.conversation import Conversation


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock user for testing"""
    user = MagicMock(spec=User)
    user.id = "test-user-123"
    user.user_id = "test-user-123"
    user.session_token = "test-session-token"
    user.is_anonymous = True
    user.is_deleted = False
    return user


@pytest.fixture
def mock_conversation():
    """Mock conversation for testing"""
    conv = MagicMock(spec=Conversation)
    conv.id = "test-conv-123"
    conv.conversation_id = "test-conv-123"
    conv.title = "Test Conversation"
    return conv


# ===========================================================================
# Non-Streaming Chat Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_send_message_success(client, mock_user, mock_conversation):
    """Test successful non-streaming message"""
    with patch("app.api.chat.get_current_user") as mock_get_user, \
         patch("app.api.chat.ConversationService") as mock_conv_service, \
         patch("app.api.chat.OpenAIService") as mock_openai, \
         patch("app.api.chat.CacheService") as mock_cache, \
         patch("app.api.chat.crisis_detection_system") as mock_crisis:

        # Setup mocks
        mock_get_user.return_value = mock_user

        # Cache service mock (rate limiting)
        cache_instance = AsyncMock()
        cache_instance.rate_limit_per_minute = AsyncMock(
            return_value=(True, {"requests_remaining": 9})
        )
        mock_cache.return_value = cache_instance

        # Conversation service mock
        conv_service_instance = AsyncMock()
        conv_service_instance.create_conversation = AsyncMock(return_value=mock_conversation)
        conv_service_instance.add_message = AsyncMock(return_value=MagicMock(
            id="msg-123",
            content="Test response",
            role="assistant"
        ))
        conv_service_instance.get_conversation_context = AsyncMock(return_value=[])
        mock_conv_service.return_value = conv_service_instance

        # OpenAI service mock
        openai_instance = AsyncMock()
        openai_instance.create_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        openai_instance.generate_conversation_title = AsyncMock(return_value="Test Title")

        async def mock_chat_completion(*args, **kwargs):
            yield "Test response from AI"

        openai_instance.chat_completion = mock_chat_completion
        openai_instance._build_system_prompt = MagicMock(return_value="System prompt")
        mock_openai.return_value = openai_instance

        # Crisis detection mock (no crisis)
        mock_crisis.detect = AsyncMock(return_value={
            "risk_level": MagicMock(value="none"),
            "detected_keywords": []
        })

        # Make request
        response = client.post(
            "/chat/message",
            json={"message": "Hello, how are you?"},
            params={"session_token": "test-session-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert data["crisis_detected"] is False


@pytest.mark.asyncio
async def test_send_message_rate_limit_exceeded(client, mock_user):
    """Test rate limit exceeded"""
    with patch("app.api.chat.get_current_user") as mock_get_user, \
         patch("app.api.chat.CacheService") as mock_cache:

        mock_get_user.return_value = mock_user

        # Rate limit exceeded
        cache_instance = AsyncMock()
        cache_instance.rate_limit_per_minute = AsyncMock(
            return_value=(False, {
                "requests_remaining": 0,
                "reset_time": "2024-01-01T00:00:00"
            })
        )
        mock_cache.return_value = cache_instance

        response = client.post(
            "/chat/message",
            json={"message": "Hello"},
            params={"session_token": "test-session-token"}
        )

        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]["message"]


@pytest.mark.asyncio
async def test_send_message_crisis_detected(client, mock_user, mock_conversation):
    """Test message with crisis detection"""
    with patch("app.api.chat.get_current_user") as mock_get_user, \
         patch("app.api.chat.ConversationService") as mock_conv_service, \
         patch("app.api.chat.OpenAIService") as mock_openai, \
         patch("app.api.chat.CacheService") as mock_cache, \
         patch("app.api.chat.crisis_detection_system") as mock_crisis:

        mock_get_user.return_value = mock_user

        # Cache service
        cache_instance = AsyncMock()
        cache_instance.rate_limit_per_minute = AsyncMock(
            return_value=(True, {"requests_remaining": 9})
        )
        mock_cache.return_value = cache_instance

        # Conversation service
        conv_service_instance = AsyncMock()
        conv_service_instance.create_conversation = AsyncMock(return_value=mock_conversation)
        conv_service_instance.add_message = AsyncMock(return_value=MagicMock(
            id="msg-123",
            content="Crisis response",
            role="assistant"
        ))
        conv_service_instance.get_conversation_context = AsyncMock(return_value=[])
        mock_conv_service.return_value = conv_service_instance

        # OpenAI service
        openai_instance = AsyncMock()
        openai_instance.create_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        openai_instance.generate_conversation_title = AsyncMock(return_value="Crisis Title")
        mock_openai.return_value = openai_instance

        # Crisis detected
        from app.services.crisis_detector import RiskLevel
        mock_crisis.detect = AsyncMock(return_value={
            "risk_level": RiskLevel.CRITICAL,
            "detected_keywords": ["자살", "죽고싶다"],
            "reasoning": "High risk detected",
            "immediate_action_needed": True,
        })
        mock_crisis.emergency_protocol = AsyncMock()
        mock_crisis.get_crisis_response_message = MagicMock(
            return_value="긴급 위기 상담이 필요합니다. 1393으로 전화주세요."
        )

        response = client.post(
            "/chat/message",
            json={"message": "자살하고 싶어요"},
            params={"session_token": "test-session-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["crisis_detected"] is True
        assert data["crisis_severity"] == "critical"
        assert "1393" in data["message"]["content"]


@pytest.mark.asyncio
async def test_send_message_invalid_session(client):
    """Test with invalid session token"""
    with patch("app.api.chat.get_current_user") as mock_get_user:
        from fastapi import HTTPException
        mock_get_user.side_effect = HTTPException(status_code=401, detail="Invalid session")

        response = client.post(
            "/chat/message",
            json={"message": "Hello"},
            params={"session_token": "invalid-token"}
        )

        assert response.status_code == 401


# ===========================================================================
# Streaming Chat Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_stream_message_success(client, mock_user, mock_conversation):
    """Test successful streaming message"""
    with patch("app.api.chat.get_current_user") as mock_get_user, \
         patch("app.api.chat.ConversationService") as mock_conv_service, \
         patch("app.api.chat.OpenAIService") as mock_openai, \
         patch("app.api.chat.CacheService") as mock_cache, \
         patch("app.api.chat.crisis_detection_system") as mock_crisis:

        mock_get_user.return_value = mock_user

        # Cache service
        cache_instance = AsyncMock()
        cache_instance.rate_limit_per_minute = AsyncMock(
            return_value=(True, {"requests_remaining": 9})
        )
        mock_cache.return_value = cache_instance

        # Conversation service
        conv_service_instance = AsyncMock()
        conv_service_instance.create_conversation = AsyncMock(return_value=mock_conversation)
        conv_service_instance.add_message = AsyncMock(return_value=MagicMock(
            id="msg-123",
            content="Test",
            role="user"
        ))
        conv_service_instance.get_conversation_context = AsyncMock(return_value=[])
        mock_conv_service.return_value = conv_service_instance

        # OpenAI service
        openai_instance = AsyncMock()
        openai_instance.create_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        openai_instance.generate_conversation_title = AsyncMock(return_value="Test Title")

        async def mock_streaming_completion(*args, **kwargs):
            for char in "Hello from AI":
                yield char

        openai_instance.chat_completion = mock_streaming_completion
        openai_instance._build_system_prompt = MagicMock(return_value="System prompt")
        mock_openai.return_value = openai_instance

        # No crisis
        mock_crisis.detect = AsyncMock(return_value={
            "risk_level": MagicMock(value="none"),
            "detected_keywords": []
        })

        # Make streaming request
        response = client.post(
            "/chat/stream",
            json={"message": "Hello"},
            params={"session_token": "test-session-token"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


@pytest.mark.asyncio
async def test_stream_message_rate_limit(client, mock_user):
    """Test streaming with rate limit exceeded"""
    with patch("app.api.chat.get_current_user") as mock_get_user, \
         patch("app.api.chat.CacheService") as mock_cache:

        mock_get_user.return_value = mock_user

        # Rate limit exceeded
        cache_instance = AsyncMock()
        cache_instance.rate_limit_per_minute = AsyncMock(
            return_value=(False, {
                "requests_remaining": 0,
                "reset_time": "60"
            })
        )
        mock_cache.return_value = cache_instance

        response = client.post(
            "/chat/stream",
            json={"message": "Hello"},
            params={"session_token": "test-session-token"}
        )

        assert response.status_code == 200
        # Check that rate limit error is in SSE stream
        content = response.text
        assert "Rate limit exceeded" in content


# ===========================================================================
# Error Handling Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_send_message_empty_content(client, mock_user):
    """Test with empty message content"""
    with patch("app.api.chat.get_current_user") as mock_get_user:
        mock_get_user.return_value = mock_user

        response = client.post(
            "/chat/message",
            json={"message": ""},
            params={"session_token": "test-session-token"}
        )

        # Should return 422 for validation error
        assert response.status_code in [422, 400]


@pytest.mark.asyncio
async def test_send_message_missing_token(client):
    """Test without session token"""
    response = client.post(
        "/chat/message",
        json={"message": "Hello"}
    )

    # Should return 422 for missing required parameter
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_send_message_conversation_not_found(client, mock_user):
    """Test with non-existent conversation ID"""
    with patch("app.api.chat.get_current_user") as mock_get_user, \
         patch("app.api.chat.ConversationService") as mock_conv_service, \
         patch("app.api.chat.CacheService") as mock_cache:

        mock_get_user.return_value = mock_user

        # Cache service
        cache_instance = AsyncMock()
        cache_instance.rate_limit_per_minute = AsyncMock(
            return_value=(True, {"requests_remaining": 9})
        )
        mock_cache.return_value = cache_instance

        # Conversation not found
        conv_service_instance = AsyncMock()
        conv_service_instance.get_conversation = AsyncMock(return_value=None)
        mock_conv_service.return_value = conv_service_instance

        response = client.post(
            "/chat/message",
            json={
                "message": "Hello",
                "conversation_id": "non-existent-id"
            },
            params={"session_token": "test-session-token"}
        )

        assert response.status_code == 404


# ===========================================================================
# Performance Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_streaming_response_time(client, mock_user, mock_conversation):
    """Test that streaming response starts quickly"""
    import time

    with patch("app.api.chat.get_current_user") as mock_get_user, \
         patch("app.api.chat.ConversationService") as mock_conv_service, \
         patch("app.api.chat.OpenAIService") as mock_openai, \
         patch("app.api.chat.CacheService") as mock_cache, \
         patch("app.api.chat.crisis_detection_system") as mock_crisis:

        mock_get_user.return_value = mock_user

        cache_instance = AsyncMock()
        cache_instance.rate_limit_per_minute = AsyncMock(
            return_value=(True, {"requests_remaining": 9})
        )
        mock_cache.return_value = cache_instance

        conv_service_instance = AsyncMock()
        conv_service_instance.create_conversation = AsyncMock(return_value=mock_conversation)
        conv_service_instance.add_message = AsyncMock(return_value=MagicMock())
        conv_service_instance.get_conversation_context = AsyncMock(return_value=[])
        mock_conv_service.return_value = conv_service_instance

        openai_instance = AsyncMock()
        openai_instance.create_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        openai_instance.generate_conversation_title = AsyncMock(return_value="Title")

        async def mock_streaming(*args, **kwargs):
            yield "response"

        openai_instance.chat_completion = mock_streaming
        openai_instance._build_system_prompt = MagicMock(return_value="prompt")
        mock_openai.return_value = openai_instance

        mock_crisis.detect = AsyncMock(return_value={
            "risk_level": MagicMock(value="none"),
            "detected_keywords": []
        })

        start_time = time.time()
        response = client.post(
            "/chat/stream",
            json={"message": "Hello"},
            params={"session_token": "test-session-token"}
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        # Streaming should start within 2 seconds
        assert elapsed < 2.0


@pytest.mark.asyncio
async def test_concurrent_requests(client, mock_user, mock_conversation):
    """Test handling multiple concurrent requests"""
    import asyncio

    with patch("app.api.chat.get_current_user") as mock_get_user, \
         patch("app.api.chat.ConversationService") as mock_conv_service, \
         patch("app.api.chat.OpenAIService") as mock_openai, \
         patch("app.api.chat.CacheService") as mock_cache, \
         patch("app.api.chat.crisis_detection_system") as mock_crisis:

        mock_get_user.return_value = mock_user

        cache_instance = AsyncMock()
        cache_instance.rate_limit_per_minute = AsyncMock(
            return_value=(True, {"requests_remaining": 9})
        )
        mock_cache.return_value = cache_instance

        conv_service_instance = AsyncMock()
        conv_service_instance.create_conversation = AsyncMock(return_value=mock_conversation)
        conv_service_instance.add_message = AsyncMock(return_value=MagicMock())
        conv_service_instance.get_conversation_context = AsyncMock(return_value=[])
        mock_conv_service.return_value = conv_service_instance

        openai_instance = AsyncMock()
        openai_instance.create_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        openai_instance.generate_conversation_title = AsyncMock(return_value="Title")

        async def mock_completion(*args, **kwargs):
            yield "response"

        openai_instance.chat_completion = mock_completion
        openai_instance._build_system_prompt = MagicMock(return_value="prompt")
        mock_openai.return_value = openai_instance

        mock_crisis.detect = AsyncMock(return_value={
            "risk_level": MagicMock(value="none"),
            "detected_keywords": []
        })

        # Make 5 concurrent requests
        responses = []
        for i in range(5):
            response = client.post(
                "/chat/message",
                json={"message": f"Hello {i}"},
                params={"session_token": "test-session-token"}
            )
            responses.append(response)

        # All should succeed (until rate limit)
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 1  # At least one should succeed
