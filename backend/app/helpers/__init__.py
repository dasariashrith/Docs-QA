"""
Helper functions for RAG application.
Framework-agnostic utilities for file processing, chunking, and deduplication.
"""

from .file_parsers import (
    extract_text_from_pdf,
    extract_text_from_txt,
    extract_text_from_json,
    extract_text_from_file,
    process_file_to_chunks
)

from .chunking import (
    create_text_chunks,
    create_chunks_with_metadata
)

from .hashing import (
    calculate_content_hash,
    is_duplicate_chunk
)

from .validation import (
    validate_file_size,
    validate_file_type,
    calculate_storage_size,
    estimate_embedding_size
)

from .embeddings import (
    EmbeddingManager,
    calculate_cosine_similarity,
    process_chunks_with_embeddings,
    search_similar_embeddings,
    update_vector_metadata,
    insert_new_vector,
    list_filenames,
    delete_vectors_by_filename
)

__all__ = [
    'extract_text_from_pdf',
    'extract_text_from_txt',
    'extract_text_from_json',
    'extract_text_from_file',
    'process_file_to_chunks',
    'create_text_chunks',
    'create_chunks_with_metadata',
    'calculate_content_hash',
    'is_duplicate_chunk',
    'validate_file_size',
    'validate_file_type',
    'calculate_storage_size',
    'estimate_embedding_size',
    'EmbeddingManager',
    'calculate_cosine_similarity',
    'process_chunks_with_embeddings',
    'search_similar_embeddings',
    'update_vector_metadata',
    'insert_new_vector',
    'list_filenames',
    'delete_vectors_by_filename'
]
