"""
Chat history management for ChatGPT-style conversations.
Stores chat sessions and messages in PostgreSQL.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json
from app.models.db_utilities import get_db_connection
from app.helpers.encrypt_decrypt import encrypt_decrypt_string

def create_chat_tables():
    """
    Initialize database schema for chat history.
    Creates chats and messages tables if they don't exist.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Create chats table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id UUID PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                title VARCHAR(500),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """)
        
        # Create index for chats table
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_chats 
            ON chats (user_id, updated_at DESC)
        """)
        
        # Create messages table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id UUID PRIMARY KEY,
                chat_id UUID NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
                role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """)
        
        # Create index for messages table
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_messages 
            ON messages (chat_id, created_at ASC)
        """)
        
        conn.commit()
        print("✓ Chat tables created successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error creating chat tables: {e}")
        raise
    finally:
        cur.close()
        conn.close()


def create_chat(user_id: str, title: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict:
    """
    Create a new chat session.
    
    Args:
        user_id: User identifier
        title: Optional chat title (will be auto-generated if None)
        metadata: Optional metadata dictionary
    
    Returns:
        Dict with chat information
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        chat_id = str(uuid.uuid4())
        chat_title = title or "New Chat"
        chat_metadata = json.dumps(metadata or {})
        
        cur.execute("""
            INSERT INTO chats (chat_id, user_id, title, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING chat_id, user_id, title, created_at, updated_at, metadata
        """, (chat_id, user_id, chat_title, chat_metadata))
        
        result = cur.fetchone()
        conn.commit()
        
        return {
            "chat_id": str(result[0]),
            "user_id": result[1],
            "title": result[2],
            "created_at": result[3].isoformat(),
            "updated_at": result[4].isoformat(),
            "metadata": result[5]
        }
        
    except Exception as e:
        conn.rollback()
        raise Exception(f"Failed to create chat: {str(e)}")
    finally:
        cur.close()
        conn.close()


def add_message(chat_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> Dict:
    """
    Add a message to a chat.
    
    Args:
        chat_id: Chat session ID
        role: Message role ('user' or 'assistant')
        content: Message content
        metadata: Optional metadata (token count, model, etc.)
    
    Returns:
        Dict with message information
    """
    if role not in ['user', 'assistant']:
        raise ValueError("Role must be 'user' or 'assistant'")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        message_id = str(uuid.uuid4())
        message_metadata = json.dumps(metadata or {})
        content = encrypt_decrypt_string(content, mode="encrypt")
        # Insert message
        cur.execute("""
            INSERT INTO messages (message_id, chat_id, role, content, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING message_id, chat_id, role, content, created_at, metadata
        """, (message_id, chat_id, role, content, message_metadata))
        
        result = cur.fetchone()
        
        # Update chat's updated_at timestamp
        cur.execute("""
            UPDATE chats 
            SET updated_at = CURRENT_TIMESTAMP 
            WHERE chat_id = %s
        """, (chat_id,))
        
        conn.commit()
        
        return {
            "message_id": str(result[0]),
            "chat_id": str(result[1]),
            "role": result[2],
            "content": result[3],
            "created_at": result[4].isoformat(),
            "metadata": result[5]
        }
        
    except Exception as e:
        conn.rollback()
        raise Exception(f"Failed to add message: {str(e)}")
    finally:
        cur.close()
        conn.close()


def get_user_chats(user_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
    """
    Get all chats for a user, ordered by most recent.
    
    Args:
        user_id: User identifier
        limit: Maximum number of chats to return
        offset: Number of chats to skip (for pagination)
    
    Returns:
        List of chat dictionaries with message counts
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT 
                c.chat_id, 
                c.user_id, 
                c.title, 
                c.created_at, 
                c.updated_at,
                c.metadata,
                COUNT(m.message_id) as message_count,
                MAX(m.created_at) as last_message_at
            FROM chats c
            LEFT JOIN messages m ON c.chat_id = m.chat_id
            WHERE c.user_id = %s
            GROUP BY c.chat_id, c.user_id, c.title, c.created_at, c.updated_at, c.metadata
            ORDER BY c.updated_at DESC
            LIMIT %s OFFSET %s
        """, (user_id, limit, offset))
        
        results = cur.fetchall()
        
        chats = []
        for row in results:
            chats.append({
                "chat_id": str(row[0]),
                "user_id": row[1],
                "title": row[2],
                "created_at": row[3].isoformat(),
                "updated_at": row[4].isoformat(),
                "metadata": row[5],
                "message_count": row[6],
                "last_message_at": row[7].isoformat() if row[7] else None
            })
        
        return chats
        
    finally:
        cur.close()
        conn.close()


def get_chat_by_id(chat_id: str) -> Optional[Dict]:
    """
    Get a specific chat by ID.
    
    Args:
        chat_id: Chat session ID
    
    Returns:
        Chat dictionary or None if not found
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT chat_id, user_id, title, created_at, updated_at, metadata
            FROM chats
            WHERE chat_id = %s
        """, (chat_id,))
        
        result = cur.fetchone()
        
        if not result:
            return None
        
        return {
            "chat_id": str(result[0]),
            "user_id": result[1],
            "title": result[2],
            "created_at": result[3].isoformat(),
            "updated_at": result[4].isoformat(),
            "metadata": result[5]
        }
        
    finally:
        cur.close()
        conn.close()


