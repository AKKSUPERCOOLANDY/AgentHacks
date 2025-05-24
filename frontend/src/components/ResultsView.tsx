import React, { useState, useEffect } from 'react';
import { useAppContext } from '../contexts/AppContext';
import type { Job } from '../contexts/AppContext';

const ResultsView: React.FC = () => {
  const { jobStatus, currentJobName, setJobSummary, jobHistory, setJobHistory, setJobStatus } = useAppContext();
  const [loading] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [currentTreeStats, setCurrentTreeStats] = useState<any>(null);
  const [expandedEvidence, setExpandedEvidence] = useState<Set<string>>(new Set());
  const [expandedFindings, setExpandedFindings] = useState<Set<number>>(new Set());
  const API_BASE = 'http://localhost:8000';

  // Poll for job completion when running
  useEffect(() => {
    let jobAddedToHistory = false;
    
    if (jobStatus.status === 'running') {
      const pollInterval = setInterval(async () => {
        console.log('Polling for job completion in ResultsView...'); // Debug log
        try {
          const response = await fetch(`${API_BASE}/api/analysis/summary`);
          if (response.ok) {
            const data = await response.json();
            console.log('Polling response:', data); // Debug log
            if (data.summary && !jobAddedToHistory) {
              setJobSummary(data.summary);
              
              // Update existing running job to completed status
              setJobHistory(prev => prev.map(job => {
                if (job.status === 'running' && job.name === currentJobName) {
                  return {
                    ...job,
                    status: 'completed' as const,
                    completedAt: new Date().toISOString(),
                    summary: data.summary
                  };
                }
                return job;
              }));
              
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
  }, [jobStatus.status, setJobSummary, setJobStatus, setJobHistory, currentJobName]);

  // Fetch current tree stats when a job is selected
  useEffect(() => {
    const fetchTreeStats = async () => {
      if (selectedJob) {
        try {
          const response = await fetch(`${API_BASE}/api/tree/stats`);
          if (response.ok) {
            const data = await response.json();
            setCurrentTreeStats(data.data);
          }
        } catch (error) {
          console.error('Error fetching tree stats:', error);
        }
      }
    };

    fetchTreeStats();
  }, [selectedJob]);

  // When a job completes, automatically show the latest job
  useEffect(() => {
    if (jobStatus.status === 'completed' && jobHistory.length > 0) {
      const latestJob = jobHistory[0];
      setSelectedJob(latestJob); // Show the most recent completed job
      setJobSummary(latestJob.summary || null); // Load the summary automatically
    }
  }, [jobStatus.status, jobHistory, setJobSummary]);



  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleJobClick = (job: Job) => {
    setSelectedJob(job);
    setJobSummary(job.summary || null);
    setExpandedEvidence(new Set()); // Reset expanded state when switching jobs
    setExpandedFindings(new Set()); // Reset findings expanded state when switching jobs
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

  const toggleEvidence = (evidenceId: string) => {
    setExpandedEvidence(prev => {
      const newSet = new Set(prev);
      if (newSet.has(evidenceId)) {
        newSet.delete(evidenceId);
      } else {
        newSet.add(evidenceId);
      }
      return newSet;
    });
  };

  const toggleFinding = (findingIndex: number) => {
    setExpandedFindings(prev => {
      const newSet = new Set(prev);
      if (newSet.has(findingIndex)) {
        newSet.delete(findingIndex);
      } else {
        newSet.add(findingIndex);
      }
      return newSet;
    });
  };

  // Function to extract evidence tags from finding text
  const getEvidenceTagsForFinding = (finding: any, evidenceList: any[]) => {
    const tags: string[] = [];
    const searchText = (finding.description || finding.title || '').toLowerCase();
    
    evidenceList.forEach((evidence: any) => {
      // Extract meaningful keywords from evidence titles
      const evidenceTitle = evidence.title.toLowerCase();
      const meaningfulKeywords = extractMeaningfulKeywords(evidenceTitle);
      
      // Check if any meaningful keyword appears in the finding
      if (meaningfulKeywords.some((keyword: string) => searchText.includes(keyword))) {
        tags.push(evidence.title);
      }
    });
    return tags.slice(0, 3); // Limit to 3 tags max
  };

  // Function to extract meaningful keywords from evidence names
  const extractMeaningfulKeywords = (text: string): string[] => {
    const words = text.split(' ');
    const meaningfulWords: string[] = [];
    
    // Filter out common words and keep important terms
    const skipWords = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'evidence', 'analysis'];
    
    words.forEach(word => {
      const cleanWord = word.replace(/[^a-zA-Z]/g, '').toLowerCase();
      if (cleanWord.length > 2 && !skipWords.includes(cleanWord)) {
        meaningfulWords.push(cleanWord);
      }
    });
    
    // Add compound keywords for better matching
    if (text.includes('fingerprint')) meaningfulWords.push('print', 'finger');
    if (text.includes('paperweight')) meaningfulWords.push('weapon', 'crystal');
    if (text.includes('fabric')) meaningfulWords.push('cloth', 'material', 'textile');
    if (text.includes('footprint')) meaningfulWords.push('foot', 'shoe', 'track');
    if (text.includes('window')) meaningfulWords.push('entry', 'break');
    if (text.includes('blood')) meaningfulWords.push('dna', 'biological');
    
    return [...new Set(meaningfulWords)]; // Remove duplicates
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
      <div className="h-full p-6 overflow-y-auto">
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
                <p className="text-gray-600">
                  {selectedJob.completedAt ? `Completed ${formatDate(selectedJob.completedAt)}` : 'In Progress'}
                </p>
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
                    <div className="rounded-lg p-4 border border-gray-200" style={{ backgroundColor: '#7ECEF4' }}>
                      <h4 className="font-semibold mb-1" style={{ color: '#19283B' }}>Files Analyzed</h4>
                      <div className="text-2xl font-bold" style={{ color: '#19283B' }}>
                        {selectedJob.summary.case_overview?.files_analyzed || 0}
                      </div>
                      <div className="text-sm" style={{ color: '#3A6B80' }}>
                        Types: {selectedJob.summary.case_overview?.document_types?.join(', ') || 'N/A'}
                      </div>
                    </div>
                    
                    <div className="rounded-lg p-4 border border-gray-200" style={{ backgroundColor: '#56A3B1' }}>
                      <h4 className="font-semibold text-white mb-1">Tree Depth</h4>
                      <div className="text-2xl font-bold text-white">
                        {currentTreeStats?.max_depth || selectedJob.summary.analysis_metrics?.analysis_depth || 0}
                      </div>
                      <div className="text-sm text-white opacity-90">
                        {currentTreeStats?.total_nodes || selectedJob.summary.analysis_metrics?.total_nodes_created || 0} nodes created
                      </div>
                    </div>
                    
                    <div className="rounded-lg p-4 border border-gray-200" style={{ backgroundColor: '#3A6B80' }}>
                      <h4 className="font-semibold text-white mb-1">Tasks Completed</h4>
                      <div className="text-2xl font-bold text-white">
                        {currentTreeStats?.nodes_by_status?.completed || selectedJob.summary.analysis_metrics?.tasks_completed || 0}
                      </div>
                      <div className="text-sm text-white opacity-90">
                        {currentTreeStats?.task_stats?.failed_tasks || selectedJob.summary.analysis_metrics?.tasks_failed || 0} failed
                      </div>
                    </div>
                  </div>
                </div>

                {/* Investigation Conclusion - MOVED TO TOP */}
                {selectedJob.summary.conclusion && (
                  <div className="bg-gradient-to-r from-emerald-50 to-blue-50 rounded-xl shadow-lg p-6 border border-emerald-200">
                    <div className="flex items-center space-x-3 mb-4">
                      <svg className="w-7 h-7 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                      </svg>
                      <h3 className="text-xl font-bold text-emerald-800">Investigation Conclusion</h3>
                      {selectedJob.summary.case_status && (
                        <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-sm font-medium rounded-full">
                          {selectedJob.summary.case_status}
                        </span>
                      )}
                    </div>
                    <div className="bg-white/60 rounded-lg p-4 border border-emerald-100">
                      <p className="text-gray-800 leading-relaxed text-base font-medium">{selectedJob.summary.conclusion}</p>
                    </div>
                    {selectedJob.summary.investigation_confidence && (
                      <div className="mt-4 flex items-center space-x-3">
                        <span className="text-sm font-medium text-emerald-700">Investigation Confidence:</span>
                        <div className="flex-1 bg-emerald-100 rounded-full h-2 max-w-32">
                          <div 
                            className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${(selectedJob.summary.investigation_confidence * 100)}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-bold text-emerald-600">
                          {Math.round(selectedJob.summary.investigation_confidence * 100)}%
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Key Findings */}
                {selectedJob.summary.key_findings && selectedJob.summary.key_findings.length > 0 && (
                  <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg p-6 border border-white/30">
                    <div className="flex items-center space-x-3 mb-4">
                      <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      <h3 className="text-xl font-bold text-gray-800">Key Findings</h3>
                      <span className="text-sm text-gray-500">({selectedJob.summary.key_findings.length} items)</span>
                    </div>
                                        <div className="space-y-2">
                      {selectedJob.summary.key_findings.map((finding, index) => {
                        const isExpanded = expandedFindings.has(index);
                        const evidenceTags = getEvidenceTagsForFinding(finding, selectedJob.summary?.evidence_summary || []);
                        
                        return (
                          <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
                            <button
                              onClick={() => toggleFinding(index)}
                              className="w-full p-4 text-left"
                              style={{ 
                                backgroundColor: '#7ECEF4',
                                color: '#19283B'
                              }}
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <h4 className="font-semibold text-lg mb-2">{finding.title}</h4>
                                  <div className="flex flex-wrap gap-1">
                                    {evidenceTags.map((tag, tagIndex) => (
                                      <span key={tagIndex} className="px-2 py-1 bg-white bg-opacity-80 text-xs rounded border border-gray-400 text-gray-800 font-medium shadow-sm">
                                        🔗 {tag.length > 20 ? tag.substring(0, 20) + '...' : tag}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                                <div className="flex items-center space-x-2 ml-4 flex-shrink-0">
                                  <span className="text-xs text-gray-600 font-medium">
                                    {finding.source_type}
                                  </span>
                                  <svg 
                                    className={`w-5 h-5 text-gray-600 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                                  >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                  </svg>
                                </div>
                              </div>
                            </button>
                            {isExpanded && (
                              <div className="p-4 bg-white" style={{ borderTopColor: '#7ECEF4', borderTopWidth: '1px' }}>
                                <p className="text-gray-700 text-sm leading-relaxed whitespace-pre-wrap">{finding.description}</p>
                              </div>
                            )}
                          </div>
                        );
                      })}
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
                      <span className="text-sm text-gray-500">({selectedJob.summary.evidence_summary.length} items)</span>
                    </div>
                    <div className="space-y-2">
                      {selectedJob.summary.evidence_summary.map((evidence) => {
                        const isExpanded = expandedEvidence.has(evidence.id);
                        return (
                          <div key={evidence.id} className="border border-gray-200 rounded-lg overflow-hidden">
                            <button
                              onClick={() => toggleEvidence(evidence.id)}
                              className="w-full p-4 text-left flex items-center justify-between"
                              style={{ 
                                backgroundColor: '#56A3B1',
                                color: 'white'
                              }}
                            >
                              <div className="flex-1">
                                <h4 className="font-semibold text-white">{evidence.title}</h4>
                              </div>
                              <div className="flex items-center space-x-2">
                                <span className="px-2 py-1 bg-black bg-opacity-20 text-xs rounded text-white font-medium border border-white border-opacity-30">
                                  {evidence.type}
                                </span>
                                <svg 
                                  className={`w-5 h-5 text-white transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                                >
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                              </div>
                            </button>
                            {isExpanded && (
                              <div className="p-4 bg-white" style={{ borderTopColor: '#7ECEF4', borderTopWidth: '1px' }}>
                                <p className="text-gray-700 text-sm leading-relaxed whitespace-pre-wrap">{evidence.description}</p>
                              </div>
                            )}
                          </div>
                        );
                      })}
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
    <div className="h-full p-6 overflow-y-auto">
          {/* Running job - show as job card with yellow icon */}
          {jobStatus.status === 'running' && currentJobName && (
            <div className="mb-6">
              <div className="flex items-center justify-between p-4 bg-white rounded-lg hover:bg-gray-50 transition-all duration-200 shadow-md">
                <div className="flex items-center space-x-4 flex-1 min-w-0">
                  <div className="text-2xl">
                    <div className="animate-spin w-8 h-8 border-4 border-yellow-200 border-t-yellow-500 rounded-full"></div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {currentJobName}
                    </p>
                    <p className="text-sm text-yellow-600 font-medium">
                      Running...
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {jobHistory.length > 0 ? (
            <div className="space-y-4">
              {jobHistory.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-4 bg-white rounded-lg hover:bg-gray-50 transition-all duration-200 shadow-md"
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
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {job.name}
                        </p>
                        <p className="text-sm text-gray-500">
                          {job.completedAt ? formatDate(job.completedAt) : 'In Progress'}
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
          ) : jobStatus.status === 'running' ? null : (
            <div className="text-center py-8">
              <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Completed Jobs</h3>
              <p className="text-gray-600 mb-4">Complete jobs to see results here</p>
              <button
                onClick={() => {
                  window.dispatchEvent(new CustomEvent('switchTab', { detail: 'analysis' }));
                }}
                className="text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
                style={{ backgroundColor: '#56A3B1' }}
                onMouseEnter={e => (e.target as HTMLElement).style.backgroundColor = '#3A6B80'}
                onMouseLeave={e => (e.target as HTMLElement).style.backgroundColor = '#56A3B1'}
              >
                Create Job
              </button>
            </div>
          )}
    </div>
  );
};

export default ResultsView; 