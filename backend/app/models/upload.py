"""
Upload business logic for file processing and TUS resumable uploads.
This module contains pure business logic without Flask dependencies.
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, BinaryIO, Union
from werkzeug.utils import secure_filename

from app.helpers import (
    validate_file_type,
    validate_file_size,
    process_file_to_chunks,
    process_chunks_with_embeddings
)
from app import EMBEDDING_DIMENSION, SIMILARITY_THRESHOLD, EMBEDDING_MODEL


# Configuration
UPLOAD_BASE_DIR = "uploads"
SESSIONS_DIR = os.path.join(UPLOAD_BASE_DIR, "sessions")
COMPLETED_DIR = os.path.join(UPLOAD_BASE_DIR, "completed")
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB chunks for TUS protocol
SESSION_EXPIRY_HOURS = 24


def ensure_upload_directories():
    """Create necessary upload directories if they don't exist."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    os.makedirs(COMPLETED_DIR, exist_ok=True)


def create_upload_session(
    filename: str,
    file_size: int,
    user_id: str,
    metadata: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a new upload session for resumable uploads.
    
    Args:
        filename: Original filename
        file_size: Total file size in bytes
        user_id: User identifier
        metadata: Optional metadata dictionary
    
    Returns:
        Dictionary with session information including session_id
    
    Raises:
        ValueError: If validation fails
    """
    ensure_upload_directories()
    
    # Validate file type
    is_valid_type, type_message = validate_file_type(filename)
    if not is_valid_type:
        raise ValueError(type_message)
    
    # Validate file size
    is_valid_size, size_message = validate_file_size(file_size)
    if not is_valid_size:
        raise ValueError(size_message)
    
    # Create session ID
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    chunks_dir = os.path.join(session_dir, "chunks")
    
    # Create session directories
    os.makedirs(chunks_dir, exist_ok=True)
    
    # Prepare session metadata
    session_metadata = {
        "session_id": session_id,
        "filename": secure_filename(filename),
        "original_filename": filename,
        "file_size": file_size,
        "user_id": user_id,
        "uploaded_bytes": 0,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=SESSION_EXPIRY_HOURS)).isoformat(),
        "status": "uploading",
        "metadata": metadata or {}
    }
    
    # Save metadata to file
    metadata_path = os.path.join(session_dir, "metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(session_metadata, f, indent=2)
    
    return session_metadata


def get_session_info(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get information about an upload session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Session metadata dictionary or None if not found
    """
    metadata_path = os.path.join(SESSIONS_DIR, session_id, "metadata.json")
    
    if not os.path.exists(metadata_path):
        return None
    
    with open(metadata_path, 'r') as f:
        return json.load(f)


def save_chunk(session_id: str, chunk_data: bytes, offset: int) -> Dict[str, Any]:
    """
    Save a chunk of data to the upload session.
    
    Args:
        session_id: Session identifier
        chunk_data: Binary chunk data
        offset: Byte offset where this chunk starts
    
    Returns:
        Updated session information
    
    Raises:
        ValueError: If session not found or offset mismatch
    """
    session_info = get_session_info(session_id)
    
    if not session_info:
        raise ValueError(f"Session {session_id} not found")
    
    # Check if session expired
    expires_at = datetime.fromisoformat(session_info["expires_at"])
    if datetime.utcnow() > expires_at:
        raise ValueError(f"Session {session_id} has expired")
    
    # Validate offset
    if offset != session_info["uploaded_bytes"]:
        raise ValueError(
            f"Offset mismatch. Expected {session_info['uploaded_bytes']}, got {offset}"
        )
    
    # Calculate chunk index
    chunk_index = offset // CHUNK_SIZE
    chunks_dir = os.path.join(SESSIONS_DIR, session_id, "chunks")
    chunk_path = os.path.join(chunks_dir, f"{chunk_index}.chunk")
    
    # Save chunk to file
    with open(chunk_path, 'wb') as f:
        f.write(chunk_data)
    
    # Update uploaded bytes
    session_info["uploaded_bytes"] += len(chunk_data)
    
    # Check if upload is complete
    if session_info["uploaded_bytes"] >= session_info["file_size"]:
        session_info["status"] = "complete"
    
    # Save updated metadata
    metadata_path = os.path.join(SESSIONS_DIR, session_id, "metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(session_info, f, indent=2)
    
    return session_info


def combine_chunks(session_id: str) -> bytes:
    """
    Combine all chunks into a single file.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Complete file content as bytes
    
    Raises:
        ValueError: If session not found or incomplete
    """
    session_info = get_session_info(session_id)
    
    if not session_info:
        raise ValueError(f"Session {session_id} not found")
    
    if session_info["status"] != "complete":
        raise ValueError(f"Session {session_id} is not complete")
    
    chunks_dir = os.path.join(SESSIONS_DIR, session_id, "chunks")
    
    # Get all chunk files sorted by index
    chunk_files = sorted(
        [f for f in os.listdir(chunks_dir) if f.endswith('.chunk')],
        key=lambda x: int(x.split('.')[0])
    )
    
    # Combine chunks
    file_content = bytearray()
    for chunk_file in chunk_files:
        chunk_path = os.path.join(chunks_dir, chunk_file)
        with open(chunk_path, 'rb') as f:
            file_content.extend(f.read())
    
    return bytes(file_content)


def finalize_upload(
    session_id: str,
    vector_db_client: Any,
    collection_name: str
) -> Dict[str, Any]:
    """
    Finalize upload by combining chunks and processing the file.
    
    Args:
        session_id: Session identifier
        vector_db_client: Qdrant client instance
        collection_name: Collection name for vector storage
    
    Returns:
        Processing result with chunk and embedding statistics
    
    Raises:
        ValueError: If session not found or processing fails
    """
    session_info = get_session_info(session_id)
    
    if not session_info:
        raise ValueError(f"Session {session_id} not found")
    
    # Combine chunks into complete file
    file_content = combine_chunks(session_id)
    
    # Process the complete file through existing pipeline
    result = upload(
        file_content=file_content,
        filename=session_info["filename"],
        user_id=session_info["user_id"],
        vector_db_client=vector_db_client,
        collection_name=collection_name
    )
    
    # Cleanup session directory
    cleanup_session(session_id)
    
    return result


def cleanup_session(session_id: str):
    """
    Delete a session directory and all its contents.
    
    Args:
        session_id: Session identifier
    """
    import shutil
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)


def cleanup_expired_sessions(max_age_hours: int = SESSION_EXPIRY_HOURS):
    """
    Clean up expired upload sessions.
    
    Args:
        max_age_hours: Maximum age in hours before cleanup
    
    Returns:
        Number of sessions cleaned up
    """
    if not os.path.exists(SESSIONS_DIR):
        return 0
    
    cleaned_count = 0
    current_time = datetime.utcnow()
    
    for session_id in os.listdir(SESSIONS_DIR):
        session_info = get_session_info(session_id)
        
        if session_info:
            expires_at = datetime.fromisoformat(session_info["expires_at"])
            
            if current_time > expires_at:
                cleanup_session(session_id)
                cleaned_count += 1
    
    return cleaned_count


def upload(
    file_content: Union[bytes, BinaryIO],
    filename: str,
    user_id: str,
    vector_db_client: Any,
    collection_name: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 100
) -> Dict[str, Any]:
    """
    Complete upload workflow with embeddings and deduplication.
    This processes a complete file (called after resumable upload completes).
    
    Args:
        file_content: File content as bytes or file-like object
        filename: Original filename
        user_id: User identifier
        vector_db_client: Qdrant client instance
        collection_name: Collection name for vector storage
        chunk_size: Size of text chunks for processing
        chunk_overlap: Overlap between chunks
    
    Returns:
        Dictionary with processing results
    
    Raises:
        ValueError: If processing fails
    """
    # Process file to text chunks
    chunks_result = process_file_to_chunks(
        file_path_or_bytes=file_content,
        filename=filename,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    # Generate embeddings and upload to vector DB with deduplication
    embedding_result = process_chunks_with_embeddings(
        chunks=chunks_result['chunks'],
        vector_db_client=vector_db_client,
        collection_name=collection_name,
        similarity_threshold=SIMILARITY_THRESHOLD,
        model_name=EMBEDDING_MODEL
    )
    
    return {
        "filename": filename,
        "file_type": chunks_result['file_type'],
        "total_chunks": embedding_result['total_chunks'],
        "new_embeddings": embedding_result['new_embeddings'],
        "updated_embeddings": embedding_result['updated_embeddings'],
        "skipped_duplicates": embedding_result['skipped_duplicates'],
        "total_characters": chunks_result['total_characters']
    }
