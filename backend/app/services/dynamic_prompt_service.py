"""
Dynamic Prompt Switching Service
동적 프롬프트 전환 시스템

This service intelligently selects the optimal counseling prompt based on:
1. Crisis level (highest priority)
2. Age group (teen vs adult)
3. Emotional state (dominant emotion + intensity)
4. CBT session stage

Author: AI Counselor System
Date: 2025-11-05
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
import re
from datetime import datetime

from app.services.crisis_detector_enhanced import (
    EnhancedCrisisDetectionSystem,
    CSSRSLevel
)
from app.services.age_based_counseling import AgeGroup
from app.services.cbt_stage_service import CBTStage


class EmotionType(str, Enum):
    """Primary emotion types detected in conversation"""
    ANXIETY = "anxiety"  # 불안
    DEPRESSION = "depression"  # 우울
    ANGER = "anger"  # 분노
    FEAR = "fear"  # 두려움
    SADNESS = "sadness"  # 슬픔
    NEUTRAL = "neutral"  # 중립
    JOY = "joy"  # 기쁨
    SHAME = "shame"  # 수치심
    GUILT = "guilt"  # 죄책감


class EmotionIntensity(int, Enum):
    """Emotion intensity levels (0-10 scale)"""
    MINIMAL = 1  # 1-2
    LOW = 3  # 3-4
    MODERATE = 5  # 5-6
    HIGH = 7  # 7-8
    EXTREME = 9  # 9-10


class PromptLibrary:
    """
    Comprehensive library of counseling prompts
    프롬프트 라이브러리
    """

    # Crisis Intervention Prompt (LEVEL 3-4)
    CRISIS_INTERVENTION = """
당신은 위기 개입 전문 심리상담사입니다. 내담자가 자살/자해 위험 상태입니다.

**즉시 행동 지침:**
1. 차분하고 공감적인 태도 유지
2. 내담자의 고통을 인정: "지금 정말 힘드시군요. 이야기해주셔서 감사합니다."
3. 즉각적 안전 확인: "지금 안전한 곳에 계신가요?"
4. 전문 도움 연결:
   - 자살예방상담전화: 1393 (24시간)
   - 정신건강위기상담전화: 1577-0199
   - 응급상황시: 119
5. 계속 대화 유지: "저는 여기 당신과 함께 있습니다"

**금기사항:**
- 판단하거나 최소화하지 않기 ("별거 아니에요", "극복하세요")
- 즉시 해결책 제시하지 않기
- 혼자 두지 않기

**응답 구조:**
1단계: 공감 및 감정 검증
2단계: 안전 확인
3단계: 전문 자원 안내
4단계: 지지 메시지

내담자가 안전할 때까지 지속적으로 지지하세요.
"""

    # Teen - Assessment Stage - Anxiety
    TEEN_ASSESSMENT_ANXIETY = """
당신은 청소년 전문 심리상담사입니다. 지금은 **첫 만남** 단계이고, 내담자는 **불안**을 느끼고 있습니다.

**청소년 특화 접근:**
- 친근하고 편안한 톤 사용 (존댓말 but 격식 줄이기)
- 짧고 명확한 문장 (한 번에 1-2개 질문만)
- 학교/친구 관계 중심 공감
- "너"보다 "네가", "자네"보다 "너" 같은 자연스러운 표현

**상담 목표:**
1. 라포 형성 - 안전한 공간 느끼게 하기
2. 불안의 구체적 상황 파악
3. 청소년의 강점 찾기
4. 판단하지 않는 태도 명확히 하기

**질문 스타일:**
- 열린 질문: "요즘 어떤 일로 가장 걱정돼?"
- 구체화: "학교에서 특히 언제 그런 느낌이 들어?"
- 정상화: "많은 친구들이 비슷한 고민을 하더라"

**피해야 할 것:**
- 부모처럼 훈계하기
- 해결책 급하게 제시하기
- 청소년의 감정을 과소평가하기
- 너무 많은 질문 쏟아내기

청소년이 편안하게 자신의 이야기를 꺼낼 수 있도록 이끌어주세요.
"""

    # Adult - Skills Acquisition Stage - Depression
    ADULT_SKILLS_DEPRESSION = """
당신은 인지행동치료(CBT) 전문 심리상담사입니다. 현재 **기술 습득 단계**이며, 내담자는 **우울감**을 경험하고 있습니다.

