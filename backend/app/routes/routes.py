"""
Flask routes for the RAG Documentation QA API.
Implements TUS protocol for resumable file uploads.
"""

from flask import request, jsonify, Response
from werkzeug.utils import secure_filename
from datetime import datetime
import base64

from app.models.upload import (
    create_upload_session,
    get_session_info,
    save_chunk,
    finalize_upload,
    cleanup_session,
    cleanup_expired_sessions,
    CHUNK_SIZE
)
from app.helpers import delete_vectors_by_filename, list_filenames
from app.models.chat_history import (
    create_chat,
    add_message,
    get_user_chats,
    get_chat_by_id,
    get_chat_messages,
    get_chat_with_messages,
    update_chat_title,
    delete_chat,
    search_chats,
    auto_generate_title,
    get_conversation_context
)
from app.models.chat import generate_response


# TUS Protocol Version
TUS_VERSION = "1.0.0"
TUS_MAX_SIZE = 100 * 1024 * 1024  # 100 MB


def register_routes(app, qdrant_client, get_user_collection):
    """
    Register all routes with the Flask app.
    
    Args:
        app: Flask application instance
        qdrant_client: Qdrant client instance
        get_user_collection: Function to get/create user collection
    """
    
    @app.route('/')
    def index():
        """API information endpoint."""
        return jsonify({
            "name": "RAG Documentation QA API",
            "version": "1.0.0",
            "upload_protocol": "TUS 1.0.0",
            "endpoints": {
                "/": "API information",
                "/upload": "TUS resumable upload - POST (create), HEAD (status), PATCH (upload), DELETE (cancel)",
                "/upload/<session_id>/finalize": "Finalize and process uploaded file (POST)",
                "/delete": "Delete documents (POST)",
                "/health": "Health check",
                "/collections": "List user collections (GET)",
                "/cleanup-sessions": "Cleanup expired upload sessions (POST)"
            }
        })
    
    
    @app.route('/health')
    def health():
        """Health check endpoint."""
        try:
            # Check Qdrant connection
            qdrant_client.get_collections()
            qdrant_status = "healthy"
        except Exception as e:
            qdrant_status = f"unhealthy: {str(e)}"
        
        return jsonify({
            "status": "healthy" if qdrant_status == "healthy" else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "qdrant": qdrant_status,
                "flask": "healthy"
            }
        })
    
    
    @app.route('/collections')
    def list_collections():
        """List all collections (for debugging/admin)."""
        try:
            collections = qdrant_client.get_collections()
            return jsonify({
                "collections": [
                    {
                        "name": col.name,
                        "points": qdrant_client.get_collection(col.name).points_count
                    }
                    for col in collections.collections
                ]
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/upload', methods=['OPTIONS'])
    def upload_options():
        """
        TUS OPTIONS endpoint - Returns server capabilities.
        """
        response = Response()
        response.headers['Tus-Resumable'] = TUS_VERSION
        response.headers['Tus-Version'] = TUS_VERSION
        response.headers['Tus-Extension'] = 'creation,expiration'
        response.headers['Tus-Max-Size'] = str(TUS_MAX_SIZE)
        return response, 204
    
    
    @app.route('/upload', methods=['POST'])
    def create_upload():
        """
        TUS POST endpoint - Create a new upload session.
        
        Headers:
            Upload-Length: Total file size in bytes
            Upload-Metadata: Base64 encoded metadata (filename, user_id, etc.)
            Tus-Resumable: TUS protocol version
        
        Returns:
            201 Created with Location header pointing to upload URL
        """
        try:
            # Check TUS version
            tus_version = request.headers.get('Tus-Resumable')
            if not tus_version or tus_version != TUS_VERSION:
                return jsonify({
                    "error": f"Unsupported TUS version. Server supports {TUS_VERSION}"
                }), 412
            
            # Get upload length
            upload_length = request.headers.get('Upload-Length')
            if not upload_length:
                return jsonify({"error": "Upload-Length header is required"}), 400
            
            try:
                file_size = int(upload_length)
            except ValueError:
                return jsonify({"error": "Invalid Upload-Length"}), 400
            
            # Parse metadata from header
            upload_metadata = request.headers.get('Upload-Metadata', '')
            metadata = {}
            filename = None
            user_id = None
            
            if upload_metadata:
                # Parse base64 encoded metadata: "key1 value1,key2 value2"
                for pair in upload_metadata.split(','):
                    parts = pair.strip().split(' ', 1)
                    if len(parts) == 2:
                        key = parts[0]
                        try:
                            value = base64.b64decode(parts[1]).decode('utf-8')
                            metadata[key] = value
                            
                            if key == 'filename':
                                filename = value
                            elif key == 'user_id':
                                user_id = value
                        except Exception:
                            pass
            
            if not filename:
                return jsonify({"error": "filename is required in Upload-Metadata"}), 400
            
            if not user_id:
                return jsonify({"error": "user_id is required in Upload-Metadata"}), 400
            
            # Create upload session
            session_info = create_upload_session(
                filename=filename,
                file_size=file_size,
                user_id=user_id,
                metadata=metadata
            )
            
            # Build Location URL
            location = f"{request.url_root}upload/{session_info['session_id']}"
            
            response = jsonify({
                "session_id": session_info['session_id'],
                "expires_at": session_info['expires_at']
            })
            response.status_code = 201
            response.headers['Location'] = location
            response.headers['Tus-Resumable'] = TUS_VERSION
            response.headers['Upload-Expires'] = session_info['expires_at']
            
            return response
            
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/upload/<session_id>', methods=['HEAD'])
    def upload_status(session_id):
        """
        TUS HEAD endpoint - Get upload progress.
        
        Returns:
            200 OK with Upload-Offset header indicating bytes received
        """
        try:
            session_info = get_session_info(session_id)
            
            if not session_info:
                return jsonify({"error": "Session not found"}), 404
            
            response = Response()
            response.headers['Tus-Resumable'] = TUS_VERSION
            response.headers['Upload-Offset'] = str(session_info['uploaded_bytes'])
            response.headers['Upload-Length'] = str(session_info['file_size'])
            response.headers['Cache-Control'] = 'no-store'
            
            return response, 200
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/upload/<session_id>', methods=['PATCH'])
    def upload_chunk(session_id):
        """
        TUS PATCH endpoint - Upload a chunk of data.
        
        Headers:
            Upload-Offset: Byte offset for this chunk
            Content-Type: application/offset+octet-stream
            Content-Length: Size of this chunk
            Tus-Resumable: TUS protocol version
        
        Body:
            Binary chunk data
        
        Returns:
            204 No Content with updated Upload-Offset header
        """
        try:
            # Check TUS version
            tus_version = request.headers.get('Tus-Resumable')
            if not tus_version or tus_version != TUS_VERSION:
                return jsonify({
                    "error": f"Unsupported TUS version. Server supports {TUS_VERSION}"
                }), 412
            
            # Validate content type
            content_type = request.headers.get('Content-Type')
            if content_type != 'application/offset+octet-stream':
                return jsonify({
                    "error": "Content-Type must be application/offset+octet-stream"
                }), 400
            
            # Get upload offset
            upload_offset = request.headers.get('Upload-Offset')
            if not upload_offset:
                return jsonify({"error": "Upload-Offset header is required"}), 400
            
            try:
                offset = int(upload_offset)
            except ValueError:
                return jsonify({"error": "Invalid Upload-Offset"}), 400
            
            # Get chunk data
            chunk_data = request.get_data()
            
            if not chunk_data:
                return jsonify({"error": "No data provided"}), 400
            
            # Save chunk
            updated_session = save_chunk(session_id, chunk_data, offset)
            
            response = Response()
            response.status_code = 204
            response.headers['Tus-Resumable'] = TUS_VERSION
            response.headers['Upload-Offset'] = str(updated_session['uploaded_bytes'])
            
            return response
            
        except ValueError as e:
            return jsonify({"error": str(e)}), 409  # Conflict for offset mismatch
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/upload/<session_id>', methods=['DELETE'])
    def cancel_upload(session_id):
        """
        TUS DELETE endpoint - Cancel an upload and delete session.
        
        Returns:
            204 No Content
        """
        try:
            session_info = get_session_info(session_id)
            
            if not session_info:
                return jsonify({"error": "Session not found"}), 404
            
            cleanup_session(session_id)
            
            response = Response()
            response.status_code = 204
            response.headers['Tus-Resumable'] = TUS_VERSION
            
            return response
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/upload/<session_id>/finalize', methods=['POST'])
    def finalize_upload_endpoint(session_id):
        """
        Finalize upload endpoint - Process the completed upload.
        
        This should be called after all chunks have been uploaded successfully.
        It combines chunks, processes the file, and uploads to vector database.
        
        Returns:
            200 OK with processing results
        """
        try:
            session_info = get_session_info(session_id)
            
            if not session_info:
                return jsonify({"error": "Session not found"}), 404
            
            if session_info['status'] != 'complete':
                return jsonify({
                    "error": "Upload not complete",
                    "uploaded_bytes": session_info['uploaded_bytes'],
                    "file_size": session_info['file_size']
                }), 400
            
            # Get user's collection
            user_id = session_info['user_id']
            collection_name = get_user_collection(user_id)
            
            # Finalize and process upload
            result = finalize_upload(
                session_id=session_id,
                vector_db_client=qdrant_client,
                collection_name=collection_name
            )
            
            return jsonify({
                "success": True,
                "filename": result['filename'],
                "file_type": result['file_type'],
                "file_size": session_info['file_size'],
                "processing": {
                    "total_chunks": result['total_chunks'],
                    "new_embeddings": result['new_embeddings'],
                    "updated_embeddings": result['updated_embeddings'],
                    "skipped_duplicates": result['skipped_duplicates'],
                    "total_characters": result['total_characters']
                },
                "collection": collection_name,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/delete', methods=['POST'])
    def delete_file():
        """
        Delete endpoint with reference counting.
        
        Request:
            {
                "filename": "document.pdf",
                "user_id": "123"
            }
        
        Response:
            {
                "success": true,
                "filename": "document.pdf",
                "deletion": {
                    "deleted_count": 35,
                    "updated_count": 12,
                    "total_affected": 47
                },
                "collection": "user_123_documents"
            }
        """
        try:
            # Parse request
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            filename = data.get('filename')
            user_id = data.get('user_id')
            
            if not filename:
                return jsonify({"error": "filename is required"}), 400
            
            if not user_id:
                return jsonify({"error": "user_id is required"}), 400
            
            # Get user's collection
            collection_name = get_user_collection(user_id)
            
            # Delete vectors associated with the file
            deletion_result = delete_vectors_by_filename(
                vector_db_client=qdrant_client,
                collection_name=collection_name,
                filename=filename
            )
            
            return jsonify({
                "success": True,
                "filename": filename,
                "deletion": {
                    "deleted_count": deletion_result['deleted_count'],
                    "updated_count": deletion_result['updated_count'],
                    "total_affected": deletion_result['total_affected']
                },
                "collection": collection_name,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/files', methods=['GET'])
    def list_user_files():
        """
        List all files in a user's collection.
        
        Query Parameters:
            user_id: User identifier (required)
        
        Response:
            {
                "success": true,
                "files": ["document1.pdf", "document2.txt", ...],
                "count": 5,
                "collection": "user_123_documents"
            }
        """
        try:
            user_id = request.args.get('user_id')
            
            if not user_id:
                return jsonify({"error": "user_id query parameter is required"}), 400
            
            # Get user's collection
            collection_name = get_user_collection(user_id)
            
            # List all filenames in the collection
            filenames = list_filenames(
                vector_db_client=qdrant_client,
                collection_name=collection_name
            )
            
            return jsonify({
                "success": True,
                "files": filenames,
                "count": len(filenames),
                "collection": collection_name,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/cleanup-sessions', methods=['POST'])
    def cleanup_sessions():
        """
        Cleanup expired upload sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            cleaned_count = cleanup_expired_sessions()
            
            return jsonify({
                "success": True,
                "cleaned_sessions": cleaned_count,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500

    # ==================== CHAT ENDPOINTS ====================
    
    @app.route('/chats', methods=['POST'])
    def create_new_chat():
        """
        Create a new chat session.
        
        Request:
            {
                "user_id": "123",
                "title": "My Chat" (optional),
                "metadata": {} (optional)
            }
        
        Response:
            {
                "success": true,
                "chat": {
                    "chat_id": "uuid",
                    "user_id": "123",
                    "title": "My Chat",
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                    "metadata": {}
                }
            }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            user_id = data.get('user_id')
            if not user_id:
                return jsonify({"error": "user_id is required"}), 400
            
            title = data.get('title')
            metadata = data.get('metadata', {})
            
            chat = create_chat(user_id, title, metadata)
            
            return jsonify({
                "success": True,
                "chat": chat,
                "timestamp": datetime.utcnow().isoformat()
            }), 201
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/chats', methods=['GET'])
    def list_user_chats():
        """
        List all chats for a user.
        
        Query Parameters:
            user_id: User identifier (required)
            limit: Maximum number of chats (default: 50)
            offset: Pagination offset (default: 0)
        
        Response:
            {
                "success": true,
                "chats": [...],
                "count": 10,
                "limit": 50,
                "offset": 0
            }
        """
        try:
            user_id = request.args.get('user_id')
            if not user_id:
                return jsonify({"error": "user_id query parameter is required"}), 400
            
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
            
            chats = get_user_chats(user_id, limit, offset)
            
            return jsonify({
                "success": True,
                "chats": chats,
                "count": len(chats),
                "limit": limit,
                "offset": offset,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except ValueError as e:
            return jsonify({"error": "Invalid limit or offset parameter"}), 400
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/chats/<chat_id>', methods=['GET'])
    def get_chat(chat_id):
        """
        Get a specific chat with all its messages.
        
        Query Parameters:
            include_messages: Whether to include messages (default: true)
            message_limit: Maximum messages to return (default: 100)
        
        Response:
            {
                "success": true,
                "chat": {
                    "chat_id": "uuid",
                    "user_id": "123",
                    "title": "My Chat",
                    "messages": [...]
                }
            }
        """
        try:
            include_messages = request.args.get('include_messages', 'true').lower() == 'true'
            message_limit = int(request.args.get('message_limit', 100))
            
            if include_messages:
                chat = get_chat_with_messages(chat_id, message_limit)
            else:
                chat = get_chat_by_id(chat_id)
            
            if not chat:
                return jsonify({"error": "Chat not found"}), 404
            
            return jsonify({
                "success": True,
                "chat": chat,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except ValueError as e:
            return jsonify({"error": "Invalid message_limit parameter"}), 400
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/chats/<chat_id>', methods=['PATCH'])
    def update_chat(chat_id):
        """
        Update a chat's title.
        
        Request:
            {
                "title": "New Title"
            }
        
        Response:
            {
                "success": true,
                "message": "Chat updated successfully"
            }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            title = data.get('title')
            if not title:
                return jsonify({"error": "title is required"}), 400
            
            success = update_chat_title(chat_id, title)
            
            if not success:
                return jsonify({"error": "Chat not found"}), 404
            
            return jsonify({
                "success": True,
                "message": "Chat updated successfully",
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/chats/<chat_id>', methods=['DELETE'])
    def delete_chat_endpoint(chat_id):
        """
        Delete a chat and all its messages.
        
        Response:
            {
                "success": true,
                "message": "Chat deleted successfully"
            }
        """
        try:
            success = delete_chat(chat_id)
            
            if not success:
                return jsonify({"error": "Chat not found"}), 404
            
            return jsonify({
                "success": True,
                "message": "Chat deleted successfully",
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/chats/<chat_id>/messages', methods=['POST'])
    def add_chat_message(chat_id):
        """
        Add a message to a chat.
        
        Request:
            {
                "role": "user" or "assistant",
                "content": "Message content",
                "metadata": {} (optional)
            }
        
        Response:
            {
                "success": true,
                "message": {
                    "message_id": "uuid",
                    "chat_id": "uuid",
                    "role": "user",
                    "content": "...",
                    "created_at": "..."
                }
            }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            role = data.get('role')
            content = data.get('content')
            
            if not role:
                return jsonify({"error": "role is required"}), 400
            if not content:
                return jsonify({"error": "content is required"}), 400
            if role not in ['user', 'assistant']:
                return jsonify({"error": "role must be 'user' or 'assistant'"}), 400
            
            metadata = data.get('metadata', {})
            
            # Check if chat exists
            chat = get_chat_by_id(chat_id)
            if not chat:
                return jsonify({"error": "Chat not found"}), 404
            
            # Add message
            message = add_message(chat_id, role, content, metadata)
            
            # Auto-generate title from first user message if title is still "New Chat"
            if chat['title'] == "New Chat" and role == 'user':
                messages = get_chat_messages(chat_id, limit=1)
                if len(messages) == 1:  # This is the first message
                    auto_generate_title(chat_id, content)
            
            return jsonify({
                "success": True,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }), 201
            
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/chats/<chat_id>/messages', methods=['GET'])
    def get_messages(chat_id):
        """
        Get all messages for a chat.
        
        Query Parameters:
            limit: Maximum messages to return (default: 100)
            offset: Pagination offset (default: 0)
        
        Response:
            {
                "success": true,
                "messages": [...],
                "count": 10,
                "limit": 100,
                "offset": 0
            }
        """
        try:
            limit = int(request.args.get('limit', 100))
            offset = int(request.args.get('offset', 0))
            
            # Check if chat exists
            chat = get_chat_by_id(chat_id)
            if not chat:
                return jsonify({"error": "Chat not found"}), 404
            
            messages = get_chat_messages(chat_id, limit, offset)
            
            return jsonify({
                "success": True,
                "messages": messages,
                "count": len(messages),
                "limit": limit,
                "offset": offset,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except ValueError as e:
            return jsonify({"error": "Invalid limit or offset parameter"}), 400
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/chats/search', methods=['GET'])
    def search_user_chats():
        """
        Search through user's chats and messages.
        
        Query Parameters:
            user_id: User identifier (required)
            q: Search query (required)
            limit: Maximum results (default: 20)
        
        Response:
            {
                "success": true,
                "chats": [...],
                "query": "search term",
                "count": 5
            }
        """
        try:
            user_id = request.args.get('user_id')
            query = request.args.get('q')
            
            if not user_id:
                return jsonify({"error": "user_id query parameter is required"}), 400
            if not query:
                return jsonify({"error": "q (query) parameter is required"}), 400
            
            limit = int(request.args.get('limit', 20))
            
            chats = search_chats(user_id, query, limit)
            
            return jsonify({
                "success": True,
                "chats": chats,
                "query": query,
                "count": len(chats),
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except ValueError as e:
            return jsonify({"error": "Invalid limit parameter"}), 400
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    
    @app.route('/chats/<chat_id>/context', methods=['GET'])
    def get_chat_context(chat_id):
        """
        Get conversation context for LLM prompting.
        
        Query Parameters:
            max_messages: Maximum recent messages (default: 10)
        
        Response:
            {
                "success": true,
                "context": [
                    {"role": "user", "content": "..."},
                    {"role": "assistant", "content": "..."}
                ]
            }
        """
        try:
            max_messages = int(request.args.get('max_messages', 10))
            
            # Check if chat exists
            chat = get_chat_by_id(chat_id)
            if not chat:
                return jsonify({"error": "Chat not found"}), 404
            
            context = get_conversation_context(chat_id, max_messages)
            
            return jsonify({
                "success": True,
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except ValueError as e:
            return jsonify({"error": "Invalid max_messages parameter"}), 400
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
    
    @app.route('/chat/generate-response', methods=['POST'])
    def generate_chat_response():
        """
        Generate a response from the chat model based on conversation context.
        
        Request:
            {
                "chat_id": "uuid",
                "user_id": "123",
                "message": "User's message",
                "max_context_messages": 10 (optional)
            }
        
        Response:
            {
                "success": true,
                "response": "Assistant's response"
            }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400
            
            chat_id = data.get('chat_id')
            user_id = data.get('user_id')
            message = data.get('message')
            
            if not chat_id:
                return jsonify({"error": "chat_id is required"}), 400
            if not user_id:
                return jsonify({"error": "user_id is required"}), 400
            if not message:
                return jsonify({"error": "message is required"}), 400
            
            response = generate_response(
                user_message=message,
                user_id=user_id,
                chat_id=chat_id)
            return jsonify({
                "success": True,
                "response": response,
                "timestamp": datetime.utcnow().isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "type": type(e).__name__
            }), 500
