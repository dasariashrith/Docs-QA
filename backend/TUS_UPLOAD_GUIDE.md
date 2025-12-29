# TUS Resumable Upload Guide

This guide explains how to use the TUS protocol-based resumable upload implementation in the RAG Documentation QA API.

## Overview

The API implements the [TUS protocol v1.0.0](https://tus.io/protocols/resumable-upload.html) for resumable file uploads. This allows:

- **Chunked uploads**: Files are uploaded in 5MB chunks
- **Resume capability**: If upload fails, it can resume from the last successful chunk
- **Progress tracking**: Check upload progress at any time
- **Session management**: Uploads are tracked via session IDs with 24-hour expiry

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Client                               │
│  (Frontend with TUS client library or custom implementation) │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ TUS Protocol (HTTP)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Flask Application                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           app/routes/routes.py                       │   │
│  │  (HTTP Layer - TUS Protocol Implementation)         │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         app/models/upload.py                         │   │
│  │  (Business Logic - Session Management & Processing)  │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           File System Storage                        │   │
│  │  uploads/sessions/<session_id>/chunks/               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### 1. OPTIONS /upload
**Discover server capabilities**

```bash
curl -X OPTIONS http://localhost:5000/upload
```

Response Headers:
- `Tus-Resumable: 1.0.0`
- `Tus-Version: 1.0.0`
- `Tus-Extension: creation,expiration`
- `Tus-Max-Size: 104857600` (100 MB)

---

### 2. POST /upload
**Create a new upload session**

```bash
curl -X POST http://localhost:5000/upload \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Length: 10485760" \
  -H "Upload-Metadata: filename $(echo -n "document.pdf" | base64),user_id $(echo -n "user123" | base64)"
```

Request Headers:
- `Tus-Resumable: 1.0.0` (required)
- `Upload-Length: <file_size_in_bytes>` (required)
- `Upload-Metadata: <base64_encoded_metadata>` (required)
  - Format: `key1 base64_value1,key2 base64_value2`
  - Required keys: `filename`, `user_id`

Response (201 Created):
```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "expires_at": "2025-01-10T20:00:00.000000"
}
```

Response Headers:
- `Location: http://localhost:5000/upload/<session_id>`
- `Upload-Expires: 2025-01-10T20:00:00.000000`

---

### 3. HEAD /upload/\<session_id\>
**Check upload progress**

```bash
curl -I http://localhost:5000/upload/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

Response Headers:
- `Tus-Resumable: 1.0.0`
- `Upload-Offset: 5242880` (bytes uploaded so far)
- `Upload-Length: 10485760` (total file size)

---

### 4. PATCH /upload/\<session_id\>
**Upload a chunk**

```bash
curl -X PATCH http://localhost:5000/upload/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Offset: 0" \
  -H "Content-Type: application/offset+octet-stream" \
  --data-binary @chunk_0.bin
```

Request Headers:
- `Tus-Resumable: 1.0.0` (required)
- `Upload-Offset: <byte_offset>` (required - must match server's current offset)
- `Content-Type: application/offset+octet-stream` (required)

Response (204 No Content):
Response Headers:
- `Upload-Offset: 5242880` (updated bytes uploaded)

---

### 5. DELETE /upload/\<session_id\>
**Cancel upload and delete session**

```bash
curl -X DELETE http://localhost:5000/upload/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

Response: 204 No Content

---

### 6. POST /upload/\<session_id\>/finalize
**Finalize and process the uploaded file**

Once all chunks are uploaded, call this endpoint to:
1. Combine chunks into complete file
2. Process file (chunk text, generate embeddings)
3. Upload to vector database with deduplication

```bash
curl -X POST http://localhost:5000/upload/a1b2c3d4-e5f6-7890-abcd-ef1234567890/finalize
```

Response (200 OK):
```json
{
  "success": true,
  "filename": "document.pdf",
  "file_type": "pdf",
  "file_size": 10485760,
  "processing": {
    "total_chunks": 50,
    "new_embeddings": 35,
    "updated_embeddings": 12,
    "skipped_duplicates": 3,
    "total_characters": 45000
  },
  "collection": "user_user123_documents",
  "timestamp": "2025-01-09T20:00:00.000000"
}
```

---

## Complete Upload Workflow

### Using Python

```python
import requests
import base64
import os

# Configuration
API_URL = "http://localhost:5000"
FILE_PATH = "document.pdf"
USER_ID = "user123"
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB

def upload_file(file_path, user_id):
    """Upload a file using TUS protocol."""
    
    # Get file size
    file_size = os.path.getsize(file_path)
    filename = os.path.basename(file_path)
    
    # Step 1: Create upload session
    print(f"Creating upload session for {filename} ({file_size} bytes)...")
    
    metadata = f"filename {base64.b64encode(filename.encode()).decode()}," \
               f"user_id {base64.b64encode(user_id.encode()).decode()}"
    
    response = requests.post(
        f"{API_URL}/upload",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": str(file_size),
            "Upload-Metadata": metadata
        }
    )
    
    if response.status_code != 201:
        raise Exception(f"Failed to create session: {response.json()}")
    
    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"✓ Session created: {session_id}")
    
    # Step 2: Upload chunks
    with open(file_path, 'rb') as f:
        offset = 0
        chunk_num = 0
        
        while offset < file_size:
            # Read chunk
            chunk = f.read(CHUNK_SIZE)
            chunk_size = len(chunk)
            
            print(f"Uploading chunk {chunk_num} ({offset}-{offset + chunk_size})...")
            
            # Upload chunk
            response = requests.patch(
                f"{API_URL}/upload/{session_id}",
                headers={
                    "Tus-Resumable": "1.0.0",
                    "Upload-Offset": str(offset),
                    "Content-Type": "application/offset+octet-stream"
                },
                data=chunk
            )
            
            if response.status_code != 204:
                raise Exception(f"Failed to upload chunk: {response.json()}")
            
            offset += chunk_size
            chunk_num += 1
            
            # Progress
            progress = (offset / file_size) * 100
            print(f"✓ Progress: {progress:.1f}%")
    
    print("✓ All chunks uploaded successfully")
    
    # Step 3: Finalize upload
    print("Finalizing upload and processing file...")
    
    response = requests.post(f"{API_URL}/upload/{session_id}/finalize")
    
    if response.status_code != 200:
        raise Exception(f"Failed to finalize: {response.json()}")
    
    result = response.json()
    print(f"✓ Upload complete!")
    print(f"  - Filename: {result['filename']}")
    print(f"  - File type: {result['file_type']}")
    print(f"  - Total chunks: {result['processing']['total_chunks']}")
    print(f"  - New embeddings: {result['processing']['new_embeddings']}")
    
    return result

# Usage
if __name__ == "__main__":
    result = upload_file("document.pdf", "user123")
```

### Resuming an Interrupted Upload

```python
def resume_upload(session_id, file_path):
    """Resume an interrupted upload."""
    
    # Step 1: Check current progress
    response = requests.head(f"{API_URL}/upload/{session_id}")
    
    if response.status_code != 200:
        raise Exception("Session not found or expired")
    
    current_offset = int(response.headers["Upload-Offset"])
    file_size = int(response.headers["Upload-Length"])
    
    print(f"Resuming from offset {current_offset}/{file_size}")
    
    # Step 2: Continue uploading from current offset
    with open(file_path, 'rb') as f:
        f.seek(current_offset)  # Seek to resume point
        offset = current_offset
        
        while offset < file_size:
            chunk = f.read(CHUNK_SIZE)
            
            response = requests.patch(
                f"{API_URL}/upload/{session_id}",
                headers={
                    "Tus-Resumable": "1.0.0",
                    "Upload-Offset": str(offset),
                    "Content-Type": "application/offset+octet-stream"
                },
                data=chunk
            )
            
            if response.status_code != 204:
                raise Exception(f"Failed to upload chunk: {response.json()}")
            
            offset += len(chunk)
    
    # Step 3: Finalize
    response = requests.post(f"{API_URL}/upload/{session_id}/finalize")
    return response.json()
```

---

## JavaScript/Frontend Example

```javascript
async function uploadFile(file, userId) {
  const API_URL = 'http://localhost:5000';
  const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
  
  // Step 1: Create session
  const metadata = btoa(`filename ${btoa(file.name)},user_id ${btoa(userId)}`);
  
  const createResponse = await fetch(`${API_URL}/upload`, {
    method: 'POST',
    headers: {
      'Tus-Resumable': '1.0.0',
      'Upload-Length': file.size.toString(),
      'Upload-Metadata': `filename ${btoa(file.name)},user_id ${btoa(userId)}`
    }
  });
  
  const { session_id } = await createResponse.json();
  console.log('Session created:', session_id);
  
  // Step 2: Upload chunks
  let offset = 0;
  
  while (offset < file.size) {
    const chunk = file.slice(offset, offset + CHUNK_SIZE);
    const chunkData = await chunk.arrayBuffer();
    
    const uploadResponse = await fetch(`${API_URL}/upload/${session_id}`, {
      method: 'PATCH',
      headers: {
        'Tus-Resumable': '1.0.0',
        'Upload-Offset': offset.toString(),
        'Content-Type': 'application/offset+octet-stream'
      },
      body: chunkData
    });
    
    if (!uploadResponse.ok) {
      throw new Error('Upload failed');
    }
    
    offset += chunk.size;
    console.log(`Progress: ${(offset / file.size * 100).toFixed(1)}%`);
  }
  
  // Step 3: Finalize
  const finalizeResponse = await fetch(
    `${API_URL}/upload/${session_id}/finalize`,
    { method: 'POST' }
  );
  
  const result = await finalizeResponse.json();
  console.log('Upload complete:', result);
  
  return result;
}
```

---

## Error Handling

### Common Error Codes

- **400 Bad Request**: Missing or invalid headers/parameters
- **404 Not Found**: Session not found or expired
- **409 Conflict**: Offset mismatch (use HEAD to get current offset)
- **412 Precondition Failed**: Unsupported TUS version
- **413 Payload Too Large**: File exceeds max size (100 MB)
- **500 Internal Server Error**: Server error during processing

### Handling Offset Mismatch

If you get a 409 error, the offset doesn't match:

```python
# Get current offset from server
response = requests.head(f"{API_URL}/upload/{session_id}")
current_offset = int(response.headers["Upload-Offset"])

# Resume from correct offset
# ... continue upload from current_offset
```

---

## Session Management

### Session Expiry

- Sessions expire after **24 hours**
- Expired sessions are automatically cleaned up
- Check `Upload-Expires` header for expiration time

### Manual Cleanup

```bash
# Cleanup expired sessions
curl -X POST http://localhost:5000/cleanup-sessions
```

Response:
```json
{
  "success": true,
  "cleaned_sessions": 5,
  "timestamp": "2025-01-09T20:00:00.000000"
}
```

---

## File Storage Structure

```
uploads/
├── sessions/
│   └── a1b2c3d4-e5f6-7890-abcd-ef1234567890/
│       ├── metadata.json
│       └── chunks/
│           ├── 0.chunk
│           ├── 1.chunk
│           └── 2.chunk
└── completed/
    └── user_123/
        └── document.pdf
```

Sessions are automatically cleaned up after finalization or expiry.

---

## Configuration

Key constants in `app/models/upload.py`:

```python
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB chunks
SESSION_EXPIRY_HOURS = 24      # Session expiry time
```

---

## Testing with curl

Complete example:

```bash
# 1. Create session
SESSION_RESPONSE=$(curl -s -X POST http://localhost:5000/upload \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Length: 1024000" \
  -H "Upload-Metadata: filename $(echo -n 'test.pdf' | base64),user_id $(echo -n 'user123' | base64)")

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
echo "Session ID: $SESSION_ID"

# 2. Upload chunk
curl -X PATCH http://localhost:5000/upload/$SESSION_ID \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Offset: 0" \
  -H "Content-Type: application/offset+octet-stream" \
  --data-binary @test.pdf

# 3. Check progress
curl -I http://localhost:5000/upload/$SESSION_ID

# 4. Finalize
curl -X POST http://localhost:5000/upload/$SESSION_ID/finalize
```

---

## Best Practices

1. **Always check offset before uploading**: Use HEAD request to verify current offset
2. **Implement retry logic**: Network failures can happen - retry with exponential backoff
3. **Monitor session expiry**: Check `Upload-Expires` header and complete upload before expiry
4. **Clean up cancelled uploads**: Use DELETE to cancel and clean up abandoned uploads
5. **Handle large files**: For files > 100MB, consider splitting or increasing max size
6. **Track progress**: Use Upload-Offset to show progress to users

---

## Troubleshooting

### Upload fails with 409 Conflict
- **Cause**: Offset mismatch
- **Solution**: Use HEAD to get current offset and resume from there

### Session not found (404)
- **Cause**: Session expired or deleted
- **Solution**: Create a new session and start upload again

### File processing fails after finalize
- **Cause**: Unsupported file type or corrupted file
- **Solution**: Check file type validation and ensure file is not corrupted

### Chunks not combining correctly
- **Cause**: Chunks uploaded out of order or with gaps
- **Solution**: Ensure offset calculation is correct and chunks are uploaded sequentially

---

For more information about the TUS protocol, visit: https://tus.io/
