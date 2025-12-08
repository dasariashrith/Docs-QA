"""
Hashing and deduplication utilities.
Framework-agnostic functions for content hashing and duplicate detection.
"""

import hashlib
from typing import Set, List


def calculate_content_hash(text: str) -> str:
    """
    Calculate SHA-256 hash of text content.
    
    Args:
        text: Text to hash
    
    Returns:
        str: Hex digest of SHA-256 hash
        
    Example:
        >>> calculate_content_hash("Hello, world!")
        '315f5bdb76d078c43b8ac0064e4a0164612b1fce77c869345bfc94c75894edd3'
    """
    if not isinstance(text, str):
        raise TypeError("Text must be a string")
    
    # Normalize text (strip whitespace, lowercase) for better deduplication
    normalized_text = text.strip().lower()
    
    # Calculate SHA-256 hash
    hash_object = hashlib.sha256(normalized_text.encode('utf-8'))
    return hash_object.hexdigest()


def is_duplicate_chunk(chunk_hash: str, existing_hashes: Set[str]) -> bool:
    """
    Check if chunk is duplicate based on exact hash match.
    
    Args:
        chunk_hash: Hash of new chunk
        existing_hashes: Set of existing chunk hashes
    
    Returns:
        bool: True if duplicate (exact match found)
        
    Example:
        >>> existing = {"abc123", "def456"}
        >>> is_duplicate_chunk("abc123", existing)
        True
        >>> is_duplicate_chunk("xyz789", existing)
        False
    """
    return chunk_hash in existing_hashes


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate basic similarity score between two text strings.
    Uses Jaccard similarity on character n-grams.
    
    Args:
        text1: First text string
        text2: Second text string
    
    Returns:
        float: Similarity score between 0.0 and 1.0
        
    Note:
        For production, consider using more sophisticated similarity measures
        like cosine similarity on embeddings.
    """
    if not text1 or not text2:
        return 0.0
    
    # Create character n-grams (n=3)
    def get_ngrams(text: str, n: int = 3) -> Set[str]:
        text = text.lower().strip()
        return set(text[i:i+n] for i in range(len(text) - n + 1))
    
    ngrams1 = get_ngrams(text1)
    ngrams2 = get_ngrams(text2)
    
    if not ngrams1 or not ngrams2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)
    
    return intersection / union if union > 0 else 0.0


def find_similar_chunks(
    new_chunk_text: str,
    existing_chunks: List[dict],
    threshold: float = 0.9
) -> List[dict]:
    """
    Find existing chunks that are similar to a new chunk.
    
    Args:
        new_chunk_text: Text of new chunk
        existing_chunks: List of existing chunks with 'chunk_text' key
        threshold: Similarity threshold (0.0 to 1.0)
    
    Returns:
        List[dict]: List of similar chunks with similarity scores
        Example:
        [
            {
                "chunk": {...},  # Original chunk dict
                "similarity": 0.95
            }
        ]
    """
    similar_chunks = []
    
    for chunk in existing_chunks:
        chunk_text = chunk.get('chunk_text', '')
        similarity = calculate_similarity(new_chunk_text, chunk_text)
        
        if similarity >= threshold:
            similar_chunks.append({
                "chunk": chunk,
                "similarity": similarity
            })
    
    # Sort by similarity (highest first)
    similar_chunks.sort(key=lambda x: x['similarity'], reverse=True)
    
    return similar_chunks


def deduplicate_chunks(chunks: List[dict], threshold: float = 0.9) -> List[dict]:
    """
    Remove duplicate chunks from a list based on content similarity.
    
    Args:
        chunks: List of chunks with 'chunk_text' and 'content_hash' keys
        threshold: Similarity threshold for considering chunks as duplicates
    
    Returns:
        List[dict]: Deduplicated list of chunks
        
    Note:
        The first occurrence of similar chunks is kept.
    """
    if not chunks:
        return []
    
    unique_chunks = []
    seen_hashes = set()
    
    for chunk in chunks:
        chunk_hash = chunk.get('content_hash')
        
        # If hash not provided, calculate it
        if not chunk_hash:
            chunk_text = chunk.get('chunk_text', '')
            chunk_hash = calculate_content_hash(chunk_text)
            chunk['content_hash'] = chunk_hash
        
        # Check for exact duplicates
        if chunk_hash not in seen_hashes:
            # For exact matches, simply add
            unique_chunks.append(chunk)
            seen_hashes.add(chunk_hash)
    
    return unique_chunks


def batch_calculate_hashes(texts: List[str]) -> List[str]:
    """
    Calculate hashes for multiple text strings efficiently.
    
    Args:
        texts: List of text strings
    
    Returns:
        List[str]: List of hash strings (same order as input)
    """
    return [calculate_content_hash(text) for text in texts]


def create_hash_index(chunks: List[dict]) -> dict:
    """
    Create a hash-to-chunk mapping for fast lookups.
    
    Args:
        chunks: List of chunks with 'content_hash' key
    
    Returns:
        dict: Mapping of content_hash to chunk
        Example:
        {
            "abc123...": {"chunk_text": "...", "chunk_index": 0},
            "def456...": {"chunk_text": "...", "chunk_index": 1}
        }
    """
    hash_index = {}
    
    for chunk in chunks:
        chunk_hash = chunk.get('content_hash')
        if chunk_hash:
            hash_index[chunk_hash] = chunk
    
    return hash_index
