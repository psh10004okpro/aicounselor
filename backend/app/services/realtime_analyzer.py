"""
Real-time Message Analysis Service
실시간 메시지 분석 서비스 (GPT-4 기반)

This service provides comprehensive message analysis using GPT-4:
- Emotion detection (primary + secondary + intensity)
- Crisis level assessment (C-SSRS 0-4)
- CBT stage suggestion
- Recommended therapeutic approach

Author: AI Counselor System
Date: 2025-11-05
"""

import json
from typing import Dict, List, Optional
from openai import AsyncOpenAI
from enum import Enum

from app.core.config import settings
from app.services.openai_client import OpenAIClientFactory


class CBTStageRecommendation(str, Enum):
    """CBT stage recommendations from analysis"""
    ASSESSMENT = "assessment"
    RECONCEPTUALIZATION = "reconceptualization"
    SKILLS = "skills"
    APPLICATION = "application"
    MAINTENANCE = "maintenance"
    TERMINATION = "termination"


class RealtimeMessageAnalyzer:
    """
    GPT-4 powered real-time message analyzer
    GPT-4 기반 실시간 메시지 분석기
    """

    def __init__(self, openai_client: Optional[AsyncOpenAI] = None):
        """Initialize with OpenAI client"""
        self.client = openai_client or OpenAIClientFactory.get_client()

    async def analyze_message(
        self,
        message: str,
        conversation_context: Optional[List[Dict]] = None,
        user_profile: Optional[Dict] = None
    ) -> Dict:
        """
        Comprehensive message analysis using GPT-4

        Args:
            message: User message to analyze
            conversation_context: Previous messages for context
            user_profile: User information (age, history, etc.)

        Returns:
            {
                "emotions": {
                    "primary": str,
                    "secondary": List[str],
                    "intensity": float (0.0-1.0)
                },
                "crisis_level": int (0-4),
                "crisis_indicators": List[str],
                "session_stage_suggestion": str,
                "recommended_approach": str,
                "confidence": float
            }
        """
        # Build analysis prompt
        analysis_prompt = self._build_analysis_prompt(
            message=message,
            conversation_context=conversation_context,
            user_profile=user_profile
        )

        try:
            # Call GPT-4 with structured output
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 심리상담 전문 분석가입니다. 메시지를 분석하여 정확한 JSON 형식으로 응답합니다."
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=800
            )

            # Parse JSON response
            analysis = json.loads(response.choices[0].message.content)

            # Validate and normalize response
            normalized_analysis = self._normalize_analysis(analysis)

            return normalized_analysis

        except Exception as e:
            print(f"❌ GPT-4 analysis error: {e}")
            # Return safe fallback
            return self._get_fallback_analysis()

    def _build_analysis_prompt(
        self,
        message: str,
        conversation_context: Optional[List[Dict]],
        user_profile: Optional[Dict]
    ) -> str:
        """Build comprehensive analysis prompt"""

        # Context section
        context_str = ""
        if conversation_context and len(conversation_context) > 0:
            recent_messages = conversation_context[-3:]  # Last 3 messages
            context_str = "\n\n**이전 대화 맥락:**\n"
            for msg in recent_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                context_str += f"- {role}: {content}\n"

        # User profile section
        profile_str = ""
        if user_profile:
            age = user_profile.get("age", "unknown")
            session_count = user_profile.get("session_count", 0)
            profile_str = f"\n\n**사용자 정보:**\n- 연령: {age}\n- 세션 횟수: {session_count}"

        # Build full prompt
        prompt = f"""
다음 메시지를 심리상담 관점에서 종합 분석하세요.
{context_str}{profile_str}

**현재 메시지:** "{message}"

다음 JSON 형식으로 정확히 반환하세요:

{{
    "emotions": {{
        "primary": "주요 감정 (anxiety/depression/anger/fear/sadness/joy/shame/guilt/neutral 중 하나)",
        "secondary": ["부차적 감정1", "부차적 감정2"],
        "intensity": 0.0에서 1.0 사이의 감정 강도 (0.0=없음, 1.0=극도)
    }},
    "crisis_level": 0에서 4 사이의 위기 수준 (0=안전, 1=낮음, 2=중간, 3=높음, 4=긴급),
    "crisis_indicators": ["위기 키워드1", "위기 키워드2"] 또는 빈 배열,
    "session_stage_suggestion": "적합한 CBT 단계 (assessment/reconceptualization/skills/application/maintenance/termination 중 하나)",
    "recommended_approach": "이 메시지에 대한 권장 상담 접근법 (한 문장)",
    "confidence": 0.0에서 1.0 사이의 분석 신뢰도
}}

**분석 가이드라인:**

1. **감정 (emotions):**
   - primary: 가장 두드러진 감정 하나
   - secondary: 추가로 감지되는 감정들 (최대 2-3개)
   - intensity: 감정의 강도를 객관적으로 평가

2. **위기 수준 (crisis_level):**
   - 0: 안전, 위기 신호 없음
   - 1: 경미한 스트레스, 일반적 고민
   - 2: 중간 수준 고통, 지속적 불편감
   - 3: 높은 위험, 자해/자살 생각 표현
   - 4: 긴급 상황, 즉각적 위험

3. **CBT 단계 제안 (session_stage_suggestion):**
   - assessment: 초기 평가 필요 (첫 세션 또는 새로운 문제)
   - reconceptualization: 문제 재정의 필요
   - skills: 대처 기술 교육 필요
   - application: 학습한 기법 적용 및 연습
   - maintenance: 유지 및 재발 방지
   - termination: 종결 고려 가능

4. **권장 접근법 (recommended_approach):**
   - 이 메시지에 어떻게 반응하면 좋을지 간단히 제안
   - 예: "공감과 안전 확인 후 구체적 상황 탐색"

5. **신뢰도 (confidence):**
   - 메시지가 명확할수록 높은 신뢰도
   - 애매하거나 짧은 메시지는 낮은 신뢰도

JSON만 반환하고 다른 설명은 포함하지 마세요.
"""

        return prompt

    def _normalize_analysis(self, raw_analysis: Dict) -> Dict:
        """Normalize and validate GPT-4 analysis response"""

        # Ensure all required fields exist
        normalized = {
            "emotions": raw_analysis.get("emotions", {
                "primary": "neutral",
                "secondary": [],
                "intensity": 0.5
            }),
            "crisis_level": max(0, min(4, raw_analysis.get("crisis_level", 0))),
            "crisis_indicators": raw_analysis.get("crisis_indicators", []),
            "session_stage_suggestion": raw_analysis.get("session_stage_suggestion", "assessment"),
            "recommended_approach": raw_analysis.get("recommended_approach", "공감적 경청 및 탐색"),
            "confidence": max(0.0, min(1.0, raw_analysis.get("confidence", 0.7)))
        }

        # Validate emotions
        emotions = normalized["emotions"]
        if not isinstance(emotions.get("primary"), str):
            emotions["primary"] = "neutral"
        if not isinstance(emotions.get("secondary"), list):
            emotions["secondary"] = []
        if not isinstance(emotions.get("intensity"), (int, float)):
            emotions["intensity"] = 0.5
        else:
            emotions["intensity"] = max(0.0, min(1.0, float(emotions["intensity"])))

        # Validate stage suggestion
        valid_stages = ["assessment", "reconceptualization", "skills", "application", "maintenance", "termination"]
        if normalized["session_stage_suggestion"] not in valid_stages:
            normalized["session_stage_suggestion"] = "assessment"

        return normalized

    def _get_fallback_analysis(self) -> Dict:
        """Return safe fallback analysis if GPT-4 fails"""
        return {
            "emotions": {
                "primary": "neutral",
                "secondary": [],
                "intensity": 0.5
            },
            "crisis_level": 0,
            "crisis_indicators": [],
            "session_stage_suggestion": "assessment",
            "recommended_approach": "경청하며 내담자의 이야기를 충분히 들어주세요",
            "confidence": 0.3,
            "error": "Analysis failed, using fallback"
        }

    async def batch_analyze_conversation(
        self,
        messages: List[str],
        user_profile: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Analyze multiple messages in batch

        Args:
            messages: List of messages to analyze
            user_profile: User profile information

        Returns:
            List of analysis results for each message
        """
        results = []

        for i, message in enumerate(messages):
            # Use previous messages as context
            context = [{"role": "user", "content": msg} for msg in messages[:i]]

            analysis = await self.analyze_message(
                message=message,
                conversation_context=context,
                user_profile=user_profile
            )

            results.append(analysis)

        return results


class EnhancedPromptSelector:
    """
    Enhanced prompt selector using GPT-4 analysis
    GPT-4 분석 기반 향상된 프롬프트 선택기
    """

    def __init__(
        self,
        message_analyzer: RealtimeMessageAnalyzer,
        prompt_library: Dict[str, str]
    ):
        """
        Initialize with message analyzer and prompt library

        Args:
            message_analyzer: RealtimeMessageAnalyzer instance
            prompt_library: Dictionary of prompt templates
        """
        self.analyzer = message_analyzer
        self.prompt_library = prompt_library

    async def select_dynamic_prompt(
        self,
        user_message: str,
        user_profile: Dict,
        conversation_history: List[Dict],
        memory_context: str = ""
    ) -> Dict:
        """
        Select optimal prompt based on GPT-4 analysis

        Args:
            user_message: Current user message
            user_profile: User profile (age, session_count, etc.)
            conversation_history: Previous conversation messages
            memory_context: Retrieved context from memory system

        Returns:
            {
                "selected_prompt": str,
                "prompt_key": str,
                "analysis": Dict,
                "reasoning": str
            }
        """

        # 1. Analyze message with GPT-4
        analysis = await self.analyzer.analyze_message(
            message=user_message,
            conversation_context=conversation_history,
            user_profile=user_profile
        )

        # 2. Check crisis level (HIGHEST PRIORITY)
        if analysis["crisis_level"] >= 3:
            prompt_key = "crisis_level_3"
            selected_prompt = self.prompt_library.get(prompt_key, self.prompt_library["default"])

            return {
                "selected_prompt": selected_prompt.format(retrieved_context=memory_context),
                "prompt_key": prompt_key,
                "analysis": analysis,
                "reasoning": f"Crisis level {analysis['crisis_level']} - immediate intervention"
            }

        # 3. Determine age prefix
        age = user_profile.get("age", 25)
        age_prefix = "teen" if age < 19 else "adult"

        # 4. Get stage from analysis
        stage = analysis["session_stage_suggestion"]

        # 5. Get primary emotion
        emotion = analysis["emotions"]["primary"]

        # 6. Build prompt key
        prompt_key = f"{age_prefix}_{stage}_{emotion}"

        # 7. Try to get prompt, fallback if not found
        selected_prompt = self.prompt_library.get(prompt_key)

        if selected_prompt is None:
            # Try with neutral emotion
            prompt_key = f"{age_prefix}_{stage}_neutral"
            selected_prompt = self.prompt_library.get(prompt_key)

        if selected_prompt is None:
            # Final fallback
            prompt_key = "default"
            selected_prompt = self.prompt_library.get(prompt_key, "")

        # 8. Format with context
        final_prompt = selected_prompt.format(retrieved_context=memory_context)

        # 9. Generate reasoning
        reasoning = self._generate_reasoning(age_prefix, stage, emotion, analysis)

        return {
            "selected_prompt": final_prompt,
            "prompt_key": prompt_key,
            "analysis": analysis,
            "reasoning": reasoning
        }

    def _generate_reasoning(
        self,
        age_prefix: str,
        stage: str,
        emotion: str,
        analysis: Dict
    ) -> str:
        """Generate human-readable reasoning"""

        parts = []

        # Age
        age_label = "청소년" if age_prefix == "teen" else "성인"
        parts.append(age_label)

        # Stage
        stage_labels = {
            "assessment": "초기 평가",
            "reconceptualization": "재개념화",
            "skills": "기술 습득",
            "application": "기술 적용",
            "maintenance": "유지 관리",
            "termination": "종결"
        }
        parts.append(stage_labels.get(stage, stage))

        # Emotion
        emotion_labels = {
            "anxiety": "불안",
            "depression": "우울",
            "anger": "분노",
            "fear": "두려움",
            "sadness": "슬픔",
            "joy": "기쁨",
            "shame": "수치심",
            "guilt": "죄책감",
            "neutral": "중립"
        }
        emotion_label = emotion_labels.get(emotion, emotion)
        parts.append(f"{emotion_label} 감정")

        # Intensity
        intensity = analysis["emotions"].get("intensity", 0.5)
        if intensity >= 0.7:
            parts.append("(강도 높음)")

        # Confidence
        confidence = analysis.get("confidence", 0.7)
        confidence_label = "높음" if confidence >= 0.8 else "중간" if confidence >= 0.5 else "낮음"

        reasoning = " + ".join(parts) + f" | GPT-4 분석 신뢰도: {confidence_label}"

        return reasoning
