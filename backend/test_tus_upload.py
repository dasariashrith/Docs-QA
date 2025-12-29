"""
Test script for TUS resumable upload implementation.
"""

import requests
import base64
import os
import json
from io import BytesIO

# Configuration
API_URL = "http://localhost:5000"
TEST_FILE = "docs.json"
USER_ID = "test_user_123"
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB


def test_tus_options():
    """Test OPTIONS endpoint for TUS capabilities."""
    print("\n" + "=" * 60)
    print("Test 1: OPTIONS /upload - Check TUS capabilities")
    print("=" * 60)
    
    response = requests.options(f"{API_URL}/upload")
    
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    print(f"  Tus-Resumable: {response.headers.get('Tus-Resumable')}")
    print(f"  Tus-Version: {response.headers.get('Tus-Version')}")
    print(f"  Tus-Extension: {response.headers.get('Tus-Extension')}")
    print(f"  Tus-Max-Size: {response.headers.get('Tus-Max-Size')}")
    
    assert response.status_code == 204, "OPTIONS should return 204"
    assert response.headers.get('Tus-Resumable') == '1.0.0', "Should support TUS 1.0.0"
    
    print("✓ Test passed!")


def test_create_session():
    """Test creating an upload session."""
    print("\n" + "=" * 60)
    print("Test 2: POST /upload - Create upload session")
    print("=" * 60)
    
    if not os.path.exists(TEST_FILE):
        print(f"✗ Test file {TEST_FILE} not found!")
        return None
    
    file_size = os.path.getsize(TEST_FILE)
    filename = os.path.basename(TEST_FILE)
    
    print(f"File: {filename}")
    print(f"Size: {file_size} bytes")
    
    # Encode metadata
    metadata = (
        f"filename {base64.b64encode(filename.encode()).decode()},"
        f"user_id {base64.b64encode(USER_ID.encode()).decode()}"
    )
    
    response = requests.post(
        f"{API_URL}/upload",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": str(file_size),
            "Upload-Metadata": metadata
        }
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        print(f"Session ID: {data['session_id']}")
        print(f"Expires At: {data['expires_at']}")
        print(f"Location: {response.headers.get('Location')}")
        print("✓ Test passed!")
        return data['session_id'], file_size
    else:
        print(f"✗ Test failed: {response.json()}")
        return None


def test_upload_chunks(session_id, file_size):
    """Test uploading file chunks."""
    print("\n" + "=" * 60)
    print("Test 3: PATCH /upload/<session_id> - Upload chunks")
    print("=" * 60)
    
    if not session_id:
        print("✗ No session ID provided")
        return False
    
    with open(TEST_FILE, 'rb') as f:
        offset = 0
        chunk_num = 0
        
        while offset < file_size:
            # Read chunk
            chunk = f.read(CHUNK_SIZE)
            chunk_size = len(chunk)
            
            print(f"\nChunk {chunk_num}: Uploading {chunk_size} bytes at offset {offset}")
            
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
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 204:
                new_offset = response.headers.get('Upload-Offset')
                print(f"New Offset: {new_offset}")
                progress = (int(new_offset) / file_size) * 100
                print(f"Progress: {progress:.1f}%")
            else:
                print(f"✗ Chunk upload failed: {response.json()}")
                return False
            
            offset += chunk_size
            chunk_num += 1
    
    print("\n✓ All chunks uploaded successfully!")
    return True


def test_upload_status(session_id):
    """Test checking upload status."""
    print("\n" + "=" * 60)
    print("Test 4: HEAD /upload/<session_id> - Check upload status")
    print("=" * 60)
    
    if not session_id:
        print("✗ No session ID provided")
        return
    
    response = requests.head(f"{API_URL}/upload/{session_id}")
    
    print(f"Status Code: {response.status_code}")
    print(f"Upload-Offset: {response.headers.get('Upload-Offset')}")
    print(f"Upload-Length: {response.headers.get('Upload-Length')}")
    print(f"Tus-Resumable: {response.headers.get('Tus-Resumable')}")
    
    assert response.status_code == 200, "HEAD should return 200"
    print("✓ Test passed!")


