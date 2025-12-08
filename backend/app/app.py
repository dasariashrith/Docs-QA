"""
Flask RAG Application with Embeddings and Vector Database.
Implements /upload and /delete endpoints with deduplication.
"""

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import os
from datetime import datetime

from app.helpers import (
    validate_file_type,
    validate_file_size,
    process_file_to_chunks,
    process_chunks_with_embeddings,
    delete_vectors_by_filename
)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Qdrant client
qdrant_client = QdrantClient("localhost", port=6333)

# Embedding model configuration
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
EMBEDDING_DIMENSION = 768
SIMILARITY_THRESHOLD = 0.9


def get_user_collection(user_id):
    """
    Get or create a collection for a user.
    Each user has isolated data in their own collection.
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


@app.route('/')
def index():
    """API information endpoint."""
    return jsonify({
        "name": "RAG Documentation QA API",
        "version": "1.0.0",
        "endpoints": {
            "/": "API information",
            "/upload": "Upload and process documents (POST)",
            "/delete": "Delete documents (POST)",
            "/health": "Health check",
            "/collections": "List user collections (GET)"
        }
    })


@app.route('/health')
def health():
    """Health check endpoint."""
    try:
        # Check Qdrant connection
        qdrant_client.get_collections()
        qdrant_status = "healthy"
    except Exception as e:
        qdrant_status = f"unhealthy: {str(e)}"
    
    return jsonify({
        "status": "healthy" if qdrant_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "qdrant": qdrant_status,
            "flask": "healthy"
        }
    })


@app.route('/collections')
def list_collections():
    """List all collections (for debugging/admin)."""
    try:
        collections = qdrant_client.get_collections()
        return jsonify({
            "collections": [
                {
                    "name": col.name,
                    "points": qdrant_client.get_collection(col.name).points_count
                }
                for col in collections.collections
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload endpoint with deduplication.
    
    Request:
        - file: File to upload (multipart/form-data)
        - user_id: User identifier (form field)
    
    Response:
        {
            "success": true,
            "filename": "document.pdf",
            "file_size": 1024,
            "processing": {
                "total_chunks": 50,
                "new_embeddings": 35,
                "updated_embeddings": 12,
                "skipped_duplicates": 3
            },
            "collection": "user_123_documents"
        }
    """
    try:
        # Validate request
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        if 'user_id' not in request.form:
            return jsonify({"error": "user_id is required"}), 400
        
        file = request.files['file']
        user_id = request.form['user_id']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Secure filename
        filename = secure_filename(file.filename)
        
        # Validate file type
        is_valid_type, type_message = validate_file_type(filename)
        if not is_valid_type:
            return jsonify({"error": type_message}), 400
        
        # Read file content for size validation
        file_content = file.read()
        file_size = len(file_content)
        
        # Validate file size
        is_valid_size, size_message = validate_file_size(file_size)
        if not is_valid_size:
            return jsonify({"error": size_message}), 400
        
        # Get user's collection
        collection_name = get_user_collection(user_id)
        
        # Process file to chunks
        chunks_result = process_file_to_chunks(
            file_path_or_bytes=file_content,
            filename=filename,
            chunk_size=1000,
            chunk_overlap=100
        )
        
        # Generate embeddings and upload with deduplication
        embedding_result = process_chunks_with_embeddings(
            chunks=chunks_result['chunks'],
            vector_db_client=qdrant_client,
            collection_name=collection_name,
            similarity_threshold=SIMILARITY_THRESHOLD,
            model_name=EMBEDDING_MODEL
        )
        
        return jsonify({
            "success": True,
            "filename": filename,
            "file_size": file_size,
            "file_type": chunks_result['file_type'],
            "processing": {
                "total_chunks": embedding_result['total_chunks'],
                "new_embeddings": embedding_result['new_embeddings'],
                "updated_embeddings": embedding_result['updated_embeddings'],
                "skipped_duplicates": embedding_result['skipped_duplicates']
            },
            "collection": collection_name,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 500


@app.route('/delete', methods=['POST'])
def delete_file():
    """
    Delete endpoint with reference counting.
    
    Request:
        {
            "filename": "document.pdf",
            "user_id": "123"
        }
    
    Response:
        {
            "success": true,
            "filename": "document.pdf",
            "deletion": {
                "deleted_count": 35,
                "updated_count": 12,
                "total_affected": 47
            },
            "collection": "user_123_documents"
        }
    """
    try:
        # Parse request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        filename = data.get('filename')
        user_id = data.get('user_id')
        
        if not filename:
            return jsonify({"error": "filename is required"}), 400
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        # Get user's collection
        collection_name = get_user_collection(user_id)
        
        # Delete vectors associated with the file
        deletion_result = delete_vectors_by_filename(
            vector_db_client=qdrant_client,
            collection_name=collection_name,
            filename=filename
        )
        
        return jsonify({
            "success": True,
            "filename": filename,
            "deletion": {
                "deleted_count": deletion_result['deleted_count'],
                "updated_count": deletion_result['updated_count'],
                "total_affected": deletion_result['total_affected']
            },
            "collection": collection_name,
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 500


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
        "available_endpoints": ["/", "/upload", "/delete", "/health", "/collections"]
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
    print("RAG Documentation QA API")
    print("=" * 60)
    print(f"Embedding Model: {EMBEDDING_MODEL}")
    print(f"Similarity Threshold: {SIMILARITY_THRESHOLD}")
    print("=" * 60 + "\n")
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
