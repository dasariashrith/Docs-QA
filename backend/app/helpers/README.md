# Helper Functions Documentation

This directory contains framework-agnostic helper functions for the RAG application. These functions can be used with Flask, FastAPI, CLI scripts, or any Python application.

## Overview

The helper functions are organized into four modules:

1. **file_parsers.py** - Extract text from various file formats
2. **chunking.py** - Split text into semantic chunks
3. **hashing.py** - Calculate hashes and detect duplicates
4. **validation.py** - Validate file uploads and storage limits

## Quick Start

### Example 1: Process a File to Chunks

```python
from app.helpers import process_file_to_chunks

# From file path
result = process_file_to_chunks(
    file_path_or_bytes="/path/to/document.pdf",
    filename="document.pdf",
    chunk_size=1000,
    chunk_overlap=100
)

print(f"Created {result['total_chunks']} chunks")
print(f"First chunk: {result['chunks'][0]['chunk_text'][:100]}...")
```

### Example 2: Use in Flask Route

```python
from flask import request
from app.helpers import process_file_to_chunks, validate_file_size, validate_file_type

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    
    # Validate
    is_valid, message = validate_file_type(file.filename)
    if not is_valid:
        return {"error": message}, 400
    
    # Process
    result = process_file_to_chunks(file, file.filename)
    return {"chunks": result['chunks']}, 200
```

### Example 3: Direct Text Chunking

```python
from app.helpers import create_chunks_with_metadata

text = "Your long document text here..."
chunks = create_chunks_with_metadata(
    text=text,
    filename="document.txt",
    chunk_size=500,
    chunk_overlap=50
)

for chunk in chunks:
    print(f"Chunk {chunk['chunk_index']}: {chunk['content_hash'][:8]}...")
```

### Example 4: Deduplication

```python
from app.helpers import calculate_content_hash, is_duplicate_chunk

# Calculate hash
text = "Some content"
hash_value = calculate_content_hash(text)

# Check for duplicates
existing_hashes = {"abc123", "def456", "ghi789"}
if is_duplicate_chunk(hash_value, existing_hashes):
    print("Duplicate detected!")
```

### Example 5: Find Similar Chunks

```python
from app.helpers import find_similar_chunks

new_text = "This is a new chunk of text"
existing_chunks = [
    {"chunk_text": "This is an existing chunk of text", "chunk_index": 0},
    {"chunk_text": "Completely different content", "chunk_index": 1}
]

similar = find_similar_chunks(new_text, existing_chunks, threshold=0.8)
for item in similar:
    print(f"Found similar chunk with {item['similarity']:.2%} similarity")
```

## Module Details

### file_parsers.py

**Functions:**
- `extract_text_from_pdf(file_path_or_bytes)` - Extract text from PDF
- `extract_text_from_txt(file_path_or_bytes)` - Extract text from TXT
- `extract_text_from_json(file_path_or_bytes)` - Convert JSON to text
- `extract_text_from_file(file_path_or_bytes, file_type)` - Universal extractor
- `process_file_to_chunks(file_path_or_bytes, filename, chunk_size, chunk_overlap)` - Complete pipeline

**Supported File Types:**
- `.pdf` - PDF documents
- `.txt` - Plain text files
- `.json` - JSON files
- `.md` - Markdown files
- `.csv` - CSV files

### chunking.py

**Functions:**
- `create_text_chunks(text, chunk_size, chunk_overlap)` - Create text chunks
- `create_chunks_with_metadata(text, filename, chunk_size, chunk_overlap)` - Chunks with metadata
- `merge_overlapping_chunks(chunks, min_similarity)` - Deduplicate chunks
- `get_chunk_statistics(chunks)` - Get statistics about chunks

**Chunk Metadata Structure:**
```python
{
    "chunk_text": "The actual text content...",
    "chunk_index": 0,
    "filename": "document.pdf",
    "content_hash": "sha256_hash_here",
    "chunk_length": 950,
    "created_at": "2025-01-01T10:00:00Z"
}
```

### hashing.py

**Functions:**
- `calculate_content_hash(text)` - Calculate SHA-256 hash
- `is_duplicate_chunk(chunk_hash, existing_hashes)` - Check for duplicates
- `calculate_similarity(text1, text2)` - Calculate similarity score
- `find_similar_chunks(new_chunk_text, existing_chunks, threshold)` - Find similar chunks
- `deduplicate_chunks(chunks, threshold)` - Remove duplicates
- `batch_calculate_hashes(texts)` - Calculate multiple hashes
- `create_hash_index(chunks)` - Create hash lookup index

### validation.py

