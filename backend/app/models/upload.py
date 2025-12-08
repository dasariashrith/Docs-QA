"""
Flask routes for file upload and processing.
This is a thin wrapper around helper functions.
"""

from flask import request
from app.helpers import (
    process_file_to_chunks,
    validate_file_size,
    validate_file_type
)


def create_chunk_file():
    """
    Flask endpoint for chunking uploaded files.
    Uses helper functions for framework-agnostic processing.
    
    Returns:
        tuple: (response_dict, status_code)
    """
    # Check if file is present in request
    if 'file' not in request.files:
        return {"error": "No file part in request"}, 400

    file = request.files['file']
    
    # Check if filename is provided
    if file.filename == '':
        return {"error": "No file selected"}, 400
    
    # Validate file type
    is_valid_type, type_message = validate_file_type(file.filename)
    if not is_valid_type:
        return {"error": type_message}, 400
    
    # Get file size (seek to end, get position, seek back to start)
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Seek back to start
    
    # Validate file size
    is_valid_size, size_message = validate_file_size(file_size)
    if not is_valid_size:
        return {"error": size_message}, 400
    
    try:
        # Process file to chunks using helper function
        result = process_file_to_chunks(
            file_path_or_bytes=file,
            filename=file.filename,
            chunk_size=1000,
            chunk_overlap=100
        )
        
        return {
            "success": True,
            "filename": result["filename"],
            "file_type": result["file_type"],
            "total_chunks": result["total_chunks"],
            "total_characters": result["total_characters"],
            "chunks": result["chunks"]
        }, 200
        
    except ValueError as e:
        return {"error": f"File processing failed: {str(e)}"}, 400
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}, 500
