# Crisis Detection System Documentation

## Overview

The Advanced Crisis Detection System is a 3-stage, multi-layered approach to identifying and responding to mental health crises in real-time chat conversations.

## Architecture

```
User Message
     ↓
Stage 1: Keyword Detection (Instant)
     ↓
Stage 2: GPT-4 Contextual Analysis
     ↓
Stage 3: Structured Output Evaluation
     ↓
Emergency Protocol Activation
```

## Stage 1: Keyword Detection

**Purpose**: Immediate detection of critical crisis indicators

**Method**: Fast pattern matching against predefined keywords

**Risk Levels**:
- **CRITICAL** (Immediate intervention)
  - Korean: 죽고 싶, 자살, 목숨을 끊, 자해, 뛰어내리, 목을 매
  - English: kill myself, end my life, commit suicide, want to die

- **HIGH** (Requires analysis)
  - Korean: 의미없, 희망이 없, 미래가 없, 끝내고 싶
  - English: no point, no hope, no future, give up

**Performance**: < 1ms response time

## Stage 2: GPT-4 Contextual Analysis

**Purpose**: Understand context and intent beyond keywords

**Features**:
- Analyzes conversation history (last 5 messages)
- Considers cultural and linguistic nuances
- Evaluates severity based on context

**Model**: GPT-4o-mini (cost-optimized)
- Temperature: 0.3 (consistent evaluation)
- Structured output via Function Calling

## Stage 3: Structured Output Evaluation

**Purpose**: Ensure reliable, schema-compliant assessments

**Function Schema**:
```json
{
  "name": "assess_crisis_level",
  "strict": true,
  "parameters": {
    "risk_level": "none|low|medium|high|critical",
    "reasoning": "string",
    "immediate_action_needed": "boolean",
    "suggested_resources": ["string"],
    "confidence": "number (0-1)"
  }
}
```

**Benefits**:
- 100% schema compliance
- Consistent output format
- Reliable parsing

## Risk Level Classification

### CRITICAL (즉각 개입)
**Indicators**:
- Explicit suicidal intent
- Active self-harm
- Imminent danger
- Concrete plans

**Response**:
- Immediate full-screen intervention
- Disable chat temporarily
- Show emergency contacts
- Alert crisis team

**Korean Resources**:
- 🆘 자살예방상담전화: **1393** (24시간)
- 📱 생명의 전화: **1588-9191** (24시간)
- 💬 정신건강위기상담전화: **1577-0199** (24시간)
- 🏥 응급: **119**

### HIGH (긴급 모니터링)
**Indicators**:
- Strong suicidal ideation
- Specific concerns about dying
- Recent deterioration
- High distress

**Response**:
- Strong recommendation for professional help
- Provide crisis resources
- Flag conversation for review
- Alert monitoring team

### MEDIUM (강화 모니터링)
**Indicators**:
- Feelings of hopelessness
- Mentions of death without intent
- Significant distress
- Warning signs

**Response**:
- Suggest professional consultation
- Provide resources
- Continue empathetic support
- Track conversation progression

### LOW (일반 지원)
**Indicators**:
- Difficult situation
- Stress or sadness
- No immediate risk

**Response**:
- Normal counseling support
- Mention resources available
- Continue conversation

### NONE (정상)
**Indicators**:
- No crisis indicators
- Normal conversation

**Response**:
- Standard AI counseling
- No special alerts

## Emergency Protocols

### Critical Intervention
```python
# Triggered for CRITICAL risk level
1. Display full-screen emergency message
2. Disable chat input temporarily
3. Log to crisis_logs table
4. Send alert to on-call team
5. Create high-priority ticket
6. Notify designated contacts
```

### High Risk Alert
```python
# Triggered for HIGH risk level
1. Show prominent warning message
2. Continue chat with resources
3. Flag for review
4. Alert monitoring team
5. Enable enhanced tracking
```

### Medium Risk Monitoring
```python
# Triggered for MEDIUM risk level
1. Provide resources in conversation
2. Flag for routine review
3. Track progression
4. Log for analysis
```

## Usage Example

