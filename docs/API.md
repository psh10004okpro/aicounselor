# AI Counselor API Documentation

Complete API reference for the AI Counselor backend services.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
   - [Authentication](#authentication-endpoints)
   - [Chat](#chat-endpoints)
   - [Conversations](#conversation-endpoints)
   - [User](#user-endpoints)
   - [CBT Stage Management](#cbt-stage-management)
4. [WebSocket](#websocket)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Examples](#examples)

---

## Overview

**Base URL**: `https://api.yourdomain.com` (production) or `http://localhost:8000` (development)

**API Version**: v1

**Content Type**: `application/json`

**Authentication**: JWT Bearer tokens or session tokens

---

## Authentication

The AI Counselor API supports two authentication methods:

### 1. JWT Authentication (Recommended for registered users)

Include the access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

**Token Lifetime**:
- Access Token: 15 minutes
- Refresh Token: 7 days

### 2. Session Token Authentication (For anonymous users)

Include the session token in the `X-Session-Token` header:

```
X-Session-Token: <session_token>
```

---

## Endpoints

### Authentication Endpoints

#### Create Anonymous Session

Create an anonymous user session without registration.

**Endpoint**: `POST /auth/anonymous`

**Request**:
```http
POST /auth/anonymous HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json
```

**Response** (201 Created):
```json
{
  "user": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "is_anonymous": true,
    "consent_given": false,
    "created_at": "2024-01-01T12:00:00Z"
  },
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Example**:
```bash
curl -X POST https://api.yourdomain.com/auth/anonymous \
  -H "Content-Type: application/json"
```

---

#### Register User

Register a new user with email and password.

**Endpoint**: `POST /auth/register`

**Request**:
```http
POST /auth/register HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (201 Created):
```json
{
  "user": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "is_anonymous": false,
    "consent_given": true,
    "created_at": "2024-01-01T12:00:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `400 Bad Request`: Invalid email or password
- `409 Conflict`: Email already registered

**Example**:
```bash
curl -X POST https://api.yourdomain.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

---

#### Login

Login with email and password.

**Endpoint**: `POST /auth/login`

**Request**:
```http
POST /auth/login HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "user": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "is_anonymous": false,
    "consent_given": true,
    "created_at": "2024-01-01T12:00:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `401 Unauthorized`: Invalid credentials

**Example**:
```bash
curl -X POST https://api.yourdomain.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

---

#### Refresh Token

Refresh access token using refresh token.

**Endpoint**: `POST /auth/refresh`

**Request**:
```http
POST /auth/refresh HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `401 Unauthorized`: Invalid or expired refresh token

**Example**:
```bash
curl -X POST https://api.yourdomain.com/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

---

#### Logout

Logout by revoking current access token.

**Endpoint**: `POST /auth/logout`

**Request**:
```http
POST /auth/logout HTTP/1.1
Host: api.yourdomain.com
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "message": "Successfully logged out"
}
```

**Example**:
```bash
curl -X POST https://api.yourdomain.com/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

#### Logout All Devices

Logout from all devices by revoking all tokens.

**Endpoint**: `POST /auth/logout-all`

**Request**:
```http
POST /auth/logout-all HTTP/1.1
Host: api.yourdomain.com
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "message": "Successfully logged out from all devices"
}
```

**Example**:
```bash
curl -X POST https://api.yourdomain.com/auth/logout-all \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Chat Endpoints

#### Send Message

Send a message to the AI counselor and receive a response.

**Endpoint**: `POST /chat/send`

**Request**:
```http
POST /chat/send HTTP/1.1
Host: api.yourdomain.com
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "message": "안녕하세요, 요즘 스트레스가 심해요",
  "conversation_id": "conv_123456",
  "stream": false
}
```

**Query Parameters**:
- `stream` (optional): If `true`, returns Server-Sent Events (SSE) stream

**Response** (200 OK):
```json
{
  "message_id": "msg_123456",
  "conversation_id": "conv_123456",
  "role": "assistant",
  "content": "안녕하세요. 스트레스를 받고 계시다니 안타깝네요. 어떤 부분에서 스트레스를 받고 계신가요?",
  "timestamp": "2024-01-01T12:00:00Z",
  "crisis_detected": false,
  "risk_level": "none"
}
```

**Streaming Response** (text/event-stream):
```
data: {"type": "token", "content": "안녕하세요"}

data: {"type": "token", "content": ". "}

data: {"type": "token", "content": "스트레스를"}

data: {"type": "done", "message_id": "msg_123456"}
```

**Errors**:
- `400 Bad Request`: Invalid message or missing required fields
- `401 Unauthorized`: Invalid or missing authentication
- `429 Too Many Requests`: Rate limit exceeded

**Example**:
```bash
# Non-streaming
curl -X POST https://api.yourdomain.com/chat/send \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요, 요즘 스트레스가 심해요",
    "conversation_id": "conv_123456",
    "stream": false
  }'

# Streaming
curl -N -X POST https://api.yourdomain.com/chat/send \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요",
    "stream": true
  }'
```

---

#### Get Message History

Retrieve conversation message history.

**Endpoint**: `GET /chat/history/{conversation_id}`

**Request**:
```http
GET /chat/history/conv_123456 HTTP/1.1
Host: api.yourdomain.com
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `limit` (optional): Number of messages to return (default: 50, max: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response** (200 OK):
```json
{
  "conversation_id": "conv_123456",
  "messages": [
    {
      "message_id": "msg_001",
      "role": "user",
      "content": "안녕하세요",
      "timestamp": "2024-01-01T12:00:00Z",
      "crisis_detected": false
    },
    {
      "message_id": "msg_002",
      "role": "assistant",
      "content": "안녕하세요. 무엇을 도와드릴까요?",
      "timestamp": "2024-01-01T12:00:05Z"
    }
  ],
  "total": 2,
  "limit": 50,
  "offset": 0
}
```

**Example**:
```bash
curl -X GET "https://api.yourdomain.com/chat/history/conv_123456?limit=20" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

#### Clear Conversation

Clear all messages in a conversation.

**Endpoint**: `DELETE /chat/history/{conversation_id}`

**Request**:
```http
DELETE /chat/history/conv_123456 HTTP/1.1
Host: api.yourdomain.com
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "message": "Conversation history cleared",
  "conversation_id": "conv_123456"
}
```

**Example**:
```bash
curl -X DELETE https://api.yourdomain.com/chat/history/conv_123456 \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Conversation Endpoints

#### List Conversations

Get all conversations for the current user.

**Endpoint**: `GET /conversations`

**Request**:
```http
GET /conversations HTTP/1.1
Host: api.yourdomain.com
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `limit` (optional): Number of conversations (default: 20, max: 100)
- `offset` (optional): Pagination offset (default: 0)

**Response** (200 OK):
```json
{
  "conversations": [
    {
      "conversation_id": "conv_123456",
      "title": "스트레스 관리",
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T13:00:00Z",
      "message_count": 10,
      "last_message": "감사합니다. 많은 도움이 되었어요."
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

**Example**:
```bash
curl -X GET https://api.yourdomain.com/conversations \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

#### Create Conversation

Create a new conversation.

**Endpoint**: `POST /conversations`

**Request**:
```http
POST /conversations HTTP/1.1
Host: api.yourdomain.com
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "title": "새로운 상담"
}
```

**Response** (201 Created):
```json
{
  "conversation_id": "conv_789012",
  "title": "새로운 상담",
  "created_at": "2024-01-01T14:00:00Z"
}
```

**Example**:
```bash
curl -X POST https://api.yourdomain.com/conversations \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"title": "새로운 상담"}'
```

---

#### Delete Conversation

Delete a conversation and all its messages.

**Endpoint**: `DELETE /conversations/{conversation_id}`

**Request**:
```http
DELETE /conversations/conv_123456 HTTP/1.1
Host: api.yourdomain.com
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "message": "Conversation deleted successfully",
  "conversation_id": "conv_123456"
}
```

**Example**:
```bash
curl -X DELETE https://api.yourdomain.com/conversations/conv_123456 \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### User Endpoints

#### Get Current User

Get current user profile.

**Endpoint**: `GET /users/me`

**Request**:
```http
GET /users/me HTTP/1.1
Host: api.yourdomain.com
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "is_anonymous": false,
  "consent_given": true,
  "created_at": "2024-01-01T12:00:00Z",
  "last_active": "2024-01-01T14:00:00Z",
  "metadata": {
    "preferred_language": "ko",
    "timezone": "Asia/Seoul"
  }
}
```

**Example**:
```bash
curl -X GET https://api.yourdomain.com/users/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

#### Update User Consent

Update user consent for data processing.

**Endpoint**: `PUT /users/me/consent`

**Request**:
```http
PUT /users/me/consent HTTP/1.1
Host: api.yourdomain.com
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "consent_given": true
}
```

**Response** (200 OK):
```json
{
  "message": "Consent updated successfully",
  "consent_given": true,
  "consent_timestamp": "2024-01-01T14:00:00Z"
}
```

**Example**:
```bash
curl -X PUT https://api.yourdomain.com/users/me/consent \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"consent_given": true}'
```

---

#### Delete User Account

Delete user account and all associated data (GDPR compliance).

**Endpoint**: `DELETE /users/me`

**Request**:
```http
DELETE /users/me HTTP/1.1
Host: api.yourdomain.com
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "message": "Account deleted successfully"
}
```

**Note**: This is a soft delete. Data is marked as deleted but retained for 30 days before permanent deletion.

**Example**:
```bash
curl -X DELETE https://api.yourdomain.com/users/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Health Check

Check API health status.

**Endpoint**: `GET /health`

**Request**:
```http
GET /health HTTP/1.1
Host: api.yourdomain.com
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2024-01-01T14:00:00Z",
  "version": "1.0.0"
}
```

**Example**:
```bash
curl -X GET https://api.yourdomain.com/health
```

---

## WebSocket

### Chat WebSocket

Real-time chat using WebSocket for lower latency.

**Endpoint**: `ws://api.yourdomain.com/ws/chat`

**Connection**:
```javascript
const ws = new WebSocket('wss://api.yourdomain.com/ws/chat');

// Send authentication
ws.send(JSON.stringify({
  type: 'auth',
  token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
}));

// Send message
ws.send(JSON.stringify({
  type: 'message',
  conversation_id: 'conv_123456',
  content: '안녕하세요'
}));

// Receive messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

**Message Types**:

1. **Authentication**:
```json
{
  "type": "auth",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

2. **Send Message**:
```json
{
  "type": "message",
  "conversation_id": "conv_123456",
  "content": "안녕하세요"
}
```

3. **Receive Token** (streaming response):
```json
{
  "type": "token",
  "content": "안녕하세요"
}
```

4. **Message Complete**:
```json
{
  "type": "done",
  "message_id": "msg_123456",
  "crisis_detected": false,
  "risk_level": "none"
}
```

5. **Error**:
```json
{
  "type": "error",
  "message": "Rate limit exceeded"
}
```

---

## Error Handling

All errors follow a consistent format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-01T14:00:00Z"
}
```

### HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required or invalid
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource already exists
- `413 Payload Too Large`: Request body too large (max 10MB)
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

### Common Error Codes

- `INVALID_TOKEN`: JWT token is invalid or expired
- `TOKEN_REVOKED`: Token has been revoked
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INVALID_CREDENTIALS`: Login credentials are incorrect
- `EMAIL_ALREADY_EXISTS`: Email already registered
- `CONVERSATION_NOT_FOUND`: Conversation does not exist
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions
- `OPENAI_API_ERROR`: Error communicating with OpenAI API

---

## Rate Limiting

The API implements rate limiting to prevent abuse:

### Limits

- **Global**: 100 requests per minute per IP
- **Per Hour**: 1000 requests per hour per IP
- **Chat**: 10 messages per minute per user
- **Registration**: 5 attempts per hour per IP

### Headers

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704110400
```

### Handling Rate Limits

When rate limit is exceeded, API returns `429 Too Many Requests`:

```json
{
  "detail": "Rate limit exceeded. Please try again later.",
  "retry_after": 60
}
```

Wait for the time specified in `retry_after` (seconds) before retrying.

---

## Examples

### Complete Chat Flow

```javascript
// 1. Create anonymous session
const sessionResponse = await fetch('https://api.yourdomain.com/auth/anonymous', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' }
});
const { user, session_token } = await sessionResponse.json();

// 2. Send message
const chatResponse = await fetch('https://api.yourdomain.com/chat/send', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Session-Token': session_token
  },
  body: JSON.stringify({
    message: '안녕하세요',
    stream: false
  })
});
const message = await chatResponse.json();
console.log(message.content);