**Functions:**
- `validate_file_size(file_size_bytes, max_size_mb)` - Validate file size
- `validate_file_type(filename, allowed_types)` - Validate file type
- `validate_user_quota(current_usage, new_file_size, max_storage)` - Check quota
- `calculate_storage_size(chunks)` - Calculate storage needed
- `estimate_embedding_size(num_chunks, embedding_dimension)` - Estimate vector storage
- `get_file_size_mb(file_size_bytes)` - Convert to MB
- `get_file_size_human_readable(file_size_bytes)` - Human-readable size
- `validate_chunk_parameters(chunk_size, chunk_overlap)` - Validate parameters
- `calculate_estimated_chunks(text_length, chunk_size)` - Estimate chunk count

**Default Limits:**
- Max file size: 100 MB
- Max user storage: 1 GB
- Supported file types: `.pdf`, `.txt`, `.json`, `.md`, `.csv`

## Advanced Usage

### Custom File Type Support

To add support for a new file type:

```python
from app.helpers.file_parsers import extract_text_from_file

# Add to extractors dictionary in extract_text_from_file()
# Or create a custom extractor:

def extract_text_from_docx(file_path_or_bytes):
    # Your extraction logic here
    pass
```

### Batch Processing

```python
from app.helpers import process_file_to_chunks
import os

def process_directory(directory_path):
    results = []
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        try:
            result = process_file_to_chunks(file_path, filename)
            results.append(result)
        except Exception as e:
            print(f"Failed to process {filename}: {e}")
    return results
```

### CLI Usage

```python
# save as process_file.py
import sys
from app.helpers import process_file_to_chunks

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_file.py <filepath>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    filename = filepath.split('/')[-1]
    
    result = process_file_to_chunks(filepath, filename)
    print(f"Processed {filename}")
    print(f"Total chunks: {result['total_chunks']}")
    print(f"Total characters: {result['total_characters']}")
```

Run: `python process_file.py document.pdf`

### Testing Helper Functions

```python
import pytest
from app.helpers import calculate_content_hash, create_text_chunks

def test_calculate_hash():
    text = "Hello, World!"
    hash1 = calculate_content_hash(text)
    hash2 = calculate_content_hash(text)
    assert hash1 == hash2  # Same text should have same hash

def test_create_chunks():
    text = "A" * 2500  # 2500 characters
    chunks = create_text_chunks(text, chunk_size=1000, chunk_overlap=100)
    assert len(chunks) == 3  # Should create 3 chunks
```

## Error Handling

All functions raise appropriate exceptions:

- `ValueError` - Invalid parameters or unsupported file types
- `TypeError` - Wrong parameter types
- Generic `Exception` - Unexpected errors with descriptive messages

Always wrap function calls in try-except blocks:

```python
try:
    result = process_file_to_chunks(file, filename)
except ValueError as e:
    print(f"Validation error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance Tips

1. **Batch Processing**: Use `batch_calculate_hashes()` for multiple texts
2. **Caching**: Cache hash calculations for frequently accessed content
3. **Async Processing**: Use with Celery for background processing
4. **Chunk Size**: Larger chunks = fewer chunks but less granular search
5. **Deduplication**: Use hash-based deduplication before similarity checks

## Integration Examples

### With Celery (Background Jobs)

```python
from celery import Celery
from app.helpers import process_file_to_chunks

app = Celery('tasks')

@app.task
def process_file_async(file_path, filename):
    result = process_file_to_chunks(file_path, filename)
    # Store in vector DB
    return result
```

### With FastAPI

```python
from fastapi import FastAPI, UploadFile
from app.helpers import process_file_to_chunks, validate_file_type

app = FastAPI()

@app.post("/upload")
async def upload_file(file: UploadFile):
    is_valid, message = validate_file_type(file.filename)
    if not is_valid:
        return {"error": message}
    
    content = await file.read()
    result = process_file_to_chunks(content, file.filename)
    return {"chunks": result['total_chunks']}
```

### With Vector Database (Qdrant)

```python
from qdrant_client import QdrantClient
from app.helpers import process_file_to_chunks
from sentence_transformers import SentenceTransformer

client = QdrantClient("localhost", port=6333)
model = SentenceTransformer('all-MiniLM-L6-v2')

def upload_to_vector_db(file_path, filename, collection_name):
    # Process file
    result = process_file_to_chunks(file_path, filename)
    
    # Generate embeddings
    texts = [chunk['chunk_text'] for chunk in result['chunks']]
    embeddings = model.encode(texts)
    
    # Upload to Qdrant
    points = []
    for i, (chunk, embedding) in enumerate(zip(result['chunks'], embeddings)):
        points.append({
            "id": i,
            "vector": embedding.tolist(),
            "payload": chunk
        })
    
    client.upsert(collection_name=collection_name, points=points)
```

## Best Practices

1. **Always validate** files before processing
2. **Check quotas** before uploading
3. **Use deduplication** to save storage
4. **Handle errors** gracefully with try-except
5. **Log processing** for debugging
6. **Clean up** temporary files
7. **Test** with various file types and sizes
8. **Monitor** storage usage and performance

## Support

For issues or questions:
- Check function docstrings for detailed parameter descriptions
- Review test files for usage examples
- Consult the main project documentation
