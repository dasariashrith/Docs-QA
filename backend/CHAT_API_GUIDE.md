# Chat History API Guide

A complete ChatGPT-style conversation storage and retrieval system for your RAG Documentation QA application.

## Overview

This implementation provides a full-featured chat history system that stores conversations in PostgreSQL, similar to ChatGPT's interface. It supports:

- **Multiple chat sessions** per user
- **Conversation history** with user and assistant messages
- **Auto-generated titles** from first user message
- **Search functionality** across chats and messages
- **Pagination** for large chat histories
- **Metadata storage** for extensibility
- **Conversation context** for LLM prompting

## Database Schema
docker run -d \
  --name postgres-chat \
  -e POSTGRES_DB=docs_qa_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your_secure_password \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15
### Tables

#### `chats` table
Stores chat sessions for users.

```sql
CREATE TABLE chats (
    chat_id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);
```

#### `messages` table
Stores individual messages within chats.

```sql
CREATE TABLE messages (
    message_id UUID PRIMARY KEY,
    chat_id UUID REFERENCES chats(chat_id) ON DELETE CASCADE,
    role VARCHAR(50) CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);
```

## Setup

### 1. Install Dependencies

All required dependencies are already in `requirements.txt`:
- `psycopg2-binary` - PostgreSQL adapter
- `Flask` - Web framework

### 2. Configure Database

Ensure your `.env` file has PostgreSQL credentials:

```bash
DB_NAME=your_database
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### 3. Initialize Database Tables

Run the setup script to create chat tables:

```bash
cd backend
python setup_chat_db.py
```

Expected output:
```
============================================================
Chat Database Initialization
============================================================
Database: your_database
Host: localhost:5432
User: your_username
============================================================

Creating chat tables...
✓ Chat tables created successfully!
```

## API Endpoints

### Base URL
```
http://localhost:5000
```

---

### 1. Create New Chat

Create a new chat session for a user.

**Endpoint:** `POST /chats`

**Request Body:**
```json
{
  "user_id": "user123",
  "title": "My Chat" (optional),
  "metadata": {} (optional)
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "chat": {
    "chat_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user123",
    "title": "New Chat",
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:00:00",
    "metadata": {}
  },
  "timestamp": "2024-01-01T10:00:00"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/chats \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'
```

---

### 2. List User's Chats

Get all chats for a specific user, ordered by most recent.

**Endpoint:** `GET /chats`

**Query Parameters:**
- `user_id` (required) - User identifier
- `limit` (optional) - Max chats to return (default: 50)
- `offset` (optional) - Pagination offset (default: 0)

**Response (200 OK):**
```json
{
  "success": true,
  "chats": [
    {
      "chat_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "user123",
      "title": "European Capitals",
      "created_at": "2024-01-01T10:00:00",
      "updated_at": "2024-01-01T10:30:00",
      "metadata": {},
      "message_count": 4,
      "last_message_at": "2024-01-01T10:30:00"
    }
  ],
  "count": 1,
  "limit": 50,
  "offset": 0,
  "timestamp": "2024-01-01T11:00:00"
}
```

**cURL Example:**
```bash
curl "http://localhost:5000/chats?user_id=user123&limit=10"
```

---

### 3. Get Chat with Messages

Retrieve a specific chat with all its messages.

**Endpoint:** `GET /chats/{chat_id}`

**Query Parameters:**
- `include_messages` (optional) - Include messages (default: true)
- `message_limit` (optional) - Max messages (default: 100)

**Response (200 OK):**
```json
{
  "success": true,
  "chat": {
    "chat_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user123",
    "title": "European Capitals",
    "created_at": "2024-01-01T10:00:00",
    "updated_at": "2024-01-01T10:30:00",
    "metadata": {},
    "messages": [
      {
        "message_id": "660e8400-e29b-41d4-a716-446655440001",
        "chat_id": "550e8400-e29b-41d4-a716-446655440000",
        "role": "user",
        "content": "What is the capital of France?",
        "created_at": "2024-01-01T10:00:00",
        "metadata": {}
      },
      {
        "message_id": "770e8400-e29b-41d4-a716-446655440002",
        "chat_id": "550e8400-e29b-41d4-a716-446655440000",
        "role": "assistant",
        "content": "The capital of France is Paris.",
        "created_at": "2024-01-01T10:00:05",
        "metadata": {"model": "gpt-4", "tokens": 50}
      }
    ]
  },
  "timestamp": "2024-01-01T11:00:00"
}
```

**cURL Example:**
```bash
curl "http://localhost:5000/chats/550e8400-e29b-41d4-a716-446655440000"
```

---

### 4. Add Message to Chat

Add a user or assistant message to a chat.

**Endpoint:** `POST /chats/{chat_id}/messages`

**Request Body:**
```json
{
  "role": "user",  // or "assistant"
  "content": "What is the capital of France?",
  "metadata": {} (optional)
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": {
    "message_id": "660e8400-e29b-41d4-a716-446655440001",
    "chat_id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "user",
    "content": "What is the capital of France?",
    "created_at": "2024-01-01T10:00:00",
    "metadata": {}
  },
  "timestamp": "2024-01-01T10:00:00"
}
```

**Auto-titling:** If this is the first user message and the chat title is still "New Chat", the system will automatically generate a title from the message content.

**cURL Example:**
```bash
curl -X POST http://localhost:5000/chats/550e8400-e29b-41d4-a716-446655440000/messages \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "What is the capital of France?"}'
```

---

### 5. Get Messages Only

Retrieve just the messages for a chat (without chat metadata).

**Endpoint:** `GET /chats/{chat_id}/messages`

**Query Parameters:**
- `limit` (optional) - Max messages (default: 100)
- `offset` (optional) - Pagination offset (default: 0)

**Response (200 OK):**
```json
{
  "success": true,
  "messages": [
    {
      "message_id": "660e8400-e29b-41d4-a716-446655440001",
      "chat_id": "550e8400-e29b-41d4-a716-446655440000",
      "role": "user",
      "content": "What is the capital of France?",
      "created_at": "2024-01-01T10:00:00",
      "metadata": {}
    }
  ],
  "count": 1,
  "limit": 100,
  "offset": 0,
  "timestamp": "2024-01-01T11:00:00"
}
```

---

### 6. Update Chat Title

Update a chat's title.

**Endpoint:** `PATCH /chats/{chat_id}`

**Request Body:**
```json
{
  "title": "European Capitals Discussion"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Chat updated successfully",
  "timestamp": "2024-01-01T11:00:00"
}
```

**cURL Example:**
```bash
curl -X PATCH http://localhost:5000/chats/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{"title": "European Capitals Discussion"}'
```

---

### 7. Delete Chat

Delete a chat and all its messages.

**Endpoint:** `DELETE /chats/{chat_id}`

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Chat deleted successfully",
  "timestamp": "2024-01-01T11:00:00"
}
```

