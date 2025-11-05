"""Crisis detection service for identifying high-risk situations (Korea-specific)"""

import re
from typing import List, Tuple, Optional
from datetime import datetime

from app.core.config import settings


class CrisisDetectionService:
    """Service for detecting crisis situations in user messages (Korea-specific)"""

    def __init__(self):
        # Korean crisis keywords
        self.crisis_keywords_ko = [
            "죽고싶",
            "자살",
            "자해",
            "목숨",
            "극단적",
            "살고싶지",
            "사라지고싶",
            "끝내고싶",
            "죽을까",
            "죽어야",
            "생을 마감",
            "더이상 못",
            "한계",
            "견딜 수 없",
        ]

        # English crisis keywords (for international users)
        self.crisis_keywords_en = [
            "suicide",
            "kill myself",
            "end my life",
            "self-harm",
            "hurt myself",
            "don't want to live",
        ]

        self.threshold = settings.CRISIS_KEYWORDS_THRESHOLD

        # Korean crisis patterns (regex)
        self.crisis_patterns_ko = [
            r"(죽|자살|자해).*?(싶|하고|할|해야)",
            r"(극단적|살고싶지|사라지고싶).*?(선택|생각)",
            r"(더이상|이제|정말).*?(못|안|힘들|버티|견디)",
            r"(생|삶|인생|목숨).*?(마감|끝|포기)",
            r"(세상|세상에|이 세상).*?(없|사라|떠나)",
        ]

        # English crisis patterns
        self.crisis_patterns_en = [
            r"\b(want to die|wanna die|wish I was dead)\b",
            r"\b(kill myself|end my life|take my life)\b",
            r"\b(suicide|suicidal)\b",
            r"\b(cut myself|hurt myself|harm myself)\b",
            r"\b(can't go on|can't take it anymore|no reason to live)\b",
            r"\b(better off dead|world.*better without me)\b",
            r"\b(plan to|planning to).*(die|suicide|kill)\b",
        ]

    def detect_crisis(self, text: str) -> Tuple[bool, int, List[str]]:
        """
        Detect crisis indicators in text (multilingual).

        Args:
            text: User message text

        Returns:
            Tuple of (is_crisis, severity, detected_keywords)
            - is_crisis: Whether crisis indicators were found
            - severity: Severity score (0-10)
            - detected_keywords: List of detected crisis keywords/patterns
        """
        detected = []
        severity = 0

        # Check Korean keywords
        for keyword in self.crisis_keywords_ko:
            if keyword in text:
                detected.append(keyword)
                severity += 1

        # Check English keywords
        text_lower = text.lower()
        for keyword in self.crisis_keywords_en:
            if keyword in text_lower:
                detected.append(keyword)
                severity += 1

        # Check Korean crisis patterns (more severe)
        for pattern in self.crisis_patterns_ko:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    if match not in detected:
                        detected.append(match)
                        severity += 2  # Patterns are weighted more heavily

        # Check English crisis patterns
        for pattern in self.crisis_patterns_en:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                for match in matches:
                    if match not in detected:
                        detected.append(match)
                        severity += 2

        # Normalize severity to 0-10 scale
        severity = min(severity, 10)

        # Crisis is detected if we exceed threshold
        is_crisis = len(detected) >= self.threshold or severity >= 5

        return is_crisis, severity, detected

    def get_crisis_response(self, severity: int) -> str:
        """
        Get appropriate crisis response based on severity (Korea-specific).

        Args:
            severity: Crisis severity score (0-10)

        Returns:
            Crisis response message in Korean
        """
        if severity >= 7:
            return """지금 공유해주신 내용이 매우 걱정됩니다. 당신의 안전이 가장 중요합니다.

**즉시 전문적인 도움을 받아주세요:**
- 🆘 자살예방상담전화: **1393** (24시간 상담 가능)
- 📱 생명의 전화: **1588-9191** (24시간 상담 가능)
- 💬 정신건강위기상담전화: **1577-0199** (24시간 상담 가능)
- 🏥 응급상황: **119** (즉시 연락)

**지금 당장 위험한 상황이라면 119에 전화하거나 가까운 응급실로 가주세요.**

제가 여기서 들을 수는 있지만, 지금은 전문가의 도움이 꼭 필요한 상황입니다. 당신은 혼자가 아닙니다."""

        elif severity >= 4:
            return """정말 힘든 시간을 보내고 계신 것 같아 마음이 아픕니다. 제가 이야기를 들을 수는 있지만, 전문적인 도움도 함께 받으시면 좋을 것 같습니다.

**위기 상담 자원:**
- 📞 자살예방상담전화: **1393** (24시간)
- 📞 생명의 전화: **1588-9191** (24시간)
- 📞 정신건강위기상담전화: **1577-0199** (24시간)

지금 무엇이 가장 힘드신지 더 이야기해주시겠어요? 전문가의 도움을 받는 것은 결코 약한 모습이 아닙니다."""

        else:
            return """힘든 마음을 나눠주셔서 감사합니다. 제가 여기서 들을 준비가 되어 있습니다. 만약 감당하기 어려워지면, 언제든지 도움을 요청할 수 있다는 것을 기억해주세요:

- 📞 자살예방상담전화: **1393** (24시간)
- 📞 생명의 전화: **1588-9191** (24시간)

지금 무엇에 대해 이야기를 나누면 가장 도움이 될까요?"""

    async def log_crisis_event(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        severity: int,
        keywords: List[str],
    ) -> None:
        """
        Log crisis event for monitoring and potential intervention.

        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            message: Crisis message content
            severity: Severity score
            keywords: Detected keywords
        """
        # In production, this would:
        # 1. Log to a secure audit system
        # 2. Alert crisis response team if severity is high
        # 3. Store for compliance/safety monitoring

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "severity": severity,
            "keywords": keywords,
            "message_preview": message[:100],  # Truncate for privacy
        }

        # For now, just print (replace with proper logging in production)
        print(f"⚠️ CRISIS DETECTED: {log_entry}")

        # In production, send email/SMS alerts for high severity
        if severity >= 7 and settings.CRISIS_ALERT_EMAIL:
            # await send_crisis_alert_email(log_entry)
            pass
