"""
Embedding generation and vector database operations.
Uses Hugging Face's BERT model for embeddings (no API key required).
"""

from typing import List, Dict, Optional, Tuple
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from app import EMBEDDING_MODEL, EMBEDDING_DIMENSION

class EmbeddingManager:
    """
    Manages embedding generation using Hugging Face BERT/SBERT model.
    Uses EMBEDDING_MODEL for efficient embeddings.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

        # Eval mode
        self.model.eval()

        # Device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    # --- FIXED: Use sentence-transformers official mean pooling ---
    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output.last_hidden_state  # shape: [B, seq, hidden]

        input_mask_expanded = (
            attention_mask.unsqueeze(-1)
            .expand(token_embeddings.size())
            .float()
        )

        # Sum embeddings * mask, then divide by number of valid tokens
        return torch.sum(token_embeddings * input_mask_expanded, dim=1) / \
            torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text chunk.
        """
        return self.generate_embeddings_batch([text])[0]

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple text chunks efficiently.
        """

        # Tokenize texts
        encoded_input = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )

        # Move to device
        encoded_input = {k: v.to(self.device) for k, v in encoded_input.items()}

        # Forward pass
        with torch.no_grad():
            model_output = self.model(**encoded_input)

        # --- FIXED pooling ---
        embeddings = self._mean_pooling(model_output, encoded_input["attention_mask"])

        # NOTE: Do NOT normalize → Qdrant handles cosine normalization internally

        # Convert to list
        return embeddings.cpu().tolist()

manager = EmbeddingManager()

def calculate_cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        float: Cosine similarity score (0 to 1)
    """
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def process_chunks_with_embeddings(
    chunks: List[Dict],
    vector_db_client,
    collection_name: str,
    similarity_threshold: float = 0.98,
    model_name: str = EMBEDDING_MODEL
) -> Dict:
    """
    Process chunks: generate embeddings, check for duplicates, and insert/update in vector DB.
    
    Workflow:
    1. Generate embeddings for all chunks using Hugging Face BERT
    2. For each chunk:
       - Search vector DB for similar embeddings (similarity >= threshold)
       - If similar embedding found: Update metadata (add filename to file_identifiers)
       - If no similar embedding: Insert new vector with metadata
    
    Args:
        chunks: List of chunks with metadata from create_chunks_with_metadata()
        vector_db_client: Vector database client (Qdrant, Milvus, etc.)
        collection_name: Name of the collection to store vectors
        similarity_threshold: Similarity threshold for deduplication (default: 0.9)
        model_name: Hugging Face model name
    
    Returns:
        dict: Processing summary
        {
            "total_chunks": int,
            "new_embeddings": int,
            "updated_embeddings": int,
            "skipped_duplicates": int,
            "details": List[dict]
        }
    """
    
    # Extract texts for batch embedding generation
    texts = [str(chunk['chunk_text']) for chunk in chunks]
    
    # Generate embeddings for all chunks
    print(f"Generating embeddings for {len(texts)} chunks...")
    embeddings = manager.generate_embeddings_batch(texts)
    
    # Track processing results
    new_embeddings = 0
    updated_embeddings = 0
    skipped_duplicates = 0
    details = []
    
    for chunk, embedding in zip(chunks, embeddings):
        # Search vector DB for similar embeddings
        similar_results = search_similar_embeddings(
            vector_db_client,
            collection_name,
            embedding,
            similarity_threshold,
            limit=1
        )
        similar_results = None #test
        if similar_results:
            # Similar embedding found - update metadata
            existing_point = similar_results[0]
            existing_id = existing_point['id']
            existing_metadata = existing_point['payload']
            
            # Update file_identifiers to include new filename
            filename = chunk['filename']
            file_identifiers = existing_metadata.get('file_identifiers', [])
            
            if filename not in file_identifiers:
                file_identifiers.append(filename)
                updated_metadata = {**existing_metadata, 'file_identifiers': file_identifiers}
                
                # Update the vector metadata in DB
                update_vector_metadata(
                    vector_db_client,
                    collection_name,
                    existing_id,
                    updated_metadata
                )
                
                updated_embeddings += 1
                details.append({
                    "action": "updated",
                    "chunk_index": chunk['chunk_index'],
                    "similarity": existing_point.get('score', 1.0),
                    "existing_id": existing_id
                })
            else:
                # Filename already exists in identifiers
                skipped_duplicates += 1
                details.append({
                    "action": "skipped",
                    "chunk_index": chunk['chunk_index'],
                    "reason": "duplicate_filename"
                })
        else:
            # No similar embedding found - insert new vector
            vector_id = insert_new_vector(
                vector_db_client,
                collection_name,
                embedding,
                {
                    **chunk,
                    'file_identifiers': [chunk['filename']]
                }
            )
            
            new_embeddings += 1
            details.append({
                "action": "inserted",
                "chunk_index": chunk['chunk_index'],
                "vector_id": vector_id
            })
    
    return {
        "total_chunks": len(chunks),
        "new_embeddings": new_embeddings,
        "updated_embeddings": updated_embeddings,
        "skipped_duplicates": skipped_duplicates,
        "details": details
    }


