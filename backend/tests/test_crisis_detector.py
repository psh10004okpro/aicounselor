"""
Test cases for Advanced Crisis Detection System

Run with: pytest tests/test_crisis_detector.py -v
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.services.crisis_detector import (
    CrisisDetectionSystem,
    RiskLevel,
)


@pytest.fixture
def crisis_detector():
    """Create crisis detector instance"""
    return CrisisDetectionSystem()


# ==============================================================================
# Stage 1: Keyword Detection Tests
# ==============================================================================


class TestKeywordDetection:
    """Test immediate keyword-based detection"""

    @pytest.mark.parametrize(
        "message,expected_level",
        [
            # Critical keywords - Korean
            ("죽고 싶어요", RiskLevel.CRITICAL),
            ("자살하고 싶습니다", RiskLevel.CRITICAL),
            ("목숨을 끊고 싶어", RiskLevel.CRITICAL),
            ("사라지고 싶어요", RiskLevel.CRITICAL),
            ("자해하고 있어요", RiskLevel.CRITICAL),
            # Critical keywords - English
            ("I want to kill myself", RiskLevel.CRITICAL),
            ("I want to end my life", RiskLevel.CRITICAL),
            ("I want to commit suicide", RiskLevel.CRITICAL),
            # High risk keywords - Korean
            ("의미없는 삶", RiskLevel.HIGH),
            ("희망이 없어요", RiskLevel.HIGH),
            ("미래가 없는 것 같아", RiskLevel.HIGH),
            ("끝내고 싶어", RiskLevel.HIGH),
            # High risk keywords - English
            ("There's no point in living", RiskLevel.HIGH),
            ("I have no hope", RiskLevel.HIGH),
            # No risk
            ("오늘 날씨가 좋네요", RiskLevel.NONE),
            ("점심 뭐 먹을까요?", RiskLevel.NONE),
        ],
    )
    def test_keyword_detection_levels(
        self, crisis_detector, message, expected_level
    ):
        """Test that keywords are correctly classified by risk level"""
        result = crisis_detector._keyword_detection(message)
        assert result["risk_level"] == expected_level

    def test_critical_keywords_detected(self, crisis_detector):
        """Test that critical keywords are captured"""
        message = "죽고 싶어요. 자살하고 싶습니다."
        result = crisis_detector._keyword_detection(message)

        assert result["risk_level"] == RiskLevel.CRITICAL
        assert len(result["detected_keywords"]) >= 2
        assert any("죽" in k for k in result["detected_keywords"])

    def test_mixed_keywords(self, crisis_detector):
        """Test message with multiple risk levels"""
        message = "희망이 없고 죽고 싶어요"  # HIGH + CRITICAL
        result = crisis_detector._keyword_detection(message)

        # Should return CRITICAL (highest level)
        assert result["risk_level"] == RiskLevel.CRITICAL

    def test_case_insensitive(self, crisis_detector):
        """Test that detection is case-insensitive for English"""
        messages = [
            "I want to KILL MYSELF",
            "i want to kill myself",
            "I Want To Kill Myself",
        ]

        for message in messages:
            result = crisis_detector._keyword_detection(message)
            assert result["risk_level"] == RiskLevel.CRITICAL


# ==============================================================================
# Stage 2 & 3: Contextual Analysis Tests
# ==============================================================================


class TestContextualAnalysis:
    """Test GPT-4 contextual analysis with structured output"""

    @pytest.mark.asyncio
    async def test_contextual_analysis_structure(self, crisis_detector):
        """Test that contextual analysis returns correct structure"""
        message = "요즘 힘들어서 죽고 싶어요"

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.function_call = Mock()
        mock_response.choices[0].message.function_call.arguments = '''
        {
            "risk_level": "critical",
            "reasoning": "명확한 자살 의도 표현",
            "immediate_action_needed": true,
            "suggested_resources": ["1393", "1588-9191"],
            "confidence": 0.95
        }
        '''

        with patch.object(
            crisis_detector.client.chat.completions,
            "create",
            return_value=mock_response,
        ):
            result = await crisis_detector.contextual_analysis(message)

            # Verify structure
            assert "risk_level" in result
            assert "reasoning" in result
            assert "immediate_action_needed" in result
            assert "suggested_resources" in result
            assert "confidence" in result

            # Verify types
            assert isinstance(result["risk_level"], str)
            assert isinstance(result["reasoning"], str)
            assert isinstance(result["immediate_action_needed"], bool)
            assert isinstance(result["suggested_resources"], list)
            assert isinstance(result["confidence"], (int, float))

    @pytest.mark.asyncio
    async def test_contextual_with_history(self, crisis_detector):
        """Test contextual analysis with conversation history"""
        message = "그래, 그렇게 해야겠어"  # Ambiguous without context
        history = [
            {"role": "user", "content": "요즘 너무 힘들어요"},
            {"role": "assistant", "content": "무슨 일이 있으신가요?"},
            {"role": "user", "content": "죽고 싶어요"},  # Previous crisis indicator
        ]

        # Context should help identify higher risk
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.function_call = Mock()
        mock_response.choices[0].message.function_call.arguments = '''
        {
            "risk_level": "high",
            "reasoning": "이전 대화에서 자살 의도가 있었고, 현재 메시지가 모호하지만 우려됨",
            "immediate_action_needed": true,
            "suggested_resources": ["1393"],
            "confidence": 0.75
        }
        '''

        with patch.object(
            crisis_detector.client.chat.completions,
            "create",
            return_value=mock_response,
        ):
            result = await crisis_detector.contextual_analysis(message, history)

            assert result["risk_level"] in ["high", "critical"]
            assert result["immediate_action_needed"] == True

    @pytest.mark.asyncio
    async def test_error_handling_in_analysis(self, crisis_detector):
        """Test that errors in GPT-4 call are handled gracefully"""
        message = "테스트 메시지"

        # Mock API error
        with patch.object(
            crisis_detector.client.chat.completions,
            "create",
            side_effect=Exception("API Error"),
        ):
            result = await crisis_detector.contextual_analysis(message)

            # Should return safe default
            assert result["risk_level"] == RiskLevel.MEDIUM
            assert result["immediate_action_needed"] == True
            assert len(result["suggested_resources"]) > 0


# ==============================================================================
# Stage 3: Full Detection Pipeline Tests
# ==============================================================================


class TestFullDetection:
    """Test the complete 3-stage detection pipeline"""

    @pytest.mark.asyncio
    async def test_critical_immediate_response(self, crisis_detector):
        """Test that critical keywords trigger immediate response"""
        message = "죽고 싶어요"

        result = await crisis_detector.detect(message)

        assert result["risk_level"] == RiskLevel.CRITICAL
        assert result["immediate_action_needed"] == True
        assert len(result["detected_keywords"]) > 0
        assert result["confidence"] == 1.0
        assert "keyword" in result["detection_method"]

    @pytest.mark.asyncio
    async def test_high_risk_requires_analysis(self, crisis_detector):
        """Test that high risk keywords trigger GPT-4 analysis"""
        message = "희망이 없어요. 의미가 없는 것 같아요."

        # Mock GPT-4 response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.function_call = Mock()
        mock_response.choices[0].message.function_call.arguments = '''
        {
            "risk_level": "medium",
            "reasoning": "절망감 표현이지만 즉각적 위험은 낮음",
            "immediate_action_needed": false,
            "suggested_resources": ["1393"],
            "confidence": 0.80
        }
        '''

        with patch.object(
            crisis_detector.client.chat.completions,
            "create",
            return_value=mock_response,
        ):
            result = await crisis_detector.detect(message)

            assert result["risk_level"] in [RiskLevel.HIGH, RiskLevel.MEDIUM]
            assert "gpt" in result["detection_method"]

    @pytest.mark.asyncio
    async def test_no_risk_detected(self, crisis_detector):
        """Test normal conversation without risk"""
        message = "오늘 날씨가 좋네요. 산책하고 싶어요."

        result = await crisis_detector.detect(message)

        assert result["risk_level"] == RiskLevel.NONE
        assert result["immediate_action_needed"] == False
        assert len(result["detected_keywords"]) == 0

    @pytest.mark.asyncio
    async def test_risk_level_escalation(self, crisis_detector):
        """Test that higher risk level from either method is used"""
        message = "희망이 없어요"  # HIGH from keyword

        # But GPT-4 assesses as CRITICAL
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.function_call = Mock()
        mock_response.choices[0].message.function_call.arguments = '''
        {
            "risk_level": "critical",
            "reasoning": "문맥상 즉각적 위험",
            "immediate_action_needed": true,
            "suggested_resources": ["1393", "119"],
            "confidence": 0.90
        }
        '''

        with patch.object(
            crisis_detector.client.chat.completions,
            "create",
            return_value=mock_response,
        ):
            result = await crisis_detector.detect(message)

            # Should use CRITICAL (higher level)
            assert result["risk_level"] == RiskLevel.CRITICAL


# ==============================================================================
# Emergency Protocol Tests
# ==============================================================================


class TestEmergencyProtocol:
    """Test emergency response protocols"""

    def test_critical_response_structure(self, crisis_detector):
        """Test critical response has correct structure"""
        assessment = {
            "risk_level": RiskLevel.CRITICAL,
            "immediate_action_needed": True,
        }

        response = crisis_detector.critical_response(assessment)

        assert response["action"] == "IMMEDIATE_INTERVENTION"
        assert response["display_mode"] == "FULL_SCREEN"
        assert "1393" in response["message"]
        assert "119" in response["message"]
        assert response["chat_disabled"] == True

    @pytest.mark.asyncio
    async def test_emergency_protocol_critical(self, crisis_detector):
        """Test that critical level triggers appropriate protocol"""
        assessment = {
            "risk_level": RiskLevel.CRITICAL,
            "immediate_action_needed": True,
            "detected_keywords": ["죽고 싶"],
        }

        # Should not raise exception
        await crisis_detector.emergency_protocol(
            assessment, "user_123", "conversation_456"
        )

    def test_crisis_response_messages(self, crisis_detector):
        """Test that response messages are appropriate for each level"""
        levels_and_expectations = [
            (RiskLevel.CRITICAL, ["119", "1393", "즉시"]),
            (RiskLevel.HIGH, ["1393", "전문"]),
            (RiskLevel.MEDIUM, ["1393", "고려"]),
            (RiskLevel.LOW, ["1393"]),
            (RiskLevel.NONE, []),
        ]

        for level, expected_keywords in levels_and_expectations:
            assessment = {"risk_level": level}
            message = crisis_detector.get_crisis_response_message(assessment)

            for keyword in expected_keywords:
                assert keyword in message, f"Expected '{keyword}' in {level} response"


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestIntegration:
    """Integration tests for complete workflow"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "scenario",
        [
            {
                "name": "Immediate crisis - Korean",
                "message": "죽고 싶어요. 도움이 필요해요.",
                "expected_min_level": RiskLevel.CRITICAL,
                "expected_action": True,
            },
            {
                "name": "Immediate crisis - English",
                "message": "I want to kill myself. I need help.",
                "expected_min_level": RiskLevel.CRITICAL,
                "expected_action": True,
            },
            {
                "name": "High risk situation",
                "message": "살아가는게 너무 힘들고 의미가 없어요",
                "expected_min_level": RiskLevel.MEDIUM,
                "expected_action": False,  # May vary with GPT-4
            },
            {
                "name": "Normal stress",
                "message": "오늘 일이 많아서 힘들었어요",
                "expected_min_level": RiskLevel.NONE,
                "expected_action": False,
            },
        ],
    )
    async def test_realistic_scenarios(self, crisis_detector, scenario):
        """Test realistic crisis detection scenarios"""
        # For high risk that requires GPT, mock the response
        if scenario["expected_min_level"] in [RiskLevel.HIGH, RiskLevel.MEDIUM]:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.function_call = Mock()
            mock_response.choices[0].message.function_call.arguments = f'''
            {{
                "risk_level": "{scenario["expected_min_level"].value}",
                "reasoning": "테스트 시나리오",
                "immediate_action_needed": {str(scenario["expected_action"]).lower()},
                "suggested_resources": ["1393"],
                "confidence": 0.85
            }}
            '''

            with patch.object(
                crisis_detector.client.chat.completions,
                "create",
                return_value=mock_response,
            ):
                result = await crisis_detector.detect(scenario["message"])
        else:
            result = await crisis_detector.detect(scenario["message"])

        # Verify expectations
        print(f"\nScenario: {scenario['name']}")
        print(f"Detected level: {result['risk_level']}")
        print(f"Expected min level: {scenario['expected_min_level']}")

        # Check minimum risk level
        risk_order = {
            RiskLevel.NONE: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }

        actual_level = RiskLevel(result["risk_level"])
        assert (
            risk_order[actual_level] >= risk_order[scenario["expected_min_level"]]
        ), f"Expected at least {scenario['expected_min_level']}, got {actual_level}"


