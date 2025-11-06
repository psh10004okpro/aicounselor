"""Advanced Crisis Detection System with GPT-4 Contextual Analysis"""

import re
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from enum import Enum

from app.core.config import settings
from app.services.openai_client import OpenAIClientFactory


class RiskLevel(str, Enum):
    """Risk level classification"""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CrisisDetectionSystem:
    """
    Advanced 3-stage crisis detection system:
    1. Keyword-based immediate detection
    2. GPT-4 contextual analysis
    3. Structured output evaluation
    """

    # Critical keywords - immediate alert
    CRITICAL_KEYWORDS = [
        # Korean
        "죽고 싶",
        "죽고싶",
        "자살",
        "목숨을 끊",
        "목숨 끊",
        "살아있고 싶지 않",
        "살고 싶지 않",
        "사라지고 싶",
        "사라지고싶",
        "세상을 떠나",
        "자해",
        "손목을 그",
        "뛰어내리",
        "목을 매",
        # English
        "kill myself",
        "end my life",
        "commit suicide",
        "take my own life",
        "want to die",
    ]

    # High risk keywords - requires analysis
    HIGH_RISK_KEYWORDS = [
        # Korean
        "의미없",
        "의미가 없",
        "희망이 없",
        "희망없",
        "미래가 없",
        "끝내고 싶",
        "포기하고 싶",
        "버티기 힘들",
        "더 이상 못",
        "한계",
        "견딜 수 없",
        # English
        "no point",
        "no hope",
        "no future",
        "give up",
        "can't go on",
        "can't take it",
    ]

    def __init__(self):
        self.client = OpenAIClientFactory.get_client()
        self.model = "gpt-4o-mini"  # Use GPT-4o-mini for cost efficiency

    async def detect(
        self, message: str, conversation_history: Optional[List[dict]] = None
    ) -> Dict:
        """
        3-stage crisis detection.

        Args:
            message: Current user message
            conversation_history: Previous messages for context

        Returns:
            Dict containing:
                - risk_level: RiskLevel enum
                - detected_keywords: List of detected keywords
                - reasoning: GPT-4 analysis reasoning
                - immediate_action_needed: bool
                - suggested_resources: List of resources
                - confidence: float (0-1)
        """
        # Stage 1: Immediate keyword detection
        keyword_result = self._keyword_detection(message)

        if keyword_result["risk_level"] == RiskLevel.CRITICAL:
            # Critical keywords found - immediate response
            return await self._create_critical_response(
                keyword_result["detected_keywords"]
            )

        # Stage 2 & 3: GPT-4 contextual analysis with structured output
        if (
            keyword_result["risk_level"] in [RiskLevel.HIGH, RiskLevel.MEDIUM]
            or len(keyword_result["detected_keywords"]) > 0
        ):
            gpt_analysis = await self.contextual_analysis(message, conversation_history)

            # Merge results
            return {
                "risk_level": self._get_higher_risk_level(
                    keyword_result["risk_level"], gpt_analysis["risk_level"]
                ),
                "detected_keywords": keyword_result["detected_keywords"],
                "reasoning": gpt_analysis["reasoning"],
                "immediate_action_needed": gpt_analysis["immediate_action_needed"],
                "suggested_resources": gpt_analysis["suggested_resources"],
                "confidence": gpt_analysis["confidence"],
                "detection_method": "keyword + gpt_contextual",
            }

        # No significant risk detected
        return {
            "risk_level": RiskLevel.NONE,
            "detected_keywords": [],
            "reasoning": "No crisis indicators detected",
            "immediate_action_needed": False,
            "suggested_resources": [],
            "confidence": 0.9,
            "detection_method": "keyword",
        }

    def _keyword_detection(self, message: str) -> Dict:
        """Stage 1: Fast keyword-based detection"""
        message_lower = message.lower()
        detected = []
        risk_level = RiskLevel.NONE

        # Check critical keywords
        for keyword in self.CRITICAL_KEYWORDS:
            if keyword.lower() in message or keyword.lower() in message_lower:
                detected.append(keyword)
                risk_level = RiskLevel.CRITICAL

        # Check high risk keywords if not critical
        if risk_level != RiskLevel.CRITICAL:
            for keyword in self.HIGH_RISK_KEYWORDS:
                if keyword.lower() in message or keyword.lower() in message_lower:
                    detected.append(keyword)
                    if risk_level == RiskLevel.NONE:
                        risk_level = RiskLevel.HIGH

        return {"risk_level": risk_level, "detected_keywords": detected}

    async def contextual_analysis(
        self, message: str, conversation_history: Optional[List[dict]] = None
    ) -> Dict:
        """
        Stage 2 & 3: GPT-4 contextual analysis with structured output.

        Uses OpenAI Function Calling for structured, reliable output.
        """
        # Build context
        context_messages = []

        if conversation_history:
            # Include last few messages for context
            context_messages = conversation_history[-5:]

        context_messages.append({"role": "user", "content": message})

        # Define the function schema for structured output
        function_schema = {
            "name": "assess_crisis_level",
            "description": "Assess the crisis level and suicide risk in the user's message",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "risk_level": {
                        "type": "string",
                        "enum": ["none", "low", "medium", "high", "critical"],
                        "description": "Overall suicide/crisis risk level",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Clear explanation of the assessment in Korean",
                    },
                    "immediate_action_needed": {
                        "type": "boolean",
                        "description": "Whether immediate intervention is required",
                    },
                    "suggested_resources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of appropriate crisis resources",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence in assessment (0-1)",
                        "minimum": 0,
                        "maximum": 1,
                    },
                },
                "required": [
                    "risk_level",
                    "reasoning",
                    "immediate_action_needed",
                    "suggested_resources",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        }

        # System prompt for crisis assessment
        system_prompt = """당신은 전문적인 위기 평가 전문가입니다. 사용자 메시지에서 자살이나 자해 위험을 정확하게 평가하세요.

위험 수준 기준:
- critical: 즉각적인 자살/자해 계획이 있거나 실행 중
- high: 강한 자살 사고와 구체적 고민
- medium: 삶에 대한 절망감이나 죽음에 대한 언급
- low: 힘든 상황이지만 즉각적 위험은 없음
- none: 위기 징후 없음

**매우 중요**: 과잉 진단하지 말고, 실제 위험이 있을 때만 high/critical을 반환하세요.
일상적인 스트레스나 어려움은 low나 none으로 평가하세요.

한국어로 명확하고 간결하게 설명하세요."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *context_messages,
                ],
                functions=[function_schema],
                function_call={"name": "assess_crisis_level"},
                temperature=0.3,  # Lower temperature for consistent assessment
            )

            # Parse function call result
            function_call = response.choices[0].message.function_call
            assessment = json.loads(function_call.arguments)

            return assessment

        except Exception as e:
            print(f"Error in contextual analysis: {e}")
            # Fallback to safe default
            return {
                "risk_level": RiskLevel.MEDIUM,
                "reasoning": "위기 분석 중 오류가 발생했습니다. 안전을 위해 전문가 상담을 권장합니다.",
                "immediate_action_needed": True,
                "suggested_resources": ["1393", "1588-9191"],
                "confidence": 0.5,
            }

    async def _create_critical_response(self, detected_keywords: List[str]) -> Dict:
        """Create immediate critical response"""
        return {
            "risk_level": RiskLevel.CRITICAL,
            "detected_keywords": detected_keywords,
            "reasoning": "위기 키워드가 감지되었습니다. 즉각적인 전문가 개입이 필요합니다.",
            "immediate_action_needed": True,
            "suggested_resources": [
                "자살예방상담전화: 1393",
                "생명의 전화: 1588-9191",
                "정신건강위기상담전화: 1577-0199",
                "응급: 119",
            ],
            "confidence": 1.0,
            "detection_method": "keyword_critical",
        }

    def _get_higher_risk_level(
        self, level1: RiskLevel, level2: RiskLevel
    ) -> RiskLevel:
        """Get the higher of two risk levels"""
        risk_order = {
            RiskLevel.NONE: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }

        # Convert string to RiskLevel if needed
        if isinstance(level1, str):
            level1 = RiskLevel(level1)
        if isinstance(level2, str):
            level2 = RiskLevel(level2)

        return level1 if risk_order[level1] >= risk_order[level2] else level2

    def critical_response(self, assessment: Dict) -> Dict:
        """
        Generate critical response that should be immediately displayed.

        This includes:
        - Emergency contact information
        - Immediate action steps
        - Support resources
        """
        return {
            "action": "IMMEDIATE_INTERVENTION",
            "display_mode": "FULL_SCREEN",
            "message": """
