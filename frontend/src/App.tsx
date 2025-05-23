import React, { useState } from 'react';
import MemoryTreeView from './components/MemoryTreeView';
import FileDropbox from './components/FileDropbox';

function App() {
  const [activeTab, setActiveTab] = useState<'tree' | 'files'>('tree');

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-cyan-50">
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-200 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-yellow-200 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
        <div className="absolute top-40 left-40 w-80 h-80 bg-pink-200 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000"></div>
      </div>

      {/* Header */}
      <div className="relative z-10">
        <header className="bg-white/80 backdrop-blur-lg border-b border-white/20 shadow-xl">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              {/* Logo and title */}
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                  <span className="text-white text-xl">🤖</span>
                </div>
                <div>
                  <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                    AI Agent System
                  </h1>
                  <p className="text-sm text-gray-600">Memory Tree Visualization & File Management</p>
                </div>
              </div>

              {/* Tab Navigation */}
              <nav className="flex items-center space-x-1 bg-gray-100/50 backdrop-blur-sm p-1 rounded-xl">
                <button
                  onClick={() => setActiveTab('tree')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center space-x-2 ${
                    activeTab === 'tree'
                      ? 'bg-white text-indigo-600 shadow-md transform scale-105'
                      : 'text-gray-600 hover:text-indigo-600 hover:bg-white/50'
                  }`}
                >
                  <span>🌳</span>
                  <span>Memory Tree</span>
                </button>
                <button
                  onClick={() => setActiveTab('files')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center space-x-2 ${
                    activeTab === 'files'
                      ? 'bg-white text-indigo-600 shadow-md transform scale-105'
                      : 'text-gray-600 hover:text-indigo-600 hover:bg-white/50'
                  }`}
                >
                  <span>📁</span>
                  <span>File Manager</span>
                </button>
              </nav>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="relative z-10 h-[calc(100vh-4rem)]">
          <div className="h-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="h-full bg-white/60 backdrop-blur-xl rounded-2xl border border-white/20 shadow-2xl overflow-hidden">
              {activeTab === 'tree' ? (
                <div className="h-full">
                  <MemoryTreeView />
                </div>
              ) : (
                <div className="h-full p-6">
                  <div className="h-full bg-white/40 backdrop-blur-sm rounded-xl border border-white/30 shadow-lg">
                    <FileDropbox />
                  </div>
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
          background: linear-gradient(to bottom, #6366f1, #8b5cf6);
          border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
          background: linear-gradient(to bottom, #4f46e5, #7c3aed);
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
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
      `}</style>
    </div>
  );
}

export default App;
