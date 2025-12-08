"""
Validation utilities for file uploads and storage management.
Framework-agnostic validation functions.
"""

from typing import List, Dict


# File size limits (in bytes)
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_USER_STORAGE_BYTES = 1 * 1024 * 1024 * 1024  # 1 GB

# Supported file types
SUPPORTED_FILE_TYPES = ['.pdf', '.txt', '.json', '.md', '.csv']


def validate_file_size(file_size_bytes: int, max_size_mb: int = 100) -> tuple:
    """
    Check if file size is within allowed limits.
    
    Args:
        file_size_bytes: File size in bytes
        max_size_mb: Maximum allowed size in MB (default: 100)
    
    Returns:
        tuple: (is_valid: bool, message: str)
        
    Example:
        >>> validate_file_size(50 * 1024 * 1024)  # 50 MB
        (True, "File size is valid")
        >>> validate_file_size(200 * 1024 * 1024)  # 200 MB
        (False, "File size exceeds maximum allowed size of 100 MB")
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_size_bytes <= 0:
        return False, "File size must be greater than 0"
    
    if file_size_bytes > max_size_bytes:
        return False, f"File size exceeds maximum allowed size of {max_size_mb} MB"
    
    return True, "File size is valid"


def validate_file_type(filename: str, allowed_types: List[str] = None) -> tuple:
    """
    Check if file type is allowed.
    
    Args:
        filename: Name of the file
        allowed_types: List of allowed extensions (default: SUPPORTED_FILE_TYPES)
    
    Returns:
        tuple: (is_valid: bool, message: str)
        
    Example:
        >>> validate_file_type("document.pdf")
        (True, "File type is supported")
        >>> validate_file_type("image.png")
        (False, "File type '.png' is not supported. Allowed types: ['.pdf', '.txt', '.json', '.md', '.csv']")
    """
    if allowed_types is None:
        allowed_types = SUPPORTED_FILE_TYPES
    
    if not filename or '.' not in filename:
        return False, "Invalid filename"
    
    # Extract file extension
    file_ext = '.' + filename.rsplit('.', 1)[-1].lower()
    
    if file_ext not in allowed_types:
        return False, f"File type '{file_ext}' is not supported. Allowed types: {allowed_types}"
    
    return True, "File type is supported"


def validate_user_quota(
    current_usage_bytes: int,
    new_file_size_bytes: int,
    max_storage_bytes: int = MAX_USER_STORAGE_BYTES
) -> tuple:
    """
    Check if user has enough quota to upload new file.
    
    Args:
        current_usage_bytes: Current storage usage in bytes
        new_file_size_bytes: Size of new file in bytes
        max_storage_bytes: Maximum storage allowed in bytes (default: 1 GB)
    
    Returns:
        tuple: (has_quota: bool, message: str)
        
    Example:
        >>> validate_user_quota(500_000_000, 100_000_000)  # 500MB used, 100MB new
        (True, "Sufficient quota available")
        >>> validate_user_quota(950_000_000, 100_000_000)  # 950MB used, 100MB new
        (False, "Insufficient quota. Available: 74 MB, Required: 95 MB")
    """
    available_bytes = max_storage_bytes - current_usage_bytes
    
    if available_bytes < 0:
        available_bytes = 0
    
    if new_file_size_bytes > available_bytes:
        available_mb = available_bytes / (1024 * 1024)
        required_mb = new_file_size_bytes / (1024 * 1024)
        return False, f"Insufficient quota. Available: {available_mb:.0f} MB, Required: {required_mb:.0f} MB"
    
    return True, "Sufficient quota available"


def calculate_storage_size(chunks: List[Dict]) -> int:
    """
    Calculate approximate storage size needed for chunks in bytes.
    Includes chunk text + metadata overhead.
    
    Args:
        chunks: List of chunks with metadata
    
    Returns:
        int: Approximate storage size in bytes
        
    Note:
        This is an estimate. Actual vector DB storage may vary.
    """
    if not chunks:
        return 0
    
    total_size = 0
    
    for chunk in chunks:
        # Chunk text size
        chunk_text = chunk.get('chunk_text', '')
        total_size += len(chunk_text.encode('utf-8'))
        
        # Metadata overhead (approximate)
        # Includes: filename, hash, timestamps, etc.
        metadata_overhead = 200  # bytes (conservative estimate)
        total_size += metadata_overhead
    
    return total_size


def estimate_embedding_size(
    num_chunks: int,
    embedding_dimension: int = 768,
    bytes_per_float: int = 4
) -> int:
    """
    Estimate vector storage size for embeddings.
    
    Args:
        num_chunks: Number of chunks
        embedding_dimension: Dimension of embedding vectors (default: 768 for MiniLM)
        bytes_per_float: Bytes per float value (default: 4 for float32)
    
    Returns:
        int: Estimated storage size in bytes
        
    Example:
        >>> estimate_embedding_size(100)  # 100 chunks
        153600  # ~150 KB for vectors only
    """
    vector_size = num_chunks * embedding_dimension * bytes_per_float
    return vector_size


def get_file_size_mb(file_size_bytes: int) -> float:
    """
    Convert file size from bytes to megabytes.
    
    Args:
        file_size_bytes: File size in bytes
    
    Returns:
        float: File size in MB (rounded to 2 decimals)
    """
    return round(file_size_bytes / (1024 * 1024), 2)


def get_file_size_human_readable(file_size_bytes: int) -> str:
    """
    Convert file size to human-readable format.
    
    Args:
        file_size_bytes: File size in bytes
    
    Returns:
        str: Human-readable size (e.g., "1.5 MB", "500 KB")
        
    Example:
        >>> get_file_size_human_readable(1536000)
        "1.46 MB"
        >>> get_file_size_human_readable(500000)
        "488.28 KB"
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(file_size_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def validate_chunk_parameters(chunk_size: int, chunk_overlap: int) -> tuple:
    """
    Validate chunking parameters.
    
    Args:
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks
    
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if chunk_size <= 0:
        return False, "chunk_size must be greater than 0"
    
    if chunk_overlap < 0:
        return False, "chunk_overlap must be >= 0"
    
    if chunk_overlap >= chunk_size:
        return False, "chunk_overlap must be less than chunk_size"
    
    # Recommended limits
    if chunk_size < 100:
        return False, "chunk_size should be at least 100 characters for meaningful context"
    
    if chunk_size > 10000:
        return False, "chunk_size should not exceed 10000 characters for optimal performance"
    
    return True, "Chunk parameters are valid"


def calculate_estimated_chunks(text_length: int, chunk_size: int = 1000) -> int:
    """
    Estimate number of chunks that will be created from text.
    
    Args:
        text_length: Length of text in characters
        chunk_size: Size of each chunk
    
    Returns:
        int: Estimated number of chunks
    """
    if text_length <= 0 or chunk_size <= 0:
        return 0
    
    return (text_length + chunk_size - 1) // chunk_size  # Ceiling division
