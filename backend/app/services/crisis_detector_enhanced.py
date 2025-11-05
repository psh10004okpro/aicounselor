"""
Enhanced Crisis Detection System with C-SSRS Framework and ASQ Integration

Based on:
1. Columbia Suicide Severity Rating Scale (C-SSRS)
2. ASQ (Ask Suicide-Screening Questions) 4-item questionnaire
3. GPT-4 Contextual Analysis
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from enum import Enum

from openai import AsyncOpenAI

from app.core.config import settings


class RiskLevel(str, Enum):
    """Risk level classification (backward compatible)"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CSSRSLevel(int, Enum):
    """
    Columbia Suicide Severity Rating Scale (C-SSRS) based levels

    5-level framework for comprehensive suicide risk assessment
    """
    LEVEL_0_SAFE = 0  # No suicidal ideation
    LEVEL_1_LOW = 1  # Passive thoughts, no intent
    LEVEL_2_MODERATE = 2  # Active thoughts, no plan
    LEVEL_3_HIGH = 3  # Active thoughts with plan
    LEVEL_4_IMMINENT = 4  # Intent and plan with preparation


class CrisisFramework:
    """
    C-SSRS based crisis assessment framework

    Provides structured indicators and actions for each level
    """

    LEVELS = {
        CSSRSLevel.LEVEL_0_SAFE: {
            "name": "안전",
            "name_en": "Safe",
            "indicators": [
                # No suicidal ideation indicators
            ],
            "assessment_criteria": [
                "자살 생각이나 의도 없음",
                "일반적인 생활 스트레스",
                "대처 능력 유지",
                "지지 체계 존재"
            ],
            "action": "일반 상담 진행",
            "action_detail": "정상적인 상담 프로세스 진행. 정기적 모니터링.",
            "resources": [],
            "monitoring_frequency": "routine"
        },

        CSSRSLevel.LEVEL_1_LOW: {
            "name": "낮음 (수동적 생각)",
            "name_en": "Low (Passive Ideation)",
            "indicators": [
                "일시적 부정적 생각",
                "가벼운 스트레스 표현",
                "희망 유지",
                "죽음에 대한 막연한 생각",
                "삶이 의미 없다는 표현 (구체성 없음)",
                "살아갈 이유를 찾기 어렵다는 표현"
            ],
            "assessment_criteria": [
                "수동적 자살 사고 (예: '더 이상 살고 싶지 않아')",
                "구체적 계획이나 의도 없음",
                "보호 요인 존재 (가족, 종교, 미래 계획 등)",
                "현실 검증 능력 유지"
            ],
            "action": "지지적 상담, 모니터링 강화",
            "action_detail": "감정 탐색 및 지지. 보호 요인 강화. 대처 전략 개발. 추가 평가 필요 시 전문가 의뢰 고려.",
            "resources": [
                "자살예방상담전화: 1393",
                "생명의 전화: 1588-9191"
            ],
            "monitoring_frequency": "weekly"
        },

        CSSRSLevel.LEVEL_2_MODERATE: {
            "name": "중등도 (능동적 생각, 계획 없음)",
            "name_en": "Moderate (Active Ideation, No Plan)",
            "indicators": [
                "죽음에 대한 수동적 생각",
                "지속적 절망감",
                "사회적 철수",
                "과거 행복했던 활동 포기",
                "무가치감 표현",
                "수면 장애, 식욕 변화",
                "집중력 저하"
            ],
            "assessment_criteria": [
                "능동적 자살 사고 (예: '죽고 싶다')",
                "구체적 방법이나 계획은 없음",
                "자살 의도는 명확하지 않음",
                "보호 요인이 약화되고 있음",
                "기능 저하 (일상, 대인관계)"
            ],
            "action": "적극적 개입, 안전 계획 수립",
            "action_detail": "즉시 전문가 평가 필요. 안전 계획 수립. 지지 체계 동원. 정기적 접촉 유지. 위기 대응 자원 제공.",
            "resources": [
                "자살예방상담전화: 1393 (24시간)",
                "생명의 전화: 1588-9191 (24시간)",
                "정신건강위기상담전화: 1577-0199",
                "가까운 정신건강복지센터"
            ],
            "monitoring_frequency": "daily"
        },

        CSSRSLevel.LEVEL_3_HIGH: {
            "name": "높음 (계획 있음)",
            "name_en": "High (Active Ideation with Plan)",
            "indicators": [
                "구체적 자해 생각",
                "자살 계획 언급",
                "무가치감 강화",
                "작별 행동",
                "소중한 물건 정리",
                "유서 작성 언급",
                "자살 수단에 대한 구체적 언급",
                "고립 증가"
            ],
            "assessment_criteria": [
                "구체적 자살 계획 존재",
                "자살 방법과 시기 고려",
                "자살 의도가 있으나 실행은 미정",
                "보호 요인이 크게 약화됨",
                "충동성 증가",
                "과거 자살 시도 이력"
            ],
            "action": "즉시 전문가 연결, 응급 프로토콜 활성화",
            "action_detail": "즉각적 위기 개입 필요. 정신과 응급 평가. 보호자 연락. 24시간 이내 전문가 면담 필수. 입원 치료 고려.",
            "resources": [
                "🆘 자살예방상담전화: 1393 (즉시 연결)",
                "📱 생명의 전화: 1588-9191 (즉시 연결)",
                "💬 정신건강위기상담전화: 1577-0199",
                "🏥 응급: 119",
                "🏥 가까운 응급실 방문"
            ],
            "monitoring_frequency": "immediate_continuous"
        },

        CSSRSLevel.LEVEL_4_IMMINENT: {
            "name": "긴급 (즉각적 위험)",
            "name_en": "Imminent (Immediate Danger)",
            "indicators": [
                "즉각적 자살 의도 표현",
                "수단 준비 언급",
                "극심한 고통",
                "현실 검증 상실",
                "충동 조절 불가",
                "자살 시도 직전 또는 진행 중",
                "명백한 위험 상황"
            ],
            "assessment_criteria": [
                "즉각적 자살 의도와 계획",
                "수단 접근 가능 또는 이미 확보",
                "즉시 실행할 의도 표현",
                "보호 요인 완전 상실",
                "현실 검증 능력 상실",
                "과거 심각한 자살 시도 이력"
            ],
            "action": "즉시 응급 서비스(119) 안내, 최우선 개입",
            "action_detail": "즉각적 응급 개입 필수. 119 신고 안내. 가능하면 보호자 즉시 연락. 혼자 두지 말 것. 응급실 또는 정신과 병동 입원 필요. 경찰/소방 협력 고려.",
            "resources": [
                "🚨 응급: 119 (즉시 전화)",
                "🆘 자살예방상담전화: 1393",
                "🏥 즉시 가까운 응급실로 이동",
                "👮 필요시 경찰 신고: 112"
            ],
            "monitoring_frequency": "immediate_intervention"
        }
    }

    @classmethod
    def get_level_info(cls, level: CSSRSLevel) -> Dict:
        """Get detailed information for a C-SSRS level"""
        return cls.LEVELS.get(level, cls.LEVELS[CSSRSLevel.LEVEL_0_SAFE])

    @classmethod
    def cssrs_to_risk_level(cls, cssrs_level: CSSRSLevel) -> RiskLevel:
        """Convert C-SSRS level to RiskLevel (for backward compatibility)"""
        mapping = {
            CSSRSLevel.LEVEL_0_SAFE: RiskLevel.NONE,
            CSSRSLevel.LEVEL_1_LOW: RiskLevel.LOW,
            CSSRSLevel.LEVEL_2_MODERATE: RiskLevel.MEDIUM,
            CSSRSLevel.LEVEL_3_HIGH: RiskLevel.HIGH,
            CSSRSLevel.LEVEL_4_IMMINENT: RiskLevel.CRITICAL
        }
        return mapping.get(cssrs_level, RiskLevel.NONE)

    @classmethod
    def risk_level_to_cssrs(cls, risk_level: RiskLevel) -> CSSRSLevel:
        """Convert RiskLevel to C-SSRS level"""
        mapping = {
            RiskLevel.NONE: CSSRSLevel.LEVEL_0_SAFE,
            RiskLevel.LOW: CSSRSLevel.LEVEL_1_LOW,
            RiskLevel.MEDIUM: CSSRSLevel.LEVEL_2_MODERATE,
            RiskLevel.HIGH: CSSRSLevel.LEVEL_3_HIGH,
            RiskLevel.CRITICAL: CSSRSLevel.LEVEL_4_IMMINENT
        }
        return mapping.get(risk_level, CSSRSLevel.LEVEL_0_SAFE)