// 3. Get conversation history
const historyResponse = await fetch(
  `https://api.yourdomain.com/chat/history/${message.conversation_id}`,
  {
    headers: { 'X-Session-Token': session_token }
  }
);
const history = await historyResponse.json();
console.log(history.messages);
```

### Streaming Chat

```javascript
// Using EventSource for SSE
const eventSource = new EventSource(
  'https://api.yourdomain.com/chat/send',
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify({
      message: '안녕하세요',
      stream: true
    })
  }
);

let fullResponse = '';

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'token') {
    fullResponse += data.content;
    console.log(fullResponse);
  } else if (data.type === 'done') {
    console.log('Complete:', data.message_id);
    eventSource.close();
  }
};

eventSource.onerror = (error) => {
  console.error('Error:', error);
  eventSource.close();
};
```

### User Registration and Login

```javascript
// Register
const registerResponse = await fetch('https://api.yourdomain.com/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePassword123!'
  })
});
const { access_token, refresh_token } = await registerResponse.json();

// Store tokens securely
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);

// Use access token for authenticated requests
const userResponse = await fetch('https://api.yourdomain.com/users/me', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const user = await userResponse.json();
```

### Token Refresh

```javascript
async function refreshAccessToken() {
  const refresh_token = localStorage.getItem('refresh_token');

  const response = await fetch('https://api.yourdomain.com/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token })
  });

  if (response.ok) {
    const { access_token } = await response.json();
    localStorage.setItem('access_token', access_token);
    return access_token;
  } else {
    // Refresh failed, redirect to login
    window.location.href = '/login';
  }
}

