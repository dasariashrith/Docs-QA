# Qdrant Vector Database Setup Guide

This guide will help you set up and run Qdrant vector database for the RAG application.

## Quick Start

### Option 1: Using Docker (Recommended)

#### 1. Start Qdrant Container

```bash
# Pull the Qdrant image
docker pull qdrant/qdrant

# Run Qdrant with persistent storage
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:v1.7.0
```

**Explanation:**
- `-d` : Run in detached mode (background)
- `--name qdrant` : Name the container "qdrant"
- `-p 6333:6333` : Expose REST API port
- `-p 6334:6334` : Expose gRPC API port
- `-v $(pwd)/qdrant_storage:/qdrant/storage` : Persist data to local directory

#### 2. Verify Qdrant is Running

```bash
# Check container status
docker ps | grep qdrant

# Test API connection
curl http://localhost:6333/
```

You should see a JSON response like:
```json
{
  "title": "qdrant - vector search engine",
  "version": "1.7.0"
}
```

#### 3. Access Qdrant Dashboard

Open your browser and navigate to:
```
http://localhost:6333/dashboard
```

You'll see a web interface to manage collections and view data.

### Option 2: Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "6333:6333"  # REST API
      - "6334:6334"  # gRPC API
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
    restart: unless-stopped
```

Start with:
```bash
docker-compose up -d
```

Stop with:
```bash
docker-compose down
```

### Option 3: Local Installation (Without Docker)

If you don't want to use Docker:

```bash
# On macOS (using Homebrew)
brew install qdrant

# On Linux (using binary)
wget https://github.com/qdrant/qdrant/releases/download/v1.7.0/qdrant-x86_64-unknown-linux-gnu.tar.gz
tar -xvf qdrant-x86_64-unknown-linux-gnu.tar.gz
cd qdrant
./qdrant
```

## Managing Qdrant Container

### Start/Stop/Restart

```bash
# Start the container
docker start qdrant

# Stop the container
docker stop qdrant

# Restart the container
docker restart qdrant

# View logs
docker logs qdrant

# Follow logs in real-time
docker logs -f qdrant
```

### Remove Container (Warning: Data loss if no volume)

```bash
# Stop and remove container
docker stop qdrant && docker rm qdrant

# To also remove the volume/data
docker stop qdrant && docker rm qdrant
rm -rf qdrant_storage/
```

## Python Client Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- `qdrant-client==1.7.0`
- `torch==2.1.0`
- `sentence-transformers==2.2.2`
- All other required packages

### 2. Test Connection

Create a test script `test_qdrant.py`:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Connect to Qdrant
client = QdrantClient("localhost", port=6333)

# Test connection
print("✓ Connected to Qdrant")
print(f"✓ Collections: {client.get_collections()}")

# Create a test collection
collection_name = "test_collection"
try:
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=768,  # Dimension for all-MiniLM-L6-v2
            distance=Distance.COSINE
        )
    )
    print(f"✓ Created collection: {collection_name}")
except Exception as e:
    print(f"✓ Collection already exists or error: {e}")

# List collections
collections = client.get_collections()
print(f"✓ Available collections: {[c.name for c in collections.collections]}")
```

Run:
```bash
python test_qdrant.py
```

## Creating User Collections

For user isolation, create a collection per user:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient("localhost", port=6333)

def create_user_collection(user_id):
    """Create a dedicated collection for a user."""
    collection_name = f"user_{user_id}_documents"
    
    try:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=768,  # all-MiniLM-L6-v2 embedding size
                distance=Distance.COSINE  # Cosine similarity
            )
        )
        print(f"✓ Created collection: {collection_name}")
        return collection_name
    except Exception as e:
        print(f"Collection already exists: {e}")
        return collection_name

