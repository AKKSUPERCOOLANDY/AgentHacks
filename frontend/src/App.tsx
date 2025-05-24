import React, { useState, useEffect, useRef } from 'react';
import JobSpecificTreeView from './components/JobSpecificTreeView';
import { AppProvider, useAppContext } from './contexts/AppContext';
import FileManagerView from './components/FileManagerView';
import JobSetupView from './components/JobSetupView';
import ResultsView from './components/ResultsView';
import type { UploadedFile } from './contexts/AppContext';

const AppContent = () => {
  const [activeTab, setActiveTab] = useState<'files' | 'analysis' | 'results' | 'tree'>('files');
  const { uploadedFiles, setUploadedFiles, uploading, setUploading, setJobStatus } = useAppContext();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const API_BASE = 'http://localhost:8000';

  // Upload functions
  const handleUploadClick = () => {
    // Switch to files tab when uploading starts
    setActiveTab('files');
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
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const fileId = newFiles[i].id;
        
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE}/api/upload`, {
          method: 'POST',
          body: formData,
        });
        
        if (response.ok) {
          // Mark this specific file as uploaded using ID
          setUploadedFiles((prev) => 
            prev.map((f) => 
              f.id === fileId ? { ...f, uploaded: true } : f
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

  // Listen for tab switch events
  useEffect(() => {
    const handleTabSwitch = (event: CustomEvent) => {
      setActiveTab(event.detail);
    };
    
    window.addEventListener('switchTab', handleTabSwitch as EventListener);
    
    return () => {
      window.removeEventListener('switchTab', handleTabSwitch as EventListener);
    };
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className="w-64 bg-gray-50 border-r border-gray-200 shadow-sm flex flex-col">
        {/* Logo Header */}
        <div className="flex items-center">
          <div className="w-20 h-20 overflow-hidden">
            <img 
              src="/logo.jpg" 
              alt="Logo" 
              className="w-full h-full object-cover"
              style={{
                clipPath: 'inset(25% 25% 25% 25%)',
                transform: 'scale(1.33)'
              }}
            />
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 space-y-2">
          {/* Upload Button */}
          <button
            onClick={handleUploadClick}
            disabled={uploading}
            className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 text-white shadow-sm hover:shadow-md disabled:cursor-not-allowed"
            style={{
              backgroundColor: uploading ? '#9CA3AF' : '#56A3B1'
            }}
            onMouseEnter={e => !uploading && ((e.target as HTMLElement).style.backgroundColor = '#3A6B80')}
            onMouseLeave={e => !uploading && ((e.target as HTMLElement).style.backgroundColor = '#56A3B1')}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <span>{uploading ? 'Uploading...' : 'Upload Files'}</span>
            {uploading && (
              <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
            )}
          </button>

          <div className="h-2"></div> {/* Spacer */}

          <button
            onClick={() => setActiveTab('files')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'files'
                ? 'border'
                : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
            }`}
            style={activeTab === 'files' ? {
              backgroundColor: '#7ECEF4',
              color: '#19283B',
              borderColor: '#56A3B1'
            } : {}}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            <span>Files</span>
          </button>
          <button
            onClick={() => setActiveTab('analysis')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'analysis'
                ? 'border'
                : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
            }`}
            style={activeTab === 'analysis' ? {
              backgroundColor: '#7ECEF4',
              color: '#19283B',
              borderColor: '#56A3B1'
            } : {}}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            <span>Jobs</span>
          </button>
          <button
            onClick={() => setActiveTab('results')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'results'
                ? 'border'
                : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
            }`}
            style={activeTab === 'results' ? {
              backgroundColor: '#7ECEF4',
              color: '#19283B',
              borderColor: '#56A3B1'
            } : {}}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span>Results</span>
          </button>
          <button
            onClick={() => setActiveTab('tree')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'tree'
                ? 'border'
                : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
            }`}
            style={activeTab === 'tree' ? {
              backgroundColor: '#7ECEF4',
              color: '#19283B',
              borderColor: '#56A3B1'
            } : {}}
          >
            <img src="/graphicon.svg" alt="Graph" className="w-5 h-5" style={{ 
              filter: activeTab === 'tree' ? 'brightness(0) saturate(100%) invert(7%) sepia(18%) saturate(1837%) hue-rotate(183deg) brightness(94%) contrast(88%)' : 'brightness(0) saturate(100%) invert(40%) sepia(6%) saturate(394%) hue-rotate(174deg) brightness(95%) contrast(89%)'
            }} />
            <span>Graph</span>
          </button>
        </nav>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".txt"
        onChange={handleFileInputChange}
        disabled={uploading}
        className="hidden"
      />

      {/* Main Content */}
      <main className="flex-1 bg-gray-50">
        <div className="h-screen bg-white shadow-sm overflow-hidden">
          {activeTab === 'files' && <FileManagerView />}
          {activeTab === 'analysis' && <JobSetupView />}
          {activeTab === 'results' && <ResultsView />}
          {activeTab === 'tree' && (
            <div className="h-full">
              <JobSpecificTreeView />
            </div>
          )}
        </div>
      </main>

      {/* CSS for scrollbars */}
      <style>{`
        /* Custom scrollbars */
        ::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        
        ::-webkit-scrollbar-track {
          background: #f1f5f9;
          border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
          background: #94a3b8;
        }
      `}</style>
    </div>
  );
};

function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}

export default App;
