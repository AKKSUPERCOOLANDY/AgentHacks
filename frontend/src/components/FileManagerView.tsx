import React, { useState } from 'react';
import { useAppContext } from '../contexts/AppContext';

const FileManagerView: React.FC = () => {
  const { uploadedFiles, setUploadedFiles, uploading } = useAppContext();

  // Load existing files on mount
  React.useEffect(() => {
    const loadExistingFiles = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/files');
        if (response.ok) {
          const data = await response.json();
          const existingFiles = data.files.map((file: any) => ({
            id: Math.random().toString(36).substring(7),
            name: file.filename,
            size: file.size,
            type: 'text/plain',
            url: '',
            uploaded: true
          }));
          setUploadedFiles(existingFiles);
        }
      } catch (error) {
        console.error('Error loading existing files:', error);
      }
    };

    // Only load if no files in context yet
    if (uploadedFiles.length === 0) {
      loadExistingFiles();
    }
  }, [uploadedFiles.length, setUploadedFiles]);
  
  // File management state
  const [contextMenu, setContextMenu] = useState<{ fileId: string; x: number; y: number } | null>(null);
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const [editingFile, setEditingFile] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

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

  // Filter files based on search term
  const filteredFiles = uploadedFiles.filter(file => 
    getDisplayName(file.name).toLowerCase().includes(searchTerm.toLowerCase())
  );



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

  const handleDelete = async (fileId: string, fileName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${getDisplayName(fileName)}"? This action cannot be undone.`)) {
      return;
    }

    try {
      // Delete from server
      const response = await fetch(`http://localhost:8000/api/files/${fileName}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        // Remove from local state
        setUploadedFiles(prev => prev.filter(file => file.id !== fileId));
        setContextMenu(null);
        setActiveDropdown(null);
      } else {
        throw new Error('Failed to delete file from server');
      }
    } catch (error) {
      console.error('Error deleting file:', error);
      alert('Failed to delete file. Please try again.');
    }
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
          {/* File Search */}
          {uploadedFiles.length > 0 && (
            <div className="mb-6">
              <div className="relative">
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search files..."
                  className="w-full px-4 py-3 pl-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                />
                <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
              </div>
              {searchTerm && (
                <p className="text-sm text-gray-500 mt-2">
                  {filteredFiles.length} of {uploadedFiles.length} files match "{searchTerm}"
                </p>
              )}
            </div>
          )}

          {/* Files List */}
          {uploadedFiles.length > 0 && (
            <div>
              {searchTerm && filteredFiles.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <svg className="w-12 h-12 text-gray-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <p>No files found matching "{searchTerm}"</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {(searchTerm ? filteredFiles : uploadedFiles).map((file) => (
                  <div
                    key={file.id}
                    className="relative flex items-center justify-between p-3 hover:bg-gray-50 transition-all duration-200 rounded-lg"
                    onContextMenu={(e) => handleRightClick(e, file.id)}
                  >
                    <div className="flex items-center space-x-4 flex-1 min-w-0">
                      <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
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
                        </div>
                        <p className="text-sm text-gray-500">
                          {(file.size / 1024).toFixed(2)} KB
                        </p>
                      </div>
                    </div>
                    
                    {/* Loading animation or menu */}
                    <div className="relative">
                      {!file.uploaded ? (
                        <div className="p-2">
                          <div className="animate-spin w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full"></div>
                        </div>
                      ) : (
                        <>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveDropdown(activeDropdown === file.id ? null : file.id);
                              setContextMenu(null);
                            }}
                            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
                          >
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                              <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                            </svg>
                          </button>
                          
                          {/* Dropdown menu */}
                          {activeDropdown === file.id && (
                            <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-[100] min-w-[120px]">
                              <button
                                onClick={() => handleRename(file.id, file.name)}
                                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 flex items-center space-x-2 transition-colors first:rounded-t-lg"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                                <span>Rename</span>
                              </button>
                              <button
                                onClick={() => handleDelete(file.id, file.name)}
                                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-red-50 hover:text-red-700 flex items-center space-x-2 transition-colors last:rounded-b-lg"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                                <span>Delete</span>
                              </button>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Empty State - replaces everything when no files */}
          {uploadedFiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-96">
              {/* Pretty illustration */}
              <div className="w-48 h-48 mb-8 relative">
                <svg viewBox="0 0 200 200" className="w-full h-full">
                  {/* Desk */}
                  <rect x="20" y="120" width="160" height="60" rx="8" fill="#8B5CF6" opacity="0.1"/>
                  <rect x="20" y="110" width="160" height="20" rx="4" fill="#8B5CF6" opacity="0.2"/>
                  
                  {/* Computer screen */}
                  <rect x="70" y="60" width="60" height="40" rx="4" fill="#374151"/>
                  <rect x="75" y="65" width="50" height="30" rx="2" fill="#60A5FA"/>
                  <circle cx="100" cy="80" r="3" fill="#FBBF24"/>
                  
                  {/* Laptop base */}
                  <rect x="65" y="95" width="70" height="25" rx="6" fill="#6B7280"/>
                  <rect x="70" y="100" width="60" height="15" rx="3" fill="#374151"/>
                  
                  {/* Person */}
                  <circle cx="140" cy="70" r="12" fill="#FBBF24"/>
                  <rect x="130" y="80" width="20" height="35" rx="8" fill="#60A5FA"/>
                  <rect x="125" y="85" width="10" height="25" rx="4" fill="#FBBF24"/>
                  <rect x="155" y="85" width="10" height="25" rx="4" fill="#FBBF24"/>
                  <rect x="135" y="110" width="8" height="20" rx="3" fill="#374151"/>
                  <rect x="147" y="110" width="8" height="20" rx="3" fill="#374151"/>
                  
                  {/* Papers/documents */}
                  <rect x="40" y="90" width="15" height="20" rx="2" fill="#FFFFFF" stroke="#E5E7EB" strokeWidth="1"/>
                  <rect x="45" y="85" width="15" height="20" rx="2" fill="#FFFFFF" stroke="#E5E7EB" strokeWidth="1"/>
                  
                  {/* Coffee cup */}
                  <ellipse cx="160" cy="100" rx="6" ry="8" fill="#8B5CF6"/>
                  <ellipse cx="160" cy="95" rx="5" ry="3" fill="#FFFFFF"/>
                  
                  {/* Floating elements */}
                  <circle cx="30" cy="40" r="3" fill="#FBBF24" opacity="0.6"/>
                  <circle cx="170" cy="30" r="4" fill="#60A5FA" opacity="0.6"/>
                  <rect x="45" y="25" width="8" height="8" rx="2" fill="#8B5CF6" opacity="0.6"/>
                </svg>
              </div>
              
              <h3 className="text-2xl font-bold text-gray-800 mb-4">No Files Uploaded</h3>
              <p className="text-gray-600 text-center mb-8 max-w-md">
                Use the "Upload Files" button in the sidebar to get started with your investigation documents. Supported file types: .txt files
              </p>
              {uploading && (
                <div className="flex items-center space-x-2 text-blue-600">
                  <div className="animate-spin w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                  <span className="font-medium">Uploading...</span>
                </div>
              )}
            </div>
          ) : null}
      
      {/* Right-click context menu */}
      {contextMenu && (
        <div 
          className="fixed bg-white border border-gray-200 rounded-lg shadow-lg z-[9999] min-w-[120px]"
          style={{ 
            left: `${Math.min(contextMenu.x, window.innerWidth - 130)}px`, 
            top: `${Math.min(contextMenu.y, window.innerHeight - 100)}px`
          }}
        >
          <button
            onClick={() => {
              const file = uploadedFiles.find(f => f.id === contextMenu.fileId);
              if (file) handleRename(file.id, file.name);
            }}
            className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 flex items-center space-x-2 transition-colors first:rounded-t-lg"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            <span>Rename</span>
          </button>
          <button
            onClick={() => {
              const file = uploadedFiles.find(f => f.id === contextMenu.fileId);
              if (file) handleDelete(file.id, file.name);
            }}
            className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-red-50 hover:text-red-700 flex items-center space-x-2 transition-colors last:rounded-b-lg"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            <span>Delete</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default FileManagerView; 