class ASQScreening:
    """
    ASQ (Ask Suicide-Screening Questions) - 4 item questionnaire

    Validated brief screening tool for suicide risk
    """

    QUESTIONS = [
        {
            "id": "asq1",
            "question_ko": "최근 2주 동안, 죽고 싶거나 자신을 다치게 하고 싶은 생각을 한 적이 있나요?",
            "question_en": "In the past 2 weeks, have you had thoughts about killing yourself or wished you were dead?",
            "timeframe": "2 weeks",
            "severity_weight": 3
        },
        {
            "id": "asq2",
            "question_ko": "최근 3개월 동안, 스스로 목숨을 끊거나 자해를 하려고 계획한 적이 있나요?",
            "question_en": "In the past 3 months, have you had a plan to kill yourself or harm yourself?",
            "timeframe": "3 months",
            "severity_weight": 5
        },
        {
            "id": "asq3",
            "question_ko": "최근 1년 동안, 스스로 목숨을 끊거나 자해를 시도한 적이 있나요?",
            "question_en": "In the past year, have you tried to kill yourself or harm yourself?",
            "timeframe": "1 year",
            "severity_weight": 7
        },
        {
            "id": "asq4",
            "question_ko": "과거에 자살을 시도한 적이 있나요?",
            "question_en": "Have you ever tried to kill yourself in the past?",
            "timeframe": "lifetime",
            "severity_weight": 4
        }
    ]

    @classmethod
    def get_questions(cls) -> List[Dict]:
        """Get all ASQ questions"""
        return cls.QUESTIONS

    @classmethod
    def evaluate_responses(cls, responses: Dict[str, bool]) -> Dict:
        """
        Evaluate ASQ responses

        Args:
            responses: Dict mapping question ID to boolean answer

        Returns:
            Dict with risk assessment based on ASQ
        """
        positive_count = sum(1 for ans in responses.values() if ans)

        if positive_count == 0:
            return {
                "asq_positive": False,
                "cssrs_level": CSSRSLevel.LEVEL_0_SAFE,
                "risk_level": RiskLevel.NONE,
                "recommendation": "Continue normal counseling"
            }

        # Calculate severity score
        severity_score = sum(
            q["severity_weight"]
            for q in cls.QUESTIONS
            if responses.get(q["id"], False)
        )

        # Determine level based on responses and severity
        if responses.get("asq3", False) or responses.get("asq4", False):
            # Recent or past suicide attempt -> HIGH or CRITICAL
            if responses.get("asq2", False):  # Also has plan
                cssrs_level = CSSRSLevel.LEVEL_4_IMMINENT
            else:
                cssrs_level = CSSRSLevel.LEVEL_3_HIGH

        elif responses.get("asq2", False):
            # Has plan but no recent attempt -> HIGH
            cssrs_level = CSSRSLevel.LEVEL_3_HIGH

        elif responses.get("asq1", False):
            # Only recent thoughts -> MODERATE
            cssrs_level = CSSRSLevel.LEVEL_2_MODERATE

        else:
            cssrs_level = CSSRSLevel.LEVEL_1_LOW

        return {
            "asq_positive": True,
            "positive_count": positive_count,
            "severity_score": severity_score,
            "cssrs_level": cssrs_level,
            "risk_level": CrisisFramework.cssrs_to_risk_level(cssrs_level),
            "recommendation": "Immediate professional assessment required",
            "positive_questions": [
                q["id"] for q in cls.QUESTIONS
                if responses.get(q["id"], False)
            ]
        }


