import React, { useState, useEffect } from 'react';
import { useAppContext } from '../contexts/AppContext';
import type { CompletedJob } from '../contexts/AppContext';

const JobSetupView: React.FC = () => {
  const { setJobStatus, jobStatus, uploadedFiles, setCurrentJobName, setJobSummary, setJobHistory, currentJobName } = useAppContext();
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [jobName, setJobName] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const API_BASE = 'http://localhost:8000';

  // Helper function to remove .txt extension for display
  const getDisplayName = (fileName: string) => {
    return fileName.endsWith('.txt') ? fileName.slice(0, -4) : fileName;
  };

  // Filter only uploaded files that are successfully uploaded
  const availableFiles = uploadedFiles.filter(file => file.uploaded);
  
  // Filter files based on search term
  const filteredFiles = availableFiles.filter(file => 
    getDisplayName(file.name).toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  // Get 5 most recently uploaded files (assuming they're in reverse chronological order)
  const recentFiles = availableFiles.slice(0, 5);
  
  // Get selected file objects
  const selectedFileObjects = availableFiles.filter(file => 
    selectedFiles.includes(file.name)
  );

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

  // Poll for job completion
  useEffect(() => {
    let jobAddedToHistory = false; // Flag to prevent duplicate job creation
    
    if (jobStatus.status === 'running') {
      const pollInterval = setInterval(async () => {
        try {
          const response = await fetch(`${API_BASE}/api/analysis/summary`);
          if (response.ok) {
            const data = await response.json();
            if (data.summary && !jobAddedToHistory) {
              setJobSummary(data.summary);
              
              // Add completed job to history
              const completedJob: CompletedJob = {
                id: Math.random().toString(36).substring(7),
                name: currentJobName || jobName || 'Untitled Job',
                completedAt: new Date().toISOString(),
                summary: data.summary,
                status: 'completed' as const
              };
              
              setJobHistory(prev => [completedJob, ...prev]);
              setJobStatus({ status: 'completed', message: 'Job completed successfully!' });
              jobAddedToHistory = true; // Mark as added
              clearInterval(pollInterval);
            }
          }
        } catch (error) {
          console.error('Error polling for completion:', error);
        }
      }, 3000);

      return () => clearInterval(pollInterval);
    }
  }, [jobStatus.status, setJobSummary, setJobStatus, setJobHistory, currentJobName, jobName]);

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
          {availableFiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-96">
              <svg className="w-24 h-24 text-gray-300 mb-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="text-2xl font-bold text-gray-800 mb-4">No Files Available</h3>
              <p className="text-gray-600 text-center mb-8 max-w-md">
                You need to upload case files before creating a job
              </p>
              <button
                onClick={() => {
                  window.dispatchEvent(new CustomEvent('switchTab', { detail: 'files' }));
                }}
                className="text-white font-medium py-3 px-6 rounded-lg transition-colors duration-200 shadow-sm hover:shadow-md flex items-center space-x-2 mx-auto"
                style={{ backgroundColor: '#56A3B1' }}
                onMouseEnter={e => (e.target as HTMLElement).style.backgroundColor = '#3A6B80'}
                onMouseLeave={e => (e.target as HTMLElement).style.backgroundColor = '#56A3B1'}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <span>Go to File Manager</span>
              </button>
            </div>
          ) : (
            <>
              {/* Job Name Input */}
              <div className="mb-4">
                <input
                  type="text"
                  value={jobName}
                  onChange={(e) => setJobName(e.target.value)}
                  placeholder="Job name"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                />
              </div>

              {/* Control buttons */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-4">
                  <button
                    onClick={selectedFiles.length === availableFiles.length ? clearSelection : selectAll}
                    className="text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                    style={{ backgroundColor: '#56A3B1' }}
                    onMouseEnter={e => (e.target as HTMLElement).style.backgroundColor = '#3A6B80'}
                    onMouseLeave={e => (e.target as HTMLElement).style.backgroundColor = '#56A3B1'}
                  >
                    {selectedFiles.length === availableFiles.length ? 'Clear All' : 'Select All'}
                  </button>
                  <button
                    onClick={startJob}
                    disabled={selectedFiles.length === 0 || !jobName.trim() || jobStatus.status === 'running'}
                    className="text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed flex items-center space-x-2"
                    style={{ 
                      backgroundColor: selectedFiles.length === 0 || !jobName.trim() || jobStatus.status === 'running' ? '#9CA3AF' : '#56A3B1'
                    }}
                    onMouseEnter={e => {
                      if (!(selectedFiles.length === 0 || !jobName.trim() || jobStatus.status === 'running')) {
                        (e.target as HTMLElement).style.backgroundColor = '#3A6B80';
                      }
                    }}
                    onMouseLeave={e => {
                      if (!(selectedFiles.length === 0 || !jobName.trim() || jobStatus.status === 'running')) {
                        (e.target as HTMLElement).style.backgroundColor = '#56A3B1';
                      }
                    }}
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    <span>
                      {jobStatus.status === 'running' 
                        ? 'Running...' 
                        : selectedFiles.length === 0 || !jobName.trim()
                          ? 'Run'
                          : `Run Job (${selectedFiles.length} files)`
                      }
                    </span>
                    {jobStatus.status === 'running' && (
                      <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                    )}
                  </button>
                </div>
                
                <div className="text-sm text-gray-600">
                  {selectedFiles.length} selected
                </div>
              </div>

              {/* File Search */}
              <div className="mb-6">
                <div className="relative mb-4">
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search for files..."
                    className="w-full px-4 py-3 pl-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                  />
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                </div>
                
                {/* Search Results */}
                {searchTerm && (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {filteredFiles.length > 0 ? (
                      filteredFiles.map((file) => (
                        <div
                          key={file.name}
                          className={`flex items-center p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                            selectedFiles.includes(file.name)
                              ? ''
                              : 'hover:bg-gray-50'
                          }`}
                          style={selectedFiles.includes(file.name) ? { backgroundColor: '#7ECEF4' } : {}}
                          onClick={() => toggleFileSelection(file.name)}
                        >
                          <div className="flex items-center space-x-3 flex-1">
                            <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                              selectedFiles.includes(file.name)
                                ? ''
                                : 'border-gray-300'
                            }`}
                            style={selectedFiles.includes(file.name) ? {
                              backgroundColor: '#56A3B1',
                              borderColor: '#56A3B1'
                            } : {}}>
                              {selectedFiles.includes(file.name) && (
                                <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                </svg>
                              )}
                            </div>
                                                          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                              <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-900 truncate">
                                {getDisplayName(file.name)}
                              </p>
                              <p className="text-xs text-gray-500">
                                {(file.size / 1024).toFixed(2)} KB
                              </p>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-4 text-gray-500">
                        No files found matching "{searchTerm}"
                      </div>
                    )}
                  </div>
                )}
                
                {!searchTerm && (
                  <div>
                    <div className="text-sm text-gray-600 mb-3 flex items-center justify-between">
                      <span>Recent Files</span>
                      <span className="text-xs">{availableFiles.length} total available</span>
                    </div>
                    <div className="space-y-2">
                      {recentFiles.length > 0 ? (
                        recentFiles.map((file) => (
                          <div
                            key={file.name}
                            className={`flex items-center p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                              selectedFiles.includes(file.name)
                                ? ''
                                : 'hover:bg-gray-50'
                            }`}
                            style={selectedFiles.includes(file.name) ? { backgroundColor: '#7ECEF4' } : {}}
                            onClick={() => toggleFileSelection(file.name)}
                          >
                            <div className="flex items-center space-x-3 flex-1">
                              <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                                selectedFiles.includes(file.name)
                                  ? ''
                                  : 'border-gray-300'
                              }`}
                              style={selectedFiles.includes(file.name) ? {
                                backgroundColor: '#56A3B1',
                                borderColor: '#56A3B1'
                              } : {}}>
                                {selectedFiles.includes(file.name) && (
                                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                  </svg>
                                )}
                              </div>
                              <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate">
                                  {getDisplayName(file.name)}
                                </p>
                                <p className="text-xs text-gray-500">
                                  {(file.size / 1024).toFixed(2)} KB
                                </p>
                              </div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-8 text-gray-500">
                          <svg className="w-12 h-12 text-gray-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                          </svg>
                          <p>No files uploaded yet</p>
                        </div>
                      )}
                    </div>
                    {availableFiles.length > 5 && (
                      <div className="text-center mt-4">
                        <p className="text-xs text-gray-500">
                          {availableFiles.length - 5} more files available - search to find them
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>





              {/* Job status */}
              {jobStatus.status !== 'idle' && (
                <div className="mt-6 bg-gray-50 rounded-lg p-4">
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
  );
};

export default JobSetupView; 