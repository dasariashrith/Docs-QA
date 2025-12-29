#!/usr/bin/env python3
"""
Setup script for Qdrant vector database.
Run this after starting Qdrant container.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import sys
from app import EMBEDDING_DIMENSION


def check_connection():
    """Check if Qdrant is running."""
    try:
        client = QdrantClient("localhost", port=6333)
        info = client.get_collections()
        print("✓ Successfully connected to Qdrant")
        print(f"✓ Current collections: {len(info.collections)}")
        return client
    except Exception as e:
        print("✗ Failed to connect to Qdrant")
        print(f"  Error: {e}")
        print("\nPlease ensure Qdrant is running:")
        print("  docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant")
        print("\nOr check the SETUP_GUIDE.md for detailed instructions.")
        sys.exit(1)


def create_demo_collection(client):
    """Create a demo collection for testing."""
    collection_name = "demo_documents"
    
    try:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSION, # Use EMBEDDING_DIMENSION from app config
                distance=Distance.COSINE
            )
        )
        print(f"✓ Created demo collection: {collection_name}")
    except Exception as e:
        print(f"✓ Demo collection already exists")


def create_test_user_collections(client):
    """Create test user collections."""
    test_users = ["123", "456", "789"]
    
    for user_id in test_users:
        collection_name = f"user_{user_id}_documents"
        try:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION, # Use EMBEDDING_DIMENSION from app config
                    distance=Distance.COSINE
                )
            )
            print(f"✓ Created collection: {collection_name}")
        except Exception:
            print(f"✓ Collection already exists: {collection_name}")


def display_info(client):
    """Display information about Qdrant setup."""
    collections = client.get_collections()
    
    print("\n" + "=" * 60)
    print("Qdrant Status:")
    print("=" * 60)
    print(f"Total collections: {len(collections.collections)}")
    print("\nCollections:")
    for collection in collections.collections:
        info = client.get_collection(collection.name)
        print(f"  • {collection.name}")
        print(f"    - Vectors: {info.points_count}")
        print(f"    - Dimension: {info.config.params.vectors.size}")


def main():
    print("=" * 60)
    print("Qdrant Vector Database Setup")
    print("=" * 60)
    print()
    
    # Check connection
    client = check_connection()
    print()
    
    # Create demo collection
    print("Creating collections...")
    create_demo_collection(client)
    
    # Create test user collections
    create_test_user_collections(client)
    
    # Display info
    display_info(client)
    
    print()
    print("=" * 60)
    print("Setup complete! You can now:")
    print("=" * 60)
    print("  1. Run example_usage.py to test the system")
    print("     python example_usage.py")
    print()
    print("  2. Start your Flask application")
    print("     python app.py")
    print()
    print("  3. Access Qdrant dashboard:")
    print("     http://localhost:6333/dashboard")
    print()
    print("  4. Test API connection:")
    print("     curl http://localhost:6333/")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