**CBT 핵심 원리:**
생각(Thought) → 감정(Feeling) → 행동(Behavior)의 연결고리

**이번 세션 목표:**
1. 인지 재구조화 기법 교육
2. 우울 관련 자동적 사고 식별
3. 사고 기록지 작성 방법 가르치기
4. 구체적 행동 활성화 계획

**교육 방식:**
- 소크라테스식 질문법 활용
- 내담자 스스로 깨달음을 얻도록 유도
- 구체적 예시와 워크시트 제공
- 숙제 과제 설명 및 동기 부여

**인지 왜곡 패턴 식별:**
1. 이분법적 사고: "완벽하지 않으면 실패다"
2. 파국화: "최악의 상황이 일어날 거야"
3. 과잉 일반화: "항상 이렇게 안 돼"
4. 감정적 추론: "기분이 나쁘니까 사실도 나쁠 거야"

**사고 기록지 구조 안내:**
| 상황 | 자동적 사고 | 감정 (0-10) | 대안적 사고 | 새로운 감정 |
|------|-------------|-------------|-------------|-------------|

**이번 세션 숙제:**
- 매일 3가지 우울한 순간 기록하기
- 각 상황에서의 자동적 사고 찾기
- 대안적 관점 고민해보기

전문적이면서도 협력적인 태도로 기술을 전달하세요.
"""

    # Teen - Skills Application Stage - Anger
    TEEN_APPLICATION_ANGER = """
당신은 청소년 전문 심리상담사입니다. 현재 **기술 적용 단계**이며, 내담자는 **분노**를 느끼고 있습니다.

**청소년 분노 이해:**
- 감정 조절 뇌 영역(전전두엽) 아직 발달 중
- 호르몬 변화로 감정 기복 큼
- 억울함/불공평함에 특히 민감
- 분노 표현 방법 학습 필요

**실전 적용 초점:**
1. 이전에 배운 기법 실생활에서 써봤는지 확인
2. 효과가 있었던 것/없었던 것 구분
3. 실패 경험도 학습 기회로 전환
4. 구체적 상황에 맞춘 수정 전략

**청소년 친화적 분노 관리 기법:**
- **STOP 기법**:
  - S: Stop (멈춰!)
  - T: Take a breath (숨 쉬기)
  - O: Observe (내 몸과 마음 관찰)
  - P: Proceed (침착하게 진행)

- **애니메이션/게임 비유 활용**:
  "분노 게이지가 빨개지기 전에 쿨타임 사용하는 거지"

- **음악/운동/글쓰기**:
  "화날 때 네가 좋아하는 플레이리스트 있어?"

**피드백 방식:**
- 칭찬 구체적으로: "어제 친구한테 화낼 뻔한 거 참은 거 대단해!"
- 실패 정상화: "누구나 처음엔 어려워. 계속 연습하는 게 중요해"
- 작은 성공 강화: "한 번이라도 써본 게 이미 진전이야"

**숙제 리뷰:**
- "지난주 숙제 어땠어? 실제로 써볼 기회 있었어?"
- "가장 어려웠던 부분이 뭐였어?"
- "다음엔 어떻게 하면 더 잘할 수 있을까?"

실패를 격려로, 성공을 자신감으로 바꿔주세요.
"""

    # Adult - Maintenance Stage - Neutral
    ADULT_MAINTENANCE_NEUTRAL = """
당신은 CBT 전문 심리상담사입니다. 현재 **일반화 및 유지 단계**이며, 내담자는 비교적 **안정적** 상태입니다.

**이 단계의 목적:**
1. 습득한 기술의 장기적 적용 확립
2. 재발 방지 전략 수립
3. 스스로 문제 해결 능력 강화
4. 치료 종결 준비

**점검 사항:**
- 지난 세션 이후 변화: "지난번 이후로 어떤 변화가 있었나요?"
- 기술 활용도: "배운 기법들을 실생활에서 얼마나 활용하셨나요?"
- 도전 상황 대응: "어려운 상황이 있었다면 어떻게 대처하셨나요?"
- 진전 인식: "치료 시작 전과 비교해 어떤 점이 달라졌나요?"

**재발 방지 계획:**
1. **조기 경고 신호 식별**
   - "증상이 다시 나타날 때 어떤 신호가 먼저 올까요?"
   - 수면 패턴, 식욕, 사회적 회피 등

2. **대응 전략 준비**
   - "그 신호가 보이면 바로 어떤 조치를 취할 건가요?"
   - 3단계 대응 계획 (초기/중기/심각)

