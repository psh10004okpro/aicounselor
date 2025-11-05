"""Crisis detection service for identifying high-risk situations"""

import re
from typing import List, Tuple
from datetime import datetime

from app.core.config import settings


class CrisisDetectionService:
    """Service for detecting crisis situations in user messages"""

    def __init__(self):
        self.crisis_keywords = settings.CRISIS_KEYWORDS
        self.threshold = settings.CRISIS_KEYWORDS_THRESHOLD

        # Extended crisis patterns (regex)
        self.crisis_patterns = [
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
        Detect crisis indicators in text.

        Args:
            text: User message text

        Returns:
            Tuple of (is_crisis, severity, detected_keywords)
            - is_crisis: Whether crisis indicators were found
            - severity: Severity score (0-10)
            - detected_keywords: List of detected crisis keywords/patterns
        """
        text_lower = text.lower()
        detected = []
        severity = 0

        # Check for exact keyword matches
        for keyword in self.crisis_keywords:
            if keyword in text_lower:
                detected.append(keyword)
                severity += 1

        # Check for crisis patterns (more severe)
        for pattern in self.crisis_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                for match in matches:
                    if match not in detected:
                        detected.append(match)
                        severity += 2  # Patterns are weighted more heavily

        # Normalize severity to 0-10 scale
        severity = min(severity, 10)

        # Crisis is detected if we exceed threshold
        is_crisis = len(detected) >= self.threshold or severity >= 5

        return is_crisis, severity, detected

    def get_crisis_response(self, severity: int) -> str:
        """
        Get appropriate crisis response based on severity.

        Args:
            severity: Crisis severity score (0-10)

        Returns:
            Crisis response message
        """
        if severity >= 7:
            return """I'm very concerned about what you've shared. Your safety is the top priority right now.

**Please reach out for immediate help:**
- 🆘 National Suicide Prevention Lifeline: 988 (call or text)
- 📱 Crisis Text Line: Text HOME to 741741
- 🌐 International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/

If you're in immediate danger, please call 911 or go to your nearest emergency room.

I'm here to listen, but I want to make sure you have access to professional crisis support right now."""

        elif severity >= 4:
            return """I hear that you're going through a really difficult time. While I'm here to support you, I want to make sure you have access to professional help:

**Crisis Resources:**
- 988 Suicide & Crisis Lifeline (24/7)
- Crisis Text Line: Text HOME to 741741

Would you like to talk more about what's troubling you? Remember, it's okay to reach out for professional support."""

        else:
            return """Thank you for sharing that with me. I'm here to listen. If things ever feel overwhelming, please know that help is available:

- 988 Suicide & Crisis Lifeline (24/7)
- Crisis Text Line: Text HOME to 741741

What would be most helpful for you to talk about right now?"""

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
