import React, { useRef, useState } from 'react';
import { useAppContext } from '../contexts/AppContext';
import type { UploadedFile } from '../contexts/AppContext';

const FileManagerView: React.FC = () => {
  const { uploadedFiles, setUploadedFiles, uploading, setUploading, setJobStatus } = useAppContext();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const API_BASE = 'http://localhost:8000';
  
  // File management state
  const [contextMenu, setContextMenu] = useState<{ fileId: string; x: number; y: number } | null>(null);
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const [editingFile, setEditingFile] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  // Helper function to remove .txt extension for display
  const getDisplayName = (fileName: string) => {
    return fileName.endsWith('.txt') ? fileName.slice(0, -4) : fileName;
  };

  // Helper function to add .txt extension back
  const getStorageName = (displayName: string) => {
    return displayName.endsWith('.txt') ? displayName : `${displayName}.txt`;
  };

  // Check if name is unique
  const isNameUnique = (newName: string, currentFileId: string) => {
    const storageName = getStorageName(newName);
    return !uploadedFiles.some(file => 
      file.id !== currentFileId && file.name === storageName
    );
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const uploadFiles = async (files: File[]) => {
    setUploading(true);
    
    try {
      // Create uploaded file objects for UI
      const newFiles: UploadedFile[] = files.map((file) => ({
        id: Math.random().toString(36).substring(7),
        name: file.name,
        size: file.size,
        type: file.type,
        url: URL.createObjectURL(file),
        uploaded: false,
      }));

      setUploadedFiles((prev) => [...prev, ...newFiles]);
      
      // Upload files one by one
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE}/api/upload`, {
          method: 'POST',
          body: formData,
        });
        
        if (response.ok) {
          // Mark this specific file as uploaded
          setUploadedFiles((prev) => 
            prev.map((f) => 
              f.name === file.name ? { ...f, uploaded: true } : f
            )
          );
        } else {
          throw new Error(`Failed to upload ${file.name}`);
        }
      }
    } catch (error) {
      console.error('Upload error:', error);
      setJobStatus({ status: 'error', message: `Upload failed: ${error}` });
    } finally {
      setUploading(false);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      uploadFiles(files);
    }
  };

  // File management functions
  const handleRightClick = (e: React.MouseEvent, fileId: string) => {
    e.preventDefault();
    
    // Get cursor position relative to viewport
    const x = e.clientX;
    const y = e.clientY;
    
    setContextMenu({ fileId, x, y });
    setActiveDropdown(null);
  };

  const handleRename = (fileId: string, currentName: string) => {
    setEditingFile(fileId);
    setEditName(getDisplayName(currentName)); // Use display name without .txt
    setContextMenu(null);
    setActiveDropdown(null);
  };

  const saveRename = () => {
    if (editingFile && editName.trim()) {
      const trimmedName = editName.trim();
      
      // Check if name is unique
      if (!isNameUnique(trimmedName, editingFile)) {
        alert('A file with this name already exists. Please choose a different name.');
        return;
      }
      
      const storageName = getStorageName(trimmedName);
      setUploadedFiles(prev => 
        prev.map(file => 
          file.id === editingFile 
            ? { ...file, name: storageName }
            : file
        )
      );
    }
    setEditingFile(null);
    setEditName('');
  };

  const cancelRename = () => {
    setEditingFile(null);
    setEditName('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      saveRename();
    } else if (e.key === 'Escape') {
      cancelRename();
    }
  };

  // Close menus when clicking outside
  React.useEffect(() => {
    const handleClickOutside = () => {
      setContextMenu(null);
      setActiveDropdown(null);
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);



  return (
    <div className="h-full p-6">
      <div className="h-full bg-white/40 backdrop-blur-sm rounded-xl border border-white/30 shadow-lg overflow-auto">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".txt"
          onChange={handleFileInputChange}
          disabled={uploading}
          className="hidden"
          id="file-upload-input"
        />
        
        {/* File Manager View */}
        <div className="p-6">
          {uploadedFiles.length > 0 && (
            <>
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-gray-800 mb-2">File Manager</h2>
                <p className="text-gray-600">Upload and manage your case files</p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-center space-x-4 mb-8">
                <button
                  onClick={handleUploadClick}
                  disabled={uploading}
                  className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium py-3 px-6 rounded-lg transition-colors duration-200 shadow-md hover:shadow-lg disabled:cursor-not-allowed flex items-center justify-center space-x-2 min-w-[180px] h-[48px]"
                >
                  <span>📁</span>
                  <span>Upload More Files</span>
                  {uploading && (
                    <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                  )}
                </button>
              </div>
            </>
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
                    className="relative flex items-center justify-between p-4 bg-white/40 backdrop-blur-sm rounded-lg hover:bg-white/60 transition-all duration-200 border border-white/20"
                    onContextMenu={(e) => handleRightClick(e, file.id)}
                  >
                    <div className="flex items-center space-x-4 flex-1 min-w-0">
                      <div className="text-2xl">📝</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          {editingFile === file.id ? (
                            <input
                              type="text"
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              onKeyDown={handleKeyPress}
                              onBlur={saveRename}
                              className="text-sm font-medium text-gray-900 bg-white border border-blue-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                              autoFocus
                            />
                          ) : (
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {getDisplayName(file.name)}
                            </p>
                          )}
                          {file.uploaded ? (
                            <span className="text-green-600 text-xs">✅ Uploaded</span>
                          ) : (
                            <span className="text-orange-600 text-xs">⏳ Uploading...</span>
                          )}
                        </div>
                        <p className="text-sm text-gray-500">
                          {(file.size / 1024).toFixed(2)} KB
                        </p>
                      </div>
                    </div>
                    
                    {/* Three dots menu */}
                    <div className="relative">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveDropdown(activeDropdown === file.id ? null : file.id);
                          setContextMenu(null);
                        }}
                        className="p-2 text-gray-400 hover:text-gray-600 hover:bg-white/50 rounded-full transition-colors"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                        </svg>
                      </button>
                      
                      {/* Dropdown menu */}
                      {activeDropdown === file.id && (
                        <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-xl z-[100] min-w-[120px] backdrop-blur-sm"
                             style={{ boxShadow: '0 10px 25px rgba(0, 0, 0, 0.15)' }}>
                          <button
                            onClick={() => handleRename(file.id, file.name)}
                            className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 flex items-center space-x-2 rounded-lg transition-colors first:rounded-t-lg last:rounded-b-lg"
                          >
                            <span>✏️</span>
                            <span>Rename</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty State - replaces everything when no files */}
          {uploadedFiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-96">
              <div className="text-8xl mb-6">📁</div>
              <h3 className="text-2xl font-bold text-gray-800 mb-4">Upload Your Case Files</h3>
              <p className="text-gray-600 text-center mb-8 max-w-md">
                Get started by uploading your investigation documents. Supported file types: .txt files
              </p>
              <label
                htmlFor="file-upload-input"
                className={`bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium py-4 px-8 rounded-lg transition-colors duration-200 shadow-lg hover:shadow-xl flex items-center justify-center space-x-3 text-lg min-w-[280px] h-[60px] ${uploading ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
              >
                <span>📎</span>
                <span>{uploading ? 'Uploading...' : 'Choose Files to Upload'}</span>
                {uploading && (
                  <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full"></div>
                )}
              </label>
              <p className="text-sm text-gray-500 mt-4">
                You can select multiple files at once
              </p>
            </div>
          ) : null}
        </div>
      </div>
      
      {/* Right-click context menu */}
      {contextMenu && (
        <div 
          className="fixed bg-white border border-gray-200 rounded-lg shadow-xl z-[9999] min-w-[120px] backdrop-blur-sm"
          style={{ 
            left: `${Math.min(contextMenu.x, window.innerWidth - 130)}px`, 
            top: `${Math.min(contextMenu.y, window.innerHeight - 60)}px`,
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.15)'
          }}
        >
          <button
            onClick={() => {
              const file = uploadedFiles.find(f => f.id === contextMenu.fileId);
              if (file) handleRename(file.id, file.name);
            }}
            className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 flex items-center space-x-2 rounded-lg transition-colors first:rounded-t-lg last:rounded-b-lg"
          >
            <span>✏️</span>
            <span>Rename</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default FileManagerView; 