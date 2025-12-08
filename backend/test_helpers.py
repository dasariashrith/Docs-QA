"""
Unit tests for helper functions.
Run with: pytest test_helpers.py
"""

import pytest
from io import BytesIO
from app.helpers import (
    calculate_content_hash,
    create_text_chunks,
    create_chunks_with_metadata,
    validate_file_size,
    validate_file_type,
    validate_chunk_parameters,
    is_duplicate_chunk,
    calculate_similarity,
    deduplicate_chunks,
    get_file_size_human_readable,
    calculate_estimated_chunks
)


class TestHashing:
    """Tests for hashing functions."""
    
    def test_calculate_content_hash(self):
        """Test hash calculation is consistent."""
        text = "Hello, World!"
        hash1 = calculate_content_hash(text)
        hash2 = calculate_content_hash(text)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters
    
    def test_different_texts_different_hashes(self):
        """Test different texts produce different hashes."""
        hash1 = calculate_content_hash("Text A")
        hash2 = calculate_content_hash("Text B")
        assert hash1 != hash2
    
    def test_is_duplicate_chunk(self):
        """Test duplicate detection."""
        existing = {"abc123", "def456"}
        assert is_duplicate_chunk("abc123", existing) is True
        assert is_duplicate_chunk("xyz789", existing) is False
    
    def test_calculate_similarity(self):
        """Test similarity calculation."""
        text1 = "This is a test"
        text2 = "This is a test"
        text3 = "Completely different"
        
        # Identical texts should have high similarity
        sim1 = calculate_similarity(text1, text2)
        assert sim1 > 0.9
        
        # Different texts should have low similarity
        sim2 = calculate_similarity(text1, text3)
        assert sim2 < 0.5


class TestChunking:
    """Tests for chunking functions."""
    
    def test_create_text_chunks(self):
        """Test basic text chunking."""
        text = "A" * 2500  # 2500 characters
        chunks = create_text_chunks(text, chunk_size=1000, chunk_overlap=100)
        assert len(chunks) == 3
        assert all(len(chunk) <= 1000 for chunk in chunks)
    
    def test_chunks_with_metadata(self):
        """Test chunks with metadata generation."""
        text = "Hello World! " * 100  # ~1300 characters
        chunks = create_chunks_with_metadata(
            text=text,
            filename="test.txt",
            chunk_size=500,
            chunk_overlap=50
        )
        
        assert len(chunks) > 0
        assert all('chunk_text' in chunk for chunk in chunks)
        assert all('chunk_index' in chunk for chunk in chunks)
        assert all('content_hash' in chunk for chunk in chunks)
        assert all('filename' in chunk for chunk in chunks)
    
    def test_empty_text_raises_error(self):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError):
            create_text_chunks("", chunk_size=1000)
    
    def test_invalid_chunk_size(self):
        """Test invalid chunk size raises ValueError."""
        with pytest.raises(ValueError):
            create_text_chunks("Some text", chunk_size=0)
    
    def test_deduplicate_chunks(self):
        """Test chunk deduplication."""
        chunks = [
            {"chunk_text": "Hello World", "content_hash": "abc123"},
            {"chunk_text": "Hello World", "content_hash": "abc123"},
            {"chunk_text": "Different", "content_hash": "def456"}
        ]
        
        unique = deduplicate_chunks(chunks)
        assert len(unique) == 2


class TestValidation:
    """Tests for validation functions."""
    
    def test_validate_file_size_valid(self):
        """Test valid file size."""
        size = 50 * 1024 * 1024  # 50 MB
        is_valid, message = validate_file_size(size)
        assert is_valid is True
    
    def test_validate_file_size_too_large(self):
        """Test file size exceeds limit."""
        size = 200 * 1024 * 1024  # 200 MB
        is_valid, message = validate_file_size(size, max_size_mb=100)
        assert is_valid is False
        assert "exceeds" in message.lower()
    
    def test_validate_file_type_supported(self):
        """Test supported file type."""
        is_valid, message = validate_file_type("document.pdf")
        assert is_valid is True
    
    def test_validate_file_type_unsupported(self):
        """Test unsupported file type."""
        is_valid, message = validate_file_type("image.png")
        assert is_valid is False
        assert "not supported" in message.lower()
    
    def test_validate_chunk_parameters_valid(self):
        """Test valid chunk parameters."""
        is_valid, message = validate_chunk_parameters(1000, 100)
        assert is_valid is True
    
    def test_validate_chunk_parameters_invalid(self):
        """Test invalid chunk parameters."""
        is_valid, message = validate_chunk_parameters(100, 150)
        assert is_valid is False
    
    def test_get_file_size_human_readable(self):
        """Test human-readable file size conversion."""
        assert "KB" in get_file_size_human_readable(1024 * 500)
        assert "MB" in get_file_size_human_readable(1024 * 1024 * 5)
        assert "GB" in get_file_size_human_readable(1024 * 1024 * 1024 * 2)
    
    def test_calculate_estimated_chunks(self):
        """Test chunk estimation."""
        text_length = 5000
        estimated = calculate_estimated_chunks(text_length, chunk_size=1000)
        assert estimated == 5


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_text_file_processing(self):
        """Test processing a text file end-to-end."""
        from app.helpers import extract_text_from_txt, create_chunks_with_metadata
        
        # Simulate file content
        content = "This is a test document. " * 100
        file_obj = BytesIO(content.encode('utf-8'))
        
        # Extract text
        text = extract_text_from_txt(file_obj)
        assert len(text) > 0
        
        # Create chunks
        chunks = create_chunks_with_metadata(text, "test.txt")
        assert len(chunks) > 0
        assert all('chunk_text' in chunk for chunk in chunks)
    
    def test_json_file_processing(self):
        """Test processing a JSON file."""
        from app.helpers import extract_text_from_json
        
        json_content = '{"name": "Test", "value": 123}'
        file_obj = BytesIO(json_content.encode('utf-8'))
        
        text = extract_text_from_json(file_obj)
        assert "Test" in text
        assert "123" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
