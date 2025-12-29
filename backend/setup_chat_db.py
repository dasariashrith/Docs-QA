"""
Database initialization script for chat history tables.
Run this script to create the necessary tables in PostgreSQL.
"""

import os
from dotenv import load_dotenv
from app.models.chat_history import create_chat_tables

def main():
    """Initialize chat database tables."""
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    required_vars = ['DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("✗ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your .env file")
        return 1
    
    print("=" * 60)
    print("Chat Database Initialization")
    print("=" * 60)
    print(f"Database: {os.getenv('DB_NAME')}")
    print(f"Host: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")
    print(f"User: {os.getenv('DB_USER')}")
    print("=" * 60)
    print()
    
    try:
        # Create tables
        print("Creating chat tables...")
        create_chat_tables()
        
        print()
        print("=" * 60)
        print("✓ Chat database initialized successfully!")
        print("=" * 60)
        print()
        print("Tables created:")
        print("  1. chats - Stores chat sessions")
        print("  2. messages - Stores individual messages")
        print()
        print("You can now use the chat endpoints:")
        print("  POST   /chats - Create new chat")
        print("  GET    /chats?user_id=<id> - List user's chats")
        print("  GET    /chats/<chat_id> - Get chat with messages")
        print("  POST   /chats/<chat_id>/messages - Add message")
        print("  PATCH  /chats/<chat_id> - Update chat title")
        print("  DELETE /chats/<chat_id> - Delete chat")
        print("  GET    /chats/search?user_id=<id>&q=<query> - Search chats")
        print()
        return 0
        
    except Exception as e:
        print()
        print("=" * 60)
        print("✗ Error initializing database")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print()
        print("Please check:")
        print("  1. PostgreSQL is running")
        print("  2. Database credentials in .env are correct")
        print("  3. Database exists and is accessible")
        print()
        return 1


if __name__ == '__main__':
    exit(main())
