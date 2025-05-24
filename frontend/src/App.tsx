import React, { useState, useEffect } from 'react';
import JobSpecificTreeView from './components/JobSpecificTreeView';
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
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 shadow-sm flex flex-col">
        {/* Logo Header */}
        <div className="flex items-center px-6 py-4 border-b border-gray-200">
          <img 
            src="/logo.jpg" 
            alt="Logo" 
            className="h-10 w-auto object-contain"
          />
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-2">
          <button
            onClick={() => setActiveTab('files')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'files'
                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            <span className="text-lg">📁</span>
            <span>Files</span>
          </button>
          <button
            onClick={() => setActiveTab('analysis')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'analysis'
                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            <span className="text-lg">🔬</span>
            <span>Jobs</span>
          </button>
          <button
            onClick={() => setActiveTab('results')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'results'
                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            <span className="text-lg">📊</span>
            <span>Results</span>
          </button>
          <button
            onClick={() => setActiveTab('tree')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === 'tree'
                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            <span className="text-lg">🌳</span>
            <span>Tree</span>
          </button>
        </nav>
      </div>

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
