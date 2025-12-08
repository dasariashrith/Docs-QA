"""
File parsing utilities for extracting text from various file formats.
Framework-agnostic - works with file paths or file-like objects.
"""

import os
import json
from io import BytesIO
from typing import Union, Dict, List
import PyPDF2


def extract_text_from_pdf(file_path_or_bytes: Union[str, BytesIO]) -> str:
    """
    Extract text from PDF file.
    
    Args:
        file_path_or_bytes: Either file path (str) or file-like object (BytesIO)
    
    Returns:
        str: Extracted text content
        
    Raises:
        ValueError: If PDF cannot be read
    """
    try:
        if isinstance(file_path_or_bytes, str):
            with open(file_path_or_bytes, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                content = ''
                for page in reader.pages:
                    content += page.extract_text()
        else:
            reader = PyPDF2.PdfReader(file_path_or_bytes)
            content = ''
            for page in reader.pages:
                content += page.extract_text()
        
        return content.strip()
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def extract_text_from_txt(file_path_or_bytes: Union[str, BytesIO]) -> str:
    """
    Extract text from TXT file.
    
    Args:
        file_path_or_bytes: Either file path (str) or file-like object (BytesIO)
    
    Returns:
        str: Extracted text content
        
    Raises:
        ValueError: If text cannot be decoded
    """
    try:
        if isinstance(file_path_or_bytes, str):
            with open(file_path_or_bytes, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            if hasattr(file_path_or_bytes, 'read'):
                content = file_path_or_bytes.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
            else:
                content = file_path_or_bytes.decode('utf-8')
        
        return content.strip()
    except Exception as e:
        raise ValueError(f"Failed to extract text from TXT: {str(e)}")


def extract_text_from_json(file_path_or_bytes: Union[str, BytesIO]) -> str:
    """
    Extract text from JSON file by converting it to readable text.
    
    Args:
        file_path_or_bytes: Either file path (str) or file-like object (BytesIO)
    
    Returns:
        str: JSON content formatted as text
        
    Raises:
        ValueError: If JSON cannot be parsed
    """
    try:
        if isinstance(file_path_or_bytes, str):
            with open(file_path_or_bytes, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            if hasattr(file_path_or_bytes, 'read'):
                content = file_path_or_bytes.read()
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                data = json.loads(content)
            else:
                content = file_path_or_bytes.decode('utf-8')
                data = json.loads(content)
        
        # Convert JSON to readable text format
        return json.dumps(data, indent=2)
    except Exception as e:
        raise ValueError(f"Failed to extract text from JSON: {str(e)}")


def extract_text_from_file(file_path_or_bytes: Union[str, BytesIO], file_type: str) -> str:
    """
    Universal text extractor - routes to specific parser based on file type.
    
    Args:
        file_path_or_bytes: File path or file-like object
        file_type: File extension (.pdf, .txt, .json, etc.)
    
    Returns:
        str: Extracted text content
        
    Raises:
        ValueError: If file type is not supported or extraction fails
    """
    file_type = file_type.lower()
    if not file_type.startswith('.'):
        file_type = f'.{file_type}'
    
    extractors = {
        '.pdf': extract_text_from_pdf,
        '.txt': extract_text_from_txt,
        '.json': extract_text_from_json,
        '.md': extract_text_from_txt,  # Markdown as text
        '.csv': extract_text_from_txt,  # CSV as text
    }
    
    if file_type not in extractors:
        raise ValueError(f"Unsupported file type: {file_type}. Supported types: {list(extractors.keys())}")
    
    return extractors[file_type](file_path_or_bytes)


def process_file_to_chunks(
    file_path_or_bytes: Union[str, BytesIO],
    filename: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 100
) -> Dict:
    """
    Complete pipeline: file → text → chunks with metadata.
    
    Args:
        file_path_or_bytes: File path or file-like object
        filename: Original filename (used to detect type and metadata)
        chunk_size: Maximum characters per chunk (default: 1000)
        chunk_overlap: Overlap between chunks (default: 100)
    
    Returns:
        dict: {
            "chunks": List[dict],  # Chunks with metadata
            "total_chunks": int,
            "total_characters": int,
            "file_type": str,
            "filename": str
        }
        
    Raises:
        ValueError: If file processing fails
    """
    from .chunking import create_chunks_with_metadata
    
    # Extract file type from filename
    file_type = os.path.splitext(filename)[1].lower()
    
    # Extract text from file
    try:
        text = extract_text_from_file(file_path_or_bytes, file_type)
        print(f"Extracted {len(text)} characters from file '{filename}'")
        print("data", text[:500])  # Print first 500 characters for debugging
    except Exception as e:
        raise ValueError(f"Failed to process file '{filename}': {str(e)}")
    
    # Create chunks with metadata
    chunks = create_chunks_with_metadata(
        text=text,
        filename=filename,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        file_type=file_type
    )
    
    return {
        "chunks": chunks,
        "total_chunks": len(chunks),
        "total_characters": len(text),
        "file_type": file_type,
        "filename": filename
    }
