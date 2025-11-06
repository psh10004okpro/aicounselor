# Frontend Integration Guide

Complete guide for integrating the Mindful AI Counselor backend APIs with your frontend application.

## Table of Contents

- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [API Modules](#api-modules)
  - [Chat API](#chat-api)
  - [Conversations API](#conversations-api)
  - [User Profile API](#user-profile-api)
  - [Session Management API](#session-management-api)
  - [Data Export API](#data-export-api)
- [WebSocket Integration](#websocket-integration)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

## Quick Start

### Base URL

```
Development: http://localhost:8000
Production: https://your-domain.com
```

### API Documentation

Interactive API docs available at:
- Swagger UI: `{BASE_URL}/docs`
- ReDoc: `{BASE_URL}/redoc`

### CORS Configuration

The backend accepts requests from origins configured in `ALLOWED_ORIGINS` environment variable.

## Authentication

The system supports anonymous users with session tokens.

### Create Anonymous User

```javascript
// POST /api/v1/auth/anonymous
const response = await fetch(`${BASE_URL}/api/v1/auth/anonymous`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
// Returns: { session_token, user_id, expires_at }

// Store session token for future requests
localStorage.setItem('session_token', data.session_token);
```

### Include Session Token in Requests

```javascript
const sessionToken = localStorage.getItem('session_token');

const response = await fetch(`${BASE_URL}/api/v1/endpoint`, {
  method: 'GET',
  headers: {
    'X-Session-Token': sessionToken
  }
});
```

## API Modules

### Chat API

#### Send Chat Message

```javascript
// POST /api/v1/chat/send
async function sendMessage(conversationId, message, age = null) {
  const response = await fetch(`${BASE_URL}/api/v1/chat/send`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-Token': sessionToken
    },
    body: JSON.stringify({
      conversation_id: conversationId,  // Optional, will create new if null
      message: message,
      age: age  // Optional, enables age-appropriate responses
    })
  });

  return await response.json();
  // Returns: { user_message, assistant_message, crisis_detected, conversation_id }
}
```

#### Stream Chat Response (Server-Sent Events)

```javascript
// POST /api/v1/chat/stream
async function streamMessage(conversationId, message, onChunk, onComplete) {
  const response = await fetch(`${BASE_URL}/api/v1/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-Token': sessionToken
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      message: message,
      age: null
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));

        if (data.type === 'token') {
          onChunk(data.content);
        } else if (data.type === 'done') {
          onComplete(data);
          break;
        } else if (data.type === 'error') {
          console.error('Stream error:', data.error);
        }
      }
    }
  }
}

// Usage
streamMessage(
  conversationId,
  "I'm feeling anxious today",
  (chunk) => {
    // Append chunk to UI
    appendToMessage(chunk);
  },
  (result) => {
    // Handle completion
    console.log('Message complete:', result);
  }
);
```

### Conversations API

#### List Conversations

```javascript
// GET /api/v1/conversations
async function getConversations(page = 1, pageSize = 20, status = null) {
  const params = new URLSearchParams({
    page: page,
    page_size: pageSize
  });

  if (status) {
    params.append('status_filter', status);
  }

  const response = await fetch(
    `${BASE_URL}/api/v1/conversations?${params}`,
    {
      headers: {
        'X-Session-Token': sessionToken
      }
    }
  );

  return await response.json();
  // Returns: { conversations, total, page, page_size, has_more }
}
```

#### Get Conversation Details

```javascript
// GET /api/v1/conversations/{id}
async function getConversation(conversationId, includeMessages = false) {
  const params = new URLSearchParams({
    include_messages: includeMessages
  });

  const response = await fetch(
    `${BASE_URL}/api/v1/conversations/${conversationId}?${params}`,
    {
      headers: {
        'X-Session-Token': sessionToken
      }
    }
  );

  return await response.json();
  // Returns: { conversation, messages (if included) }
}
```

#### Get Conversation Messages

```javascript
// GET /api/v1/conversations/{id}/messages
async function getMessages(conversationId, page = 1, pageSize = 50) {
  const params = new URLSearchParams({
    page: page,
    page_size: pageSize
  });

  const response = await fetch(
    `${BASE_URL}/api/v1/conversations/${conversationId}/messages?${params}`,
    {
      headers: {
        'X-Session-Token': sessionToken
      }
    }
  );

  return await response.json();
  // Returns: { messages, total, page, page_size, has_more }
}
```

#### Update Conversation

```javascript
// PUT /api/v1/conversations/{id}
async function updateConversation(conversationId, updates) {
  const response = await fetch(
    `${BASE_URL}/api/v1/conversations/${conversationId}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken
      },
      body: JSON.stringify({
        title: updates.title,           // Optional
        summary: updates.summary,       // Optional
        status: updates.status          // Optional: active, archived, completed
      })
    }
  );

  return await response.json();
}
```

#### Delete Conversation

```javascript
// DELETE /api/v1/conversations/{id}
async function deleteConversation(conversationId, hardDelete = false) {
  const params = new URLSearchParams({
    hard_delete: hardDelete
  });

  const response = await fetch(
    `${BASE_URL}/api/v1/conversations/${conversationId}?${params}`,
    {
      method: 'DELETE',
      headers: {
        'X-Session-Token': sessionToken
      }
    }
  );

  return await response.json();
  // Returns: { success, message }
}
```

#### Search Conversations

```javascript
// GET /api/v1/conversations/search/query
async function searchConversations(query) {
  const params = new URLSearchParams({
    query: query
  });

  const response = await fetch(
    `${BASE_URL}/api/v1/conversations/search/query?${params}`,
    {
      headers: {
        'X-Session-Token': sessionToken
      }
    }
  );

  return await response.json();
  // Returns: { results: [...], count }
}
```

### User Profile API

#### Get Profile

```javascript
// GET /api/v1/users/me
async function getProfile() {
  const response = await fetch(`${BASE_URL}/api/v1/users/me`, {
    headers: {
      'X-Session-Token': sessionToken
    }
  });

  return await response.json();
  // Returns: { id, email, is_anonymous, age, display_name, preferences, ... }
}
```

#### Update Profile

```javascript
// PUT /api/v1/users/me
async function updateProfile(updates) {
  const response = await fetch(`${BASE_URL}/api/v1/users/me`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-Token': sessionToken
    },
    body: JSON.stringify({
      age: updates.age,                      // Optional
      display_name: updates.displayName,     // Optional
      preferences: updates.preferences       // Optional: object with user preferences
    })
  });

  return await response.json();
}
```

#### Get Statistics

```javascript
// GET /api/v1/users/me/statistics
async function getStatistics() {
  const response = await fetch(`${BASE_URL}/api/v1/users/me/statistics`, {
    headers: {
      'X-Session-Token': sessionToken
    }
  });

  return await response.json();
  // Returns: {
  //   user_id, total_conversations, total_messages, total_sessions,
  //   crisis_events_count, average_crisis_level, days_active,
  //   emotion_distribution, crisis_level_trend
  // }
}
```

### Session Management API

#### Start Session

```javascript
// POST /api/v1/sessions/start
async function startSession(conversationId = null, title = null) {
  const response = await fetch(`${BASE_URL}/api/v1/sessions/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-Token': sessionToken
    },
    body: JSON.stringify({
      conversation_id: conversationId,  // Optional, creates new if null
      title: title                       // Optional
    })
  });

  return await response.json();
  // Returns: { session_id, conversation_id, started_at, ... }
}
```

#### End Session

```javascript
// PUT /api/v1/sessions/{id}/end
async function endSession(sessionId, notes = null) {
  const response = await fetch(
    `${BASE_URL}/api/v1/sessions/${sessionId}/end`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken
      },
      body: JSON.stringify({
        notes: notes  // Optional closing notes
      })
    }
  );

  return await response.json();
  // Returns: { session (with calculated duration_minutes) }
}
```

#### Get AI Summary

```javascript
// GET /api/v1/sessions/{id}/summary
async function getSessionSummary(sessionId, regenerate = false) {
  const params = new URLSearchParams({
    regenerate: regenerate
  });

  const response = await fetch(
    `${BASE_URL}/api/v1/sessions/${sessionId}/summary?${params}`,
    {
      headers: {
        'X-Session-Token': sessionToken
      }
    }
  );

  return await response.json();
  // Returns: {
  //   session_id, summary, key_topics, emotions_detected,
  //   crisis_level, progress_notes, recommendations, generated_at
  // }
}
```

#### List Sessions

```javascript
// GET /api/v1/sessions
async function getSessions(page = 1, pageSize = 20) {
  const params = new URLSearchParams({
    page: page,
    page_size: pageSize
  });

  const response = await fetch(
    `${BASE_URL}/api/v1/sessions?${params}`,
    {
      headers: {
        'X-Session-Token': sessionToken
      }
    }
  );

  return await response.json();
  // Returns: { sessions, total, page, page_size, has_more }
}
```

#### Add Session Note

```javascript
// POST /api/v1/sessions/{id}/notes
async function addNote(sessionId, content) {
  const response = await fetch(
    `${BASE_URL}/api/v1/sessions/${sessionId}/notes`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken
      },
      body: JSON.stringify({
        content: content
      })
    }
  );

  return await response.json();
  // Returns: { session (with updated notes array) }
}
```

### Data Export API

#### Export Conversation

```javascript
// POST /api/v1/export/conversations/{id}
async function exportConversation(conversationId, format = 'pdf', options = {}) {
  const response = await fetch(
    `${BASE_URL}/api/v1/export/conversations/${conversationId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken
      },
      body: JSON.stringify({
        format: format,  // 'pdf' or 'json'
        include_metadata: options.includeMetadata !== false,
        include_system_messages: options.includeSystemMessages || false
      })
    }
  );

  // For PDF, download as file
  if (format === 'pdf') {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation_${conversationId}.pdf`;
    a.click();
  } else {
    // For JSON, return data
    return await response.json();
  }
}
```

#### Export Progress Report

```javascript
// POST /api/v1/export/progress-report
async function exportProgressReport(format = 'pdf', dateRange = {}) {
  const response = await fetch(
    `${BASE_URL}/api/v1/export/progress-report`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken
      },
      body: JSON.stringify({
        format: format,  // 'pdf' or 'json'
        include_statistics: true,
        include_crisis_history: true,
        include_emotion_timeline: true,
        date_from: dateRange.from || null,  // ISO datetime
        date_to: dateRange.to || null        // ISO datetime
      })
    }
  );

  if (format === 'pdf') {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'progress_report.pdf';
    a.click();
  } else {
    return await response.json();
  }
}
```

#### Export All Data (GDPR)

```javascript
// POST /api/v1/export/all-data
async function exportAllData(format = 'json') {
  const response = await fetch(
    `${BASE_URL}/api/v1/export/all-data`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken
      },
      body: JSON.stringify({
        format: format,  // 'json' or 'zip'
        include_deleted: false
      })
    }
  );

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `user_data_export.${format}`;
  a.click();
}
```

## WebSocket Integration

For real-time features (future implementation):

```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${conversationId}?token=${sessionToken}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

