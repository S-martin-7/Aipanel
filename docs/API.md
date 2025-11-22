# AIPanel API Documentation

**Version:** 1.0.0
**Base URL:** `https://api.aipanel.cl/api/v1`

---

## Authentication

AIPanel uses JWT (JSON Web Tokens) for authentication. There are two authentication methods:

### 1. JWT Token (for web applications)

```http
Authorization: Bearer <access_token>
```

### 2. API Key (for external integrations)

```http
X-API-Key: <api_key>
```

---

## Endpoints

### Auth

#### POST /auth/login
Authenticate user and get tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "usr_123",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "ADMIN"
  }
}
```

#### POST /auth/register
Register a new user.

#### POST /auth/refresh
Refresh access token using refresh token.

#### POST /auth/logout
Invalidate refresh token.

#### GET /auth/me
Get current user info.

---

### Tenants

#### GET /tenants
List all tenants (admin only).

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `per_page` (int): Items per page (default: 20)
- `status` (string): Filter by status (active, trial, suspended)
- `plan` (string): Filter by plan

**Response:**
```json
{
  "items": [
    {
      "id": "tnt_123",
      "name": "Acme Corp",
      "email": "admin@acme.com",
      "slug": "acme-corp",
      "status": "active",
      "plan": "pro",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20
}
```

#### POST /tenants
Create a new tenant.

#### GET /tenants/{id}
Get tenant by ID.

#### PUT /tenants/{id}
Update tenant.

#### DELETE /tenants/{id}
Delete tenant.

---

### Agents

#### GET /agents
List agents for current tenant.

**Response:**
```json
{
  "items": [
    {
      "id": "agt_123",
      "name": "Customer Support",
      "description": "Handles customer inquiries",
      "model": "gpt-4o-mini",
      "status": "active",
      "temperature": 0.7,
      "max_tokens": 1000,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 5
}
```

#### POST /agents
Create a new agent.

**Request:**
```json
{
  "name": "Sales Assistant",
  "description": "Helps with sales inquiries",
  "model": "gpt-4o",
  "system_prompt": "You are a helpful sales assistant...",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

#### GET /agents/{id}
Get agent by ID.

#### PUT /agents/{id}
Update agent.

#### DELETE /agents/{id}
Delete agent.

---

### Chat

#### POST /chat/completions
Send a message and get a response.

**Request:**
```json
{
  "agent_id": "agt_123",
  "message": "Hello, how can you help me?",
  "conversation_id": "conv_456",
  "stream": false
}
```

**Response:**
```json
{
  "id": "msg_789",
  "conversation_id": "conv_456",
  "role": "assistant",
  "content": "Hello! I'm here to help you...",
  "usage": {
    "input_tokens": 45,
    "output_tokens": 82,
    "total_tokens": 127
  },
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### POST /chat/stream
Send a message and get a streaming response (Server-Sent Events).

**Response (SSE):**
```
data: {"delta": "Hello"}
data: {"delta": "! I'm"}
data: {"delta": " here"}
data: {"delta": " to help"}
data: [DONE]
```

#### GET /chat/conversations
List conversations.

#### GET /chat/conversations/{id}
Get conversation with messages.

---

### Documents

#### GET /documents
List documents.

#### POST /documents/upload
Upload a document.

**Request (multipart/form-data):**
- `file`: Document file (PDF, DOCX, TXT)
- `agent_id`: Optional agent ID to associate

**Response:**
```json
{
  "id": "doc_123",
  "name": "product-manual.pdf",
  "type": "pdf",
  "size": 1048576,
  "status": "processing",
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### GET /documents/{id}
Get document details.

#### DELETE /documents/{id}
Delete document.

#### GET /documents/{id}/chunks
Get document chunks.

#### GET /documents/{id}/summaries
Get chunk summaries.

---

### Search

#### POST /search/query
Search documents.

**Request:**
```json
{
  "query": "return policy",
  "agent_id": "agt_123",
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "chk_123",
      "document_id": "doc_456",
      "document_name": "policies.pdf",
      "content": "Our return policy allows...",
      "summary": "Return policy details",
      "score": 0.95
    }
  ],
  "total": 5
}
```

---

### Usage

#### GET /usage/summary
Get usage summary for current period.

**Response:**
```json
{
  "period": {
    "start": "2025-01-01",
    "end": "2025-01-31"
  },
  "tokens": {
    "used": 150000,
    "limit": 500000,
    "percentage": 30
  },
  "storage": {
    "used_mb": 250,
    "limit_mb": 1000,
    "percentage": 25
  },
  "api_calls": {
    "count": 1500,
    "limit": 10000
  }
}
```

#### GET /usage/history
Get usage history.

#### GET /usage/by-agent
Get usage breakdown by agent.

---

### Billing

#### GET /billing/subscription
Get current subscription.

#### POST /billing/subscription
Create or update subscription.

#### DELETE /billing/subscription
Cancel subscription.

#### GET /billing/invoices
List invoices.

#### GET /billing/invoices/{id}
Get invoice details.

---

### Webhooks

#### POST /webhooks
Register a webhook.

**Request:**
```json
{
  "url": "https://yoursite.com/webhook",
  "events": ["agent.message", "document.processed", "usage.threshold"],
  "secret": "your-webhook-secret"
}
```

#### GET /webhooks
List webhooks.

#### DELETE /webhooks/{id}
Delete webhook.

---

## Webhook Events

When events occur, AIPanel sends POST requests to your webhook URL:

```json
{
  "id": "evt_123",
  "type": "agent.message",
  "timestamp": "2025-01-01T00:00:00Z",
  "data": {
    "agent_id": "agt_123",
    "conversation_id": "conv_456",
    "message": "..."
  }
}
```

**Signature Verification:**
```
X-AIPanel-Signature: sha256=abc123...
```

---

## Error Responses

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

**Common Status Codes:**
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Server Error

---

## Rate Limits

| Plan       | Requests/min | Tokens/month |
|------------|--------------|--------------|
| Básico     | 5            | 50,000       |
| Pro        | 20           | 500,000      |
| Enterprise | 100          | 5,000,000    |

---

## SDKs

### Python
```python
from aipanel import AIPanel

client = AIPanel(api_key="your-api-key")
response = client.chat.send(
    agent_id="agt_123",
    message="Hello!"
)
```

### JavaScript
```javascript
import { AIPanel } from '@aipanel/sdk';

const client = new AIPanel({ apiKey: 'your-api-key' });
const response = await client.chat.send({
  agentId: 'agt_123',
  message: 'Hello!'
});
```

---

## Support

- Email: soporte@aipanel.cl
- Documentation: https://docs.aipanel.cl
- Status: https://status.aipanel.cl
