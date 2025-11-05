"""
Age-Based Counseling Framework

Provides differentiated counseling strategies for adolescents (13-18) and adults (19+)
based on developmental psychology and cognitive-behavioral therapy principles.
"""

from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime, date


class AgeGroup(str, Enum):
    """Age group classification"""
    CHILD = "child"  # Under 13 (not supported yet)
    ADOLESCENT = "adolescent"  # 13-18
    ADULT = "adult"  # 19+
    SENIOR = "senior"  # 65+ (treated as adult for now)


class AgeBasedCounselingFramework:
    """
    Framework for age-appropriate counseling strategies

    Based on developmental psychology and age-specific therapeutic approaches
    """

    # Adolescent (13-18) counseling strategies
    ADOLESCENT_STRATEGY = {
        "age_range": "13-18세",
        "age_range_en": "13-18 years",

        "cognitive_characteristics": [
            "추상적 사고 발달 중",
            "충동성이 높음",
            "감정 변화가 크고 빠름",
            "자아 정체성 형성 중",
            "또래 영향력이 큼"
        ],

        "communication_style": {
            "tone": "친근하고 비공식적",
            "language": "쉽고 일상적인 표현 사용",
            "emojis": "이모티콘/이모지 활용 가능",
            "slang": "유행어 이해 및 수용",
            "directness": "간접적 표현 이해 필요",
            "examples": [
                "학교 생활",
                "친구 관계",
                "소셜미디어",
                "학업 스트레스",
                "부모님과의 갈등"
            ]
        },

        "session_characteristics": {
            "duration": "30-40분 (짧게)",
            "frequency": "주 1-2회",
            "structure": "유연하고 창의적",
            "homework_compliance": "낮음 (단순하고 재미있게)"
        },

        "therapeutic_approach": {
            "engagement": [
                "관심사에서 시작 (게임, 유튜브, 아이돌 등)",
                "강요하지 않고 선택권 제공",
                "단기 목표와 즉각적 성과 강조",
                "창의적 도구 활용 (저널링, 그림, 음악)"
            ],
            "resistance_management": [
                "\"너를 바꾸려는 게 아니라 도우려는 것\"",
                "비판 피하고 이해와 공감 우선",
                "강점 기반 접근",
                "자율성 존중"
            ],
            "parent_involvement": [
                "필요시 부모 상담 병행",
                "청소년 동의 필수",
                "비밀 보장 원칙 설명",
                "부모와의 경계 명확히"
            ]
        },

        "cbt_adaptations": {
            "thought_records": "단순화된 형식, 시각적 요소",
            "behavioral_activation": "즉각적 보상, 작은 단계",
            "cognitive_restructuring": "구체적 예시, 짧은 연습",
            "homework": "짧고 재미있는 과제, 앱 활용 가능"
        },

        "common_issues": [
            "학업 스트레스",
            "또래 관계 갈등",
            "가족 갈등",
            "정체성 혼란",
            "소셜미디어 압박",
            "우울 및 불안",
            "자존감 문제"
        ],

        "crisis_considerations": [
            "충동성 높아 자해/자살 위험 주의",
            "사이버불링 관련 위기",
            "가족 문제로 인한 스트레스",
            "학업 실패에 대한 극단적 반응"
        ],

        "language_examples": {
            "greeting": "안녕! 오늘 어떻게 지냈어? 😊",
            "empathy": "그래, 학교에서 그런 일 있으면 진짜 힘들지...",
            "encouragement": "와, 그거 해냈다니 대박이야! 👍",
            "homework": "이번 주에 한번 해볼까? 부담 갖지 말고~"
        }
    }

    # Adult (19+) counseling strategies
    ADULT_STRATEGY = {
        "age_range": "19세 이상",
        "age_range_en": "19+ years",

        "cognitive_characteristics": [
            "완전한 추상적 사고 가능",
            "충동 조절 능력 발달",
            "자기 성찰 능력 높음",
            "장기적 관점 가능",
            "복잡한 문제 분석 가능"
        ],

        "communication_style": {
            "tone": "전문적이고 존중하는",
            "language": "정확하고 명확한 표현",
            "emojis": "최소화 (필요시만)",
            "slang": "사용 자제",
            "directness": "직접적이고 논리적",
            "examples": [
                "직장 스트레스",
                "가족 관계",
                "재정 문제",
                "부부/연애 관계",
                "인생 목표"
            ]
        },

        "session_characteristics": {
            "duration": "50-60분 (표준)",
            "frequency": "주 1회 또는 격주",
            "structure": "구조화되고 체계적",
            "homework_compliance": "높음 (구체적이고 의미있게)"
        },

        "therapeutic_approach": {
            "engagement": [
                "명확한 치료 목표 설정",
                "증거 기반 접근법 설명",
                "자율성과 자기 결정권 강조",
                "장기적 변화 추구"
            ],
            "collaboration": [
                "치료 방향 결정에 적극 참여",
                "전문가-내담자 협력 관계",
                "피드백 주고받기",
                "진행 상황 정기 검토"
            ],
            "depth_exploration": [
                "과거 경험의 영향 탐색",
                "핵심 믿음 파악",
                "패턴 인식 및 분석",
                "통찰 발전"
            ]
        },

        "cbt_adaptations": {
            "thought_records": "상세한 7단 사고기록지",
            "behavioral_activation": "체계적 활동 계획, 가치 기반",
            "cognitive_restructuring": "깊이 있는 믿음 탐색",
            "homework": "구조화된 워크시트, 일일 기록"
        },

        "common_issues": [
            "직장 스트레스",
            "우울증, 불안장애",
            "관계 문제",
            "생활 전환기 어려움",
            "자아 실현",
            "일과 삶의 균형",
            "트라우마"
        ],

        "crisis_considerations": [
            "만성적 스트레스 누적",
            "중대한 생활 사건 (이직, 이혼, 사별)",
            "재정적 어려움",
            "건강 문제"
        ],

        "language_examples": {
            "greeting": "안녕하세요. 오늘은 어떻게 지내셨나요?",
            "empathy": "그런 상황에서 그렇게 느끼시는 것이 충분히 이해됩니다.",
            "encouragement": "노력하신 결과가 나타나고 있네요.",
            "homework": "다음 주까지 사고기록지를 작성해보시겠습니까?"
        }
    }

    @classmethod
    def get_age_group(cls, age: int) -> AgeGroup:
        """
        Determine age group from age

        Args:
            age: User age in years

        Returns:
            AgeGroup enum
        """
        if age < 13:
            return AgeGroup.CHILD
        elif 13 <= age <= 18:
            return AgeGroup.ADOLESCENT
        elif 19 <= age < 65:
            return AgeGroup.ADULT
        else:
            return AgeGroup.SENIOR

    @classmethod
    def get_age_group_from_birthdate(cls, birthdate: date) -> AgeGroup:
        """
        Determine age group from birthdate

        Args:
            birthdate: User's birthdate

        Returns:
            AgeGroup enum
        """
        today = date.today()
        age = today.year - birthdate.year

        # Adjust if birthday hasn't occurred yet this year
        if today.month < birthdate.month or (
            today.month == birthdate.month and today.day < birthdate.day
        ):
            age -= 1

        return cls.get_age_group(age)

    @classmethod
    def get_strategy(cls, age_group: AgeGroup) -> Dict:
        """
        Get counseling strategy for age group

        Args:
            age_group: AgeGroup enum

        Returns:
            Dictionary with age-appropriate strategies
        """
        if age_group == AgeGroup.ADOLESCENT:
            return cls.ADOLESCENT_STRATEGY
        elif age_group in [AgeGroup.ADULT, AgeGroup.SENIOR]:
            return cls.ADULT_STRATEGY
        else:
            # Child - not fully supported yet, use simplified adolescent
            return cls.ADOLESCENT_STRATEGY

    @classmethod
    def get_system_prompt_additions(cls, age_group: AgeGroup) -> str:
        """
        Get age-appropriate system prompt additions

        Args:
            age_group: AgeGroup enum

        Returns:
            String to add to system prompt
        """
        strategy = cls.get_strategy(age_group)

        if age_group == AgeGroup.ADOLESCENT:
            return f"""
**내담자 연령대: 청소년 (13-18세)**

**의사소통 스타일**:
- 친근하고 비공식적인 톤 사용
- 쉽고 일상적인 표현 사용
- 이모티콘 활용 가능 (적절히)
- 유행어나 청소년 언어 이해하고 수용
- 간접적 표현과 비언어적 단서 주의깊게 파악

**치료적 접근**:
- 청소년의 관심사에서 시작 (학교, 친구, 게임, 유튜브 등)
- 단기 목표와 즉각적 성과 강조
- 강요하지 않고 선택권 제공
- "너를 바꾸려는 게 아니라 도우려는 것" 강조
- 비판 피하고 이해와 공감 우선
- 청소년의 자율성과 독립성 존중

**주요 고려사항**:
- 추상적 사고가 발달 중이므로 구체적 예시 사용
- 충동성이 높으므로 위기 상황 주의
- 부모와의 갈등이 흔하므로 균형있는 시각 유지
- 또래 관계의 중요성 인정
- 짧고 재미있는 과제 제시

**대화 예시**:
- "오늘 학교에서 어떤 일 있었어?"
- "친구들이랑 그런 상황이면 진짜 힘들었겠다..."
- "이번 주에 한번만 해볼래? 부담 갖지 말고~"
"""

        elif age_group in [AgeGroup.ADULT, AgeGroup.SENIOR]:
            return f"""
**내담자 연령대: 성인 (19세 이상)**

**의사소통 스타일**:
- 전문적이고 존중하는 톤 유지
- 정확하고 명확한 표현 사용
- 이모티콘 최소화 (필요시만)
- 직접적이고 논리적인 대화
- 복잡한 개념 설명 가능

**치료적 접근**:
- 명확한 치료 목표 설정
- 증거 기반 접근법 설명
- 내담자의 자율성과 자기 결정권 강조
- 장기적 변화와 지속 가능성 추구
- 과거 경험의 영향 깊이 탐색
- 전문가-내담자 협력 관계 구축

**주요 고려사항**:
- 완전한 추상적 사고 가능
- 자기 성찰 능력 활용
- 복잡한 문제 분석 가능
- 장기적 관점에서 접근
- 구조화된 워크시트와 과제 활용

**대화 예시**:
- "오늘은 어떻게 지내셨나요?"
- "그런 상황에서 그렇게 느끼시는 것이 충분히 이해됩니다."
- "다음 주까지 사고기록지를 작성해보시겠습니까?"
"""

        else:
            return ""


