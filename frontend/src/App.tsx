import React, { useState, useEffect } from 'react';
import MemoryTreeView from './components/MemoryTreeView';
import { AppProvider } from './contexts/AppContext';
import FileManagerView from './components/FileManagerView';
import JobSetupView from './components/JobSetupView';
import ResultsView from './components/ResultsView';

const AppContent = () => {
  const [activeTab, setActiveTab] = useState<'files' | 'analysis' | 'results' | 'tree'>('files');

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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center">
              <img 
                src="/logo.jpg" 
                alt="Logo" 
                className="h-12 w-auto object-contain"
              />
            </div>

            {/* Tab Navigation */}
            <nav className="flex items-center space-x-1 bg-gray-100 p-1 rounded-lg">
              <button
                onClick={() => setActiveTab('files')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 flex items-center space-x-2 ${
                  activeTab === 'files'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <span>📁</span>
                <span>Files</span>
              </button>
              <button
                onClick={() => setActiveTab('analysis')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 flex items-center space-x-2 ${
                  activeTab === 'analysis'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <span>🔬</span>
                <span>Jobs</span>
              </button>
              <button
                onClick={() => setActiveTab('results')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 flex items-center space-x-2 ${
                  activeTab === 'results'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <span>📊</span>
                <span>Results</span>
              </button>
              <button
                onClick={() => setActiveTab('tree')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 flex items-center space-x-2 ${
                  activeTab === 'tree'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                <span>🌳</span>
                <span>Tree</span>
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="h-[calc(100vh-4rem)]">
        <div className="h-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="h-full bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            {activeTab === 'files' && <FileManagerView />}
            {activeTab === 'analysis' && <JobSetupView />}
            {activeTab === 'results' && <ResultsView />}
            {activeTab === 'tree' && (
              <div className="h-full">
                <MemoryTreeView />
              </div>
            )}
          </div>
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