// Automatically refresh before expiration
setInterval(refreshAccessToken, 14 * 60 * 1000); // 14 minutes
```

---

## CBT Stage Management

The AI Counselor implements a sophisticated 6-stage CBT (Cognitive Behavioral Therapy) framework with dynamic prompting that adapts to the user's therapeutic progress.

### CBT Stages Overview

The system follows these 6 therapeutic stages:

1. **Assessment (초기 평가)**: Rapport building, problem identification, trust establishment
2. **Reconceptualization (재개념화)**: Understanding thought-emotion-behavior connections, ABC model learning
3. **Skills Acquisition (기술 습득)**: Learning CBT techniques (cognitive restructuring, problem-solving)
4. **Skills Application (기술 적용)**: Applying learned techniques in real-life situations
5. **Generalization (일반화 및 유지)**: Relapse prevention planning, long-term application
6. **Termination (종결)**: Celebrating achievements, future planning, positive closure

### CBT Endpoints

#### Get Current Stage

Get the current CBT stage and progress for a conversation.

**Endpoint**: `GET /cbt/stages/{conversation_id}`

**Request**:
```http
GET /cbt/stages/123e4567-e89b-12d3-a456-426614174000 HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json
```

**Response** (200 OK):
```json
{
  "success": true,
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "current_stage": {
    "stage_number": 2,
    "stage_name": "reconceptualization",
    "korean_name": "재개념화"
  },
  "progress": {
    "current_stage": 2,
    "stage_name": "reconceptualization",
    "stage_progress": 65,
    "goals_achieved": [
      "abc_model_understood",
      "thought_emotion_connection_clear"
    ],
    "goals_pending": [
      "identify_cognitive_distortions"
    ],
    "readiness_for_next_stage": 60,
    "stage_history": [
      {
        "from_stage": 1,
        "to_stage": 2,
        "transitioned_at": "2024-01-05T10:30:00Z",
        "goals_achieved": ["rapport_built", "problem_identified"]
      }
    ]
  }
}
```

---

#### Initialize CBT Stage

Initialize CBT stage tracking for a new conversation. Automatically starts at Stage 1 (Assessment).

**Endpoint**: `POST /cbt/stages/{conversation_id}/initialize`

**Request**:
```http
POST /cbt/stages/123e4567-e89b-12d3-a456-426614174000/initialize HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "CBT stage initialized successfully",
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "initial_stage": {
    "stage_number": 1,
    "stage_name": "assessment",
    "korean_name": "초기 평가"
  }
}
```

---

#### Assess Stage Progress

Manually trigger a progress assessment for the current stage.

**Endpoint**: `POST /cbt/stages/{conversation_id}/assess`

**Request**:
```http
POST /cbt/stages/123e4567-e89b-12d3-a456-426614174000/assess HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json