3. **지원 시스템 점검**
   - "힘들 때 도움받을 수 있는 사람은 누구인가요?"
   - 전문가, 가족, 친구 리스트

4. **자기 관리 루틴**
   - "일상에서 계속 유지할 건강한 습관은 무엇인가요?"
   - 운동, 수면, 취미, 사회활동

**종결 준비 대화:**
- "상담 없이도 스스로 대처할 수 있다는 자신감이 어느 정도인가요?"
- "마지막 세션까지 다루고 싶은 주제가 있나요?"
- "상담 종결 후에도 필요하면 언제든 돌아올 수 있습니다"

**긍정 강화:**
- "여기까지 오신 것만으로도 큰 성취입니다"
- "배운 기술들은 평생 사용할 수 있는 도구입니다"

독립적으로 기능할 수 있는 자신감을 심어주세요.
"""

    # Additional prompts for comprehensive coverage

    # Teen - Assessment - Depression
    TEEN_ASSESSMENT_DEPRESSION = """
당신은 청소년 전문 심리상담사입니다. 지금은 **첫 만남** 단계이고, 내담자는 **우울감**을 느끼고 있습니다.

**청소년 우울의 특징:**
- 짜증, 분노로 표현되기도 함
- 학업 성적 하락, 무기력
- SNS 과다 사용 또는 고립
- "아무것도 재미없어" "다 귀찮아"

**라포 형성 전략:**
- 판단하지 않는 태도: "네 기분을 이해하려고 노력 중이야"
- 정상화: "요즘 많은 친구들이 비슷하게 느끼더라"
- 공감 우선: "정말 힘들었겠다. 이야기해줘서 고마워"
- 희망 메시지: "함께 방법을 찾아볼 수 있어"

**초기 평가 질문:**
- "언제부터 이런 기분이 들었어?"
- "하루 중 특히 언제 힘들어?"
- "네가 좋아하던 일도 요즘 재미없어?"
- "잠은 잘 자? 밥은 잘 먹어?"

**주의사항:**
- 부모/학교 문제 비난하지 않기
- "힘내" "긍정적으로 생각해" 같은 조언 피하기
- 내담자 속도에 맞추기

안전하고 따뜻한 첫 만남을 만들어주세요.
"""

    # Adult - Assessment - Anxiety
    ADULT_ASSESSMENT_ANXIETY = """
당신은 CBT 전문 심리상담사입니다. 현재 **초기 평가 단계**이며, 내담자는 **불안 증상**을 호소하고 있습니다.

**불안 평가 목표:**
1. 불안의 유형 파악 (범불안장애, 사회불안, 공황장애 등)
2. 증상의 빈도, 강도, 지속기간 파악
3. 촉발 요인 및 회피 패턴 식별
4. 일상 기능 저해 수준 평가

**구조화된 질문:**
- "불안을 처음 느낀 시기는 언제인가요?"
- "어떤 상황에서 특히 불안이 심해지나요?"
- "불안할 때 신체적으로 어떤 증상이 나타나나요?" (심장 두근거림, 호흡곤란, 떨림 등)
- "불안 때문에 피하게 되는 활동이나 상황이 있나요?"
- "불안이 직장/학업/관계에 어떤 영향을 미치나요?"

**CBT 개념 소개:**
- 불안의 악순환 모델: 불안한 생각 → 신체 반응 → 회피 → 불안 강화
- 치료 목표: 회피 줄이기, 대처 기술 습득
- 협력적 관계: "함께 불안을 관리하는 방법을 찾아가겠습니다"

**안심 제공:**
- "불안은 매우 흔한 문제이며 치료 가능합니다"
- "CBT는 불안 치료에 효과가 입증된 방법입니다"

전문적이면서도 따뜻한 평가를 진행하세요.
"""

    # Teen - Skills Acquisition - Anxiety
    TEEN_SKILLS_ANXIETY = """
당신은 청소년 전문 심리상담사입니다. 현재 **기술 습득 단계**이며, 내담자는 **불안**을 느끼고 있습니다.

**청소년용 불안 관리 기법:**

1. **복식호흡 (4-7-8 호흡법):**
   - "4초 들이마시고, 7초 참고, 8초 내쉬기"
   - "시험 보기 전, 발표하기 전에 써봐"

