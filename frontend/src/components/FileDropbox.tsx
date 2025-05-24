import React, { useState, useRef, useEffect } from 'react';
import type { DragEvent } from 'react';

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  url: string;
  uploaded: boolean;
}

interface AnalysisStatus {
  status: 'idle' | 'running' | 'completed' | 'error';
  message?: string;
  conclusion?: string;
}

interface AnalysisSummary {
  case_overview: {
    files_analyzed: number;
    document_types: string[];
    total_characters: number;
  };
  analysis_metrics: {
    total_nodes_created: number;
    analysis_depth: number;
    tasks_completed: number;
    tasks_failed: number;
  };
  key_findings: string[];
  evidence_summary: Array<{
    type: string;
    description: string;
  }>;
  conclusion: string;
  case_status: string;
}

const FileDropbox: React.FC = () => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>({ status: 'idle' });
  const [uploading, setUploading] = useState(false);
  const [analysisSummary, setAnalysisSummary] = useState<AnalysisSummary | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const API_BASE = 'http://localhost:8000';

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (fileType: string): string => {
    if (fileType.startsWith('image/')) return '🖼️';
    if (fileType.startsWith('video/')) return '🎥';
    if (fileType.startsWith('audio/')) return '🎵';
    if (fileType.includes('pdf')) return '📄';
    if (fileType.includes('text/')) return '📝';
    if (fileType.includes('zip') || fileType.includes('rar')) return '📦';
    return '📁';
  };

  const uploadFilesToServer = async (files: UploadedFile[]) => {
    setUploading(true);
    
    try {
      for (const file of files) {
        // Create FormData for file upload
        const formData = new FormData();
        
        // Convert blob URL back to File object
        const response = await fetch(file.url);
        const blob = await response.blob();
        const fileObj = new File([blob], file.name, { type: file.type });
        
        formData.append('file', fileObj);
        
        // Upload to server
        const uploadResponse = await fetch(`${API_BASE}/api/upload`, {
          method: 'POST',
          body: formData,
        });
        
        if (uploadResponse.ok) {
          // Mark file as uploaded
          setUploadedFiles((prev) =>
            prev.map((f) =>
              f.id === file.id ? { ...f, uploaded: true } : f
            )
          );
        } else {
          throw new Error(`Failed to upload ${file.name}`);
        }
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert(`Upload failed: ${error}`);
    } finally {
      setUploading(false);
    }
  };

  const startAnalysis = async () => {
    try {
      setAnalysisStatus({ status: 'running', message: 'Starting document analysis...' });
      
      const response = await fetch(`${API_BASE}/api/analysis/start`, {
        method: 'POST',
      });
      
      if (response.ok) {
        setAnalysisStatus({ status: 'running', message: 'Document analysis is running...' });
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to start analysis');
      }
    } catch (error) {
      console.error('Analysis start error:', error);
      setAnalysisStatus({ status: 'error', message: `Failed to start analysis: ${error}` });
    }
  };

  const fetchAnalysisSummary = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/analysis/summary`);
      if (response.ok) {
        const data = await response.json();
        setAnalysisSummary(data.summary);
        return true;
      }
    } catch (error) {
      console.error('Summary fetch error:', error);
    }
    return false;
  };

  const fetchAnalysisStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/analysis/status`);
      if (response.ok) {
        const data = await response.json();
        if (data.status === 'idle' && analysisStatus.status === 'running') {
          setAnalysisStatus({ status: 'completed', message: 'Analysis completed successfully!' });
          // Fetch the summary when analysis completes
          await fetchAnalysisSummary();
        }
      }
    } catch (error) {
      console.error('Status fetch error:', error);
    }
  };

  // Poll for analysis status
  useEffect(() => {
    if (analysisStatus.status === 'running') {
      const interval = setInterval(fetchAnalysisStatus, 2000);
      return () => clearInterval(interval);
    }
  }, [analysisStatus.status]);

  const handleFiles = async (files: File[]) => {
    const newFiles: UploadedFile[] = files.map((file) => ({
      id: Math.random().toString(36).substring(7),
      name: file.name,
      size: file.size,
      type: file.type,
      url: URL.createObjectURL(file),
      uploaded: false,
    }));

    setUploadedFiles((prev) => [...prev, ...newFiles]);
    
    // Auto-upload the files
    await uploadFilesToServer(newFiles);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFiles(files);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      handleFiles(files);
    }
  };

  const handleDeleteFile = (id: string) => {
    setUploadedFiles((prev) => {
      const fileToDelete = prev.find(f => f.id === id);
      if (fileToDelete) {
        URL.revokeObjectURL(fileToDelete.url);
      }
      return prev.filter((file) => file.id !== id);
    });
  };

  return (
    <div className="h-full p-4 overflow-auto">
      <div className="max-w-4xl mx-auto">
        {/* File Dropbox Content */}
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">File Dropbox</h2>
          <p className="text-gray-600">Upload and manage your case files</p>
        </div>

        {/* Upload Zone */}
        <div
          className={`border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300 mb-8 ${
            isDragOver
              ? 'border-indigo-500 bg-indigo-50 scale-105'
              : 'border-gray-300 bg-white/60 hover:border-gray-400 hover:bg-white/80'
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="space-y-4">
            <div className="text-6xl">📁</div>
            <div>
              <h3 className="text-xl font-semibold text-gray-700 mb-2">
                Drop files here or click to upload
              </h3>
              <p className="text-gray-500 mb-4">
                Upload .txt case files for AI analysis • Max file size: 10MB
              </p>
              <button
                onClick={handleUploadClick}
                disabled={uploading}
                className="bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium py-3 px-6 rounded-lg transition-all duration-200 shadow-md hover:shadow-lg transform hover:scale-105 disabled:transform-none disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {uploading ? (
                  <>
                    <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                    <span>Uploading...</span>
                  </>
                ) : (
                  <span>Choose Files</span>
                )}
              </button>
            </div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileInputChange}
            className="hidden"
          />
        </div>

        {/* Analysis Control Panel */}
        {uploadedFiles.length > 0 && (
          <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg p-6 border border-white/30 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">Analysis Control</h3>
                <p className="text-sm text-gray-600">
                  {uploadedFiles.filter(f => f.uploaded).length} of {uploadedFiles.length} files uploaded
                </p>
              </div>
              <div className="flex items-center space-x-4">
                {analysisStatus.status === 'idle' && (
                  <button
                    onClick={startAnalysis}
                    disabled={uploadedFiles.filter(f => f.uploaded).length === 0 || uploading}
                    className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium py-2 px-4 rounded-lg transition-all duration-200 shadow-md hover:shadow-lg transform hover:scale-105 disabled:transform-none disabled:cursor-not-allowed"
                  >
                    🔬 Start Analysis
                  </button>
                )}
                {analysisStatus.status === 'running' && (
                  <div className="flex items-center space-x-2 text-blue-600">
                    <div className="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                    <span className="font-medium">Analyzing...</span>
                  </div>
                )}
                {analysisStatus.status === 'completed' && (
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center space-x-2 text-green-600">
                      <span>✅</span>
                      <span className="font-medium">Analysis Complete</span>
                    </div>
                    {!analysisSummary && (
                      <button
                        onClick={fetchAnalysisSummary}
                        className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-medium py-2 px-4 rounded-lg transition-all duration-200 shadow-md hover:shadow-lg transform hover:scale-105"
                      >
                        📊 View Summary
                      </button>
                    )}
                  </div>
                )}
                {analysisStatus.status === 'error' && (
                  <div className="flex items-center space-x-2 text-red-600">
                    <span>❌</span>
                    <span className="font-medium">Analysis Failed</span>
                  </div>
                )}
              </div>
            </div>
            {analysisStatus.message && (
              <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-700">{analysisStatus.message}</p>
              </div>
            )}
          </div>
        )}

        {/* Analysis Summary */}
        {analysisSummary && (
          <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg p-6 border border-white/30 mb-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-6 flex items-center">
              <span className="mr-2">📊</span>
              Analysis Summary
            </h2>
            
            {/* Case Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <h3 className="font-semibold text-blue-800 mb-2">Files Analyzed</h3>
                <p className="text-2xl font-bold text-blue-600">{analysisSummary.case_overview.files_analyzed}</p>
                <p className="text-sm text-blue-600">
                  Types: {analysisSummary.case_overview.document_types.join(', ')}
                </p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <h3 className="font-semibold text-green-800 mb-2">Analysis Depth</h3>
                <p className="text-2xl font-bold text-green-600">{analysisSummary.analysis_metrics.analysis_depth}</p>
                <p className="text-sm text-green-600">
                  {analysisSummary.analysis_metrics.total_nodes_created} nodes created
                </p>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <h3 className="font-semibold text-purple-800 mb-2">Tasks Completed</h3>
                <p className="text-2xl font-bold text-purple-600">{analysisSummary.analysis_metrics.tasks_completed}</p>
                <p className="text-sm text-purple-600">
                  {analysisSummary.analysis_metrics.tasks_failed} failed
                </p>
              </div>
            </div>

            {/* Key Findings */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">🔍 Key Findings</h3>
              <div className="space-y-2">
                {analysisSummary.key_findings.map((finding, index) => (
                  <div key={index} className="bg-gray-50 p-3 rounded-lg">
                    <p className="text-gray-700">{finding}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Evidence Summary */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">📋 Evidence Summary</h3>
              <div className="space-y-2">
                {analysisSummary.evidence_summary.map((evidence, index) => (
                  <div key={index} className="bg-yellow-50 p-3 rounded-lg border-l-4 border-yellow-400">
                    <h4 className="font-medium text-yellow-800">{evidence.type}</h4>
                    <p className="text-yellow-700 text-sm">{evidence.description}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Conclusion */}
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">🏁 Conclusion</h3>
              <div className="bg-indigo-50 p-4 rounded-lg border-l-4 border-indigo-400">
                <pre className="text-indigo-800 whitespace-pre-wrap text-sm">{analysisSummary.conclusion}</pre>
              </div>
            </div>

            {/* Case Status */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-lg">📈</span>
                <span className="font-semibold text-gray-800">Case Status:</span>
                <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
                  {analysisSummary.case_status}
                </span>
              </div>
              <button
                onClick={() => setAnalysisSummary(null)}
                className="text-gray-500 hover:text-gray-700 p-2 hover:bg-gray-100 rounded-lg transition-colors duration-200"
                title="Close summary"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* Files List */}
        {uploadedFiles.length > 0 && (
          <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg p-6 border border-white/30">
            <h2 className="text-2xl font-semibold text-gray-800 mb-6">
              Uploaded Files ({uploadedFiles.length})
            </h2>
            <div className="space-y-3">
              {uploadedFiles.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center justify-between p-4 bg-white/40 backdrop-blur-sm rounded-lg hover:bg-white/60 transition-all duration-200 border border-white/20"
                >
                  <div className="flex items-center space-x-4 flex-1 min-w-0">
                    <div className="text-2xl">{getFileIcon(file.type)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {file.name}
                        </p>
                        {file.uploaded ? (
                          <span className="text-green-600 text-xs">✅ Uploaded</span>
                        ) : (
                          <span className="text-orange-600 text-xs">⏳ Uploading...</span>
                        )}
                      </div>
                      <p className="text-sm text-gray-500">
                        {formatFileSize(file.size)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {file.type.startsWith('image/') && (
                      <img
                        src={file.url}
                        alt={file.name}
                        className="w-12 h-12 object-cover rounded-lg shadow-md"
                      />
                    )}
                    <button
                      onClick={() => handleDeleteFile(file.id)}
                      className="text-red-500 hover:text-red-700 p-2 hover:bg-red-50 rounded-lg transition-colors duration-200"
                      title="Delete file"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {uploadedFiles.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg">
              No files uploaded yet. Start by dropping some files above!
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FileDropbox; 