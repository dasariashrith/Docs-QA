"""
Complete example showing how to use the helper functions with embeddings.
This demonstrates the full workflow: file upload → chunks → embeddings → vector DB
"""

from app.helpers import (
    process_file_to_chunks,
    process_chunks_with_embeddings,
    delete_vectors_by_filename,
    validate_file_size,
    validate_file_type
)
from app import EMBEDDING_DIMENSION
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


def example_1_basic_file_processing():
    """Example 1: Basic file processing without vector DB."""
    print("=" * 60)
    print("Example 1: Basic File Processing")
    print("=" * 60)
    
    # Process a file to chunks
    result = process_file_to_chunks(
        file_path_or_bytes="docs.json",
        filename="docs.json",
        chunk_size=1000,
        chunk_overlap=100
    )
    
    print(f"\n✓ Processed file: {result['filename']}")
    print(f"✓ File type: {result['file_type']}")
    print(f"✓ Total chunks: {result['total_chunks']}")
    print(f"✓ Total characters: {result['total_characters']}")
    print(f"\n✓ First chunk preview:")
    print(f"  {result['chunks'][0]['chunk_text'][:100]}...")
    print(f"  Hash: {result['chunks'][0]['content_hash'][:16]}...")


def example_2_upload_with_embeddings(collection_name="user_123_documents",filename="docs2.json"):
    """
    Example 2: Complete upload workflow with embeddings and deduplication.
    This is what your /upload endpoint should do.
    """
    print("\n" + "=" * 60)
    print("Example 2: Upload with Embeddings & Deduplication")
    print("=" * 60)
    
    # Step 1: Initialize vector DB client
    client = QdrantClient("localhost", port=6333)
    
    # Step 2: Create collection if it doesn't exist
    try:
        client.get_collection(collection_name)
        print(f"\n✓ Collection '{collection_name}' already exists")
    except Exception:
        print(f"\n✓ Creating collection '{collection_name}'...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSION,  # Dimension from app config
                distance=Distance.COSINE
            )
        )
    
    # Step 3: Validate file
    file_size = 50 * 1024 * 1024  # 50 MB
    
    is_valid_type, type_msg = validate_file_type(filename)
    is_valid_size, size_msg = validate_file_size(file_size)
    
    if not is_valid_type or not is_valid_size:
        print(f"\n✗ Validation failed: {type_msg if not is_valid_type else size_msg}")
        return
    
    print(f"\n✓ File validation passed")
    
    # Step 4: Process file to chunks
    print(f"✓ Processing file to chunks...")
    chunks_result = process_file_to_chunks(
        file_path_or_bytes=filename,
        filename=filename,
        chunk_size=1000,
        chunk_overlap=100
    )
    
    print(f"✓ Created {chunks_result['total_chunks']} chunks")
    
    # Step 5: Generate embeddings and upload to vector DB with deduplication
    print(f"✓ Generating embeddings and checking for duplicates...")
    
    embedding_result = process_chunks_with_embeddings(
        chunks=chunks_result['chunks'],
        vector_db_client=client,
        collection_name=collection_name,
        similarity_threshold=0.9  # 90% similarity threshold
    )
    
    # Step 6: Print results
    print(f"\n" + "-" * 60)
    print("Upload Results:")
    print(f"  Total chunks processed: {embedding_result['total_chunks']}")
    print(f"  New embeddings inserted: {embedding_result['new_embeddings']}")
    print(f"  Existing embeddings updated: {embedding_result['updated_embeddings']}")
    print(f"  Duplicates skipped: {embedding_result['skipped_duplicates']}")
    print("-" * 60)
    
    # Show details of first few operations
    print("\nFirst 3 operations:")
    for detail in embedding_result['details'][:3]:
        action = detail['action']
        chunk_idx = detail['chunk_index']
        if action == 'inserted':
            print(f"  • Chunk {chunk_idx}: Inserted as new vector")
        elif action == 'updated':
            similarity = detail.get('similarity', 0)
            print(f"  • Chunk {chunk_idx}: Updated existing (similarity: {similarity:.2%})")
        elif action == 'skipped':
            print(f"  • Chunk {chunk_idx}: Skipped (duplicate)")


def example_3_upload_second_file():
    """
    Example 3: Upload a second file that shares some content.
    Shows deduplication in action.
    """
    print("\n" + "=" * 60)
    print("Example 3: Upload Second File (Deduplication Test)")
    print("=" * 60)
    
    client = QdrantClient("localhost", port=6333)
    collection_name = "user_123_documents"
    
    # Process second file (might have overlapping content)
    filename2 = "document2.pdf"
    print(f"\n✓ Processing second file: {filename2}")
    
    chunks_result = process_file_to_chunks(
        file_path_or_bytes=filename2,
        filename=filename2,
        chunk_size=1000,
        chunk_overlap=100
    )
    
    # Upload with deduplication
    embedding_result = process_chunks_with_embeddings(
        chunks=chunks_result['chunks'],
        vector_db_client=client,
        collection_name=collection_name,
        similarity_threshold=0.9
    )
    
    print(f"\n✓ Second file results:")
    print(f"  New embeddings: {embedding_result['new_embeddings']}")
    print(f"  Updated (shared content): {embedding_result['updated_embeddings']}")
    print(f"  Skipped: {embedding_result['skipped_duplicates']}")


