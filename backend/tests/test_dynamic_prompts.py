"""
Tests for Dynamic Prompt System
동적 프롬프트 시스템 테스트

Run with: pytest tests/test_dynamic_prompts.py -v
"""

import pytest
from app.services.dynamic_prompt_service import (
    DynamicPromptService,
    EmotionDetector,
    EmotionType,
    EmotionIntensity,
    PromptLibrary
)
from app.services.crisis_detector_enhanced import CSSRSLevel
from app.services.age_based_counseling import AgeGroup
from app.services.cbt_stage_service import CBTStage


# ============================================================================
# Emotion Detection Tests
# ============================================================================

class TestEmotionDetector:
    """Test emotion detection functionality"""

    def setup_method(self):
        self.detector = EmotionDetector()

    def test_anxiety_detection_high(self):
        """Test high intensity anxiety detection"""
        message = "너무 불안하고 공황이 올 것 같아요"
        emotion, intensity = self.detector.detect_emotion(message)

        assert emotion == EmotionType.ANXIETY
        assert intensity >= EmotionIntensity.HIGH

    def test_anxiety_detection_moderate(self):
        """Test moderate anxiety detection"""
        message = "요즘 좀 불안하고 걱정돼요"
        emotion, intensity = self.detector.detect_emotion(message)

        assert emotion == EmotionType.ANXIETY
        assert intensity >= EmotionIntensity.LOW

    def test_depression_detection_high(self):
        """Test high intensity depression detection"""
        message = "삶의 의미가 없고 완전히 희망이 없어요"
        emotion, intensity = self.detector.detect_emotion(message)

        assert emotion == EmotionType.DEPRESSION
        assert intensity >= EmotionIntensity.HIGH

    def test_depression_detection_moderate(self):
        """Test moderate depression detection"""
        message = "요즘 우울하고 무기력해요"
        emotion, intensity = self.detector.detect_emotion(message)

        assert emotion == EmotionType.DEPRESSION
        assert intensity >= EmotionIntensity.MODERATE

    def test_anger_detection(self):
        """Test anger detection"""
        message = "너무 화나고 짜증나서 폭발할 것 같아요"
        emotion, intensity = self.detector.detect_emotion(message)

        assert emotion == EmotionType.ANGER
        assert intensity >= EmotionIntensity.MODERATE

    def test_neutral_detection(self):
        """Test neutral state detection"""
        message = "오늘은 그냥 평범한 하루였어요"
        emotion, intensity = self.detector.detect_emotion(message)

        assert emotion == EmotionType.NEUTRAL
        assert intensity == EmotionIntensity.MINIMAL

    def test_multiple_emotions_strongest_wins(self):
        """Test that strongest emotion is detected when multiple present"""
        message = "조금 불안하지만 극도로 우울해요"
        emotion, intensity = self.detector.detect_emotion(message)

        # Depression should win (higher intensity keywords)
        assert emotion == EmotionType.DEPRESSION


# ============================================================================
# Prompt Library Tests
# ============================================================================

class TestPromptLibrary:
    """Test prompt library completeness"""

    def setup_method(self):
        self.library = PromptLibrary()

    def test_crisis_prompt_exists(self):
        """Test crisis intervention prompt exists"""
        assert hasattr(self.library, 'CRISIS_INTERVENTION')
        assert len(self.library.CRISIS_INTERVENTION) > 100
        assert "위기 개입" in self.library.CRISIS_INTERVENTION

    def test_teen_prompts_exist(self):
        """Test all teen prompts exist"""
        assert hasattr(self.library, 'TEEN_ASSESSMENT_ANXIETY')
        assert hasattr(self.library, 'TEEN_ASSESSMENT_DEPRESSION')
        assert hasattr(self.library, 'TEEN_APPLICATION_ANGER')
        assert hasattr(self.library, 'TEEN_SKILLS_ANXIETY')

    def test_adult_prompts_exist(self):
        """Test all adult prompts exist"""
        assert hasattr(self.library, 'ADULT_ASSESSMENT_ANXIETY')
        assert hasattr(self.library, 'ADULT_SKILLS_DEPRESSION')
        assert hasattr(self.library, 'ADULT_APPLICATION_ANXIETY')
        assert hasattr(self.library, 'ADULT_MAINTENANCE_NEUTRAL')

    def test_default_prompt_exists(self):
        """Test default fallback prompt exists"""
        assert hasattr(self.library, 'DEFAULT_GENERAL')
        assert "심리상담사" in self.library.DEFAULT_GENERAL

    def test_prompt_language_korean(self):
        """Test all prompts are in Korean"""
        prompts_to_check = [
            self.library.CRISIS_INTERVENTION,
            self.library.TEEN_ASSESSMENT_ANXIETY,
            self.library.ADULT_SKILLS_DEPRESSION
        ]

        for prompt in prompts_to_check:
            # Check for Korean characters (Hangul)
            assert any('\uac00' <= char <= '\ud7a3' for char in prompt)

    def test_prompt_minimum_length(self):
        """Test prompts have reasonable length"""
        prompts = [
            self.library.CRISIS_INTERVENTION,
            self.library.TEEN_ASSESSMENT_ANXIETY,
            self.library.ADULT_SKILLS_DEPRESSION,
            self.library.DEFAULT_GENERAL
        ]

        for prompt in prompts:
            assert len(prompt) > 200  # At least 200 characters


