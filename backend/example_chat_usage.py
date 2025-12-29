"""
Example usage of the Chat History API.
Demonstrates how to create chats, add messages, and retrieve conversations.
"""

import requests
import json
from datetime import datetime

# API Base URL
BASE_URL = "http://localhost:5000"

# Test user ID
USER_ID = "test_user_123"


def print_response(title, response):
    """Pretty print API response."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))


def main():
    """Demonstrate chat functionality."""
    
    print("\n" + "=" * 60)
    print("Chat History API - Example Usage")
    print("=" * 60)
    
    # 1. Create a new chat
    print("\n1. Creating a new chat...")
    response = requests.post(
        f"{BASE_URL}/chats",
        json={
            "user_id": USER_ID,
            "metadata": {
                "source": "example_script",
                "version": "1.0"
            }
        }
    )
    print_response("Create Chat Response", response)
    
    if response.status_code != 201:
        print("\n✗ Failed to create chat. Exiting.")
        return
    
    chat_id = response.json()["chat"]["chat_id"]
    print(f"\n✓ Chat created with ID: {chat_id}")
    
    # 2. Add user message
    print("\n2. Adding user message...")
    response = requests.post(
        f"{BASE_URL}/chats/{chat_id}/messages",
        json={
            "role": "user",
            "content": "What is the capital of France?",
            "metadata": {
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
    print_response("Add User Message Response", response)
    
    # 3. Add assistant message
    print("\n3. Adding assistant message...")
    response = requests.post(
        f"{BASE_URL}/chats/{chat_id}/messages",
        json={
            "role": "assistant",
            "content": "The capital of France is Paris. Paris is not only the capital but also the largest city in France, known for its art, fashion, gastronomy, and culture. Famous landmarks include the Eiffel Tower, Louvre Museum, and Notre-Dame Cathedral.",
            "metadata": {
                "model": "gpt-4",
                "tokens": 150
            }
        }
    )
    print_response("Add Assistant Message Response", response)
    
    # 4. Add another exchange
    print("\n4. Adding follow-up question...")
    response = requests.post(
        f"{BASE_URL}/chats/{chat_id}/messages",
        json={
            "role": "user",
            "content": "What about Germany?"
        }
    )
    print_response("Add Follow-up Question", response)
    
    response = requests.post(
        f"{BASE_URL}/chats/{chat_id}/messages",
        json={
            "role": "assistant",
            "content": "The capital of Germany is Berlin. It's the largest city in Germany and serves as the country's political and cultural center.",
            "metadata": {
                "model": "gpt-4",
                "tokens": 80
            }
        }
    )
    print_response("Add Assistant Response", response)
    
    # 5. Retrieve chat with all messages
    print("\n5. Retrieving complete chat history...")
    response = requests.get(f"{BASE_URL}/chats/{chat_id}")
    print_response("Get Chat with Messages", response)
    
    # 6. Get conversation context (for LLM prompting)
    print("\n6. Getting conversation context (last 5 messages)...")
    response = requests.get(f"{BASE_URL}/chats/{chat_id}/context?max_messages=5")
    print_response("Get Conversation Context", response)
    
    # 7. Update chat title
    print("\n7. Updating chat title...")
    response = requests.patch(
        f"{BASE_URL}/chats/{chat_id}",
        json={
            "title": "European Capitals Discussion"
        }
    )
    print_response("Update Chat Title", response)
    
    # 8. List all chats for user
    print("\n8. Listing all chats for user...")
    response = requests.get(f"{BASE_URL}/chats?user_id={USER_ID}")
    print_response("List User Chats", response)
    
    # 9. Search chats
    print("\n9. Searching chats for 'capital'...")
    response = requests.get(f"{BASE_URL}/chats/search?user_id={USER_ID}&q=capital")
    print_response("Search Chats", response)
    
    # 10. Get only messages (paginated)
    print("\n10. Getting messages only (limit 2)...")
    response = requests.get(f"{BASE_URL}/chats/{chat_id}/messages?limit=2")
    print_response("Get Messages (Paginated)", response)
    
    # 11. Create another chat to demonstrate multiple chats
    print("\n11. Creating a second chat...")
    response = requests.post(
        f"{BASE_URL}/chats",
        json={
            "user_id": USER_ID,
            "title": "Science Questions"
        }
    )
    chat_id_2 = response.json()["chat"]["chat_id"]
    
    # Add a message to the second chat
    requests.post(
        f"{BASE_URL}/chats/{chat_id_2}/messages",
        json={
            "role": "user",
            "content": "Explain quantum physics in simple terms"
        }
    )
    
    # 12. List all chats again to show multiple chats
    print("\n12. Listing all chats (should show 2 chats)...")
    response = requests.get(f"{BASE_URL}/chats?user_id={USER_ID}")
    print_response("List All User Chats", response)
    
    # Summary
    print("\n" + "=" * 60)
    print("Example Usage Complete!")
    print("=" * 60)
    print(f"\nCreated chats:")
    print(f"  1. Chat ID: {chat_id}")
    print(f"     Title: European Capitals Discussion")
    print(f"     Messages: 4")
    print(f"  2. Chat ID: {chat_id_2}")
    print(f"     Title: Science Questions")
    print(f"     Messages: 1")
    print("\nAll endpoints tested successfully!")
    print("\nNote: To clean up, you can delete these chats using:")
    print(f"  DELETE {BASE_URL}/chats/{chat_id}")
    print(f"  DELETE {BASE_URL}/chats/{chat_id_2}")
    print()


if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to the API")
        print("Please ensure the Flask server is running:")
        print("  cd backend")
        print("  python app/app.py")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