ws.send(JSON.stringify({
  type: 'message',
  content: 'Hello'
}));
```

## Error Handling

### Standard Error Response

```javascript
{
  "detail": "Error message",
  "status_code": 400
}
```

### Common Status Codes

- `200` - Success
- `400` - Bad Request (validation error)
- `401` - Unauthorized (invalid/expired session token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Validation Error (check request body)
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error

### Error Handling Example

```javascript
async function apiRequest(url, options = {}) {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Request failed');
    }

    return await response.json();
  } catch (error) {
    if (error.message.includes('session_token')) {
      // Session expired, create new anonymous user
      await createAnonymousUser();
      // Retry request
      return apiRequest(url, options);
    }

    // Handle other errors
    console.error('API Error:', error);
    throw error;
  }
}
```

## Best Practices

### 1. Session Token Management

```javascript
// Check token expiration
function isTokenExpired() {
  const expiresAt = localStorage.getItem('token_expires_at');
  return !expiresAt || new Date(expiresAt) < new Date();
}

// Refresh token if needed
async function ensureValidToken() {
  if (isTokenExpired()) {
    const data = await createAnonymousUser();
    localStorage.setItem('session_token', data.session_token);
    localStorage.setItem('token_expires_at', data.expires_at);
  }
}
```

### 2. Rate Limiting

```javascript
// Implement exponential backoff for rate limit errors
async function apiWithRetry(url, options, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fetch(url, options);
    } catch (error) {
      if (error.status === 429 && i < maxRetries - 1) {
        const delay = Math.pow(2, i) * 1000; // Exponential backoff
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      throw error;
    }
  }
}
```

### 3. Crisis Detection Handling

```javascript
// Monitor crisis detection in responses
function handleChatResponse(data) {
  if (data.crisis_detected) {
    // Show crisis resources
    showCrisisResources({
      level: data.crisis_severity,
      keywords: data.crisis_keywords_found
    });
  }

  // Display message normally
  displayMessage(data.assistant_message);
}
```

### 4. Pagination

```javascript
// Infinite scroll implementation
async function loadMoreMessages(conversationId, page) {
  const data = await getMessages(conversationId, page);

  // Append messages to UI
  appendMessages(data.messages);

  // Check if more pages exist
  if (data.has_more) {
    // Load next page when user scrolls
    setupInfiniteScroll(() => loadMoreMessages(conversationId, page + 1));
  }
}
```

### 5. Optimistic Updates

```javascript
// Optimistically add user message to UI
function sendMessageOptimistic(message) {
  const tempMessage = {
    id: 'temp-' + Date.now(),
    role: 'user',
    content: message,
    created_at: new Date().toISOString()
  };

  // Add to UI immediately
  addMessageToUI(tempMessage);

  // Send to API
  sendMessage(conversationId, message).then((data) => {
    // Replace temp message with real one
    replaceMessage(tempMessage.id, data.user_message);
    addMessageToUI(data.assistant_message);
  }).catch((error) => {
    // Remove temp message and show error
    removeMessage(tempMessage.id);
    showError(error);
  });
}
```

### 6. TypeScript Types

```typescript
// Define types for better type safety
interface Message {
  message_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  contains_crisis_keywords: boolean;
  detected_keywords: string[];
}