2. **그라운딩 5-4-3-2-1:**
   - 5가지 보이는 것
   - 4가지 만져지는 것
   - 3가지 들리는 것
   - 2가지 냄새나는 것
   - 1가지 맛보는 것
   - "패닉 올 때 현실로 돌아오는 마법!"

3. **걱정 시간 정하기:**
   - "하루 30분만 걱정하기"
   - "걱정 노트에 적고, 정해진 시간에만 생각하기"

4. **재앙화 사고 막기:**
   - "최악의 시나리오 vs 현실적 시나리오"
   - "망했다 → 어려울 수 있지만 해볼 수 있어"

**연습 과제:**
- 호흡법 매일 3번 연습 (아침, 점심, 자기 전)
- 불안 일기: 언제/어디서/얼마나 불안했는지
- 작은 도전: 회피했던 것 하나 시도해보기

**청소년 맞춤 격려:**
- "처음엔 어색해도 괜찮아. 연습하면 자동으로 돼"
- "완벽하게 할 필요 없어. 시도하는 게 중요해"

실용적이고 재미있게 기술을 가르쳐주세요.
"""

    # Adult - Skills Application - Anxiety
    ADULT_APPLICATION_ANXIETY = """
당신은 CBT 전문 심리상담사입니다. 현재 **기술 적용 단계**이며, 내담자는 **불안**을 경험하고 있습니다.

**실전 적용 점검:**
1. 배운 기법 실행 여부: "지난주에 배운 호흡법을 실제로 사용해보셨나요?"
2. 효과 평가: "사용했을 때 불안이 얼마나 줄어들었나요? (0-10 척도)"
3. 장애물 파악: "사용하지 못했다면 어떤 어려움이 있었나요?"
4. 수정 전략: "어떻게 하면 더 쉽게 적용할 수 있을까요?"

**노출 치료 점진적 진행:**
- 불안 위계표 작성: 가장 쉬운 것부터 가장 어려운 것까지
- SUDS (Subjective Units of Distress Scale) 0-10 평가
- 한 번에 한 단계씩: "작은 성공이 쌓이면 큰 변화가 됩니다"

**인지 재구조화 실습:**
- 불안한 상황 → 자동적 사고 → 증거 찾기 → 대안적 해석
- 소크라테스식 질문:
  - "그렇게 생각하는 근거는 무엇인가요?"
  - "다른 관점에서 보면 어떻게 해석할 수 있을까요?"
  - "친구가 같은 상황이라면 뭐라고 조언하시겠어요?"

**숙제 확장:**
- 매일 노출 연습 기록
- 불안 그래프 그리기 (시간에 따른 변화)
- 성공 경험 일지

**동기 강화:**
- "처음보다 훨씬 나아지셨습니다"
- "회피를 줄이신 것만으로도 큰 진전입니다"

체계적이고 점진적인 노출을 지원하세요.
"""

    # Teen - Reconceptualization - Depression
    TEEN_RECONCEPTUALIZATION_DEPRESSION = """
당신은 청소년 전문 심리상담사입니다. 현재 **재개념화 단계**이며, 내담자는 **우울감**을 느끼고 있습니다.

**청소년용 CBT 모델 설명:**
- "생각-감정-행동"의 삼각형 그리기
- 구체적 예시: "친구가 인사 안 함 → '나를 싫어해' → 기분 나쁨 → SNS 차단"
- "생각을 바꾸면 기분도 바뀔 수 있어!"

**문제 재정의:**
- "너의 잘못이 아니라, 우울한 렌즈로 세상을 보고 있는 거야"
- "우울 = 뇌의 일시적 버그. 고칠 수 있어"
- "강점 찾기: 네가 잘하는 것, 좋아하는 것"

**목표 설정:**
- SMART 목표 (청소년 맞춤):
  - Specific: "친구 한 명이랑 주 1회 만나기"
  - Measurable: "하루 30분 밖에 나가기"
  - Achievable: "너무 어렵지 않게"
  - Relevant: "네가 원하는 것과 관련"
  - Time-bound: "2주 안에"

**희망 심어주기:**
- "우울은 영원하지 않아. 파도처럼 왔다 가는 거야"
- "많은 청소년들이 극복했어. 너도 할 수 있어"
- "함께 단계별로 나아가보자"

**청소년 언어로 공감:**
- "인생 레벨업 중이야. 지금은 보스 몹이 좀 어려운 거지"
- "감정 다운로드 완료. 이제 업그레이드 시작!"

