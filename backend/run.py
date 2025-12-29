"""
Flask RAG Application with TUS Resumable Upload Support.
Minimal bootstrap - routes are defined in app.routes.routes
"""

from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from flask import Flask, jsonify
from flask_cors import CORS
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import os

from app.__init__ import EMBEDDING_DIMENSION, SIMILARITY_THRESHOLD, EMBEDDING_MODEL

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for all routes
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000", "http://localhost:3001"],
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
        "allow_headers": [
            "Content-Type", 
            "Authorization", 
            "Upload-Offset", 
            "Upload-Length", 
            "Upload-Metadata",
            "Tus-Resumable",
            "Content-Length"
        ],
        "expose_headers": [
            "Upload-Offset", 
            "Upload-Length", 
            "Upload-Metadata",
            "Location", 
            "Tus-Resumable",
            "Tus-Version",
            "Tus-Extension",
            "Tus-Max-Size",
            "Upload-Expires"
        ],
        "supports_credentials": True
    }
})

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Qdrant client
qdrant_client = QdrantClient("localhost", port=6333)


def get_user_collection(user_id):
    """
    Get or create a collection for a user.
    Each user has isolated data in their own collection.
    
    Args:
        user_id: User identifier
    
    Returns:
        Collection name for the user
    """
    collection_name = f"user_{user_id}_documents"
    
    try:
        qdrant_client.get_collection(collection_name)
    except Exception:
        # Collection doesn't exist, create it
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSION,
                distance=Distance.COSINE
            )
        )
    
    return collection_name


# Register all routes from routes.py
from app.routes.routes import register_routes
register_routes(app, qdrant_client, get_user_collection)


# Error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors."""
    return jsonify({
        "error": "File too large",
        "max_size": "100 MB"
    }), 413


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Endpoint not found",
        "message": "Check the root endpoint (/) for available endpoints"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    return jsonify({
        "error": "Internal server error",
        "message": str(error)
    }), 500


if __name__ == '__main__':
    # Check Qdrant connection on startup
    try:
        qdrant_client.get_collections()
        print("✓ Connected to Qdrant")
    except Exception as e:
        print(f"✗ Failed to connect to Qdrant: {e}")
        print("\nPlease start Qdrant first:")
        print("  docker run -d --name qdrant -p 6333:6333 qdrant/qdrant")
        exit(1)
    
    print("\n" + "=" * 60)
    print("RAG Documentation QA API with TUS Resumable Upload")
    print("=" * 60)
    print(f"Upload Protocol: TUS 1.0.0")
    print(f"Chunk Size: 5 MB")
    print(f"Session Expiry: 24 hours")
    print(f"Embedding Model: {EMBEDDING_MODEL}")
    print(f"Similarity Threshold: {SIMILARITY_THRESHOLD}")
    print("=" * 60 + "\n")
    
    # Run Flask app
    # use_reloader=False prevents loading the model twice (once for main process, once for reloader)
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False
    )