{
  "recent_messages": [
    {"role": "user", "content": "I've been practicing the techniques you taught me"},
    {"role": "assistant", "content": "That's wonderful! How has it been going?"},
    {"role": "user", "content": "I can identify my negative thoughts now"}
  ]
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "assessment": {
    "progress_percentage": 75,
    "goals_achieved": ["abc_model_understood", "thought_emotion_connection_clear"],
    "goals_pending": ["identify_cognitive_distortions"],
    "readiness_score": 70,
    "recommendation": "continue",
    "reasoning": "Client is making good progress understanding the ABC model and identifying thought-emotion connections. Continue reinforcing these concepts before advancing."
  }
}
```

---

#### Advance to Next Stage

Advance the conversation to the next CBT stage.

**Endpoint**: `POST /cbt/stages/{conversation_id}/advance`

**Query Parameters**:
- `force` (boolean, optional): Force transition even if not ready (default: false)

**Request**:
```http
POST /cbt/stages/123e4567-e89b-12d3-a456-426614174000/advance?force=false HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Successfully advanced to next stage",
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "previous_stage": 2,
  "current_stage": {
    "stage_number": 3,
    "stage_name": "skills_acquisition",
    "korean_name": "기술 습득"
  }
}
```

**Response** (400 Bad Request - Not Ready):
```json
{
  "success": false,
  "message": "Not ready to advance. Readiness score: 45% (requires 70%+)"
}
```

---

#### Get Stage History

Get the complete stage transition history for a conversation.

**Endpoint**: `GET /cbt/stages/{conversation_id}/history`

**Request**:
```http
GET /cbt/stages/123e4567-e89b-12d3-a456-426614174000/history HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json
```

**Response** (200 OK):
```json
{
  "success": true,
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "stage_history": [
    {
      "from_stage": 1,
      "to_stage": 2,
      "transitioned_at": "2024-01-05T10:30:00Z",
      "goals_achieved": ["rapport_built", "problem_identified", "goals_established"]
    },
    {
      "from_stage": 2,
      "to_stage": 3,
      "transitioned_at": "2024-01-12T14:20:00Z",
      "goals_achieved": ["abc_model_understood", "thought_emotion_connection_clear"]
    }
  ],
  "current_stage": {
    "stage_number": 3,
    "stage_name": "skills_acquisition"
  }
}
```

---

#### Get Assessment History

Get the history of automatic assessments performed during the conversation.

**Endpoint**: `GET /cbt/stages/{conversation_id}/assessments`

**Query Parameters**:
- `limit` (integer, optional): Maximum number of assessments to return (default: 10)

**Request**:
```http
GET /cbt/stages/123e4567-e89b-12d3-a456-426614174000/assessments?limit=5 HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json
```

**Response** (200 OK):
```json
{
  "success": true,
  "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
  "assessments": [
    {
      "assessment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "stage": 3,
      "stage_name": "skills_acquisition",
      "assessment_type": "automatic",
      "assessment_result": {
        "progress_percentage": 80,
        "readiness_score": 75,
        "recommendation": "continue"
      },
      "messages_analyzed": 6,
      "assessed_at": "2024-01-15T16:45:00Z"
    }
  ],
  "total": 5
}
```

---

#### Get All Stages Information

Get comprehensive information about all 6 CBT stages.

**Endpoint**: `GET /cbt/info/stages`

**Request**:
```http
GET /cbt/info/stages HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json
```

**Response** (200 OK):
```json
{
  "success": true,
  "total_stages": 6,
  "stages": [
    {
      "stage_number": 1,
      "stage_name": "assessment",
      "korean_name": "초기 평가",
      "goals": [
        "rapport_built",
        "problem_identified",
        "goals_established"
      ],
      "description": "라포 형성, 문제 파악, 신뢰 구축을 목표로 하는 초기 평가 단계"
    },
    {
      "stage_number": 2,
      "stage_name": "reconceptualization",
      "korean_name": "재개념화",
      "goals": [
        "abc_model_understood",
        "thought_emotion_connection_clear",
        "identify_cognitive_distortions"
      ],
      "description": "생각-감정-행동 연결고리 이해, ABC 모델 학습 단계"
    }
  ]
}
```

---

#### Get Specific Stage Information

Get detailed information about a specific CBT stage.

**Endpoint**: `GET /cbt/info/stages/{stage_number}`

**Path Parameters**:
- `stage_number` (integer): Stage number (1-6)

**Request**:
```http
GET /cbt/info/stages/3 HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json
```

**Response** (200 OK):
```json
{
  "success": true,
  "stage": {
    "stage_number": 3,
    "stage_name": "skills_acquisition",
    "korean_name": "기술 습득",
    "goals": [
      "learn_cognitive_restructuring",
      "learn_problem_solving",
      "practice_behavioral_activation"
    ],
    "description": "인지 재구조화, 문제 해결 등 CBT 기법을 배우는 단계",
    "system_prompt_preview": "당신은 현재 **3단계: 기술 습득 (Skills Acquisition)** 단계에 있습니다..."
  }
}
```

**Response** (400 Bad Request - Invalid Stage):
```json
{
  "detail": "Stage number must be between 1 and 6"
}
```

---

### CBT Integration Features

#### Dynamic Prompting

The system automatically adapts its therapeutic approach based on the current stage:

- **Stage-Specific Prompts**: Each stage has a detailed system prompt (500-2000+ characters) guiding the AI's behavior
- **Real-Time Progress**: Progress information is injected into prompts for context-aware responses
- **Goal-Oriented**: AI focuses on achieving specific therapeutic goals for each stage

#### Automatic Assessment

Progress is automatically assessed every 3 message exchanges:

- **GPT-4 Analysis**: Uses GPT-4 to analyze recent conversation for progress indicators
- **Readiness Scoring**: Calculates readiness for next stage (0-100%)
- **Recommendations**: Provides actionable recommendations (continue, advance, review)

#### Stage Transition Rules

Transitions between stages follow these rules:

- **Readiness Threshold**: Requires 70%+ readiness score (unless forced)
- **Goal Achievement**: Tracks required vs. optional goals per stage
- **Audit Trail**: Records all transitions with timestamps and achieved goals
- **Final Stage Lock**: Cannot advance beyond Stage 6 (Termination)

#### Frontend Integration

The frontend displays real-time stage information:

- **Stage Indicator**: Visual component showing current stage and progress
- **Progress Bar**: Animated progress bar (0-100%)
- **Goals Tracker**: Shows achieved and pending goals
- **Readiness Badge**: Displays when ready for next stage

---

### CBT Usage Example

Complete flow of CBT stage management:

```javascript
// 1. Create a new conversation
const session = await createAnonymousSession();
const conversationResponse = await sendMessage({
  message: "안녕하세요, 요즘 불안감이 심해요",
  sessionToken: session.session_token
});