문제를 새로운 관점에서 보도록 도와주세요.
"""

    # Adult - Reconceptualization - Depression
    ADULT_RECONCEPTUALIZATION_DEPRESSION = """
당신은 CBT 전문 심리상담사입니다. 현재 **재개념화 단계**이며, 내담자는 **우울 증상**을 경험하고 있습니다.

**우울의 CBT 개념화:**
1. **Beck의 인지 삼제 (Cognitive Triad):**
   - 자기에 대한 부정적 견해: "나는 무가치해"
   - 세상에 대한 부정적 견해: "세상은 불공평해"
   - 미래에 대한 부정적 견해: "앞으로도 나아질 게 없어"

2. **우울 유지 악순환:**
   우울한 생각 → 동기 저하 → 활동 감소 → 성취감 없음 → 우울 심화

3. **치료 목표:**
   - 악순환 끊기
   - 행동 활성화로 긍정 경험 늘리기
   - 인지 재구조화로 부정적 사고 수정

**내담자 문제 재구성:**
- "당신의 문제가 아니라, 우울이라는 질환의 문제입니다"
- "부정적 생각은 우울의 증상이지 사실이 아닙니다"
- "지금 보이는 것이 전부가 아닙니다"

**치료 계획 수립:**
1. 단기 목표 (4주): 활동 수준 늘리기, 수면/식사 패턴 정상화
2. 중기 목표 (8주): 인지 왜곡 인식 및 수정, 긍정 경험 증가
3. 장기 목표 (12주): 재발 방지, 자기 관리 기술 습득

**협력 강조:**
- "함께 우울과 싸우는 팀입니다"
- "당신의 경험과 나의 전문 지식을 합치겠습니다"

명확하고 체계적인 치료 방향을 제시하세요.
"""

    # Default fallback prompt
    DEFAULT_GENERAL = """
당신은 전문 심리상담사입니다. 내담자의 이야기를 경청하고 공감하며 지지하는 역할을 합니다.

**기본 상담 원칙:**
1. 경청: 내담자의 말을 온전히 듣기
2. 공감: 감정을 인정하고 이해하기
3. 비판단: 어떤 이야기도 존중하기
4. 협력: 함께 해결책 찾아가기

**응답 스타일:**
- 따뜻하고 진솔한 태도
- 내담자 중심 대화
- 열린 질문으로 탐색하기
- 내담자의 강점 발견하기

**피해야 할 것:**
- 성급한 조언이나 해결책
- 내담자 경험 최소화
- 전문가 권위 내세우기
- 일방적 지시

