"""
Text chunking utilities for creating semantic text chunks.
Framework-agnostic chunking with metadata generation.
"""

from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter, RecursiveJsonSplitter
from datetime import datetime
import json


def create_text_chunks(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    file_type: str = None
) -> List[str]:
    """
    Split text into semantic chunks using RecursiveCharacterTextSplitter.
    
    Args:
        text: Input text to chunk
        chunk_size: Maximum characters per chunk (default: 1000)
        chunk_overlap: Overlap between consecutive chunks (default: 100)
    
    Returns:
        List[str]: List of text chunks
        
    Raises:
        ValueError: If text is empty or chunk_size is invalid
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")
    
    if file_type == '.json':
        # Use JSON-specific splitter for JSON files
        data = json.loads(text)
        splitter = RecursiveJsonSplitter(max_chunk_size=chunk_size)
        return splitter.split_json(data)
    else:
        # Initialize the text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    # Split the content into chunks
    chunks = text_splitter.split_text(text)
    
    return chunks


def create_chunks_with_metadata(
    text: str,
    filename: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    file_type: str = None
) -> List[Dict]:
    """
    Create chunks with associated metadata for each chunk.
    
    Args:
        text: Input text to chunk
        filename: Original filename for metadata
        chunk_size: Maximum characters per chunk (default: 1000)
        chunk_overlap: Overlap between chunks (default: 100)
    
    Returns:
        List[dict]: List of chunks with metadata
        Example:
        [
            {
                "chunk_text": "The actual text content...",
                "chunk_index": 0,
                "filename": "doc.pdf",
                "content_hash": "sha256...",
                "chunk_length": 950,
                "created_at": "2025-01-01T10:00:00Z"
            },
            ...
        ]
        
    Raises:
        ValueError: If text is empty or parameters are invalid
    """
    
    from .embeddings import manager
    # Create text chunks
    chunks = create_text_chunks(text, chunk_size, chunk_overlap, file_type=file_type)
    
    # Create chunks with metadata
    chunks_with_metadata = []
    current_time = datetime.utcnow().isoformat() + 'Z'
    
    for index, chunk_text in enumerate(chunks):
        chunk_metadata = {
            "chunk_text": chunk_text,
            "chunk_index": index,
            "filename": filename,
            "chunk_length": len(chunk_text),
            "created_at": current_time
        }
        chunks_with_metadata.append(chunk_metadata)
    
    return chunks_with_metadata


def merge_overlapping_chunks(chunks: List[str], min_similarity: float = 0.9) -> List[str]:
    """
    Merge chunks that have high overlap/similarity.
    Useful for deduplication when processing multiple files.
    
    Args:
        chunks: List of text chunks
        min_similarity: Minimum similarity threshold for merging (0-1)
    
    Returns:
        List[str]: Deduplicated chunks
    """
    if not chunks:
        return []
    
    # Simple implementation - can be enhanced with more sophisticated similarity
    unique_chunks = []
    seen_hashes = set()
    
    from .hashing import calculate_content_hash
    
    for chunk in chunks:
        chunk_hash = calculate_content_hash(chunk)
        if chunk_hash not in seen_hashes:
            unique_chunks.append(chunk)
            seen_hashes.add(chunk_hash)
    
    return unique_chunks


def get_chunk_statistics(chunks: List[Dict]) -> Dict:
    """
    Calculate statistics about the chunks.
    
    Args:
        chunks: List of chunks with metadata
    
    Returns:
        dict: Statistics including total chunks, avg length, etc.
        Example:
        {
            "total_chunks": 10,
            "total_characters": 9500,
            "avg_chunk_length": 950,
            "min_chunk_length": 800,
            "max_chunk_length": 1000
        }
    """
    if not chunks:
        return {
            "total_chunks": 0,
            "total_characters": 0,
            "avg_chunk_length": 0,
            "min_chunk_length": 0,
            "max_chunk_length": 0
        }
    
    chunk_lengths = [chunk.get("chunk_length", len(chunk.get("chunk_text", ""))) for chunk in chunks]
    
    return {
        "total_chunks": len(chunks),
        "total_characters": sum(chunk_lengths),
        "avg_chunk_length": sum(chunk_lengths) / len(chunk_lengths) if chunk_lengths else 0,
        "min_chunk_length": min(chunk_lengths) if chunk_lengths else 0,
        "max_chunk_length": max(chunk_lengths) if chunk_lengths else 0
    }