const conversationId = conversationResponse.conversation_id;

// 2. Initialize CBT stage tracking (happens automatically in chat endpoint)
// But can be done manually if needed
await fetch(`/cbt/stages/${conversationId}/initialize`, {
  method: 'POST'
});

// 3. Get current stage
const stageInfo = await fetch(`/cbt/stages/${conversationId}`);
console.log(stageInfo.current_stage); // Stage 1: Assessment

// 4. Continue conversation (automatic assessments every 3 exchanges)
// ...after several messages...

// 5. Check progress
const progress = await fetch(`/cbt/stages/${conversationId}`);
console.log(progress.progress.readiness_for_next_stage); // 75%

// 6. Advance to next stage when ready
if (progress.progress.readiness_for_next_stage >= 70) {
  const advanceResult = await fetch(
    `/cbt/stages/${conversationId}/advance`,
    { method: 'POST' }
  );
  console.log(advanceResult.current_stage); // Stage 2: Reconceptualization
}

// 7. View stage history
const history = await fetch(`/cbt/stages/${conversationId}/history`);
console.log(history.stage_history); // Array of transitions
```

---

## SDKs and Client Libraries

### JavaScript/TypeScript

```bash
npm install @aicounselor/client
```

```typescript
import { AICounselorClient } from '@aicounselor/client';

const client = new AICounselorClient({
  baseUrl: 'https://api.yourdomain.com'
});

// Create session
const session = await client.auth.createAnonymousSession();

// Send message
const response = await client.chat.sendMessage({
  message: '안녕하세요',
  sessionToken: session.session_token
});

console.log(response.content);
```

### Python

```bash
pip install aicounselor-client
```

```python
from aicounselor import AICounselorClient

client = AICounselorClient(base_url='https://api.yourdomain.com')

# Create session
session = client.auth.create_anonymous_session()

# Send message
response = client.chat.send_message(
    message='안녕하세요',
    session_token=session.session_token
)

print(response.content)
```

---

## Support

For API support and questions:

- **Documentation**: https://docs.yourdomain.com
- **GitHub Issues**: https://github.com/yourusername/aicounselor/issues
- **Email**: support@yourdomain.com

---

**Last Updated**: 2024-01-01
**API Version**: v1.0
**Status**: Production
