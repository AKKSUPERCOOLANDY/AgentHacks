import React, { useState, useEffect } from 'react';
import { useAppContext } from '../contexts/AppContext';
import type { CompletedJob } from '../contexts/AppContext';

const ResultsView: React.FC = () => {
  const { jobStatus, currentJobName, setJobSummary, jobSummary, jobHistory, setJobHistory } = useAppContext();
  const [loading, setLoading] = useState(false);
  const [selectedJob, setSelectedJob] = useState<CompletedJob | null>(null);
  const API_BASE = 'http://localhost:8000';

  // Poll for results when job is running and add to history when complete
  useEffect(() => {
    if (jobStatus.status === 'running') {
      const pollInterval = setInterval(async () => {
        try {
          const response = await fetch(`${API_BASE}/api/analysis/summary`);
          if (response.ok) {
            const data = await response.json();
            if (data.summary) {
              setJobSummary(data.summary);
              
              // Add completed job to history
              const completedJob: CompletedJob = {
                id: Math.random().toString(36).substring(7),
                name: currentJobName || 'Untitled Job',
                completedAt: new Date().toISOString(),
                summary: data.summary,
                status: 'completed'
              };
              
              setJobHistory(prev => [completedJob, ...prev]);
              setSelectedJob(completedJob);
              clearInterval(pollInterval);
            }
          }
        } catch (error) {
          console.error('Error polling for results:', error);
        }
      }, 3000);

      return () => clearInterval(pollInterval);
    }
  }, [jobStatus.status, setJobSummary, currentJobName, setJobHistory]);

  // Fetch results on mount if not running
  useEffect(() => {
    if (jobStatus.status !== 'running' && !jobSummary && jobHistory.length === 0) {
      fetchResults();
    }
  }, []);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/analysis/summary`);
      if (response.ok) {
        const data = await response.json();
        if (data.summary) {
          setJobSummary(data.summary);
          
          // If we have current job name and summary, add to history
          if (currentJobName) {
            const completedJob: CompletedJob = {
              id: Math.random().toString(36).substring(7),
              name: currentJobName,
              completedAt: new Date().toISOString(),
              summary: data.summary,
              status: 'completed'
            };
            
            setJobHistory(prev => {
              // Don't duplicate if already exists
              if (prev.some(job => job.name === completedJob.name)) {
                return prev;
              }
              return [completedJob, ...prev];
            });
            setSelectedJob(completedJob);
          }
        }
      }
    } catch (error) {
      console.error('Error fetching results:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleJobClick = (job: CompletedJob) => {
    setSelectedJob(job);
    setJobSummary(job.summary);
  };

  const handleBackToList = () => {
    setSelectedJob(null);
  };

  const handleDeleteJob = (jobId: string, jobName: string) => {
    if (!window.confirm(`Are you sure you want to delete the job "${jobName}"? This action cannot be undone.`)) {
      return;
    }

    setJobHistory(prev => prev.filter(job => job.id !== jobId));
    
    // If we're currently viewing the deleted job, go back to list
    if (selectedJob && selectedJob.id === jobId) {
      setSelectedJob(null);
    }
  };

  if (loading) {
    return (
      <div className="h-full p-6">
        <div className="flex items-center justify-center h-full">
            <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full"></div>
            <span className="ml-3 text-gray-600">Loading results...</span>
          </div>
      </div>
    );
  }

  // Show detailed view if a job is selected
  if (selectedJob) {
    return (
      <div className="h-full p-6">
            {/* Header with back button */}
            <div className="flex items-center mb-8">
              <button
                onClick={handleBackToList}
                className="mr-4 p-2 text-gray-600 hover:text-gray-800 hover:bg-white/50 rounded-full transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h2 className="text-2xl font-bold text-gray-800">{selectedJob.name}</h2>
                <p className="text-gray-600">Completed {formatDate(selectedJob.completedAt)}</p>
              </div>
            </div>

            {selectedJob.summary && (
              <div className="space-y-6">
                {/* Summary Metrics */}
                <div className="bg-gray-50 rounded-lg p-6">
                  <div className="flex items-center space-x-3 mb-4">
                    <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    <h3 className="text-xl font-bold text-gray-800">Summary</h3>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <h4 className="font-semibold text-blue-800 mb-1">Files Analyzed</h4>
                      <div className="text-2xl font-bold text-blue-600">
                        {selectedJob.summary.case_overview?.files_analyzed || 0}
                      </div>
                      <div className="text-sm text-blue-600">
                        Types: {selectedJob.summary.case_overview?.document_types?.join(', ') || 'N/A'}
                      </div>
                    </div>
                    
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <h4 className="font-semibold text-green-800 mb-1">Analysis Depth</h4>
                      <div className="text-2xl font-bold text-green-600">
                        {selectedJob.summary.analysis_metrics?.analysis_depth || 0}
                      </div>
                      <div className="text-sm text-green-600">
                        {selectedJob.summary.analysis_metrics?.total_nodes_created || 0} nodes created
                      </div>
                    </div>
                    
                    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                      <h4 className="font-semibold text-purple-800 mb-1">Tasks Completed</h4>
                      <div className="text-2xl font-bold text-purple-600">
                        {selectedJob.summary.analysis_metrics?.tasks_completed || 0}
                      </div>
                      <div className="text-sm text-purple-600">
                        {selectedJob.summary.analysis_metrics?.tasks_failed || 0} failed
                      </div>
                    </div>
                  </div>
                </div>

                {/* Key Findings */}
                {selectedJob.summary.key_findings && selectedJob.summary.key_findings.length > 0 && (
                  <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg p-6 border border-white/30">
                    <div className="flex items-center space-x-3 mb-4">
                      <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      <h3 className="text-xl font-bold text-gray-800">Key Findings</h3>
                    </div>
                    <div className="space-y-3">
                      {selectedJob.summary.key_findings.map((finding, index) => (
                        <div key={index} className="p-4 bg-gray-50 rounded-lg">
                          <p className="text-gray-700">{finding}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Evidence Summary */}
                {selectedJob.summary.evidence_summary && selectedJob.summary.evidence_summary.length > 0 && (
                  <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg p-6 border border-white/30">
                    <div className="flex items-center space-x-3 mb-4">
                      <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                      <h3 className="text-xl font-bold text-gray-800">Evidence Summary</h3>
                    </div>
                    <div className="space-y-3">
                      {selectedJob.summary.evidence_summary.map((evidence, index) => (
                        <div key={index} className="p-4 bg-yellow-50 border-l-4 border-yellow-400 rounded-r-lg">
                          <h4 className="font-semibold text-yellow-800 mb-1">{evidence.type}</h4>
                          <p className="text-yellow-700 text-sm">{evidence.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Conclusion */}
                {selectedJob.summary.conclusion && (
                  <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg p-6 border border-white/30">
                    <div className="flex items-center space-x-3 mb-4">
                      <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                      </svg>
                      <h3 className="text-xl font-bold text-gray-800">Conclusion</h3>
                    </div>
                    <p className="text-gray-700 leading-relaxed">{selectedJob.summary.conclusion}</p>
                    <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                      <span className="text-blue-800 font-medium">Status: </span>
                      <span className="text-blue-600">{selectedJob.summary.case_status || 'Complete'}</span>
                    </div>
                  </div>
                )}
              </div>
            )}
      </div>
    );
  }

  // Show job history list
  return (
    <div className="h-full p-6">
          {/* Running job status */}
          {jobStatus.status === 'running' && (
            <div className="bg-blue-50 rounded-lg p-4 mb-6">
              <div className="flex items-center">
                <div className="animate-spin w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full mr-3"></div>
                <div>
                  <p className="text-blue-800 font-medium">
                    {currentJobName ? `Running: ${currentJobName}` : 'Job in Progress'}
                  </p>
                  <p className="text-blue-600 text-sm">Results will appear here when complete</p>
                </div>
              </div>
            </div>
          )}

          {jobHistory.length > 0 ? (
            <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg p-6 border border-white/30">
              <h2 className="text-2xl font-semibold text-gray-800 mb-6">
                Job History ({jobHistory.length})
              </h2>
              <div className="space-y-3">
                {jobHistory.map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between p-4 bg-white/40 backdrop-blur-sm rounded-lg hover:bg-white/60 transition-all duration-200 border border-white/20"
                  >
                    <div 
                      className="flex items-center space-x-4 flex-1 min-w-0 cursor-pointer"
                      onClick={() => handleJobClick(job)}
                    >
                      <div className="text-2xl">
                        {job.status === 'completed' ? (
                          <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                          </svg>
                        ) : (
                          <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {job.name}
                          </p>
                          <span className={`text-xs px-2 py-1 rounded-full ${
                            job.status === 'completed' 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {job.status === 'completed' ? 'Completed' : 'Failed'}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500">
                          {formatDate(job.completedAt)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteJob(job.id, job.name);
                        }}
                        className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-full transition-colors"
                        title="Delete job"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                      <div 
                        className="text-gray-400 cursor-pointer p-2"
                        onClick={() => handleJobClick(job)}
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : jobStatus.status === 'running' ? null : (
            <div className="flex flex-col items-center justify-center h-96">
              <svg className="w-24 h-24 text-gray-300 mb-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <h3 className="text-2xl font-bold text-gray-800 mb-4">No Jobs Completed</h3>
              <p className="text-gray-600 text-center mb-8 max-w-md">
                Complete jobs to see results here
              </p>
              <button
                onClick={() => {
                  window.dispatchEvent(new CustomEvent('switchTab', { detail: 'analysis' }));
                }}
                className="text-white font-medium py-4 px-8 rounded-lg transition-colors duration-200 shadow-lg hover:shadow-xl flex items-center justify-center space-x-3 text-lg min-w-[280px] h-[60px]"
                style={{ backgroundColor: '#56A3B1' }}
                onMouseEnter={e => (e.target as HTMLElement).style.backgroundColor = '#3A6B80'}
                onMouseLeave={e => (e.target as HTMLElement).style.backgroundColor = '#56A3B1'}
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span>Create New Job</span>
              </button>
            </div>
          )}
    </div>
  );
};

export default ResultsView; 