def search_similar_embeddings(
    vector_db_client,
    collection_name: str,
    query_embedding: List[float],
    similarity_threshold: float,
    limit: int = 10
) -> List[Dict]:
    """
    Search vector DB for embeddings similar to query embedding.
    
    Args:
        vector_db_client: Vector database client
        collection_name: Collection to search
        query_embedding: Query vector
        similarity_threshold: Minimum similarity score (0-1)
        limit: Maximum number of results
    
    Returns:
        List[Dict]: List of similar vectors with metadata
        [
            {
                "id": "vector_id",
                "score": 0.95,
                "payload": {"chunk_text": "...", "file_identifiers": [...]}
            }
        ]
    """
    # This is a generic interface - implement based on your vector DB
    # Example for Qdrant:
    try:
        results = vector_db_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=similarity_threshold
        )
        
        return [
            {
                "id": result.id,
                "score": result.score,
                "payload": result.payload
            }
            for result in results
        ]
    except Exception as e:
        raise ValueError(f"Vector DB search failed: {str(e)}")

def advanced_search_similar_embeddings(
    user_message: str,
    vector_db_client,
    collection_name: str,
    similarity_threshold: float,
    limit: int = 10
) -> List[Dict]:
    """
    Search vector DB for embeddings similar to query embedding.
    
    Args:
        vector_db_client: Vector database client
        collection_name: Collection to search
        query_embedding: Query vector
        similarity_threshold: Minimum similarity score (0-1)
        limit: Maximum number of results
    
    Returns:
        List[Dict]: List of similar vectors with metadata
        [
            {
                "id": "vector_id",
                "score": 0.95,
                "payload": {"chunk_text": "...", "file_identifiers": [...]}
            }
        ]
    """
    # This is a generic interface - implement based on your vector DB
    # Example for Qdrant:
    try:
        from app.models.chat import generate_queries
        queries = generate_queries(user_message, queries_number=5)
        print("Generated queries for vector search:", queries)
        all_results = []
        for query in queries:
            query_embedding = manager.generate_embedding(query)
            results = search_similar_embeddings(
                vector_db_client=vector_db_client,
                collection_name=collection_name,
                query_embedding=query_embedding,
                similarity_threshold=similarity_threshold,
                limit=limit
            )
            all_results.extend(results)
        # Remove duplicates based on vector ID
        unique_results = {}
        for result in all_results:
            unique_results[result['id']] = result
        return list(unique_results.values())
    except Exception as e:
        raise ValueError(f"Vector DB search failed: {str(e)}")


def update_vector_metadata(
    vector_db_client,
    collection_name: str,
    vector_id: str,
    updated_metadata: Dict
) -> bool:
    """
    Update metadata for an existing vector in the database.
    
    Args:
        vector_db_client: Vector database client
        collection_name: Collection name
        vector_id: ID of vector to update
        updated_metadata: New metadata
    
    Returns:
        bool: True if successful
    """
    # This is a generic interface - implement based on your vector DB
    # Example for Qdrant:
    try:
        vector_db_client.set_payload(
            collection_name=collection_name,
            points=[vector_id],
            payload=updated_metadata
        )
        return True
    except Exception as e:
        raise ValueError(f"Failed to update vector metadata: {str(e)}")