**cURL Example:**
```bash
curl -X DELETE http://localhost:5000/chats/550e8400-e29b-41d4-a716-446655440000
```

---

### 8. Search Chats

Search through a user's chats and messages.

**Endpoint:** `GET /chats/search`

**Query Parameters:**
- `user_id` (required) - User identifier
- `q` (required) - Search query
- `limit` (optional) - Max results (default: 20)

**Response (200 OK):**
```json
{
  "success": true,
  "chats": [
    {
      "chat_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "user123",
      "title": "European Capitals",
      "created_at": "2024-01-01T10:00:00",
      "updated_at": "2024-01-01T10:30:00",
      "metadata": {}
    }
  ],
  "query": "capital",
  "count": 1,
  "timestamp": "2024-01-01T11:00:00"
}
```

**cURL Example:**
```bash
curl "http://localhost:5000/chats/search?user_id=user123&q=capital"
```

---

### 9. Get Conversation Context

Get recent conversation context formatted for LLM prompting.

**Endpoint:** `GET /chats/{chat_id}/context`

**Query Parameters:**
- `max_messages` (optional) - Max recent messages (default: 10)

**Response (200 OK):**
```json
{
  "success": true,
  "context": [
    {
      "role": "user",
      "content": "What is the capital of France?"
    },
    {
      "role": "assistant",
      "content": "The capital of France is Paris."
    }
  ],
  "timestamp": "2024-01-01T11:00:00"
}
```

**Use Case:** This endpoint returns messages in a format ready to be used as context in your RAG system or LLM prompts.

---

## Integration with RAG System

### Typical Workflow

1. **User starts conversation:**
   ```python
   # Create new chat
   chat = create_chat(user_id="user123")
   chat_id = chat["chat_id"]
   ```

2. **User asks question:**
   ```python
   # Add user message
   add_message(chat_id, role="user", content="What is quantum computing?")
   
   # Get conversation context for RAG
   context = get_conversation_context(chat_id, max_messages=5)
   
   # Use context + RAG to generate response
   # ... your RAG logic here ...
   
   # Store assistant response
   add_message(chat_id, role="assistant", content=assistant_response)
   ```

