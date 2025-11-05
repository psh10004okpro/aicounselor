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