class AgeBasedCounselingService:
    """
    Service for managing age-based counseling

    Integrates with CBT system and crisis detection
    """

    def __init__(self):
        self.framework = AgeBasedCounselingFramework

    def get_age_group_from_user(
        self,
        age: Optional[int] = None,
        birthdate: Optional[date] = None
    ) -> AgeGroup:
        """
        Get age group from user information

        Args:
            age: User's age in years
            birthdate: User's birthdate

        Returns:
            AgeGroup enum
        """
        if age is not None:
            return self.framework.get_age_group(age)
        elif birthdate is not None:
            return self.framework.get_age_group_from_birthdate(birthdate)
        else:
            # Default to adult if no age info
            return AgeGroup.ADULT

    def get_counseling_strategy(self, age_group: AgeGroup) -> Dict:
        """Get complete counseling strategy for age group"""
        return self.framework.get_strategy(age_group)

    def get_enhanced_system_prompt(
        self,
        base_prompt: str,
        age_group: AgeGroup,
        include_cbt_stage: bool = True
    ) -> str:
        """
        Enhance system prompt with age-appropriate guidelines

        Args:
            base_prompt: Base system prompt
            age_group: User's age group
            include_cbt_stage: Whether to include CBT stage info

        Returns:
            Enhanced system prompt
        """
        age_additions = self.framework.get_system_prompt_additions(age_group)

        # Combine base prompt with age-specific additions
        enhanced_prompt = f"""{base_prompt}

---

{age_additions}
"""

        return enhanced_prompt

    def get_session_recommendations(self, age_group: AgeGroup) -> Dict:
        """
        Get session configuration recommendations

        Args:
            age_group: User's age group

        Returns:
            Dictionary with session recommendations
        """
        strategy = self.framework.get_strategy(age_group)

        return {
            "age_group": age_group.value,
            "duration": strategy["session_characteristics"]["duration"],
            "frequency": strategy["session_characteristics"]["frequency"],
            "structure": strategy["session_characteristics"]["structure"],
            "homework_approach": strategy["session_characteristics"]["homework_compliance"],
            "crisis_considerations": strategy["crisis_considerations"]
        }

    def adapt_cbt_approach(self, age_group: AgeGroup, cbt_stage: int) -> Dict:
        """
        Adapt CBT approach based on age group and current stage

        Args:
            age_group: User's age group
            cbt_stage: Current CBT stage (1-6)

        Returns:
            Dictionary with adapted CBT approach
        """
        strategy = self.framework.get_strategy(age_group)
        cbt_adaptations = strategy["cbt_adaptations"]

        # General adaptations
        adaptations = {
            "age_group": age_group.value,
            "cbt_stage": cbt_stage,
            "adaptations": cbt_adaptations
        }

        # Stage-specific adaptations
        if age_group == AgeGroup.ADOLESCENT:
            if cbt_stage == 1:  # Assessment
                adaptations["focus"] = "관계 형성, 관심사 탐색"
                adaptations["techniques"] = ["대화형 평가", "게임화된 질문"]
            elif cbt_stage == 2:  # Reconceptualization
                adaptations["focus"] = "간단한 ABC 모델, 구체적 예시"
                adaptations["techniques"] = ["만화/그림 활용", "짧은 예시"]
            elif cbt_stage == 3:  # Skills Acquisition
                adaptations["focus"] = "재미있는 기술 학습"
                adaptations["techniques"] = ["앱 활용", "짧은 연습", "즉각 피드백"]
            elif cbt_stage == 4:  # Skills Application
                adaptations["focus"] = "학교/친구 상황에 적용"
                adaptations["techniques"] = ["역할극", "일상 과제"]

        elif age_group in [AgeGroup.ADULT, AgeGroup.SENIOR]:
            if cbt_stage == 1:  # Assessment
                adaptations["focus"] = "체계적 평가, 명확한 목표"
                adaptations["techniques"] = ["구조화된 면접", "표준화된 척도"]
            elif cbt_stage == 2:  # Reconceptualization
                adaptations["focus"] = "핵심 믿음 탐색, 패턴 분석"
                adaptations["techniques"] = ["하향 화살표 기법", "핵심 믿음 워크시트"]
            elif cbt_stage == 3:  # Skills Acquisition
                adaptations["focus"] = "증거 기반 기술 학습"
                adaptations["techniques"] = ["7단 사고기록지", "체계적 노출"]
            elif cbt_stage == 4:  # Skills Application
                adaptations["focus"] = "직장/가족 상황에 적용"
                adaptations["techniques"] = ["행동 실험", "일상 기록"]

        return adaptations

    def get_communication_guidelines(self, age_group: AgeGroup) -> Dict:
        """
        Get communication guidelines for age group

        Args:
            age_group: User's age group

        Returns:
            Dictionary with communication guidelines
        """
        strategy = self.framework.get_strategy(age_group)

        return {
            "age_group": age_group.value,
            "style": strategy["communication_style"],
            "examples": strategy["language_examples"],
            "common_issues": strategy["common_issues"]
        }


# Global instance
age_based_counseling_service = AgeBasedCounselingService()