class EnhancedCrisisDetectionSystem:
    """
    Enhanced crisis detection with C-SSRS framework and ASQ integration

    Features:
    - 5-level C-SSRS based assessment
    - ASQ 4-item screening
    - Enhanced keyword classification
    - GPT-4 contextual analysis
    - Backward compatible with existing RiskLevel system
    """

    # Enhanced keyword classification
    CRISIS_KEYWORDS = {
        "immediate_risk": [
            # Korean - Immediate danger
            "자살", "죽고 싶", "살고 싶지 않", "삶의 의미 없",
            "사라지고 싶", "끝내고 싶", "안녕이라고", "유서",
            "목숨을 끊", "목숨 끊", "세상을 떠나", "자해",
            "손목을 그", "뛰어내리", "목을 매", "약을 먹",
            "죽는 방법", "자살 방법", "수단을 준비",
            # English
            "kill myself", "end my life", "commit suicide",
            "take my own life", "want to die", "suicide method",
            "prepared means", "goodbye forever"
        ],

        "high_risk": [
            # Korean - High risk indicators
            "절망", "희망 없", "소용없", "아무도 신경 안 써",
            "혼자", "외로", "버려진", "무가치", "의미없",
            "미래가 없", "포기하고 싶", "버티기 힘들",
            "더 이상 못", "한계", "견딜 수 없",
            "끝내야", "정리하고", "작별",
            # English
            "no hope", "hopeless", "worthless", "nobody cares",
            "alone", "abandoned", "no future", "give up",
            "can't go on", "can't take it", "say goodbye"
        ],

        "moderate_risk": [
            # Korean - Moderate concern
            "우울", "불안", "힘들", "지쳤", "포기",
            "견딜 수 없", "고통스러", "괴로", "슬프",
            "무기력", "의욕 없", "잠 못 자", "악몽",
            "두렵", "공포", "패닉",
            # English
            "depressed", "anxious", "tired", "exhausted",
            "can't cope", "painful", "suffering", "scared",
            "hopeless", "helpless", "panic"
        ]
    }

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

    async def detect(
        self,
        message: str,
        conversation_history: Optional[List[dict]] = None,
        asq_responses: Optional[Dict[str, bool]] = None
    ) -> Dict:
        """
        Enhanced multi-stage crisis detection

        Args:
            message: Current user message
            conversation_history: Previous messages for context
            asq_responses: Optional ASQ questionnaire responses

        Returns:
            Comprehensive crisis assessment
        """
        # Stage 0: ASQ Screening (if provided)
        asq_result = None
        if asq_responses:
            asq_result = ASQScreening.evaluate_responses(asq_responses)
            if asq_result["asq_positive"]:
                # ASQ positive -> immediately escalate to at least MODERATE
                return await self._create_asq_positive_response(asq_result, message)

        # Stage 1: Enhanced keyword detection
        keyword_result = self._enhanced_keyword_detection(message)

        if keyword_result["cssrs_level"] >= CSSRSLevel.LEVEL_4_IMMINENT:
            # Immediate risk detected
            return await self._create_immediate_response(keyword_result)

        # Stage 2 & 3: GPT-4 contextual analysis with C-SSRS framework
        if (
            keyword_result["cssrs_level"] >= CSSRSLevel.LEVEL_1_LOW
            or len(keyword_result["detected_keywords"]) > 0
        ):
            gpt_analysis = await self._contextual_analysis_cssrs(
                message, conversation_history, keyword_result
            )

            # Merge results - take higher risk level
            final_cssrs = max(
                keyword_result["cssrs_level"],
                gpt_analysis["cssrs_level"]
            )

            level_info = CrisisFramework.get_level_info(final_cssrs)

            return {
                "risk_level": CrisisFramework.cssrs_to_risk_level(final_cssrs),
                "cssrs_level": final_cssrs,
                "cssrs_level_name": level_info["name"],
                "detected_keywords": keyword_result["detected_keywords"],
                "keyword_categories": keyword_result["keyword_categories"],
                "reasoning": gpt_analysis["reasoning"],
                "immediate_action_needed": gpt_analysis["immediate_action_needed"],
                "suggested_resources": level_info["resources"],
                "action_required": level_info["action"],
                "action_detail": level_info["action_detail"],
                "confidence": gpt_analysis["confidence"],
                "detection_method": "enhanced_multi_stage",
                "asq_result": asq_result
            }

        # No significant risk detected
        return {
            "risk_level": RiskLevel.NONE,
            "cssrs_level": CSSRSLevel.LEVEL_0_SAFE,
            "cssrs_level_name": "안전",
            "detected_keywords": [],
            "keyword_categories": {},
            "reasoning": "No crisis indicators detected",
            "immediate_action_needed": False,
            "suggested_resources": [],
            "action_required": "일반 상담 진행",
            "action_detail": "정상적인 상담 프로세스 진행",
            "confidence": 0.9,
            "detection_method": "keyword_screening",
            "asq_result": asq_result
        }

    def _enhanced_keyword_detection(self, message: str) -> Dict:
        """Enhanced keyword detection with categorization"""
        message_lower = message.lower()
        detected = {
            "immediate_risk": [],
            "high_risk": [],
            "moderate_risk": []
        }

        # Check each category
        for category, keywords in self.CRISIS_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in message or keyword.lower() in message_lower:
                    detected[category].append(keyword)

        # Determine C-SSRS level based on detected categories
        if detected["immediate_risk"]:
            cssrs_level = CSSRSLevel.LEVEL_4_IMMINENT
        elif detected["high_risk"]:
            cssrs_level = CSSRSLevel.LEVEL_3_HIGH
        elif detected["moderate_risk"]:
            cssrs_level = CSSRSLevel.LEVEL_2_MODERATE
        else:
            cssrs_level = CSSRSLevel.LEVEL_0_SAFE

        # Flatten detected keywords
        all_detected = (
            detected["immediate_risk"] +
            detected["high_risk"] +
            detected["moderate_risk"]
        )

        return {
            "cssrs_level": cssrs_level,
            "detected_keywords": all_detected,
            "keyword_categories": detected
        }

    async def _contextual_analysis_cssrs(
        self,
        message: str,
        conversation_history: Optional[List[dict]],
        keyword_result: Dict
    ) -> Dict:
        """
        GPT-4 contextual analysis using C-SSRS framework
        """
        # Build context
        context_messages = []
        if conversation_history:
            context_messages = conversation_history[-5:]
        context_messages.append({"role": "user", "content": message})

        # Enhanced function schema with C-SSRS
        function_schema = {
            "name": "assess_crisis_cssrs",
            "description": "Assess suicide risk using C-SSRS framework",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "cssrs_level": {
                        "type": "integer",
                        "enum": [0, 1, 2, 3, 4],
                        "description": "C-SSRS level (0=Safe, 1=Low, 2=Moderate, 3=High, 4=Imminent)"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Detailed assessment reasoning in Korean"
                    },
                    "immediate_action_needed": {
                        "type": "boolean",
                        "description": "Whether immediate intervention required"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence in assessment (0-1)",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "risk_factors_identified": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of specific risk factors found"
                    },
                    "protective_factors_identified": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of protective factors present"
                    }
                },
                "required": [
                    "cssrs_level",
                    "reasoning",
                    "immediate_action_needed",
                    "confidence",
                    "risk_factors_identified",
                    "protective_factors_identified"
                ],
                "additionalProperties": False
            }
        }

        # Enhanced system prompt with C-SSRS guidance
        system_prompt = """당신은 C-SSRS (Columbia Suicide Severity Rating Scale) 기반 위기 평가 전문가입니다.

**C-SSRS 레벨 기준**:

**Level 0 (Safe/안전)**: 자살 생각이나 의도 없음. 일반적인 스트레스.

**Level 1 (Low/낮음)**: 수동적 자살 사고
- "더 이상 살고 싶지 않아" (구체적 계획 없음)
- 보호 요인 존재 (가족, 희망)
- 현실 검증 능력 유지

**Level 2 (Moderate/중등도)**: 능동적 자살 사고, 계획 없음
- "죽고 싶다" (방법은 생각 안 함)
- 지속적 절망감
- 기능 저하
- 보호 요인 약화

**Level 3 (High/높음)**: 능동적 자살 사고 + 계획
- 구체적 자살 방법 언급
- 시기와 방법 고려
- 작별 행동
- 충동성 증가

**Level 4 (Imminent/긴급)**: 즉각적 위험
- 지금 당장 자살하려는 의도
- 수단 준비 또는 접근 가능
- 실행 직전 또는 진행 중

**중요**:
- 과잉 진단 금지 - 실제 위험이 있을 때만 Level 3-4
- 보호 요인과 위험 요인 모두 평가
- 일상적 우울/스트레스는 Level 0-1

한국어로 명확하게 평가하세요."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *context_messages
                ],
                functions=[function_schema],
                function_call={"name": "assess_crisis_cssrs"},
                temperature=0.2
            )

            function_call = response.choices[0].message.function_call
            assessment = json.loads(function_call.arguments)

            # Convert integer to CSSRSLevel enum
            assessment["cssrs_level"] = CSSRSLevel(assessment["cssrs_level"])

            return assessment

        except Exception as e:
            print(f"Error in C-SSRS analysis: {e}")
            # Safe fallback
            return {
                "cssrs_level": CSSRSLevel.LEVEL_2_MODERATE,
                "reasoning": "분석 중 오류 발생. 안전을 위해 전문가 상담 권장.",
                "immediate_action_needed": True,
                "confidence": 0.5,
                "risk_factors_identified": [],
                "protective_factors_identified": []
            }

    async def _create_immediate_response(self, keyword_result: Dict) -> Dict:
        """Create immediate intervention response"""
        level_info = CrisisFramework.get_level_info(CSSRSLevel.LEVEL_4_IMMINENT)

        return {
            "risk_level": RiskLevel.CRITICAL,
            "cssrs_level": CSSRSLevel.LEVEL_4_IMMINENT,
            "cssrs_level_name": level_info["name"],
            "detected_keywords": keyword_result["detected_keywords"],
            "keyword_categories": keyword_result["keyword_categories"],
            "reasoning": "즉각적 위험 키워드 감지. 긴급 개입 필요.",
            "immediate_action_needed": True,
            "suggested_resources": level_info["resources"],
            "action_required": level_info["action"],
            "action_detail": level_info["action_detail"],
            "confidence": 1.0,
            "detection_method": "immediate_keyword_match"
        }

    async def _create_asq_positive_response(
        self, asq_result: Dict, message: str
    ) -> Dict:
        """Create response when ASQ is positive"""
        cssrs_level = asq_result["cssrs_level"]
        level_info = CrisisFramework.get_level_info(cssrs_level)

        return {
            "risk_level": asq_result["risk_level"],
            "cssrs_level": cssrs_level,
            "cssrs_level_name": level_info["name"],
            "detected_keywords": [],
            "keyword_categories": {},
            "reasoning": f"ASQ 선별검사 양성 ({asq_result['positive_count']}개 항목). 전문가 평가 필요.",
            "immediate_action_needed": True,
            "suggested_resources": level_info["resources"],
            "action_required": level_info["action"],
            "action_detail": level_info["action_detail"],
            "confidence": 0.95,
            "detection_method": "asq_screening",
            "asq_result": asq_result
        }

    def get_crisis_response_message(self, assessment: Dict) -> str:
        """Get appropriate response message based on C-SSRS level"""
        cssrs_level = assessment.get("cssrs_level", CSSRSLevel.LEVEL_0_SAFE)

        if isinstance(cssrs_level, int):
            cssrs_level = CSSRSLevel(cssrs_level)

        level_info = CrisisFramework.get_level_info(cssrs_level)

        if cssrs_level == CSSRSLevel.LEVEL_4_IMMINENT:
            resources_text = "\n".join(f"- {r}" for r in level_info["resources"])
            return f"""⚠️ **긴급 상황이 감지되었습니다. 즉시 도움이 필요합니다.**