def insert_new_vector(
    vector_db_client,
    collection_name: str,
    embedding: List[float],
    metadata: Dict
) -> str:
    """
    Insert a new vector with metadata into the database.
    
    Args:
        vector_db_client: Vector database client
        collection_name: Collection name
        embedding: Vector to insert
        metadata: Metadata for the vector
    
    Returns:
        str: ID of inserted vector
    """
    # This is a generic interface - implement based on your vector DB
    # Example for Qdrant:
    try:
        import uuid
        vector_id = str(uuid.uuid4())
        
        vector_db_client.upsert(
            collection_name=collection_name,
            points=[{
                "id": vector_id,
                "vector": embedding,
                "payload": metadata
            }]
        )
        
        return vector_id
    except Exception as e:
        raise ValueError(f"Failed to insert vector: {str(e)}")


def list_filenames(
    vector_db_client,
    collection_name: str
) -> List[str]:
    """
    List all unique filenames in a user's collection.
    
    Workflow:
    1. Scroll through all vectors in the collection
    2. Extract file_identifiers from each vector's payload
    3. Return unique list of filenames
    
    Args:
        vector_db_client: Vector database client
        collection_name: Collection name
    
    Returns:
        List[str]: List of unique filenames in the collection
    """
    try:
        # Set to store unique filenames
        unique_filenames = set()
        
        # Scroll through all vectors in the collection
        offset = None
        while True:
            # Scroll in batches
            vectors, offset = vector_db_client.scroll(
                collection_name=collection_name,
                limit=100,  # Batch size
                offset=offset,
                with_payload=True,
                with_vectors=False  # Don't need vectors, just payload
            )
            
            # Extract filenames from each vector's payload
            for vector in vectors:
                file_identifiers = vector.payload.get('file_identifiers', [])
                unique_filenames.update(file_identifiers)
            
            # Break if no more vectors
            if offset is None:
                break
        
        # Return sorted list
        return sorted(list(unique_filenames))
        
    except Exception as e:
        raise ValueError(f"Failed to list filenames: {str(e)}")


def delete_vectors_by_filename(
    vector_db_client,
    collection_name: str,
    filename: str
) -> Dict:
    """
    Delete or update vectors associated with a filename.
    
    Workflow:
    1. Query all vectors where file_identifiers contains filename
    2. For each vector:
       - If file_identifiers has only this filename: Delete vector
       - If file_identifiers has multiple filenames: Remove this filename and update
    
    Args:
        vector_db_client: Vector database client
        collection_name: Collection name
        filename: Filename to remove
    
    Returns:
        dict: Deletion summary
        {
            "deleted_count": int,
            "updated_count": int,
            "total_affected": int
        }
    """
    # Query vectors with this filename
    # This is a generic interface - implement based on your vector DB
    try:
        # Example filter for Qdrant
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="file_identifiers",
                    match=MatchValue(value=filename)
                )
            ]
        )
        
        # Scroll through all matching vectors
        vectors = vector_db_client.scroll(
            collection_name=collection_name,
            scroll_filter=filter_condition,
            limit=1000  # Adjust based on expected volume
        )[0]
        
        deleted_count = 0
        updated_count = 0
        
        for vector in vectors:
            file_identifiers = vector.payload.get('file_identifiers', [])
            
            if len(file_identifiers) == 1:
                # Only this file - delete vector
                vector_db_client.delete(
                    collection_name=collection_name,
                    points_selector=[vector.id]
                )
                deleted_count += 1
            else:
                # Multiple files - remove this filename
                file_identifiers.remove(filename)
                updated_metadata = {
                    **vector.payload,
                    'file_identifiers': file_identifiers
                }
                
                vector_db_client.set_payload(
                    collection_name=collection_name,
                    points=[vector.id],
                    payload=updated_metadata
                )
                updated_count += 1
        
        return {
            "deleted_count": deleted_count,
            "updated_count": updated_count,
            "total_affected": deleted_count + updated_count
        }
    except Exception as e:
        raise ValueError(f"Failed to delete vectors: {str(e)}")