def test_finalize_upload(session_id):
    """Test finalizing the upload."""
    print("\n" + "=" * 60)
    print("Test 5: POST /upload/<session_id>/finalize - Finalize upload")
    print("=" * 60)
    
    if not session_id:
        print("✗ No session ID provided")
        return
    
    response = requests.post(f"{API_URL}/upload/{session_id}/finalize")
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\nProcessing Results:")
        print(f"  Filename: {data['filename']}")
        print(f"  File Type: {data['file_type']}")
        print(f"  File Size: {data['file_size']} bytes")
        print(f"  Total Chunks: {data['processing']['total_chunks']}")
        print(f"  New Embeddings: {data['processing']['new_embeddings']}")
        print(f"  Updated Embeddings: {data['processing']['updated_embeddings']}")
        print(f"  Skipped Duplicates: {data['processing']['skipped_duplicates']}")
        print(f"  Collection: {data['collection']}")
        print("✓ Test passed!")
    else:
        print(f"✗ Test failed: {response.json()}")


def test_cancel_upload():
    """Test cancelling an upload."""
    print("\n" + "=" * 60)
    print("Test 6: DELETE /upload/<session_id> - Cancel upload")
    print("=" * 60)
    
    # Create a session
    file_size = 1000000
    filename = "test_cancel.pdf"
    
    metadata = (
        f"filename {base64.b64encode(filename.encode()).decode()},"
        f"user_id {base64.b64encode(USER_ID.encode()).decode()}"
    )
    
    response = requests.post(
        f"{API_URL}/upload",
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Length": str(file_size),
            "Upload-Metadata": metadata
        }
    )
    
    if response.status_code == 201:
        session_id = response.json()['session_id']
        print(f"Created session: {session_id}")
        
        # Cancel it
        response = requests.delete(f"{API_URL}/upload/{session_id}")
        print(f"Delete Status Code: {response.status_code}")
        
        assert response.status_code == 204, "DELETE should return 204"
        
        # Verify it's gone
        response = requests.head(f"{API_URL}/upload/{session_id}")
        print(f"Verify deletion Status Code: {response.status_code}")
        
        assert response.status_code == 404, "Session should not exist after deletion"
        print("✓ Test passed!")
    else:
        print(f"✗ Failed to create session: {response.json()}")


def test_health_check():
    """Test health check endpoint."""
    print("\n" + "=" * 60)
    print("Test 7: GET /health - Health check")
    print("=" * 60)
    
    response = requests.get(f"{API_URL}/health")
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data['status']}")
        print(f"Services:")
        for service, status in data['services'].items():
            print(f"  {service}: {status}")
        print("✓ Test passed!")
    else:
        print(f"✗ Test failed: {response.json()}")


def test_api_info():
    """Test API information endpoint."""
    print("\n" + "=" * 60)
    print("Test 8: GET / - API information")
    print("=" * 60)
    
    response = requests.get(API_URL)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Name: {data['name']}")
        print(f"Version: {data['version']}")
        print(f"Upload Protocol: {data['upload_protocol']}")
        print("\nAvailable Endpoints:")
        for endpoint, description in data['endpoints'].items():
            print(f"  {endpoint}: {description}")
        print("✓ Test passed!")
    else:
        print(f"✗ Test failed: {response.json()}")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TUS RESUMABLE UPLOAD TEST SUITE")
    print("=" * 60)
    
    try:
        # Check if server is running
        response = requests.get(API_URL)
        if response.status_code != 200:
            print(f"\n✗ Server not responding at {API_URL}")
            print("Please start the Flask server first:")
            print("  cd backend && python -m app.app")
            return
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Cannot connect to server at {API_URL}")
        print("Please start the Flask server first:")
        print("  cd backend && python -m app.app")
        return
    
    # Run tests
    test_api_info()
    test_health_check()
    test_tus_options()
    
    # Main upload workflow test
    result = test_create_session()
    if result:
        session_id, file_size = result
        test_upload_status(session_id)
        
        if test_upload_chunks(session_id, file_size):
            test_upload_status(session_id)  # Check status after upload
            test_finalize_upload(session_id)
    
    # Test cancellation
    test_cancel_upload()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