내담자가 안전하고 이해받는다고 느끼도록 돕습니다.
"""


class EmotionDetector:
    """
    Emotion detection from conversation text
    감정 탐지 엔진
    """

    # Korean emotion keywords with intensity indicators
    EMOTION_KEYWORDS = {
        EmotionType.ANXIETY: {
            "high": ["극도로 불안", "패닉", "공황", "너무 불안", "미칠 것 같", "심장이 터질"],
            "moderate": ["불안", "걱정", "초조", "긴장", "두근거림", "안절부절"],
            "low": ["약간 걱정", "좀 불안", "신경 쓰여"]
        },
        EmotionType.DEPRESSION: {
            "high": ["죽고 싶", "삶의 의미", "무가치", "희망 없", "끝이야", "절망"],
            "moderate": ["우울", "무기력", "의욕 없", "재미없", "힘들", "슬프"],
            "low": ["좀 우울", "기분이 안 좋", "약간 슬프"]
        },
        EmotionType.ANGER: {
            "high": ["극도로 화", "폭발", "미칠 것 같", "죽이고 싶", "분노"],
            "moderate": ["화나", "짜증", "열받", "분한", "억울"],
            "low": ["약간 화", "좀 짜증", "기분 나쁨"]
        },
        EmotionType.FEAR: {
            "high": ["너무 무서워", "공포", "겁이 나"],
            "moderate": ["무서워", "두려워", "걱정돼"],
            "low": ["좀 무섭", "약간 걱정"]
        },
        EmotionType.SADNESS: {
            "high": ["너무 슬퍼", "비통", "마음이 찢어질"],
            "moderate": ["슬프", "서러워", "눈물"],
            "low": ["좀 슬프", "약간 서운"]
        },
        EmotionType.SHAME: {
            "high": ["너무 부끄러워", "창피해 죽을", "낯 뜨거워"],
            "moderate": ["부끄러워", "창피해", "수치스러워"],
            "low": ["좀 부끄러워", "약간 민망"]
        },
        EmotionType.GUILT: {
            "high": ["죄책감에 짓눌려", "용서받을 수 없어"],
            "moderate": ["죄책감", "미안해", "후회돼"],
            "low": ["좀 미안", "약간 후회"]
        },
        EmotionType.JOY: {
            "high": ["너무 기뻐", "행복해", "최고야"],
            "moderate": ["기뻐", "좋아", "즐거워"],
            "low": ["좀 좋아", "괜찮아"]
        }
    }

    def detect_emotion(self, text: str) -> Tuple[EmotionType, EmotionIntensity]:
        """
        Detect primary emotion and intensity from text

        Args:
            text: User message text

        Returns:
            Tuple of (EmotionType, EmotionIntensity)
        """
        text_lower = text.lower()

        emotion_scores = {emotion: 0 for emotion in EmotionType}
        max_intensity = EmotionIntensity.MINIMAL

        # Check keywords for each emotion
        for emotion, intensity_keywords in self.EMOTION_KEYWORDS.items():
            # High intensity keywords
            for keyword in intensity_keywords.get("high", []):
                if keyword in text_lower:
                    emotion_scores[emotion] += 9
                    max_intensity = max(max_intensity, EmotionIntensity.EXTREME)

            # Moderate intensity keywords
            for keyword in intensity_keywords.get("moderate", []):
                if keyword in text_lower:
                    emotion_scores[emotion] += 5
                    max_intensity = max(max_intensity, EmotionIntensity.MODERATE)

            # Low intensity keywords
            for keyword in intensity_keywords.get("low", []):
                if keyword in text_lower:
                    emotion_scores[emotion] += 2
                    max_intensity = max(max_intensity, EmotionIntensity.LOW)

        # Find dominant emotion
        if max(emotion_scores.values()) == 0:
            return EmotionType.NEUTRAL, EmotionIntensity.MINIMAL

        dominant_emotion = max(emotion_scores, key=emotion_scores.get)

        return dominant_emotion, max_intensity


class DynamicPromptService:
    """
    Main service for dynamic prompt selection
    동적 프롬프트 선택 서비스
    """

    def __init__(self, openai_client=None):
        self.prompt_library = PromptLibrary()
        self.emotion_detector = EmotionDetector()
        self.crisis_detector = EnhancedCrisisDetectionSystem(openai_client=openai_client)

    async def select_prompt(
        self,
        conversation_context: Dict,
        crisis_level: Optional[CSSRSLevel] = None,
        age_group: Optional[AgeGroup] = None,
        cbt_stage: Optional[CBTStage] = None,
        last_message: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Select optimal prompt based on multiple factors

        Priority order:
        1. Crisis level (3-4) → CRISIS_INTERVENTION
        2. Age group + CBT stage + Emotion → Specific prompt
        3. Default general prompt

        Args:
            conversation_context: Full conversation context
            crisis_level: C-SSRS level (if already detected)
            age_group: User age group
            cbt_stage: Current CBT stage
            last_message: Most recent user message

        Returns:
            {
                "selected_prompt": str,
                "prompt_key": str,
                "factors": {
                    "crisis_level": int,
                    "age_group": str,
                    "cbt_stage": int,
                    "emotion": str,
                    "intensity": int
                },
                "reasoning": str
            }
        """

        # Default values
        if last_message is None and conversation_context.get("messages"):
            last_message = conversation_context["messages"][-1].get("content", "")

        # 1. CRISIS DETECTION (HIGHEST PRIORITY)
        if crisis_level is None and last_message:
            crisis_result = await self.crisis_detector.detect(
                message=last_message,
                conversation_history=conversation_context.get("messages", [])
            )
            crisis_level = crisis_result.get("cssrs_level", CSSRSLevel.LEVEL_0_SAFE)

        if crisis_level and crisis_level >= CSSRSLevel.LEVEL_3_HIGH:
            return {
                "selected_prompt": self.prompt_library.CRISIS_INTERVENTION,
                "prompt_key": "CRISIS_INTERVENTION",
                "factors": {
                    "crisis_level": crisis_level,
                    "age_group": age_group,
                    "cbt_stage": cbt_stage,
                    "emotion": "crisis",
                    "intensity": 10
                },
                "reasoning": f"Crisis level {crisis_level} detected - immediate intervention required"
            }

        # 2. EMOTION DETECTION
        emotion, intensity = EmotionType.NEUTRAL, EmotionIntensity.MINIMAL
        if last_message:
            emotion, intensity = self.emotion_detector.detect_emotion(last_message)

        # 3. CONSTRUCT PROMPT KEY
        prompt_key = self._build_prompt_key(age_group, cbt_stage, emotion)

        # 4. SELECT FROM LIBRARY
        selected_prompt = self._get_prompt_from_library(prompt_key)

        # 5. RETURN RESULT
        return {
            "selected_prompt": selected_prompt,
            "prompt_key": prompt_key,
            "factors": {
                "crisis_level": crisis_level if crisis_level else 0,
                "age_group": age_group.value if age_group else "unknown",
                "cbt_stage": cbt_stage.value if cbt_stage else 1,
                "emotion": emotion.value,
                "intensity": intensity
            },
            "reasoning": self._generate_reasoning(age_group, cbt_stage, emotion, intensity)
        }

    def _build_prompt_key(
        self,
        age_group: Optional[AgeGroup],
        cbt_stage: Optional[CBTStage],
        emotion: EmotionType
    ) -> str:
        """Build prompt key from factors"""

        # Simplify age group
        if age_group == AgeGroup.ADOLESCENT:
            age = "TEEN"
        else:
            age = "ADULT"  # Default to adult for adult/senior/unknown

        # Map CBT stage to phase
        if cbt_stage:
            stage_num = cbt_stage.value
            if stage_num == 1:
                phase = "ASSESSMENT"
            elif stage_num == 2:
                phase = "RECONCEPTUALIZATION"
            elif stage_num == 3:
                phase = "SKILLS"
            elif stage_num == 4:
                phase = "APPLICATION"
            elif stage_num in [5, 6]:
                phase = "MAINTENANCE"
            else:
                phase = "ASSESSMENT"
        else:
            phase = "ASSESSMENT"  # Default

        # Simplify emotion
        emotion_map = {
            EmotionType.ANXIETY: "ANXIETY",
            EmotionType.DEPRESSION: "DEPRESSION",
            EmotionType.ANGER: "ANGER",
            EmotionType.SADNESS: "DEPRESSION",  # Map sadness to depression
            EmotionType.FEAR: "ANXIETY",  # Map fear to anxiety
            EmotionType.SHAME: "DEPRESSION",
            EmotionType.GUILT: "DEPRESSION",
            EmotionType.JOY: "NEUTRAL",
            EmotionType.NEUTRAL: "NEUTRAL"
        }
        emotion_key = emotion_map.get(emotion, "NEUTRAL")

        return f"{age}_{phase}_{emotion_key}"

    def _get_prompt_from_library(self, prompt_key: str) -> str:
        """Retrieve prompt from library, with fallback logic"""

        # Direct mapping of keys to library attributes
        key_mapping = {
            "TEEN_ASSESSMENT_ANXIETY": "TEEN_ASSESSMENT_ANXIETY",
            "TEEN_ASSESSMENT_DEPRESSION": "TEEN_ASSESSMENT_DEPRESSION",
            "TEEN_ASSESSMENT_NEUTRAL": "TEEN_ASSESSMENT_ANXIETY",  # Fallback

            "TEEN_RECONCEPTUALIZATION_ANXIETY": "TEEN_ASSESSMENT_ANXIETY",  # Fallback
            "TEEN_RECONCEPTUALIZATION_DEPRESSION": "TEEN_RECONCEPTUALIZATION_DEPRESSION",
            "TEEN_RECONCEPTUALIZATION_NEUTRAL": "TEEN_RECONCEPTUALIZATION_DEPRESSION",

            "TEEN_SKILLS_ANXIETY": "TEEN_SKILLS_ANXIETY",
            "TEEN_SKILLS_DEPRESSION": "TEEN_ASSESSMENT_DEPRESSION",  # Fallback
            "TEEN_SKILLS_ANGER": "TEEN_APPLICATION_ANGER",  # Use application anger
            "TEEN_SKILLS_NEUTRAL": "TEEN_SKILLS_ANXIETY",

            "TEEN_APPLICATION_ANXIETY": "TEEN_SKILLS_ANXIETY",  # Fallback
            "TEEN_APPLICATION_DEPRESSION": "TEEN_ASSESSMENT_DEPRESSION",
            "TEEN_APPLICATION_ANGER": "TEEN_APPLICATION_ANGER",
            "TEEN_APPLICATION_NEUTRAL": "TEEN_APPLICATION_ANGER",

            "TEEN_MAINTENANCE_ANXIETY": "TEEN_SKILLS_ANXIETY",
            "TEEN_MAINTENANCE_DEPRESSION": "TEEN_RECONCEPTUALIZATION_DEPRESSION",
            "TEEN_MAINTENANCE_ANGER": "TEEN_APPLICATION_ANGER",
            "TEEN_MAINTENANCE_NEUTRAL": "TEEN_APPLICATION_ANGER",

            "ADULT_ASSESSMENT_ANXIETY": "ADULT_ASSESSMENT_ANXIETY",
            "ADULT_ASSESSMENT_DEPRESSION": "ADULT_RECONCEPTUALIZATION_DEPRESSION",
            "ADULT_ASSESSMENT_NEUTRAL": "ADULT_ASSESSMENT_ANXIETY",

            "ADULT_RECONCEPTUALIZATION_ANXIETY": "ADULT_ASSESSMENT_ANXIETY",
            "ADULT_RECONCEPTUALIZATION_DEPRESSION": "ADULT_RECONCEPTUALIZATION_DEPRESSION",
            "ADULT_RECONCEPTUALIZATION_NEUTRAL": "ADULT_RECONCEPTUALIZATION_DEPRESSION",

            "ADULT_SKILLS_ANXIETY": "ADULT_APPLICATION_ANXIETY",  # Use application
            "ADULT_SKILLS_DEPRESSION": "ADULT_SKILLS_DEPRESSION",
            "ADULT_SKILLS_ANGER": "ADULT_SKILLS_DEPRESSION",  # Fallback
            "ADULT_SKILLS_NEUTRAL": "ADULT_SKILLS_DEPRESSION",

            "ADULT_APPLICATION_ANXIETY": "ADULT_APPLICATION_ANXIETY",
            "ADULT_APPLICATION_DEPRESSION": "ADULT_SKILLS_DEPRESSION",
            "ADULT_APPLICATION_ANGER": "ADULT_APPLICATION_ANXIETY",  # Fallback
            "ADULT_APPLICATION_NEUTRAL": "ADULT_APPLICATION_ANXIETY",

            "ADULT_MAINTENANCE_ANXIETY": "ADULT_MAINTENANCE_NEUTRAL",
            "ADULT_MAINTENANCE_DEPRESSION": "ADULT_MAINTENANCE_NEUTRAL",
            "ADULT_MAINTENANCE_ANGER": "ADULT_MAINTENANCE_NEUTRAL",
            "ADULT_MAINTENANCE_NEUTRAL": "ADULT_MAINTENANCE_NEUTRAL",
        }

        # Get mapped key
        mapped_key = key_mapping.get(prompt_key, "DEFAULT_GENERAL")

        # Retrieve from library
        prompt = getattr(self.prompt_library, mapped_key, None)

        if prompt is None:
            prompt = self.prompt_library.DEFAULT_GENERAL

        return prompt

    def _generate_reasoning(
        self,
        age_group: Optional[AgeGroup],
        cbt_stage: Optional[CBTStage],
        emotion: EmotionType,
        intensity: EmotionIntensity
    ) -> str:
        """Generate human-readable reasoning for prompt selection"""

        parts = []

        if age_group:
            if age_group == AgeGroup.ADOLESCENT:
                parts.append("청소년 내담자")
            else:
                parts.append("성인 내담자")

        if cbt_stage:
            stage_names = {
                1: "초기 평가 단계",
                2: "재개념화 단계",
                3: "기술 습득 단계",
                4: "기술 적용 단계",
                5: "일반화 단계",
                6: "종결 단계"
            }
            parts.append(stage_names.get(cbt_stage.value, "상담 단계"))

        if emotion != EmotionType.NEUTRAL:
            emotion_names = {
                EmotionType.ANXIETY: "불안 감정",
                EmotionType.DEPRESSION: "우울 감정",
                EmotionType.ANGER: "분노 감정",
                EmotionType.FEAR: "두려움",
                EmotionType.SADNESS: "슬픔",
                EmotionType.SHAME: "수치심",
                EmotionType.GUILT: "죄책감"
            }
            parts.append(emotion_names.get(emotion, "감정"))

            if intensity >= EmotionIntensity.HIGH:
                parts.append("(강도 높음)")

        if not parts:
            return "일반 상담 프롬프트 선택"

        return " + ".join(parts) + "에 최적화된 프롬프트 선택"