당신의 안전이 가장 중요합니다. 지금 당장 전문가의 도움을 받아주세요:

{resources_text}

**지금 위험한 상황이라면 119에 즉시 전화하거나 가까운 응급실로 가주세요.**

당신은 혼자가 아닙니다. 전문가들이 24시간 대기하고 있습니다."""

        elif cssrs_level == CSSRSLevel.LEVEL_3_HIGH:
            resources_text = "\n".join(f"- {r}" for r in level_info["resources"])
            return f"""정말 힘든 시간을 보내고 계시는 것 같아 마음이 아픕니다.

**지금 즉시 전문가의 도움이 필요한 상황입니다:**

{resources_text}

전문가가 당신을 도울 준비가 되어 있습니다. 지금 바로 연락해주세요."""

        elif cssrs_level == CSSRSLevel.LEVEL_2_MODERATE:
            resources_text = "\n".join(f"- {r}" for r in level_info["resources"])
            return f"""힘든 감정을 나눠주셔서 감사합니다.

전문가의 도움을 받으시는 것을 권장드립니다:

{resources_text}

지금 어떤 점이 가장 힘드신가요? 함께 이야기 나눠보아요."""

        elif cssrs_level == CSSRSLevel.LEVEL_1_LOW:
            return """힘든 마음을 표현해주셔서 감사합니다. 제가 함께 이야기를 들어드리겠습니다.