interface Conversation {
  conversation_id: string;
  title?: string;
  summary?: string;
  status: 'active' | 'archived' | 'completed';
  crisis_detected: boolean;
  crisis_severity: number;
  message_count: number;
  created_at: string;
  updated_at: string;
}

interface Session {
  session_id: string;
  conversation_id: string;
  started_at: string;
  ended_at?: string;
  duration_minutes?: number;
  summary?: string;
  message_count: number;
  crisis_level: number;
}
```

## Example: Complete Chat Component

```javascript
class ChatComponent {
  constructor(baseUrl, sessionToken) {
    this.baseUrl = baseUrl;
    this.sessionToken = sessionToken;
    this.conversationId = null;
    this.sessionId = null;
  }

  async initialize() {
    // Start a new session
    const session = await this.startSession();
    this.sessionId = session.session_id;
    this.conversationId = session.conversation_id;
  }

  async startSession() {
    const response = await fetch(`${this.baseUrl}/api/v1/sessions/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': this.sessionToken
      },
      body: JSON.stringify({})
    });
    return await response.json();
  }

  async sendMessage(message) {
    // Show user message immediately
    this.displayMessage({ role: 'user', content: message });

    // Stream AI response
    const response = await fetch(`${this.baseUrl}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': this.sessionToken
      },
      body: JSON.stringify({
        conversation_id: this.conversationId,
        message: message
      })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let assistantMessage = '';

    // Create message container
    this.createMessageContainer('assistant');

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));

          if (data.type === 'token') {
            assistantMessage += data.content;
            this.updateMessage('assistant', assistantMessage);
          } else if (data.type === 'done') {
            this.finalizeMessage(data);
            break;
          }
        }
      }
    }
  }

  async endSession() {
    if (!this.sessionId) return;

    const response = await fetch(
      `${this.baseUrl}/api/v1/sessions/${this.sessionId}/end`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': this.sessionToken
        },
        body: JSON.stringify({})
      }
    );

    return await response.json();
  }

  displayMessage(message) {
    // UI logic to display message
  }

  createMessageContainer(role) {
    // UI logic
  }

  updateMessage(role, content) {
    // UI logic to update streaming message
  }

  finalizeMessage(data) {
    // Handle crisis detection, etc.
    if (data.crisis_detected) {
      this.showCrisisAlert(data);
    }
  }

  showCrisisAlert(data) {
    // UI logic for crisis alert
  }
}

// Usage
const chat = new ChatComponent('http://localhost:8000', sessionToken);
await chat.initialize();
await chat.sendMessage("I'm feeling down today");
```

## Support

For questions or issues:
- Check [API Documentation](http://localhost:8000/docs)
- Review error responses for debugging info
- Open an issue on GitHub