# ============================================================================
# Prompt Selection Tests
# ============================================================================

class TestPromptSelection:
    """Test prompt selection logic"""

    def setup_method(self):
        self.service = DynamicPromptService(openai_client=None)

    @pytest.mark.asyncio
    async def test_crisis_override_priority(self):
        """Test crisis prompt overrides all other factors"""
        result = await self.service.select_prompt(
            conversation_context={"messages": []},
            crisis_level=CSSRSLevel.LEVEL_4_IMMINENT,
            age_group=AgeGroup.ADOLESCENT,
            cbt_stage=CBTStage.ASSESSMENT,
            last_message="죽고 싶어요"
        )

        assert result["prompt_key"] == "CRISIS_INTERVENTION"
        assert result["factors"]["crisis_level"] == 4

    @pytest.mark.asyncio
    async def test_teen_anxiety_assessment(self):
        """Test teen anxiety assessment prompt selection"""
        result = await self.service.select_prompt(
            conversation_context={"messages": [{"content": "너무 불안해요", "role": "user"}]},
            crisis_level=CSSRSLevel.LEVEL_0_SAFE,
            age_group=AgeGroup.ADOLESCENT,
            cbt_stage=CBTStage.ASSESSMENT,
            last_message="학교 가는 게 너무 불안해요"
        )

        assert result["prompt_key"] == "TEEN_ASSESSMENT_ANXIETY"
        assert result["factors"]["age_group"] == "adolescent"
        assert result["factors"]["emotion"] == "anxiety"

    @pytest.mark.asyncio
    async def test_adult_depression_skills(self):
        """Test adult depression skills prompt selection"""
        result = await self.service.select_prompt(
            conversation_context={"messages": [{"content": "우울해요", "role": "user"}]},
            crisis_level=CSSRSLevel.LEVEL_0_SAFE,
            age_group=AgeGroup.ADULT,
            cbt_stage=CBTStage.SKILLS_ACQUISITION,
            last_message="계속 우울한 생각만 들어요"
        )

        assert result["prompt_key"] == "ADULT_SKILLS_DEPRESSION"
        assert result["factors"]["age_group"] == "adult"
        assert result["factors"]["cbt_stage"] == 3

    @pytest.mark.asyncio
    async def test_teen_anger_application(self):
        """Test teen anger application prompt selection"""
        result = await self.service.select_prompt(
            conversation_context={"messages": [{"content": "화나요", "role": "user"}]},
            crisis_level=CSSRSLevel.LEVEL_0_SAFE,
            age_group=AgeGroup.ADOLESCENT,
            cbt_stage=CBTStage.SKILLS_APPLICATION,
            last_message="친구한테 너무 화나서 때리고 싶어요"
        )

        assert result["prompt_key"] == "TEEN_APPLICATION_ANGER"
        assert result["factors"]["emotion"] == "anger"

    @pytest.mark.asyncio
    async def test_adult_maintenance_neutral(self):
        """Test adult maintenance neutral prompt selection"""
        result = await self.service.select_prompt(
            conversation_context={"messages": [{"content": "좋아요", "role": "user"}]},
            crisis_level=CSSRSLevel.LEVEL_0_SAFE,
            age_group=AgeGroup.ADULT,
            cbt_stage=CBTStage.GENERALIZATION,
            last_message="요즘 많이 좋아졌어요"
        )

        assert result["prompt_key"] == "ADULT_MAINTENANCE_NEUTRAL"
        assert result["factors"]["cbt_stage"] == 5

    @pytest.mark.asyncio
    async def test_fallback_to_default(self):
        """Test fallback to default prompt when factors are None"""
        result = await self.service.select_prompt(
            conversation_context={"messages": []},
            crisis_level=None,
            age_group=None,
            cbt_stage=None,
            last_message="안녕하세요"
        )

        # Should not fail, should use some prompt
        assert result["selected_prompt"] is not None
        assert len(result["selected_prompt"]) > 0