필요하시다면 언제든 전문가의 도움도 받으실 수 있습니다:
- 자살예방상담전화: 1393 (24시간)
- 생명의 전화: 1588-9191 (24시간)

지금 어떤 이야기를 나누고 싶으신가요?"""

        else:  # LEVEL_0_SAFE
            return """감정을 나눠주셔서 감사합니다. 제가 여기서 함께 이야기를 들어드리겠습니다.

무엇에 대해 이야기하고 싶으신가요?"""

    async def emergency_protocol(
        self, assessment: Dict, user_id: str, conversation_id: str
    ) -> None:
        """Execute emergency protocol based on C-SSRS level"""
        cssrs_level = assessment.get("cssrs_level", CSSRSLevel.LEVEL_0_SAFE)

        if isinstance(cssrs_level, int):
            cssrs_level = CSSRSLevel(cssrs_level)

        # Log crisis event
        await self._log_crisis_event(assessment, user_id, conversation_id)

        if cssrs_level >= CSSRSLevel.LEVEL_4_IMMINENT:
            await self._imminent_intervention(user_id, conversation_id, assessment)
        elif cssrs_level >= CSSRSLevel.LEVEL_3_HIGH:
            await self._high_risk_intervention(user_id, conversation_id, assessment)
        elif cssrs_level >= CSSRSLevel.LEVEL_2_MODERATE:
            await self._moderate_risk_monitoring(user_id, conversation_id, assessment)

    async def _log_crisis_event(
        self, assessment: Dict, user_id: str, conversation_id: str
    ) -> None:
        """Log crisis event with C-SSRS details"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "cssrs_level": assessment.get("cssrs_level"),
            "risk_level": assessment.get("risk_level"),
            "detected_keywords": assessment.get("detected_keywords", []),
            "keyword_categories": assessment.get("keyword_categories", {}),
            "reasoning": assessment.get("reasoning", ""),
            "confidence": assessment.get("confidence", 0),
            "asq_result": assessment.get("asq_result"),
            "detection_method": assessment.get("detection_method")
        }

        print(f"🚨 C-SSRS CRISIS EVENT: {log_entry}")
        # TODO: Save to database

    async def _imminent_intervention(
        self, user_id: str, conversation_id: str, assessment: Dict
    ) -> None:
        """Imminent danger protocol - Level 4"""
        print(f"🚨🚨🚨 LEVEL 4 IMMINENT DANGER - User {user_id}")
        # TODO: Immediate intervention protocol

    async def _high_risk_intervention(
        self, user_id: str, conversation_id: str, assessment: Dict
    ) -> None:
        """High risk protocol - Level 3"""
        print(f"🚨🚨 LEVEL 3 HIGH RISK - User {user_id}")
        # TODO: High risk intervention protocol

    async def _moderate_risk_monitoring(
        self, user_id: str, conversation_id: str, assessment: Dict
    ) -> None:
        """Moderate risk protocol - Level 2"""
        print(f"⚠️ LEVEL 2 MODERATE RISK - User {user_id}")
        # TODO: Moderate risk monitoring protocol


# Global instance
enhanced_crisis_detection_system = EnhancedCrisisDetectionSystem()