def get_chat_messages(chat_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
    """
    Get all messages for a chat, ordered chronologically.
    
    Args:
        chat_id: Chat session ID
        limit: Maximum number of messages to return
        offset: Number of messages to skip (for pagination)
    
    Returns:
        List of message dictionaries
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT message_id, chat_id, role, content, created_at, metadata
            FROM messages
            WHERE chat_id = %s
            ORDER BY created_at ASC
            LIMIT %s OFFSET %s
        """, (chat_id, limit, offset))
        
        results = cur.fetchall()
        
        messages = []
        for row in results:
            messages.append({
                "message_id": str(row[0]),
                "chat_id": str(row[1]),
                "role": row[2],
                "content": encrypt_decrypt_string(row[3], mode="decrypt"),
                "created_at": row[4].isoformat(),
                "metadata": row[5]
            })
        
        return messages
        
    finally:
        cur.close()
        conn.close()


def get_chat_with_messages(chat_id: str, message_limit: int = 100) -> Optional[Dict]:
    """
    Get a chat with all its messages.
    
    Args:
        chat_id: Chat session ID
        message_limit: Maximum number of messages to return
    
    Returns:
        Dict with chat info and messages, or None if chat not found
    """
    chat = get_chat_by_id(chat_id)
    
    if not chat:
        return None
    
    messages = get_chat_messages(chat_id, limit=message_limit)
    chat["messages"] = messages
    
    return chat


def update_chat_title(chat_id: str, title: str) -> bool:
    """
    Update a chat's title.
    
    Args:
        chat_id: Chat session ID
        title: New title
    
    Returns:
        True if successful, False if chat not found
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE chats 
            SET title = %s, updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = %s
        """, (title, chat_id))
        
        conn.commit()
        return cur.rowcount > 0
        
    except Exception as e:
        conn.rollback()
        raise Exception(f"Failed to update chat title: {str(e)}")
    finally:
        cur.close()
        conn.close()


def delete_chat(chat_id: str) -> bool:
    """
    Delete a chat and all its messages (CASCADE).
    
    Args:
        chat_id: Chat session ID
    
    Returns:
        True if successful, False if chat not found
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("DELETE FROM chats WHERE chat_id = %s", (chat_id,))
        conn.commit()
        return cur.rowcount > 0
        
    except Exception as e:
        conn.rollback()
        raise Exception(f"Failed to delete chat: {str(e)}")
    finally:
        cur.close()
        conn.close()


def search_chats(user_id: str, query: str, limit: int = 20) -> List[Dict]:
    """
    Search through user's chats and messages.
    
    Args:
        user_id: User identifier
        query: Search query
        limit: Maximum number of results
    
    Returns:
        List of chats containing the query
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT DISTINCT 
                c.chat_id, 
                c.user_id, 
                c.title, 
                c.created_at, 
                c.updated_at,
                c.metadata
            FROM chats c
            LEFT JOIN messages m ON c.chat_id = m.chat_id
            WHERE c.user_id = %s 
            AND (
                c.title ILIKE %s 
                OR m.content ILIKE %s
            )
            ORDER BY c.updated_at DESC
            LIMIT %s
        """, (user_id, f"%{query}%", f"%{query}%", limit))
        
        results = cur.fetchall()
        
        chats = []
        for row in results:
            chats.append({
                "chat_id": str(row[0]),
                "user_id": row[1],
                "title": row[2],
                "created_at": row[3].isoformat(),
                "updated_at": row[4].isoformat(),
                "metadata": row[5]
            })
        
        return chats
        
    finally:
        cur.close()
        conn.close()


def auto_generate_title(chat_id: str, first_message: str, max_length: int = 50) -> bool:
    """
    Auto-generate a chat title from the first user message.
    
    Args:
        chat_id: Chat session ID
        first_message: First user message content
        max_length: Maximum title length
    
    Returns:
        True if successful
    """
    # Generate title from first message (truncate if needed)
    title = first_message[:max_length]
    if len(first_message) > max_length:
        title = title.rsplit(' ', 1)[0] + "..."
    
    return update_chat_title(chat_id, title)


def get_conversation_context(chat_id: str, max_messages: int = 10) -> List[Dict]:
    """
    Get recent conversation context for RAG/LLM prompting.
    Returns messages in format suitable for LangChain/OpenAI.
    
    Args:
        chat_id: Chat session ID
        max_messages: Maximum number of recent messages to include
    
    Returns:
        List of messages in [{"role": "user/assistant", "content": "..."}] format
    """
    messages = get_chat_messages(chat_id, limit=max_messages)
    
    # Convert to simple format for LLM context
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in messages
    ]
