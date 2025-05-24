import React, { useState, useEffect } from 'react';
import { useAppContext } from '../contexts/AppContext';

const JobSetupView: React.FC = () => {
  const { setJobStatus, jobStatus, uploadedFiles, setCurrentJobName } = useAppContext();
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [jobName, setJobName] = useState('');
  const API_BASE = 'http://localhost:8000';

  // Filter only uploaded files that are successfully uploaded
  const availableFiles = uploadedFiles.filter(file => file.uploaded);

  // Helper function to remove .txt extension for display
  const getDisplayName = (fileName: string) => {
    return fileName.endsWith('.txt') ? fileName.slice(0, -4) : fileName;
  };

  // Generate default job name based on selected files
  useEffect(() => {
    if (selectedFiles.length > 0 && !jobName) {
      const timestamp = new Date().toLocaleString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      });
      setJobName(`Job - ${timestamp}`);
    }
  }, [selectedFiles, jobName]);

  const toggleFileSelection = (fileName: string) => {
    setSelectedFiles(prev => 
      prev.includes(fileName) 
        ? prev.filter(f => f !== fileName)
        : [...prev, fileName]
    );
  };

  const selectAll = () => {
    setSelectedFiles(availableFiles.map(file => file.name));
  };

  const clearSelection = () => {
    setSelectedFiles([]);
  };

  const startJob = async () => {
    if (selectedFiles.length === 0) {
      alert('Please select at least one file for this job');
      return;
    }

    if (!jobName.trim()) {
      alert('Please enter a name for this job');
      return;
    }

    // Save the job name to context
    setCurrentJobName(jobName);
    setJobStatus({ status: 'running', message: `Starting job: ${jobName}...` });
    
    try {
      // Clear session first
      await fetch(`${API_BASE}/api/session/clear`, { method: 'POST' });
      
      // Start analysis
      const response = await fetch(`${API_BASE}/api/analysis/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          selected_files: selectedFiles
        })
      });
      
      if (response.ok) {
        setJobStatus({ status: 'running', message: 'Job is running...' });
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to start job');
      }
    } catch (error) {
      console.error('Job start error:', error);
      setJobStatus({ status: 'error', message: `Failed to start job: ${error}` });
    }
  };

  return (
    <div className="h-full p-6">
      <div className="h-full bg-white/40 backdrop-blur-sm rounded-xl border border-white/30 shadow-lg overflow-auto">
        <div className="p-6">
          {availableFiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-96">
              <div className="text-8xl mb-6">📄</div>
              <h3 className="text-2xl font-bold text-gray-800 mb-4">No Files Available</h3>
              <p className="text-gray-600 text-center mb-8 max-w-md">
                You need to upload case files before creating a job
              </p>
              <button
                onClick={() => {
                  window.dispatchEvent(new CustomEvent('switchTab', { detail: 'files' }));
                }}
                className="bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-medium py-3 px-6 rounded-lg transition-all duration-200 shadow-md hover:shadow-lg transform hover:scale-105 flex items-center space-x-2 mx-auto"
              >
                <span>📁</span>
                <span>Go to File Manager</span>
              </button>
            </div>
          ) : (
            <>
              {/* Job Name Input */}
              <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg p-6 border border-white/30 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Job Name</h3>
                <input
                  type="text"
                  value={jobName}
                  onChange={(e) => setJobName(e.target.value)}
                  placeholder="Enter a name for this job..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white/70 backdrop-blur-sm"
                />
                <p className="text-sm text-gray-500 mt-2">
                  Give your job a descriptive name to help identify it later
                </p>
              </div>

              {/* Control buttons */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-4">
                  <button
                    onClick={selectAll}
                    className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    Select All ({availableFiles.length})
                  </button>
                  <button
                    onClick={clearSelection}
                    className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                  >
                    Clear Selection
                  </button>
                </div>
                
                <div className="text-sm text-gray-600">
                  {selectedFiles.length} of {availableFiles.length} files selected
                </div>
              </div>

              {/* Files list */}
              <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg p-6 border border-white/30 mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Available Files</h3>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {availableFiles.map((file) => (
                    <div
                      key={file.name}
                      className={`flex items-center p-4 rounded-lg border-2 cursor-pointer transition-all duration-200 ${
                        selectedFiles.includes(file.name)
                          ? 'bg-blue-50 border-blue-300 shadow-sm'
                          : 'bg-white/40 border-gray-200 hover:bg-white/60'
                      }`}
                      onClick={() => toggleFileSelection(file.name)}
                    >
                      <div className="flex items-center space-x-4 flex-1">
                        <div className={`w-6 h-6 rounded border-2 flex items-center justify-center ${
                          selectedFiles.includes(file.name)
                            ? 'bg-blue-500 border-blue-500'
                            : 'border-gray-300'
                        }`}>
                          {selectedFiles.includes(file.name) && (
                            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                        <div className="text-2xl">📝</div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {getDisplayName(file.name)}
                          </p>
                          <p className="text-sm text-gray-500">
                            {(file.size / 1024).toFixed(2)} KB
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Start job button */}
              <div className="text-center">
                <button
                  onClick={startJob}
                  disabled={selectedFiles.length === 0 || !jobName.trim() || jobStatus.status === 'running'}
                  className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium py-3 px-8 rounded-lg transition-all duration-200 shadow-md hover:shadow-lg transform hover:scale-105 disabled:transform-none disabled:cursor-not-allowed flex items-center space-x-2 mx-auto"
                >
                  <span>🔬</span>
                  <span>
                    {jobStatus.status === 'running' 
                      ? `Running: ${jobName}...` 
                      : selectedFiles.length === 0
                        ? 'Select files to start'
                        : !jobName.trim()
                          ? 'Enter job name'
                          : `Start "${jobName}" (${selectedFiles.length} files)`
                    }
                  </span>
                  {jobStatus.status === 'running' && (
                    <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full ml-2"></div>
                  )}
                </button>
              </div>

              {/* Job status */}
              {jobStatus.status !== 'idle' && (
                <div className="mt-6 bg-white/80 backdrop-blur-sm rounded-xl shadow-lg p-4 border border-white/30">
                  <div className="flex items-center space-x-3">
                    {jobStatus.status === 'running' && (
                      <>
                        <div className="animate-spin w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                        <span className="text-blue-600 font-medium">{jobStatus.message}</span>
                      </>
                    )}
                    {jobStatus.status === 'completed' && (
                      <>
                        <span className="text-green-600 text-lg">✅</span>
                        <span className="text-green-600 font-medium">Job completed! Check the Results tab.</span>
                      </>
                    )}
                    {jobStatus.status === 'error' && (
                      <>
                        <span className="text-red-600 text-lg">❌</span>
                        <span className="text-red-600 font-medium">{jobStatus.message}</span>
                      </>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default JobSetupView; 