def example_4_delete_file():
    """
    Example 4: Delete a file.
    This is what your /delete endpoint should do.
    """
    print("\n" + "=" * 60)
    print("Example 4: Delete File")
    print("=" * 60)
    
    client = QdrantClient("localhost", port=6333)
    collection_name = "user_123_documents"
    filename_to_delete = "document.pdf"
    
    print(f"\n✓ Deleting file: {filename_to_delete}")
    
    # Delete vectors associated with the file
    delete_result = delete_vectors_by_filename(
        vector_db_client=client,
        collection_name=collection_name,
        filename=filename_to_delete
    )
    
    print(f"\n✓ Deletion complete:")
    print(f"  Vectors deleted: {delete_result['deleted_count']}")
    print(f"  Vectors updated: {delete_result['updated_count']}")
    print(f"  Total affected: {delete_result['total_affected']}")


def example_5_flask_route_implementation():
    """
    Example 5: How to implement in Flask route.
    This is pseudocode showing the actual implementation.
    """
    print("\n" + "=" * 60)
    print("Example 5: Flask Route Implementation")
    print("=" * 60)
    
    print("""
from flask import request, jsonify
from app.helpers import (
    validate_file_type,
    validate_file_size,
    process_file_to_chunks,
    process_chunks_with_embeddings
)
from qdrant_client import QdrantClient

@app.route('/upload', methods=['POST'])
def upload_file():
    # Get file from request
    file = request.files['file']
    user_id = request.form.get('user_id')  # From auth
    
    # Validate
    is_valid, message = validate_file_type(file.filename)
    if not is_valid:
        return jsonify({"error": message}), 400
    
    # Get file size
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    
    is_valid, message = validate_file_size(file_size)
    if not is_valid:
        return jsonify({"error": message}), 400
    
    # Process to chunks
    chunks_result = process_file_to_chunks(
        file_path_or_bytes=file,
        filename=file.filename
    )
    
    # Initialize vector DB
    client = QdrantClient("localhost", port=6333)
    collection_name = f"user_{user_id}_documents"
    
    # Generate embeddings and upload with deduplication
    result = process_chunks_with_embeddings(
        chunks=chunks_result['chunks'],
        vector_db_client=client,
        collection_name=collection_name,
        similarity_threshold=0.9
    )
    
    return jsonify({
        "success": True,
        "filename": file.filename,
        "total_chunks": result['total_chunks'],
        "new_embeddings": result['new_embeddings'],
        "updated_embeddings": result['updated_embeddings']
    }), 200

@app.route('/delete', methods=['POST'])
def delete_file():
    filename = request.json.get('filename')
    user_id = request.form.get('user_id')  # From auth
    
    client = QdrantClient("localhost", port=6333)
    collection_name = f"user_{user_id}_documents"
    
    result = delete_vectors_by_filename(
        vector_db_client=client,
        collection_name=collection_name,
        filename=filename
    )
    
    return jsonify({
        "success": True,
        "deleted_count": result['deleted_count'],
        "updated_count": result['updated_count']
    }), 200
    """)


# if __name__ == "__main__":
#     print("\n" + "=" * 60)
#     print("RAG Helper Functions - Usage Examples")
#     print("=" * 60)
    
#     # Run examples (comment out as needed)
#     try:
#         example_1_basic_file_processing()
#     except Exception as e:
#         print(f"\n✗ Example 1 failed: {e}")
    
#     try:
#         example_2_upload_with_embeddings()
#     except Exception as e:
#         print(f"\n✗ Example 2 failed: {e}")
    
#     try:
#         example_3_upload_second_file()
#     except Exception as e:
#         print(f"\n✗ Example 3 failed: {e}")
    
#     try:
#         example_4_delete_file()
#     except Exception as e:
#         print(f"\n✗ Example 4 failed: {e}")
    
#     example_5_flask_route_implementation()
    
#     print("\n" + "=" * 60)
#     print("Examples complete!")
#     print("=" * 60 + "\n")


def search_vectors_example():
    """
    Example: Searching for similar vectors in the vector DB.
    """
    print("\n" + "=" * 60)
    print("Example: Search Vectors")
    print("=" * 60)
    
    client = QdrantClient("localhost", port=6333)
    collection_name = "user_123_documents"
    
    # Example query text
    query_text = """how to list resources in Unified Workspace?"""
    # Generate embedding for query text
    from app.helpers.embeddings import EmbeddingManager, search_similar_embeddings
    embedding_manager = EmbeddingManager()
    query_embedding = embedding_manager.generate_embedding(query_text)
    
    # Search similar embeddings
    results = search_similar_embeddings(
        vector_db_client=client,
        collection_name=collection_name,
        query_embedding=query_embedding,
        similarity_threshold=0.25,
        limit=5
    )
    # print(results)
    print(f"\n✓ Search results for query: '{query_text}'")
    for idx, res in enumerate(results):
        print(f"result {idx + 1}: {res['payload'].get('chunk_text', '')}... (score: {res['score']:.4f})")

# example_2_upload_with_embeddings()
# search_vectors_example()