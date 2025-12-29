import React, { useState, useEffect } from 'react';
import './FilesTab.css';

function FilesTab({ userId, apiUrl }) {
  const [files, setFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState({});
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchFiles = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${apiUrl}/files?user_id=${userId}`);
      const data = await response.json();
      
      if (data.success && data.files) {
        // Convert filenames to file objects
        const fileObjects = data.files.map(filename => ({
          name: filename,
          isCollection: false
        }));
        setFiles(fileObjects);
      }
    } catch (error) {
      console.error('Error fetching files:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    await uploadFile(file);
    e.target.value = ''; // Reset input
  };

  const uploadFile = async (file) => {
    setUploading(true);
    const sessionId = `${Date.now()}-${file.name}`;

    try {
      setUploadProgress({ [sessionId]: { filename: file.name, progress: 0, status: 'uploading' } });

      // Step 1: Create upload session
      const metadata = {
        filename: btoa(file.name),
        user_id: btoa(userId),
      };

      const createResponse = await fetch(`${apiUrl}/upload`, {
        method: 'POST',
        headers: {
          'Upload-Length': file.size.toString(),
          'Upload-Metadata': `filename ${metadata.filename},user_id ${metadata.user_id}`,
          'Tus-Resumable': '1.0.0',
        },
      });

      if (!createResponse.ok) {
        throw new Error('Failed to create upload session');
      }

      const createData = await createResponse.json();
      const uploadSessionId = createData.session_id;

      setUploadProgress({ [sessionId]: { filename: file.name, progress: 10, status: 'uploading' } });

      // Step 2: Upload file in chunks
      const chunkSize = 256 * 1024; // 256 KB chunks
      let offset = 0;

      while (offset < file.size) {
        const chunk = file.slice(offset, offset + chunkSize);
        const chunkData = await chunk.arrayBuffer();

        const uploadResponse = await fetch(`${apiUrl}/upload/${uploadSessionId}`, {
          method: 'PATCH',
          headers: {
            'Upload-Offset': offset.toString(),
            'Content-Type': 'application/offset+octet-stream',
            'Tus-Resumable': '1.0.0',
          },
          body: chunkData,
        });

        if (!uploadResponse.ok) {
          throw new Error('Failed to upload chunk');
        }

        offset += chunk.size;
        const progress = Math.round((offset / file.size) * 80) + 10; // 10-90%
        setUploadProgress({ [sessionId]: { filename: file.name, progress, status: 'uploading' } });
      }

      setUploadProgress({ [sessionId]: { filename: file.name, progress: 90, status: 'processing' } });

      // Step 3: Finalize upload
      const finalizeResponse = await fetch(`${apiUrl}/upload/${uploadSessionId}/finalize`, {
        method: 'POST',
      });

      if (!finalizeResponse.ok) {
        throw new Error('Failed to finalize upload');
      }

      await finalizeResponse.json();

      setUploadProgress({ [sessionId]: { filename: file.name, progress: 100, status: 'complete' } });

      // Refresh file list
      setTimeout(() => {
        setUploadProgress({});
        fetchFiles();
      }, 2000);

    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadProgress({ [sessionId]: { filename: file.name, progress: 0, status: 'error', error: error.message } });
    } finally {
      setUploading(false);
    }
  };

  const deleteFile = async (filename) => {
    if (!window.confirm(`Delete ${filename}?`)) return;

    try {
      const response = await fetch(`${apiUrl}/delete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename,
          user_id: userId,
        }),
      });

      const data = await response.json();
      if (data.success) {
        fetchFiles();
      }
    } catch (error) {
      console.error('Error deleting file:', error);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="files-tab">
      <div className="files-header">
        <h2>Document Files</h2>
        <label className="upload-btn">
          <input
            type="file"
            onChange={handleFileSelect}
            accept=".pdf,.doc,.docx,.txt,.json"
            disabled={uploading}
            style={{ display: 'none' }}
          />
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M12 4V16M12 4L8 8M12 4L16 8M4 17V19C4 20.1046 4.89543 21 6 21H18C19.1046 21 20 20.1046 20 19V17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Upload File
        </label>
      </div>

      {Object.keys(uploadProgress).length > 0 && (
        <div className="upload-progress-section">
          {Object.entries(uploadProgress).map(([id, progress]) => (
            <div key={id} className="upload-progress-item">
              <div className="upload-progress-header">
                <span className="upload-filename">{progress.filename}</span>
                <span className={`upload-status ${progress.status}`}>
                  {progress.status === 'uploading' && 'Uploading...'}
                  {progress.status === 'processing' && 'Processing...'}
                  {progress.status === 'complete' && '✓ Complete'}
                  {progress.status === 'error' && '✗ Error'}
                </span>
              </div>
              <div className="upload-progress-bar">
                <div 
                  className="upload-progress-fill"
                  style={{ width: `${progress.progress}%` }}
                />
              </div>
              {progress.error && (
                <div className="upload-error">{progress.error}</div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="files-list">
        {loading ? (
          <div className="loading-state">Loading files...</div>
        ) : files.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
                <path d="M7 18H17V16H7V18ZM7 14H17V12H7V14ZM5 22C4.45 22 3.979 21.804 3.587 21.412C3.195 21.02 2.99934 20.5493 3 20V4C3 3.45 3.196 2.979 3.588 2.587C3.98 2.195 4.45067 1.99934 5 2H14L19 7V20C19 20.55 18.804 21.021 18.412 21.413C18.02 21.805 17.5493 22.0007 17 22H5ZM13 8V4H5V20H17V8H13Z" fill="currentColor"/>
              </svg>
            </div>
            <p>No files uploaded yet</p>
            <p className="empty-state-hint">Upload PDF, JSON, DOC, DOCX, or TXT files to get started</p>
          </div>
        ) : (
          files.map((file, index) => (
            <div key={index} className="file-item">
              <div className="file-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M7 18H17V16H7V18ZM7 14H17V12H7V14ZM5 22C4.45 22 3.979 21.804 3.587 21.412C3.195 21.02 2.99934 20.5493 3 20V4C3 3.45 3.196 2.979 3.588 2.587C3.98 2.195 4.45067 1.99934 5 2H14L19 7V20C19 20.55 18.804 21.021 18.412 21.413C18.02 21.805 17.5493 22.0007 17 22H5ZM13 8V4H5V20H17V8H13Z" fill="currentColor"/>
                </svg>
              </div>
              <div className="file-info">
                <div className="file-name">{file.name}</div>
              </div>
              <button
                  className="delete-file-btn"
                  onClick={() => deleteFile(file.name)}
                  title="Delete file"
                >
                  <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                    <path d="M7 3H13M3 6H17M15 6L14.5 15C14.5 16.1046 13.6046 17 12.5 17H7.5C6.39543 17 5.5 16.1046 5.5 15L5 6M8 9V13M12 9V13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default FilesTab;
