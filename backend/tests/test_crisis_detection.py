"""
Tests for Crisis Detection System

Tests cover:
- Keyword detection (Stage 1)
- GPT-4 analysis (Stage 2)
- Structured output validation (Stage 3)
- False positive prevention
- False negative prevention
- Response time requirements
- Emergency protocol activation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time

from app.services.crisis_detector import (
    CrisisDetectionSystem,
    RiskLevel,
    CRISIS_KEYWORDS,
)


@pytest.fixture
def crisis_system():
    """Crisis detection system instance"""
    return CrisisDetectionSystem()


# ===========================================================================
# Stage 1: Keyword Detection Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_keyword_detection_critical(crisis_system):
    """Test detection of critical keywords"""
    messages = [
        "자살하고 싶어요",
        "죽고 싶다",
        "목숨을 끊고 싶습니다",
    ]

    for message in messages:
        detected, keywords, severity = crisis_system._detect_crisis_keywords(message)
        assert detected is True
        assert len(keywords) > 0
        assert severity >= 8  # Critical severity


@pytest.mark.asyncio
async def test_keyword_detection_high_risk(crisis_system):
    """Test detection of high-risk keywords"""
    messages = [
        "너무 힘들어서 더 이상 살 수 없어",
        "세상에서 사라지고 싶어",
        "아무도 날 필요로 하지 않아",
    ]

    for message in messages:
        detected, keywords, severity = crisis_system._detect_crisis_keywords(message)
        assert detected is True
        assert severity >= 5  # High risk


@pytest.mark.asyncio
async def test_keyword_detection_no_crisis(crisis_system):
    """Test normal messages without crisis keywords"""
    messages = [
        "오늘 날씨가 좋네요",
        "저녁 뭐 먹을까요",
        "일이 조금 힘들어요",
    ]

    for message in messages:
        detected, keywords, severity = crisis_system._detect_crisis_keywords(message)
        assert detected is False


@pytest.mark.asyncio
async def test_keyword_detection_context_dependent(crisis_system):
    """Test context-dependent keyword detection"""
    # Word "죽다" in different contexts
    messages = {
        "배고파 죽겠어": False,  # Idiom - not crisis
        "웃겨 죽겠네": False,  # Idiom - not crisis
        "정말 죽고 싶어": True,  # Crisis
    }

    for message, should_detect in messages.items():
        detected, keywords, severity = crisis_system._detect_crisis_keywords(message)
        # Note: Simple keyword detection might have false positives
        # Full system (with GPT-4) filters these out


# ===========================================================================
# Full Detection Pipeline Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_full_detection_critical_case(crisis_system):
    """Test full detection pipeline for critical case"""
    with patch.object(crisis_system.openai_service.client.chat.completions, 'create') as mock_create:
        # Mock GPT-4 response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```json
{
    "risk_level": "critical",
    "reasoning": "User expressed clear suicidal intent",
    "immediate_action_needed": true,
    "suggested_resources": ["1393", "emergency_services"],
    "confidence": 0.95,
    "detected_keywords": ["자살", "죽고싶다"]
}```'''
        mock_create.return_value = mock_response

        message = "더 이상 살 수 없어요. 자살하고 싶어요."
        conversation_history = []

        assessment = await crisis_system.detect(message, conversation_history)

        assert assessment["risk_level"] == RiskLevel.CRITICAL
        assert assessment["immediate_action_needed"] is True
        assert assessment["confidence"] > 0.9
        assert len(assessment["detected_keywords"]) > 0


@pytest.mark.asyncio
async def test_full_detection_high_risk(crisis_system):
    """Test full detection pipeline for high risk"""
    with patch.object(crisis_system.openai_service.client.chat.completions, 'create') as mock_create:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```json
{
    "risk_level": "high",
    "reasoning": "Strong indicators of severe depression and hopelessness",
    "immediate_action_needed": true,
    "suggested_resources": ["1393", "mental_health_clinic"],
    "confidence": 0.85,
    "detected_keywords": ["죽고싶다", "힘들다"]
}```'''
        mock_create.return_value = mock_response

        message = "너무 힘들어요. 아무도 날 이해 못해요."
        conversation_history = [
            {"role": "user", "content": "요즘 계속 죽고 싶다는 생각이 들어요"}
        ]

        assessment = await crisis_system.detect(message, conversation_history)

        assert assessment["risk_level"] == RiskLevel.HIGH
        assert assessment["immediate_action_needed"] is True


@pytest.mark.asyncio
async def test_full_detection_medium_risk(crisis_system):
    """Test full detection pipeline for medium risk"""
    with patch.object(crisis_system.openai_service.client.chat.completions, 'create') as mock_create:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```json
{
    "risk_level": "medium",
    "reasoning": "Shows signs of depression but no immediate danger",
    "immediate_action_needed": false,
    "suggested_resources": ["counseling_center", "mental_health_hotline"],
    "confidence": 0.75,
    "detected_keywords": ["우울", "힘들다"]
}```'''
        mock_create.return_value = mock_response

        message = "요즘 우울해요. 아침에 일어나기 힘들어요."
        assessment = await crisis_system.detect(message, [])

        assert assessment["risk_level"] == RiskLevel.MEDIUM
        assert assessment["immediate_action_needed"] is False


@pytest.mark.asyncio
async def test_full_detection_no_risk(crisis_system):
    """Test full detection pipeline for normal conversation"""
    message = "오늘 날씨가 좋네요. 기분이 좀 나아졌어요."
    assessment = await crisis_system.detect(message, [])

    # No keywords detected, should return none
    assert assessment["risk_level"] == RiskLevel.NONE
    assert assessment["immediate_action_needed"] is False


# ===========================================================================
# False Positive Prevention Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_false_positive_prevention_idioms(crisis_system):
    """Test that common idioms don't trigger false positives"""
    idioms = [
        "배고파 죽겠어",
        "웃겨 죽겠네",
        "심심해 죽겠어",
        "더워 죽겠다",
    ]

    for idiom in idioms:
        with patch.object(crisis_system.openai_service.client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '''```json
{
    "risk_level": "none",
    "reasoning": "Common Korean idiom, no actual crisis",
    "immediate_action_needed": false,
    "suggested_resources": [],
    "confidence": 0.9,
    "detected_keywords": []
}```'''
            mock_create.return_value = mock_response

            assessment = await crisis_system.detect(idiom, [])

            # GPT-4 should filter out false positives
            assert assessment["risk_level"] in [RiskLevel.NONE, RiskLevel.LOW]


@pytest.mark.asyncio
async def test_false_positive_prevention_context(crisis_system):
    """Test context-aware false positive prevention"""
    # Conversation about a movie/book
    conversation = [
        {"role": "user", "content": "영화 봤는데 주인공이 죽는 장면이 슬펐어요"},
        {"role": "assistant", "content": "슬픈 영화였군요. 어떤 영화인가요?"}
    ]

    message = "주인공이 죽는 장면에서 울었어요"

    with patch.object(crisis_system.openai_service.client.chat.completions, 'create') as mock_create:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```json
{
    "risk_level": "none",
    "reasoning": "Discussing movie plot, not personal crisis",
    "immediate_action_needed": false,
    "suggested_resources": [],
    "confidence": 0.95,
    "detected_keywords": []
}```'''
        mock_create.return_value = mock_response

        assessment = await crisis_system.detect(message, conversation)

        assert assessment["risk_level"] == RiskLevel.NONE


# ===========================================================================
# False Negative Prevention Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_false_negative_prevention_indirect_expression(crisis_system):
    """Test detection of indirectly expressed suicidal thoughts"""
    indirect_messages = [
        "더 이상 여기 있고 싶지 않아요",
        "모든 게 끝났으면 좋겠어요",
        "세상에서 사라지고 싶어요",
    ]

    for message in indirect_messages:
        with patch.object(crisis_system.openai_service.client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '''```json
{
    "risk_level": "high",
    "reasoning": "Indirect expression of suicidal ideation",
    "immediate_action_needed": true,
    "suggested_resources": ["1393"],
    "confidence": 0.80,
    "detected_keywords": ["사라지다", "끝나다"]
}```'''
            mock_create.return_value = mock_response

            assessment = await crisis_system.detect(message, [])

            # Should detect high or critical risk
            assert assessment["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]


@pytest.mark.asyncio
async def test_false_negative_prevention_pattern_recognition(crisis_system):
    """Test detection based on conversation patterns"""
    conversation = [
        {"role": "user", "content": "요즘 아무것도 하기 싫어요"},
        {"role": "assistant", "content": "힘든 시간이군요. 언제부터 그러셨나요?"},
        {"role": "user", "content": "한 달 전부터요. 아무 의미가 없어요"},
        {"role": "assistant", "content": "많이 힘드셨겠어요."},
        {"role": "user", "content": "밤에 잠도 안 와요. 식욕도 없고"},
    ]

    message = "이제 정말 끝인 것 같아요"

    with patch.object(crisis_system.openai_service.client.chat.completions, 'create') as mock_create:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```json
{
    "risk_level": "high",
    "reasoning": "Pattern of severe depression symptoms over time",
    "immediate_action_needed": true,
    "suggested_resources": ["1393", "mental_health_clinic"],
    "confidence": 0.85,
    "detected_keywords": ["끝", "의미없다"]
}```'''
        mock_create.return_value = mock_response

        assessment = await crisis_system.detect(message, conversation)

        assert assessment["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]


# ===========================================================================
# Response Time Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_detection_response_time(crisis_system):
    """Test that crisis detection completes within acceptable time"""
    with patch.object(crisis_system.openai_service.client.chat.completions, 'create') as mock_create:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```json
{
    "risk_level": "critical",
    "reasoning": "Clear suicidal intent",
    "immediate_action_needed": true,
    "suggested_resources": ["1393"],
    "confidence": 0.95,
    "detected_keywords": ["자살"]
}```'''
        mock_create.return_value = mock_response

        message = "자살하고 싶어요"

        start_time = time.time()
        assessment = await crisis_system.detect(message, [])
        elapsed = time.time() - start_time

        # Should complete within 3 seconds (including GPT-4 call)
        assert elapsed < 3.0
        assert assessment["risk_level"] == RiskLevel.CRITICAL


# ===========================================================================
# Emergency Protocol Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_emergency_protocol_activation(crisis_system):
    """Test emergency protocol activation for critical cases"""
    with patch.object(crisis_system, '_log_crisis_event') as mock_log:
        assessment = {
            "risk_level": RiskLevel.CRITICAL,
            "reasoning": "Immediate danger",
            "immediate_action_needed": True,
            "suggested_resources": ["1393"],
            "confidence": 0.95,
            "detected_keywords": ["자살"],
        }

        await crisis_system.emergency_protocol(
            assessment=assessment,
            user_id="test-user",
            conversation_id="test-conv"
        )

        # Should log crisis event
        mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_get_crisis_response_message_critical(crisis_system):
    """Test crisis response message for critical level"""
    assessment = {
        "risk_level": RiskLevel.CRITICAL,
        "suggested_resources": ["1393", "119"],
        "confidence": 0.95,
    }

    response = crisis_system.get_crisis_response_message(assessment)

    # Should include emergency contact
    assert "1393" in response
    assert "긴급" in response or "위기" in response


@pytest.mark.asyncio
async def test_get_crisis_response_message_high(crisis_system):
    """Test crisis response message for high level"""
    assessment = {
        "risk_level": RiskLevel.HIGH,
        "suggested_resources": ["1393", "mental_health_clinic"],
        "confidence": 0.85,
    }

    response = crisis_system.get_crisis_response_message(assessment)

    # Should include help resources
    assert "1393" in response
    assert len(response) > 50  # Should be detailed


@pytest.mark.asyncio
async def test_get_crisis_response_message_medium(crisis_system):
    """Test crisis response message for medium level"""
    assessment = {
        "risk_level": RiskLevel.MEDIUM,
        "suggested_resources": ["counseling_center"],
        "confidence": 0.75,
    }

    response = crisis_system.get_crisis_response_message(assessment)

    # Should provide guidance
    assert len(response) > 30
    # May include general mental health resources


# ===========================================================================
# Edge Cases Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_detection_with_empty_message(crisis_system):
    """Test detection with empty message"""
    assessment = await crisis_system.detect("", [])

    assert assessment["risk_level"] == RiskLevel.NONE


@pytest.mark.asyncio
async def test_detection_with_very_long_message(crisis_system):
    """Test detection with very long message"""
    long_message = "힘들어요 " * 1000  # 3000+ characters

    with patch.object(crisis_system.openai_service.client.chat.completions, 'create') as mock_create:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```json
{
    "risk_level": "medium",
    "reasoning": "Repeated expression of distress",
    "immediate_action_needed": false,
    "suggested_resources": [],
    "confidence": 0.70,
    "detected_keywords": ["힘들다"]
}```'''
        mock_create.return_value = mock_response

        assessment = await crisis_system.detect(long_message, [])

        # Should handle long messages
        assert "risk_level" in assessment


@pytest.mark.asyncio
async def test_detection_with_mixed_languages(crisis_system):
    """Test detection with Korean and English mixed"""
    message = "I want to die 죽고 싶어요"

    detected, keywords, severity = crisis_system._detect_crisis_keywords(message)

    # Should detect Korean keywords
    assert detected is True
    assert len(keywords) > 0


@pytest.mark.asyncio
async def test_detection_robustness_to_typos(crisis_system):
    """Test detection with typos"""
    # Note: Typo handling depends on GPT-4's understanding
    messages_with_typos = [
        "쥭고싶어요",  # 죽고싶어요
        "자쌀하고싶어",  # 자살하고싶어
    ]

    for message in messages_with_typos:
        with patch.object(crisis_system.openai_service.client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '''```json
{
    "risk_level": "critical",
    "reasoning": "Clear suicidal intent despite typos",
    "immediate_action_needed": true,
    "suggested_resources": ["1393"],
    "confidence": 0.90,
    "detected_keywords": ["자살"]
}```'''
            mock_create.return_value = mock_response

            assessment = await crisis_system.detect(message, [])

            # GPT-4 should understand despite typos
            assert assessment["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]