# ============================================================================
# Prompt Key Construction Tests
# ============================================================================

class TestPromptKeyConstruction:
    """Test prompt key building logic"""

    def setup_method(self):
        self.service = DynamicPromptService(openai_client=None)

    def test_teen_assessment_anxiety_key(self):
        """Test key construction for teen assessment anxiety"""
        key = self.service._build_prompt_key(
            age_group=AgeGroup.ADOLESCENT,
            cbt_stage=CBTStage.ASSESSMENT,
            emotion=EmotionType.ANXIETY
        )

        assert key == "TEEN_ASSESSMENT_ANXIETY"

    def test_adult_skills_depression_key(self):
        """Test key construction for adult skills depression"""
        key = self.service._build_prompt_key(
            age_group=AgeGroup.ADULT,
            cbt_stage=CBTStage.SKILLS_ACQUISITION,
            emotion=EmotionType.DEPRESSION
        )

        assert key == "ADULT_SKILLS_DEPRESSION"

    def test_teen_application_anger_key(self):
        """Test key construction for teen application anger"""
        key = self.service._build_prompt_key(
            age_group=AgeGroup.ADOLESCENT,
            cbt_stage=CBTStage.SKILLS_APPLICATION,
            emotion=EmotionType.ANGER
        )

        assert key == "TEEN_APPLICATION_ANGER"

    def test_adult_maintenance_neutral_key(self):
        """Test key construction for adult maintenance neutral"""
        key = self.service._build_prompt_key(
            age_group=AgeGroup.ADULT,
            cbt_stage=CBTStage.GENERALIZATION,
            emotion=EmotionType.NEUTRAL
        )

        assert key == "ADULT_MAINTENANCE_NEUTRAL"

    def test_emotion_mapping_sadness_to_depression(self):
        """Test sadness maps to depression"""
        key = self.service._build_prompt_key(
            age_group=AgeGroup.ADULT,
            cbt_stage=CBTStage.ASSESSMENT,
            emotion=EmotionType.SADNESS
        )

        # Sadness should map to DEPRESSION in key
        assert "DEPRESSION" in key

    def test_emotion_mapping_fear_to_anxiety(self):
        """Test fear maps to anxiety"""
        key = self.service._build_prompt_key(
            age_group=AgeGroup.ADOLESCENT,
            cbt_stage=CBTStage.SKILLS_ACQUISITION,
            emotion=EmotionType.FEAR
        )

        # Fear should map to ANXIETY in key
        assert "ANXIETY" in key


# ============================================================================
# Integration Tests
# ============================================================================

