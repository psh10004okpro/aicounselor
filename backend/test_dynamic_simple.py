"""
Simple manual test for dynamic prompt system
"""

import asyncio
from app.services.dynamic_prompt_service import (
    DynamicPromptService,
    EmotionDetector,
    EmotionType,
    PromptLibrary
)
from app.services.age_based_counseling import AgeGroup
from app.services.cbt_stage_service import CBTStage
from app.services.crisis_detector_enhanced import CSSRSLevel


def test_emotion_detection():
    """Test emotion detection"""
    print("=" * 60)
    print("Testing Emotion Detection")
    print("=" * 60)

    detector = EmotionDetector()

    test_cases = [
        ("너무 불안하고 공황이 올 것 같아요", EmotionType.ANXIETY),
        ("삶의 의미가 없고 우울해요", EmotionType.DEPRESSION),
        ("너무 화나고 짜증나요", EmotionType.ANGER),
        ("평범한 하루였어요", EmotionType.NEUTRAL),
    ]

    for message, expected_emotion in test_cases:
        emotion, intensity = detector.detect_emotion(message)
        status = "✅" if emotion == expected_emotion else "❌"
        print(f"{status} Message: {message[:30]}...")
        print(f"   Expected: {expected_emotion.value}, Got: {emotion.value}, Intensity: {intensity}")

    print()


def test_prompt_library():
    """Test prompt library completeness"""
    print("=" * 60)
    print("Testing Prompt Library")
    print("=" * 60)

    library = PromptLibrary()

    prompts_to_check = [
        "CRISIS_INTERVENTION",
        "TEEN_ASSESSMENT_ANXIETY",
        "TEEN_ASSESSMENT_DEPRESSION",
        "ADULT_SKILLS_DEPRESSION",
        "ADULT_MAINTENANCE_NEUTRAL",
        "DEFAULT_GENERAL"
    ]

    for prompt_name in prompts_to_check:
        if hasattr(library, prompt_name):
            prompt = getattr(library, prompt_name)
            print(f"✅ {prompt_name}: {len(prompt)} characters")
        else:
            print(f"❌ {prompt_name}: NOT FOUND")

    print()


async def test_prompt_selection():
    """Test prompt selection logic"""
    print("=" * 60)
    print("Testing Prompt Selection")
    print("=" * 60)

    service = DynamicPromptService(openai_client=None)

    test_scenarios = [
        {
            "name": "Crisis Scenario",
            "age_group": AgeGroup.ADULT,
            "cbt_stage": CBTStage.ASSESSMENT,
            "message": "죽고 싶어요",
            "crisis_level": CSSRSLevel.LEVEL_4_IMMINENT,
            "expected_key": "CRISIS_INTERVENTION"
        },
        {
            "name": "Teen Anxiety Assessment",
            "age_group": AgeGroup.ADOLESCENT,
            "cbt_stage": CBTStage.ASSESSMENT,
            "message": "학교 가는 게 너무 불안해요",
            "crisis_level": CSSRSLevel.LEVEL_0_SAFE,
            "expected_key": "TEEN_ASSESSMENT_ANXIETY"
        },
        {
            "name": "Adult Depression Skills",
            "age_group": AgeGroup.ADULT,
            "cbt_stage": CBTStage.SKILLS_ACQUISITION,
            "message": "계속 우울한 생각만 들어요",
            "crisis_level": CSSRSLevel.LEVEL_0_SAFE,
            "expected_key": "ADULT_SKILLS_DEPRESSION"
        },
        {
            "name": "Teen Anger Application",
            "age_group": AgeGroup.ADOLESCENT,
            "cbt_stage": CBTStage.SKILLS_APPLICATION,
            "message": "친구한테 너무 화나요",
            "crisis_level": CSSRSLevel.LEVEL_0_SAFE,
            "expected_key": "TEEN_APPLICATION_ANGER"
        },
        {
            "name": "Adult Maintenance",
            "age_group": AgeGroup.ADULT,
            "cbt_stage": CBTStage.GENERALIZATION,
            "message": "요즘 많이 좋아졌어요",
            "crisis_level": CSSRSLevel.LEVEL_0_SAFE,
            "expected_key": "ADULT_MAINTENANCE_NEUTRAL"
        }
    ]

    for scenario in test_scenarios:
        context = {
            "messages": [{"content": scenario["message"], "role": "user"}]
        }

        result = await service.select_prompt(
            conversation_context=context,
            age_group=scenario["age_group"],
            cbt_stage=scenario["cbt_stage"],
            crisis_level=scenario["crisis_level"],
            last_message=scenario["message"]
        )

        status = "✅" if result["prompt_key"] == scenario["expected_key"] else "❌"
        print(f"{status} {scenario['name']}")
        print(f"   Expected: {scenario['expected_key']}")
        print(f"   Got: {result['prompt_key']}")
        print(f"   Reasoning: {result['reasoning']}")
        print()


def test_prompt_key_construction():
    """Test prompt key building"""
    print("=" * 60)
    print("Testing Prompt Key Construction")
    print("=" * 60)

    service = DynamicPromptService(openai_client=None)

    test_cases = [
        {
            "age": AgeGroup.ADOLESCENT,
            "stage": CBTStage.ASSESSMENT,
            "emotion": EmotionType.ANXIETY,
            "expected": "TEEN_ASSESSMENT_ANXIETY"
        },
        {
            "age": AgeGroup.ADULT,
            "stage": CBTStage.SKILLS_ACQUISITION,
            "emotion": EmotionType.DEPRESSION,
            "expected": "ADULT_SKILLS_DEPRESSION"
        },
        {
            "age": AgeGroup.ADOLESCENT,
            "stage": CBTStage.SKILLS_APPLICATION,
            "emotion": EmotionType.ANGER,
            "expected": "TEEN_APPLICATION_ANGER"
        },
        {
            "age": AgeGroup.ADULT,
            "stage": CBTStage.GENERALIZATION,
            "emotion": EmotionType.NEUTRAL,
            "expected": "ADULT_MAINTENANCE_NEUTRAL"
        }
    ]

    for case in test_cases:
        key = service._build_prompt_key(
            age_group=case["age"],
            cbt_stage=case["stage"],
            emotion=case["emotion"]
        )
        status = "✅" if key == case["expected"] else "❌"
        print(f"{status} Expected: {case['expected']}, Got: {key}")

    print()


async def main():
    """Run all tests"""
    print("\n")
    print("🧪 DYNAMIC PROMPT SYSTEM TEST SUITE")
    print("=" * 60)
    print()

    # Run synchronous tests
    test_emotion_detection()
    test_prompt_library()
    test_prompt_key_construction()

    # Run async tests
    await test_prompt_selection()

    print("=" * 60)
    print("✅ All Manual Tests Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