# ==============================================================================
# Performance Tests
# ==============================================================================


class TestPerformance:
    """Test performance characteristics"""

    def test_keyword_detection_speed(self, crisis_detector, benchmark):
        """Test that keyword detection is fast"""

        def detect_keywords():
            return crisis_detector._keyword_detection("죽고 싶어요")

        # Should complete in less than 1ms
        result = benchmark(detect_keywords)
        assert result["risk_level"] == RiskLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_handles_long_messages(self, crisis_detector):
        """Test that system handles long messages"""
        long_message = "요즘 힘들어요. " * 500 + "죽고 싶어요"

        result = await crisis_detector.detect(long_message)

        assert result["risk_level"] == RiskLevel.CRITICAL


# ==============================================================================
# Edge Cases
# ==============================================================================


class TestEdgeCases:
    """Test edge cases and unusual inputs"""

    @pytest.mark.asyncio
    async def test_empty_message(self, crisis_detector):
        """Test empty message handling"""
        result = await crisis_detector.detect("")

        assert result["risk_level"] == RiskLevel.NONE
        assert not result["immediate_action_needed"]

    @pytest.mark.asyncio
    async def test_special_characters(self, crisis_detector):
        """Test messages with special characters"""
        message = "!@#$%^&*() 죽고 싶어요 !@#$%"

        result = await crisis_detector.detect(message)

        assert result["risk_level"] == RiskLevel.CRITICAL

    @pytest.mark.asyncio
    async def test_unicode_characters(self, crisis_detector):
        """Test Unicode emoji and special characters"""
        message = "😢😭 죽고 싶어요 💔"

        result = await crisis_detector.detect(message)

        assert result["risk_level"] == RiskLevel.CRITICAL

    def test_get_higher_risk_level(self, crisis_detector):
        """Test risk level comparison"""
        assert (
            crisis_detector._get_higher_risk_level(RiskLevel.HIGH, RiskLevel.MEDIUM)
            == RiskLevel.HIGH
        )
        assert (
            crisis_detector._get_higher_risk_level(RiskLevel.NONE, RiskLevel.CRITICAL)
            == RiskLevel.CRITICAL
        )
        assert (
            crisis_detector._get_higher_risk_level(RiskLevel.LOW, RiskLevel.LOW)
            == RiskLevel.LOW
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