class TestDynamicPromptIntegration:
    """Integration tests for complete system"""

    def setup_method(self):
        self.service = DynamicPromptService(openai_client=None)

    @pytest.mark.asyncio
    async def test_complete_flow_crisis_scenario(self):
        """Test complete flow for crisis scenario"""
        # Simulate crisis message
        context = {
            "messages": [
                {"role": "user", "content": "더 이상 살고 싶지 않아요. 유서도 썼어요."}
            ]
        }

        result = await self.service.select_prompt(
            conversation_context=context,
            age_group=AgeGroup.ADULT,
            cbt_stage=CBTStage.ASSESSMENT,
            last_message="더 이상 살고 싶지 않아요. 유서도 썼어요."
        )

        # Should detect crisis and override
        assert "CRISIS" in result["prompt_key"]
        assert "위기" in result["selected_prompt"]
        assert "1393" in result["selected_prompt"]  # Crisis hotline

    @pytest.mark.asyncio
    async def test_complete_flow_teen_anxiety(self):
        """Test complete flow for teen anxiety"""
        context = {
            "messages": [
                {"role": "user", "content": "학교 가기가 너무 불안하고 무서워요"}
            ]
        }

        result = await self.service.select_prompt(
            conversation_context=context,
            age_group=AgeGroup.ADOLESCENT,
            cbt_stage=CBTStage.ASSESSMENT,
            last_message="학교 가기가 너무 불안하고 무서워요"
        )

        assert result["prompt_key"] == "TEEN_ASSESSMENT_ANXIETY"
        assert "청소년" in result["selected_prompt"]
        assert "학교" in result["selected_prompt"] or "친구" in result["selected_prompt"]

    @pytest.mark.asyncio
    async def test_complete_flow_adult_depression_skills(self):
        """Test complete flow for adult depression skills"""
        context = {
            "messages": [
                {"role": "user", "content": "부정적인 생각을 어떻게 바꿔야 할까요?"}
            ]
        }

        result = await self.service.select_prompt(
            conversation_context=context,
            age_group=AgeGroup.ADULT,
            cbt_stage=CBTStage.SKILLS_ACQUISITION,
            last_message="부정적인 생각을 어떻게 바꿔야 할까요?"
        )

        assert result["prompt_key"] == "ADULT_SKILLS_DEPRESSION"
        assert "CBT" in result["selected_prompt"] or "인지행동" in result["selected_prompt"]
        assert "사고" in result["selected_prompt"]

    @pytest.mark.asyncio
    async def test_reasoning_generation(self):
        """Test that reasoning is generated correctly"""
        result = await self.service.select_prompt(
            conversation_context={"messages": []},
            age_group=AgeGroup.ADOLESCENT,
            cbt_stage=CBTStage.ASSESSMENT,
            last_message="불안해요"
        )

        # Reasoning should be in Korean and describe the selection
        assert result["reasoning"] is not None
        assert len(result["reasoning"]) > 0
        # Should contain Korean characters
        assert any('\uac00' <= char <= '\ud7a3' for char in result["reasoning"])

    @pytest.mark.asyncio
    async def test_factors_completeness(self):
        """Test that all factors are included in result"""
        result = await self.service.select_prompt(
            conversation_context={"messages": []},
            age_group=AgeGroup.ADULT,
            cbt_stage=CBTStage.SKILLS_ACQUISITION,
            last_message="우울해요"
        )

        # Check all required factors are present
        assert "crisis_level" in result["factors"]
        assert "age_group" in result["factors"]
        assert "cbt_stage" in result["factors"]
        assert "emotion" in result["factors"]
        assert "intensity" in result["factors"]


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    def setup_method(self):
        self.service = DynamicPromptService(openai_client=None)

    @pytest.mark.asyncio
    async def test_empty_message(self):
        """Test handling of empty message"""
        result = await self.service.select_prompt(
            conversation_context={"messages": []},
            age_group=AgeGroup.ADULT,
            cbt_stage=CBTStage.ASSESSMENT,
            last_message=""
        )

        # Should not crash, should return valid prompt
        assert result["selected_prompt"] is not None

    @pytest.mark.asyncio
    async def test_none_age_group(self):
        """Test handling when age group is None"""
        result = await self.service.select_prompt(
            conversation_context={"messages": []},
            age_group=None,
            cbt_stage=CBTStage.ASSESSMENT,
            last_message="도와주세요"
        )

        # Should default to adult or general
        assert result["selected_prompt"] is not None

    @pytest.mark.asyncio
    async def test_none_cbt_stage(self):
        """Test handling when CBT stage is None"""
        result = await self.service.select_prompt(
            conversation_context={"messages": []},
            age_group=AgeGroup.ADULT,
            cbt_stage=None,
            last_message="도와주세요"
        )

        # Should default to assessment
        assert result["selected_prompt"] is not None

    def test_very_long_message(self):
        """Test emotion detection on very long message"""
        detector = EmotionDetector()
        long_message = "불안해요 " * 1000  # 1000 repetitions

        emotion, intensity = detector.detect_emotion(long_message)

        # Should still detect anxiety
        assert emotion == EmotionType.ANXIETY

    def test_message_with_special_characters(self):
        """Test emotion detection with special characters"""
        detector = EmotionDetector()
        message = "!@#$% 너무 불안해요 ㅠㅠㅠ 😢😰"

        emotion, intensity = detector.detect_emotion(message)

        # Should still detect anxiety despite special chars
        assert emotion == EmotionType.ANXIETY


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test performance characteristics"""

    def setup_method(self):
        self.service = DynamicPromptService(openai_client=None)
        self.detector = EmotionDetector()

    def test_emotion_detection_speed(self):
        """Test emotion detection is fast enough"""
        import time

        message = "너무 불안하고 걱정돼서 잠을 못 자요"

        start = time.time()
        for _ in range(100):
            self.detector.detect_emotion(message)
        duration = time.time() - start

        # Should process 100 messages in under 100ms
        assert duration < 0.1, f"Too slow: {duration}s for 100 detections"

    @pytest.mark.asyncio
    async def test_prompt_selection_speed(self):
        """Test prompt selection is fast enough"""
        import time

        start = time.time()
        for _ in range(100):
            await self.service.select_prompt(
                conversation_context={"messages": []},
                age_group=AgeGroup.ADULT,
                cbt_stage=CBTStage.ASSESSMENT,
                last_message="안녕하세요"
            )
        duration = time.time() - start

        # Should process 100 selections in under 200ms
        assert duration < 0.2, f"Too slow: {duration}s for 100 selections"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
