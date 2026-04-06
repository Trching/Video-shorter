import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState('');

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
    setError(null);
    setDownloadUrl(null);
    if (file) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      setStatus(`✓ Selected: ${file.name} (${sizeMB} MB)`);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setError(null);
    setStatus('Processing...');
    
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      setStatus('Uploading video...');
      
      const response = await axios.post('http://localhost:8000/process', formData, {
        responseType: 'blob',
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setStatus(`Uploading... ${percentCompleted}%`);
        }
      });

      // Create a download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      setDownloadUrl(url);
      setStatus('✓ Video processed successfully! Ready to download.');
    } catch (error) {
      console.error('Error processing video:', error);
      
      let errorMsg = 'Error processing video. ';
      if (error.response?.data) {
        try {
          const errorData = await error.response.data.text();
          const parsed = JSON.parse(errorData);
          errorMsg += parsed.detail || 'Unknown error';
        } catch (e) {
          errorMsg += error.response.status === 0 ? 'Backend not responding. Make sure backend is running.' : `HTTP ${error.response.status}`;
        }
      } else if (error.message) {
        errorMsg += error.message;
      }
      
      setError(errorMsg);
      setStatus('');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <h1>🎬 Video Shorter</h1>
          <p className="subtitle">AI-powered video shortening using Whisper & DeepSeek</p>
        </header>

        <main className="main">
          <div className="upload-section">
            <label htmlFor="videoFile" className="file-input-label">
              📁 Select Video File
            </label>
            <input 
              id="videoFile"
              type="file" 
              accept="video/*" 
              onChange={handleFileSelect}
              disabled={uploading}
              className="file-input"
            />
            
            {selectedFile && (
              <div className="file-preview">
                <span>📹 {selectedFile.name}</span>
                <span className="file-size">({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)</span>
              </div>
            )}
          </div>

          <button 
            onClick={handleUpload} 
            disabled={!selectedFile || uploading}
            className="submit-button"
          >
            {uploading ? '⏳ Processing...' : '✨ Shorten Video'}
          </button>

          {status && (
            <div className={`status-message ${uploading ? 'processing' : 'success'}`}>
              {status}
            </div>
          )}

          {error && (
            <div className="error-message">
              ❌ {error}
            </div>
          )}

          {downloadUrl && (
            <div className="download-section">
              <div className="success-icon">✓</div>
              <h2>Your video is ready!</h2>
              <a href={downloadUrl} download="shortened_video.mp4" className="download-button">
                ⬇️ Download Shortened Video
              </a>
              <button 
                onClick={() => {
                  setDownloadUrl(null);
                  setStatus('');
                  setSelectedFile(null);
                  document.getElementById('videoFile').value = '';
                }}
                className="process-another-button"
              >
                Process Another Video
              </button>
            </div>
          )}

          <div className="info-section">
            <h3>How it works:</h3>
            <ol>
              <li><strong>Transcribe:</strong> Whisper converts video audio to text</li>
              <li><strong>Analyze:</strong> DeepSeek LLM identifies off-topic content</li>
              <li><strong>Clip:</strong> FFmpeg removes irrelevant segments</li>
              <li><strong>Download:</strong> Get your shortened video</li>
            </ol>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;