### Basic Detection
```python
from app.services.crisis_detector import crisis_detection_system

# Detect crisis in message
assessment = await crisis_detection_system.detect(
    message="죽고 싶어요",
    conversation_history=[...]
)

# Check result
if assessment["risk_level"] == "critical":
    response = crisis_detection_system.critical_response(assessment)
    await emergency_protocol(assessment, user_id, conversation_id)
```

### Full Workflow
```python
# 1. User sends message
user_message = "요즘 살기 힘들어요"

# 2. Detect crisis
assessment = await crisis_detection_system.detect(user_message)

# 3. Get appropriate response
crisis_message = crisis_detection_system.get_crisis_response_message(assessment)

# 4. Execute protocol
await crisis_detection_system.emergency_protocol(
    assessment,
    user_id,
    conversation_id
)

# 5. Return to user
return {
    "ai_response": crisis_message,
    "risk_level": assessment["risk_level"],
    "resources": assessment["suggested_resources"]
}
```

## Testing

### Run All Tests
```bash
pytest tests/test_crisis_detector.py -v
```

### Run Specific Test Category
```bash
# Keyword detection only
pytest tests/test_crisis_detector.py::TestKeywordDetection -v

# Contextual analysis
pytest tests/test_crisis_detector.py::TestContextualAnalysis -v

# Full pipeline
pytest tests/test_crisis_detector.py::TestFullDetection -v
```

### Test Coverage
```bash
pytest tests/test_crisis_detector.py --cov=app.services.crisis_detector --cov-report=html
```

## Performance Benchmarks

- **Keyword Detection**: < 1ms
- **GPT-4 Analysis**: 500-2000ms (depends on API)
- **Total (Critical path)**: < 1ms (keyword bypass)
- **Total (Analysis path)**: 500-2000ms

## Configuration

Environment variables:
```bash
# Crisis detection
CRISIS_KEYWORDS_THRESHOLD=3
CRISIS_ALERT_EMAIL=crisis-team@example.com

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## Logging and Monitoring

All crisis events are logged with:
- Timestamp
- User ID (anonymized for privacy)
- Conversation ID
- Risk level
- Detected keywords
- GPT-4 reasoning
- Confidence score
- Actions taken

**Storage**: `crisis_logs` table (PostgreSQL)

**Retention**: Per HIPAA/GDPR requirements

## Privacy and Compliance

### Data Handling
- ✅ Minimal data collection
- ✅ Encrypted storage
- ✅ Audit trail
- ✅ Anonymization options
- ✅ Data retention policies

### HIPAA Compliance
- ✅ Secure logging
- ✅ Access controls
- ✅ Encryption at rest
- ✅ Audit trails

### Ethical Considerations
- False positives minimized
- User autonomy respected
- Professional help encouraged
- Clear AI limitations stated

## Korean Crisis Resources

### 24-Hour Hotlines
- **자살예방상담전화**: 1393
- **생명의 전화**: 1588-9191
- **정신건강위기상담전화**: 1577-0199
- **청소년전화**: 1388
- **희망의 전화**: 129

### Emergency
- **응급**: 119
- **경찰**: 112

### Online Resources
- [한국자살예방협회](https://www.suicideprevention.or.kr/)
- [중앙자살예방센터](https://www.spckorea.or.kr/)
- [정신건강복지센터](https://www.mentalhealth.go.kr/)

## Limitations

1. **Not a replacement for professional care**
   - System provides initial detection only
   - Always refers to professionals
   - Clear disclaimers shown

2. **False positives possible**
   - Errs on side of caution
   - Context may be misunderstood
   - User verification important

3. **Language limitations**
   - Primarily Korean and English
   - Slang and idioms may be missed
   - Cultural contexts vary

4. **Technical limitations**
   - GPT-4 API latency
   - Network dependencies
   - Rate limiting considerations

## Future Enhancements

- [ ] Multi-language support (Chinese, Japanese)
- [ ] Voice/audio analysis
- [ ] Historical pattern detection
- [ ] Family notification system
- [ ] Integration with emergency services
- [ ] Machine learning risk prediction
- [ ] Sentiment trend analysis

## Support

For questions or issues:
- Technical: See README.md
- Clinical: Consult mental health professionals
- Emergency: Call 1393 or 119

## License

See main project LICENSE file.

---

**Remember**: This system is a tool to assist, not replace, human judgment and professional mental health care.
