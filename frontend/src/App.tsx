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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-700" style={{background: 'linear-gradient(135deg, #19283B 0%, #3A6B80 50%, #56A3B1 100%)'}}>
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full mix-blend-multiply filter blur-xl opacity-30 animate-blob" style={{backgroundColor: '#7ECEF4'}}></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full mix-blend-multiply filter blur-xl opacity-40 animate-blob animation-delay-2000" style={{backgroundColor: '#56A3B1'}}></div>
        <div className="absolute top-40 left-40 w-80 h-80 rounded-full mix-blend-multiply filter blur-xl opacity-35 animate-blob animation-delay-4000" style={{backgroundColor: '#3A6B80'}}></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <header className="backdrop-blur-lg border-b shadow-xl" style={{backgroundColor: 'rgba(25, 40, 59, 0.9)', borderBottomColor: 'rgba(86, 163, 177, 0.3)'}}>
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
              <nav className="flex items-center space-x-1 backdrop-blur-sm p-1 rounded-xl" style={{backgroundColor: 'rgba(58, 107, 128, 0.3)'}}>
                <button
                  onClick={() => setActiveTab('files')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center space-x-2 ${
                    activeTab === 'files'
                      ? 'shadow-md transform scale-105'
                      : 'hover:shadow-sm'
                  }`}
                  style={activeTab === 'files' 
                    ? {backgroundColor: '#56A3B1', color: 'white'} 
                    : {color: '#7ECEF4'}}
                  onMouseEnter={(e) => {
                    if (activeTab !== 'files') {
                      e.currentTarget.style.backgroundColor = 'rgba(86, 163, 177, 0.2)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (activeTab !== 'files') {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  <span>📁</span>
                  <span>Files</span>
                </button>
                <button
                  onClick={() => setActiveTab('analysis')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center space-x-2 ${
                    activeTab === 'analysis'
                      ? 'shadow-md transform scale-105'
                      : 'hover:shadow-sm'
                  }`}
                  style={activeTab === 'analysis' 
                    ? {backgroundColor: '#56A3B1', color: 'white'} 
                    : {color: '#7ECEF4'}}
                  onMouseEnter={(e) => {
                    if (activeTab !== 'analysis') {
                      e.currentTarget.style.backgroundColor = 'rgba(86, 163, 177, 0.2)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (activeTab !== 'analysis') {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  <span>🔬</span>
                  <span>Jobs</span>
                </button>
                <button
                  onClick={() => setActiveTab('results')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center space-x-2 ${
                    activeTab === 'results'
                      ? 'shadow-md transform scale-105'
                      : 'hover:shadow-sm'
                  }`}
                  style={activeTab === 'results' 
                    ? {backgroundColor: '#56A3B1', color: 'white'} 
                    : {color: '#7ECEF4'}}
                  onMouseEnter={(e) => {
                    if (activeTab !== 'results') {
                      e.currentTarget.style.backgroundColor = 'rgba(86, 163, 177, 0.2)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (activeTab !== 'results') {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  <span>📊</span>
                  <span>Results</span>
                </button>
                <button
                  onClick={() => setActiveTab('tree')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center space-x-2 ${
                    activeTab === 'tree'
                      ? 'shadow-md transform scale-105'
                      : 'hover:shadow-sm'
                  }`}
                  style={activeTab === 'tree' 
                    ? {backgroundColor: '#56A3B1', color: 'white'} 
                    : {color: '#7ECEF4'}}
                  onMouseEnter={(e) => {
                    if (activeTab !== 'tree') {
                      e.currentTarget.style.backgroundColor = 'rgba(86, 163, 177, 0.2)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (activeTab !== 'tree') {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  <span>🌳</span>
                  <span>Tree</span>
                </button>
              </nav>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="relative z-10 h-[calc(100vh-4rem)]">
          <div className="h-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="h-full backdrop-blur-xl rounded-2xl shadow-2xl overflow-hidden" style={{backgroundColor: 'rgba(25, 40, 59, 0.7)', borderColor: 'rgba(86, 163, 177, 0.4)', borderWidth: '1px'}}>
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
      </div>

      {/* CSS Animations */}
      <style>{`
        @keyframes blob {
          0% { transform: translate(0px, 0px) scale(1); }
          33% { transform: translate(30px, -50px) scale(1.1); }
          66% { transform: translate(-20px, 20px) scale(0.9); }
          100% { transform: translate(0px, 0px) scale(1); }
        }
        
        .animate-blob {
          animation: blob 7s infinite;
        }
        
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        
        .animation-delay-4000 {
          animation-delay: 4s;
        }
        
        /* Custom scrollbars */
        ::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        
        ::-webkit-scrollbar-track {
          background: rgba(0, 0, 0, 0.1);
          border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
          background: linear-gradient(to bottom, #56A3B1, #3A6B80);
          border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
          background: linear-gradient(to bottom, #7ECEF4, #56A3B1);
        }
        
        /* Glass morphism utility */
        .glass {
          background: rgba(255, 255, 255, 0.25);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.18);
        }
        
        /* Gradient text */
        .gradient-text {
          background: linear-gradient(135deg, #56A3B1 0%, #7ECEF4 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
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