3. **User continues conversation:**
   ```python
   # Get previous context
   context = get_conversation_context(chat_id)
   
   # Add new user message
   add_message(chat_id, role="user", content="Can you explain more?")
   
   # Generate response with full context
   # ... RAG logic ...
   
   # Store response
   add_message(chat_id, role="assistant", content=new_response)
   ```

### Python Integration Example

```python
from app.models.chat_history import (
    create_chat,
    add_message,
    get_conversation_context,
    get_chat_with_messages
)

def handle_user_query(user_id, chat_id, query):
    """Handle a user query with conversation context."""
    
    # Create chat if new conversation
    if not chat_id:
        chat = create_chat(user_id)
        chat_id = chat["chat_id"]
    
    # Add user message
    add_message(chat_id, role="user", content=query)
    
    # Get conversation context
    context = get_conversation_context(chat_id, max_messages=10)
    
    # Your RAG logic here
    # Use context to provide better answers
    response = your_rag_function(query, context)
    
    # Store assistant response
    add_message(
        chat_id,
        role="assistant",
        content=response,
        metadata={"model": "gpt-4", "tokens": 150}
    )
    
    return {
        "chat_id": chat_id,
        "response": response
    }
```

## Testing

### Run Example Script

Test all endpoints with the provided example:

```bash
cd backend
python example_chat_usage.py
```

This will:
1. Create a new chat
2. Add multiple messages
3. Retrieve chat history
4. Update chat title
5. Search chats
6. Demonstrate all API endpoints

### Manual Testing with cURL

```bash
# 1. Create chat
CHAT_ID=$(curl -s -X POST http://localhost:5000/chats \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user"}' | jq -r '.chat.chat_id')

# 2. Add user message
curl -X POST http://localhost:5000/chats/$CHAT_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "Hello!"}'

# 3. Add assistant message
curl -X POST http://localhost:5000/chats/$CHAT_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"role": "assistant", "content": "Hi! How can I help?"}'

# 4. Get chat with messages
curl http://localhost:5000/chats/$CHAT_ID

# 5. List all chats
curl "http://localhost:5000/chats?user_id=test_user"
```

## Features

### ✅ Implemented Features

- **Chat Management:** Create, read, update, delete chats
- **Message Storage:** Store user and assistant messages
- **Pagination:** Handle large chat histories efficiently
- **Search:** Search across chat titles and message content
- **Auto-titling:** Generate titles from first user message
- **Metadata:** Store additional info (model, tokens, etc.)
- **Context Retrieval:** Get formatted conversation history for LLMs
- **Multi-user Support:** Isolated chats per user
- **Cascade Deletion:** Deleting a chat removes all messages

### 🎯 Use Cases

1. **ChatGPT-like Interface:** Build a conversational UI with persistent history
2. **RAG Enhancement:** Use conversation context for better answers
3. **Multi-turn Conversations:** Support follow-up questions
4. **Chat History:** Let users revisit previous conversations
5. **Search & Discovery:** Find relevant past conversations
6. **Analytics:** Track conversation patterns and usage

## Error Handling

### Common Error Responses

**404 Not Found:**
```json
{
  "error": "Chat not found"
}
```

**400 Bad Request:**
```json
{
  "error": "user_id is required"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Database connection failed",
  "type": "DatabaseError"
}
```

## Performance Considerations

### Indexes

The schema includes indexes for:
- `chats(user_id, updated_at)` - Fast user chat listing
- `messages(chat_id, created_at)` - Fast message retrieval

### Pagination

Always use pagination for:
- Listing chats (`limit`, `offset`)
- Retrieving messages (`limit`, `offset`)
- Search results (`limit`)

### Metadata Storage

Use JSONB metadata fields for:
- Model information
- Token counts
- Custom tags
- Timestamps
- User preferences

## Next Steps

1. **Authentication:** Add user authentication/authorization
2. **WebSockets:** Real-time message updates
3. **Message Editing:** Allow editing/deleting individual messages
4. **Exports:** Export chat history to various formats
5. **Analytics:** Add usage tracking and insights
6. **Rate Limiting:** Prevent abuse
7. **Soft Deletes:** Archive instead of hard delete

## Support

For issues or questions:
1. Check error messages in API responses
2. Review PostgreSQL logs
3. Verify database credentials in `.env`
4. Ensure tables are created with `setup_chat_db.py`

---

**Happy Chatting! 💬**