⚠️ **긴급 상황이 감지되었습니다**

당신의 안전이 가장 중요합니다. 지금 즉시 도움을 받아주세요:

**즉시 연락하세요:**
🆘 자살예방상담전화: **1393** (24시간, 무료)
📱 생명의 전화: **1588-9191** (24시간)
💬 정신건강위기상담전화: **1577-0199** (24시간)

**응급 상황:**
🚨 119 (즉시 연락)
🏥 가까운 응급실 방문

당신은 혼자가 아닙니다. 전문가들이 24시간 대기하고 있습니다.
""",
            "chat_disabled": True,
            "assessment": assessment,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def emergency_protocol(
        self, assessment: Dict, user_id: str, conversation_id: str
    ) -> None:
        """
        Execute emergency protocol based on risk level.

        Args:
            assessment: Crisis assessment result
            user_id: User identifier
            conversation_id: Conversation identifier
        """
        risk_level = assessment["risk_level"]

        # Log all crisis events
        await self._log_crisis_event(assessment, user_id, conversation_id)

        if risk_level == RiskLevel.CRITICAL:
            # Critical: Immediate intervention
            await self._critical_intervention(user_id, conversation_id, assessment)

        elif risk_level == RiskLevel.HIGH:
            # High: Alert monitoring team
            await self._high_risk_alert(user_id, conversation_id, assessment)

        elif risk_level == RiskLevel.MEDIUM:
            # Medium: Enhanced monitoring
            await self._medium_risk_monitoring(user_id, conversation_id, assessment)

    async def _log_crisis_event(
        self, assessment: Dict, user_id: str, conversation_id: str
    ) -> None:
        """Log crisis event to database and monitoring systems"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "risk_level": assessment["risk_level"],
            "detected_keywords": assessment.get("detected_keywords", []),
            "reasoning": assessment.get("reasoning", ""),
            "confidence": assessment.get("confidence", 0),
            "immediate_action_needed": assessment.get("immediate_action_needed", False),
        }

        # TODO: Save to database crisis_logs table
        print(f"🚨 CRISIS EVENT LOGGED: {log_entry}")

        # TODO: Send to monitoring system (Sentry, CloudWatch, etc.)
        # await send_to_monitoring_system(log_entry)

    async def _critical_intervention(
        self, user_id: str, conversation_id: str, assessment: Dict
    ) -> None:
        """Critical intervention protocol"""
        print(f"⚠️ CRITICAL INTERVENTION ACTIVATED for user {user_id}")

        # TODO: Implement in production:
        # 1. Notify on-call crisis team immediately
        # 2. Send SMS/email to designated crisis responders
        # 3. Create high-priority ticket in crisis management system
        # 4. Log in secure audit trail

        if settings.CRISIS_ALERT_EMAIL:
            # await send_crisis_alert_email(user_id, assessment)
            pass

    async def _high_risk_alert(
        self, user_id: str, conversation_id: str, assessment: Dict
    ) -> None:
        """High risk alert protocol"""
        print(f"⚠️ HIGH RISK ALERT for user {user_id}")

        # TODO: Implement in production:
        # 1. Flag conversation for review
        # 2. Alert monitoring team
        # 3. Enable enhanced tracking

    async def _medium_risk_monitoring(
        self, user_id: str, conversation_id: str, assessment: Dict
    ) -> None:
        """Medium risk monitoring protocol"""
        print(f"⚠️ MEDIUM RISK MONITORING for user {user_id}")

        # TODO: Implement in production:
        # 1. Flag for routine review
        # 2. Track conversation progression
        # 3. Provide additional resources

    def get_crisis_response_message(self, assessment: Dict) -> str:
        """
        Get appropriate crisis response message based on assessment.

        Returns Korean language response appropriate for the risk level.
        """
        risk_level = assessment["risk_level"]

        if isinstance(risk_level, str):
            risk_level = RiskLevel(risk_level)

        if risk_level == RiskLevel.CRITICAL:
            return """⚠️ **지금 공유해주신 내용이 매우 걱정됩니다. 당신의 안전이 가장 중요합니다.**

**즉시 전문적인 도움을 받아주세요:**
- 🆘 자살예방상담전화: **1393** (24시간 상담 가능)
- 📱 생명의 전화: **1588-9191** (24시간 상담 가능)
- 💬 정신건강위기상담전화: **1577-0199** (24시간 상담 가능)
- 🏥 응급상황: **119** (즉시 연락)

**지금 당장 위험한 상황이라면 119에 전화하거나 가까운 응급실로 가주세요.**

당신은 혼자가 아닙니다. 전문가들이 당신을 도울 준비가 되어 있습니다."""

        elif risk_level == RiskLevel.HIGH:
            return """정말 힘든 시간을 보내고 계신 것 같아 마음이 아픕니다.

**전문적인 도움을 받으시는 것을 강력히 권장합니다:**
- 📞 자살예방상담전화: **1393** (24시간, 무료)
- 📞 생명의 전화: **1588-9191** (24시간)
- 📞 정신건강위기상담전화: **1577-0199** (24시간)

지금 무엇이 가장 힘드신지 더 이야기해주시겠어요? 하지만 전문가의 도움이 정말 필요한 상황인 것 같습니다."""

        elif risk_level == RiskLevel.MEDIUM:
            return """힘든 감정을 나눠주셔서 감사합니다. 제가 여기서 들을 준비가 되어 있습니다.

만약 더 힘들어지거나 감당하기 어려워지면, 전문가의 도움을 받는 것을 고려해주세요:
- 📞 자살예방상담전화: **1393**
- 📞 생명의 전화: **1588-9191**

지금 어떤 점이 가장 힘드신가요?"""

        else:  # LOW or NONE
            return """힘든 마음을 나눠주셔서 감사합니다. 제가 여기서 함께 이야기를 들어드리겠습니다.

필요하시다면 언제든 전문가의 도움도 받으실 수 있습니다:
- 자살예방상담전화: 1393 (24시간)

지금 어떤 이야기를 나누고 싶으신가요?"""


# Global instance
crisis_detection_system = CrisisDetectionSystem()