# Example: Create collection for user 123
create_user_collection("123")
```

## Complete Setup Script

Create `backend/setup_vectordb.py`:

```python
#!/usr/bin/env python3
"""
Setup script for Qdrant vector database.
Run this after starting Qdrant container.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import sys

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
        print("  docker run -d -p 6333:6333 qdrant/qdrant")
        sys.exit(1)

def create_demo_collection(client):
    """Create a demo collection for testing."""
    collection_name = "demo_documents"
    
    try:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE
            )
        )
        print(f"✓ Created demo collection: {collection_name}")
    except Exception as e:
        print(f"✓ Demo collection already exists")

def main():
    print("=" * 60)
    print("Qdrant Vector Database Setup")
    print("=" * 60)
    print()
    
    # Check connection
    client = check_connection()
    
    # Create demo collection
    create_demo_collection(client)
    
    print()
    print("=" * 60)
    print("Setup complete! You can now:")
    print("  1. Run example_usage.py to test the system")
    print("  2. Start your Flask application")
    print("  3. Access Qdrant dashboard: http://localhost:6333/dashboard")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

Make it executable and run:
```bash
chmod +x backend/setup_vectordb.py
python backend/setup_vectordb.py
```

## Complete Startup Sequence

Follow these steps in order:

```bash
# 1. Start Qdrant
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# 2. Wait a few seconds for Qdrant to start
sleep 5

# 3. Verify Qdrant is running
curl http://localhost:6333/

# 4. Install Python dependencies
cd backend
pip install -r requirements.txt

# 5. Run setup script
python setup_vectordb.py

# 6. Test the system
python example_usage.py

# 7. Start Flask application
python app.py
```

## Troubleshooting

### Issue: Port already in use

```bash
# Find what's using port 6333
lsof -i :6333

# Kill the process or use a different port
docker run -d --name qdrant -p 6335:6333 qdrant/qdrant

# Update client connection
client = QdrantClient("localhost", port=6335)
```

### Issue: Cannot connect to Qdrant

```bash
# Check if container is running
docker ps | grep qdrant

# Check container logs
docker logs qdrant

# Restart container
docker restart qdrant
```

### Issue: Permission denied on qdrant_storage

```bash
# Fix permissions
sudo chown -R $USER:$USER qdrant_storage/
chmod -R 755 qdrant_storage/
```

### Issue: Container not starting

```bash
# Remove old container
docker stop qdrant && docker rm qdrant

# Start fresh
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

## Production Considerations

For production deployment:

1. **Use persistent storage**: Always mount a volume
2. **Set resource limits**:
   ```bash
   docker run -d --name qdrant \
     --memory="4g" \
     --cpus="2" \
     -p 6333:6333 \
     -v $(pwd)/qdrant_storage:/qdrant/storage \
     qdrant/qdrant
   ```

3. **Enable authentication**: Add API keys in production
4. **Use docker-compose** for easier management
5. **Set up backups**: Regularly backup `qdrant_storage/`
6. **Monitor performance**: Use Qdrant dashboard and metrics

## Useful Commands Reference

```bash
# Docker commands
docker ps                          # List running containers
docker ps -a                       # List all containers
docker logs qdrant                 # View logs
docker logs -f qdrant              # Follow logs
docker stats qdrant                # View resource usage
docker exec -it qdrant sh          # Access container shell

# Qdrant API commands
curl http://localhost:6333/                      # Get version
curl http://localhost:6333/collections           # List collections
curl http://localhost:6333/dashboard             # Access dashboard

# Python client commands
from qdrant_client import QdrantClient
client = QdrantClient("localhost", port=6333)
client.get_collections()                         # List collections
client.get_collection("collection_name")         # Get collection info
client.delete_collection("collection_name")      # Delete collection
```

## Next Steps

After setting up Qdrant:

1. ✅ Test connection with `test_qdrant.py`
2. ✅ Run `setup_vectordb.py` to create collections
3. ✅ Try `example_usage.py` to see the full workflow
4. ✅ Integrate with your Flask application
5. ✅ Implement user authentication and collection isolation

For more information:
- Qdrant Documentation: https://qdrant.tech/documentation/
- Python Client Docs: https://python-client.qdrant.tech/
