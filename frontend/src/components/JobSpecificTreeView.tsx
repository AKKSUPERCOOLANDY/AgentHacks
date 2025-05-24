import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAppContext } from '../contexts/AppContext';
import TreeViewer from './TreeViewer';
import NodeDetailPanel from './NodeDetailPanel';
import TaskFlowViewer from './TaskFlowViewer';
import TaskDetailPanel from './TaskDetailPanel';

interface TreeNode {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  created_at: string;
  children?: TreeNode[];
}

interface Task {
  id: string;
  description: string;
  instructions: string;
  priority: number;
  dependencies: string[];
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'blocked';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  estimated_duration?: number;
  actual_duration?: number;
  context_requirements: string[];
  metadata: any;
  result?: string;
  error_message?: string;
  retry_count: number;
  max_retries: number;
}

interface TreeStats {
  total_nodes: number;
  max_depth: number;
  nodes_by_status: Record<string, number>;
}

const JobSpecificTreeView: React.FC = () => {
  const { jobHistory, setJobHistory } = useAppContext();
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [treeData, setTreeData] = useState<TreeNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [viewMode, setViewMode] = useState<'tree' | 'tasks' | 'split'>('split');
  const [agentPerspective, setAgentPerspective] = useState<'raw' | 'planner' | 'executor' | 'synthesizer' | 'summarization'>('raw');
  const [showAgentInsights, setShowAgentInsights] = useState(false);
  const [treeStats, setTreeStats] = useState<TreeStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSilentUpdating, setIsSilentUpdating] = useState(false);
  const pollIntervalRef = useRef<number | null>(null);
  const lastFetchTimeRef = useRef<number>(0);

  // Auto-redirect and select newest job when a job starts
  useEffect(() => {
    if (jobHistory.length > 0) {
      // Find the most recent job (by creation time or position in array)
      const newestJob = jobHistory[0]; // Assuming newest is first
      
      // Check if job is active (running, in progress, or pending)
      const jobStatus = String(newestJob.status || '').toLowerCase();
      const isActiveJob = jobStatus.includes('progress') || jobStatus.includes('running') || jobStatus.includes('pending');
      
      // Only auto-select if we don't have a selected job, or if there's a new active job
      if (!selectedJob || (isActiveJob && newestJob.id !== selectedJob)) {
        console.log(`🎯 Auto-selecting job: ${newestJob.name} (${newestJob.status})`);
        setSelectedJob(newestJob.id);
        
        // Auto-redirect to graph page if job is running
        const isRunningJob = jobStatus.includes('progress') || jobStatus.includes('running');
        if (isRunningJob) {
          console.log('🚀 Job started, redirecting to graph view');
          window.dispatchEvent(new CustomEvent('switchTab', { detail: 'tree' }));
        }
      }
    }
  }, [jobHistory, selectedJob]);

  // Filter jobs based on search term (now includes all statuses)
  const filteredJobs = jobHistory.filter(job => 
    job.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    job.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Get selected job object
  const selectedJobObject = jobHistory.find(job => job.id === selectedJob);

  // Fetch tree data for a specific job
  const fetchJobTreeData = useCallback(async (jobId: string, silent: boolean = false) => {
    // Debouncing: prevent calls that are too close together (less than 1 second apart)
    const now = Date.now();
    const timeSinceLastFetch = now - lastFetchTimeRef.current;
    
    if (silent && timeSinceLastFetch < 1000) {
      console.log(`⚡ Skipping fetch due to debouncing (${timeSinceLastFetch}ms since last fetch)`);
      return;
    }
    
    lastFetchTimeRef.current = now;
    
    if (!silent) {
      setIsLoading(true);
    } else {
      setIsSilentUpdating(true);
    }
    setError(null);
    
    try {
      console.log(`📡 ${silent ? 'Polling' : 'Fetching'} tree data for job: ${jobId}`);
      
      // Fetch job-specific tree data from backend API
      const [treeResponse, statsResponse] = await Promise.all([
        fetch(`http://localhost:8000/api/tree/job/${encodeURIComponent(jobId)}`),
        fetch(`http://localhost:8000/api/tree/job/${encodeURIComponent(jobId)}/stats`)
      ]);
      
      console.log('📊 Tree API status:', treeResponse.status);
      console.log('📈 Stats API status:', statsResponse.status);
      
      if (!treeResponse.ok || !statsResponse.ok) {
        // If job-specific endpoints don't exist, fall back to global tree
        console.log('⚠️ Job-specific endpoints not available, falling back to global tree');
        const [globalTreeResponse, globalStatsResponse] = await Promise.all([
          fetch('http://localhost:8000/api/tree'),
          fetch('http://localhost:8000/api/tree/stats')
        ]);
        
        if (!globalTreeResponse.ok || !globalStatsResponse.ok) {
          throw new Error(`API error: Tree ${globalTreeResponse.status}, Stats ${globalStatsResponse.status}`);
        }
        
        const treeResult = await globalTreeResponse.json();
        const statsResult = await globalStatsResponse.json();
        
        if (treeResult.data) {
          setTreeData(treeResult.data);
          if (!silent) {
            setIsLoading(false);
          }
          setError(null);
        } else {
          setError('No tree data available for this job');
          if (!silent) {
            setIsLoading(false);
          }
        }
        
        if (statsResult.data) {
          setTreeStats(statsResult.data);
        }
        
        return;
      }
      
      const treeResult = await treeResponse.json();
      const statsResult = await statsResponse.json();
      
      console.log('📊 API Response - Tree:', treeResult);
      console.log('📊 API Response - Stats:', statsResult);
      
      if (treeResult.data) {
        console.log(`🌳 ${silent ? 'Updating' : 'Setting'} tree data for job: ${jobId}`);
        setTreeData(treeResult.data);
        if (!silent) {
          setIsLoading(false);
        }
        setError(null);
      } else {
        console.log('⚠️ No tree data from API, received:', treeResult);
        if (!silent) {
          setError(`No tree data available for job: ${selectedJobObject?.name || jobId}`);
          setIsLoading(false);
        }
      }
      
      if (statsResult.data) {
        console.log('📈 Setting stats data from API:', statsResult.data);
        setTreeStats(statsResult.data);
      }
      
    } catch (err) {
      console.error('❌ Failed to fetch data from API:', err);
      if (!silent) {
        setError(`Failed to load tree for job: ${err instanceof Error ? err.message : 'Unknown error'}`);
        setIsLoading(false);
      }
    } finally {
      if (silent) {
        setIsSilentUpdating(false);
      }
    }
  }, [selectedJobObject]);

  // Real-time polling for active jobs
  useEffect(() => {
    // Clear any existing interval first
    if (pollIntervalRef.current) {
      console.log('🛑 Clearing existing polling interval');
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    
    if (selectedJob && selectedJobObject) {
      const jobStatus = String(selectedJobObject.status || '').toLowerCase();
      const isActiveJob = jobStatus.includes('progress') || jobStatus.includes('running') || jobStatus.includes('pending');
      
      if (isActiveJob) {
        console.log(`🔄 Starting real-time polling for job: ${selectedJobObject.name}`);
        
        // Initial fetch with loading state
        fetchJobTreeData(selectedJob, false);
        
        // Poll every 3 seconds for active jobs with silent updates
        pollIntervalRef.current = setInterval(async () => {
          console.log(`🔄 Silent polling update for job: ${selectedJobObject.name}`);
          fetchJobTreeData(selectedJob, true); // Silent = true for polling
          
          // Also check if analysis has completed
          try {
            const summaryResponse = await fetch('http://localhost:8000/api/analysis/summary');
            if (summaryResponse.ok) {
              const summaryData = await summaryResponse.json();
              if (summaryData.summary && selectedJobObject.status === 'running') {
                console.log('🎉 Analysis completed! Updating job status...');
                
                // Update job status to completed
                setJobHistory(prev => prev.map(job => {
                  if (job.id === selectedJob && job.status === 'running') {
                    return {
                      ...job,
                      status: 'completed' as const,
                      completedAt: new Date().toISOString(),
                      summary: summaryData.summary
                    };
                  }
                  return job;
                }));
                
                // Stop polling since job is complete
                if (pollIntervalRef.current) {
                  clearInterval(pollIntervalRef.current);
                  pollIntervalRef.current = null;
                }
              }
            }
          } catch (error) {
            console.error('Error checking analysis completion:', error);
          }
        }, 3000);
      } else {
        // For completed jobs, just fetch once with loading state
        fetchJobTreeData(selectedJob, false);
      }
    }
    
    // Cleanup interval on component unmount or job change
    return () => {
      if (pollIntervalRef.current) {
        console.log('🛑 Stopping real-time polling');
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [selectedJob, selectedJobObject, fetchJobTreeData, setJobHistory]);

  // Handle job selection
  const handleJobSelect = (jobId: string) => {
    console.log(`👆 Manual job selection: ${jobId}`);
    setSelectedJob(jobId);
    setSelectedNode(null); // Clear selected node when switching jobs
    // Note: fetchJobTreeData will be called by the useEffect polling logic
  };

  // Handle node click
  const handleNodeClick = (nodeData: TreeNode) => {
    setSelectedNode(nodeData);
  };

  // Close detail panel
  const closeDetailPanel = () => {
    setSelectedNode(null);
  };

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    // Close tree detail panel when selecting a task
    setSelectedNode(null);
  };

  const closeTaskDetailPanel = () => {
    setSelectedTask(null);
  };

  // Manual refresh for current job
  const handleManualRefresh = () => {
    if (selectedJob) {
      fetchJobTreeData(selectedJob);
    }
  };

  // Format date for display
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Get icon color based on job status
  const getJobIconColor = (job: any) => {
    if (job.status === 'completed') return 'text-green-500';
    if (job.status === 'in_progress' || job.status === 'running') return 'text-yellow-500';
    if (job.status === 'pending') return 'text-blue-500';
    if (job.status === 'failed' || job.status === 'error') return 'text-red-500';
    return 'text-gray-400';
  };

  // Get status display text
  const getStatusText = (job: any) => {
    if (job.status === 'completed') return job.completedAt ? formatDate(job.completedAt) : 'Completed';
    if (job.status === 'in_progress' || job.status === 'running') return 'In Progress...';
    if (job.status === 'pending') return 'Pending';
    if (job.status === 'failed' || job.status === 'error') return 'Failed';
    return job.completedAt ? formatDate(job.completedAt) : 'Unknown';
  };

  return (
    <div className="h-full flex flex-col">
      {/* Job Selection Header */}
      <div className="bg-white p-4 flex-shrink-0">
        <div className="max-w-4xl mx-auto relative">
          
          {jobHistory.length === 0 ? (
            <div className="text-center py-8">
              <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Jobs Yet</h3>
              <p className="text-gray-600 mb-4">Start a job to view its analysis in real-time</p>
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
          ) : (
            <>
              {/* Job Search */}
              <div className="flex items-center space-x-4">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search jobs..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-80 pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <svg className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>

                {/* Agent Perspective Selector */}
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-700">Agent View:</span>
                  <select 
                    className="border border-gray-300 rounded-lg px-3 py-1 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    value={agentPerspective}
                    onChange={(e) => {
                      const newPerspective = e.target.value as typeof agentPerspective;
                      setAgentPerspective(newPerspective);
                      setShowAgentInsights(newPerspective !== 'raw');
                    }}
                  >
                    <option value="raw">Raw Tree</option>
                    <option value="planner">🎯 Planner Agent</option>
                    <option value="executor">⚙️ Executor Agent</option>
                    <option value="synthesizer">🔗 Synthesizer Agent</option>
                    <option value="summarization">📊 Summarization Agent</option>
                  </select>
                </div>

                {/* View Mode Toggle */}
                <div className="flex bg-gray-100 rounded-lg p-1">
                  <button
                    onClick={() => setViewMode('tree')}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      viewMode === 'tree' 
                        ? 'bg-white text-gray-900 shadow-sm' 
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Tree
                  </button>
                  <button
                    onClick={() => setViewMode('split')}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      viewMode === 'split' 
                        ? 'bg-white text-gray-900 shadow-sm' 
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Split
                  </button>
                  <button
                    onClick={() => setViewMode('tasks')}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      viewMode === 'tasks' 
                        ? 'bg-white text-gray-900 shadow-sm' 
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Tasks
                  </button>
                </div>
              </div>

              <div className="mb-4"></div> {/* Spacer */}

              {/* Job List */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
                {(searchTerm ? filteredJobs : jobHistory.slice(0, 6)).map((job) => (
                  <button
                    key={job.id}
                    onClick={() => handleJobSelect(job.id)}
                    className={`text-left p-4 rounded-lg border transition-all duration-200 ${
                      selectedJob === job.id
                        ? 'bg-blue-50 border-blue-300 ring-2 ring-blue-500'
                        : 'bg-white border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div className="relative">
                        <svg className={`w-6 h-6 ${getJobIconColor(job)}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                        {/* Real-time indicator for active jobs */}
                        {(() => {
                          const jobStatus = String(job.status || '').toLowerCase();
                          const isActiveJob = jobStatus.includes('progress') || jobStatus.includes('running') || jobStatus.includes('pending');
                          return isActiveJob && selectedJob === job.id ? (
                            <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse">
                              <div className="absolute inset-0 w-3 h-3 bg-red-500 rounded-full animate-ping"></div>
                            </div>
                          ) : null;
                        })()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {job.name}
                        </p>
                        <div className="flex items-center space-x-2 mt-1">
                          <p className="text-xs text-gray-500">
                            {getStatusText(job)}
                          </p>
                          {(() => {
                            const jobStatus = String(job.status || '').toLowerCase();
                            const isActiveJob = jobStatus.includes('progress') || jobStatus.includes('running') || jobStatus.includes('pending');
                            return isActiveJob ? (
                              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full font-medium">
                                LIVE
                              </span>
                            ) : null;
                          })()}
                        </div>
                      </div>
                      {selectedJob === job.id && (
                        <div className="text-blue-600">
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>

              {searchTerm && filteredJobs.length === 0 && (
                <div className="text-center py-4 text-gray-500">
                  No jobs found matching "{searchTerm}"
                </div>
              )}

              {/* Tree Stats - positioned horizontally aligned with selected job */}
              {treeStats && selectedJob && (
                <div className="absolute right-0 top-20 bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
                  <div className="flex items-center space-x-4 text-sm text-gray-600">
                    <div><span className="font-medium">{treeStats.total_nodes}</span> nodes</div>
                    <div><span className="font-medium">{treeStats.max_depth}</span> levels deep</div>
                    <div className="text-green-600 font-medium">
                      {Object.entries(treeStats.nodes_by_status).find(([status]) => status === 'completed')?.[1] || 0} completed
                    </div>
                  </div>
                </div>
              )}

            </>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 relative">
        {!selectedJob ? (
          jobHistory.length > 0 && (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <div className="text-6xl mb-4">🌳</div>
                <h3 className="text-xl font-medium text-gray-900 mb-2">Select a Job</h3>
                <p className="text-gray-600">Choose a completed job above to view its analysis tree and tasks</p>
              </div>
            </div>
          )
        ) : isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-200 border-t-blue-600 mx-auto mb-4"></div>
              <p className="text-blue-700 font-medium">Loading data for {selectedJobObject?.name}...</p>
            </div>
          </div>
        ) : error && !treeData ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md mx-auto p-8">
              <div className="text-red-500 text-6xl mb-4">🚫</div>
              <h3 className="text-red-800 font-semibold text-lg mb-2">Data Not Available</h3>
              <p className="text-red-600 mb-4">{error}</p>
              <button
                onClick={handleManualRefresh}
                className="text-white px-4 py-2 rounded-lg transition-colors font-medium"
                style={{ backgroundColor: '#ef4444' }}
                onMouseEnter={e => (e.target as HTMLElement).style.backgroundColor = '#dc2626'}
                onMouseLeave={e => (e.target as HTMLElement).style.backgroundColor = '#ef4444'}
              >
                🔄 Try Again
              </button>
            </div>
          </div>
        ) : (
          <div className="h-full flex">
            {/* Tree View */}
            {(viewMode === 'tree' || viewMode === 'split') && (
              <div className={`${viewMode === 'split' ? 'w-1/2 border-r border-gray-200' : 'w-full'} relative`}>
                {!treeData ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center max-w-md mx-auto p-8">
                      <div className="text-gray-400 text-6xl mb-4">🌱</div>
                      <h3 className="text-gray-700 font-semibold text-lg mb-2">No Tree Data</h3>
                      <p className="text-gray-600 mb-4">
                        {selectedJobObject && (() => {
                          const jobStatus = String(selectedJobObject.status || '').toLowerCase();
                          const isActiveJob = jobStatus.includes('progress') || jobStatus.includes('running') || jobStatus.includes('pending');
                          return isActiveJob ? 'Analysis in progress... Tree will appear as nodes are created.' : 'No analysis tree is available for this job yet.';
                        })()}
                      </p>
                      {!selectedJobObject || (!String(selectedJobObject.status || '').toLowerCase().includes('progress') && !String(selectedJobObject.status || '').toLowerCase().includes('running') && !String(selectedJobObject.status || '').toLowerCase().includes('pending')) && (
                        <button
                          onClick={() => {
                            window.dispatchEvent(new CustomEvent('switchTab', { detail: 'results' }));
                          }}
                          className="text-white px-4 py-2 rounded-lg transition-colors font-medium"
                          style={{ backgroundColor: '#56A3B1' }}
                          onMouseEnter={e => (e.target as HTMLElement).style.backgroundColor = '#3A6B80'}
                          onMouseLeave={e => (e.target as HTMLElement).style.backgroundColor = '#56A3B1'}
                        >
                          View Results
                        </button>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className={`h-full ${selectedNode && viewMode === 'tree' ? 'pr-96' : ''} transition-all duration-300`}>
                    {/* Live update indicator for active jobs */}
                    {selectedJobObject && (() => {
                      const jobStatus = String(selectedJobObject.status || '').toLowerCase();
                      const isActiveJob = jobStatus.includes('progress') || jobStatus.includes('running') || jobStatus.includes('pending');
                      return isActiveJob ? (
                        <div className={`absolute top-4 left-4 border border-green-300 rounded-lg px-3 py-2 z-20 transition-colors duration-200 ${
                          isSilentUpdating ? 'bg-green-200' : 'bg-green-100'
                        }`}>
                          <div className="flex items-center space-x-2">
                            <div className={`w-2 h-2 bg-green-500 rounded-full ${
                              isSilentUpdating ? 'animate-pulse' : 'animate-pulse'
                            }`}></div>
                            <span className="text-sm font-medium text-green-800">
                              {isSilentUpdating ? 'Updating...' : 'Live Updates • Every 3s'}
                            </span>
                          </div>
                        </div>
                      ) : null;
                    })()}
                    
                    {/* Agent View Indicator */}
                    {agentPerspective !== 'raw' && (
                      <div className={`absolute ${selectedJobObject && (() => {
                        const jobStatus = String(selectedJobObject.status || '').toLowerCase();
                        const isActiveJob = jobStatus.includes('progress') || jobStatus.includes('running') || jobStatus.includes('pending');
                        return isActiveJob ? 'top-16' : 'top-4';
                      })()} left-4 bg-blue-100 border border-blue-300 rounded-lg px-3 py-2 z-10`}>
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                          <span className="text-sm font-medium text-blue-800">
                            {agentPerspective === 'planner' && '🎯 Planner View Active'}
                            {agentPerspective === 'executor' && '⚙️ Executor View Active'}
                            {agentPerspective === 'synthesizer' && '🔗 Synthesizer View Active'}
                            {agentPerspective === 'summarization' && '📊 Summarization View Active'}
                          </span>
                        </div>
                      </div>
                    )}
                    <TreeViewer 
                      data={treeData} 
                      onNodeClick={handleNodeClick}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Task View */}
            {(viewMode === 'tasks' || viewMode === 'split') && (
              <div className={`${viewMode === 'split' ? 'w-1/2' : 'w-full'} relative`}>
                <TaskFlowViewer onTaskClick={handleTaskClick} />
              </div>
            )}
          </div>
        )}

        {/* Detail Panels */}
        {viewMode === 'tree' && (
          <NodeDetailPanel 
            node={selectedNode} 
            onClose={closeDetailPanel}
          />
        )}
        
        {/* Agent Insights Sidebar */}
        {showAgentInsights && (
          <div className="absolute right-0 top-0 h-full w-80 bg-white border-l border-gray-200 shadow-lg z-30">
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">
                  {agentPerspective === 'planner' && '🎯 Planner Agent View'}
                  {agentPerspective === 'executor' && '⚙️ Executor Agent View'}
                  {agentPerspective === 'synthesizer' && '🔗 Synthesizer Agent View'}
                  {agentPerspective === 'summarization' && '📊 Summarization Agent View'}
                </h3>
                <button
                  onClick={() => setShowAgentInsights(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            
            <div className="p-4 space-y-6 overflow-y-auto h-full">
              {/* Agent Access Level */}
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Access Level</h4>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  {agentPerspective === 'planner' && (
                    <div>
                      <p className="text-sm text-blue-800"><strong>Task Queue:</strong> Full access with modification rights</p>
                      <p className="text-sm text-blue-800"><strong>Memory:</strong> Navigation + clustering view</p>
                      <p className="text-sm text-blue-800"><strong>Files:</strong> Metadata only</p>
                    </div>
                  )}
                  {agentPerspective === 'executor' && (
                    <div>
                      <p className="text-sm text-blue-800"><strong>Memory:</strong> Full navigation + file access</p>
                      <p className="text-sm text-blue-800"><strong>Files:</strong> Read access to case files</p>
                      <p className="text-sm text-blue-800"><strong>Tasks:</strong> No access</p>
                    </div>
                  )}
                  {agentPerspective === 'synthesizer' && (
                    <div>
                      <p className="text-sm text-blue-800"><strong>Task Queue:</strong> Full access, read-only</p>
                      <p className="text-sm text-blue-800"><strong>Memory:</strong> Full analysis + patterns</p>
                      <p className="text-sm text-blue-800"><strong>Files:</strong> Read access to case files</p>
                    </div>
                  )}
                  {agentPerspective === 'summarization' && (
                    <div>
                      <p className="text-sm text-blue-800"><strong>Memory:</strong> Read-only access</p>
                      <p className="text-sm text-blue-800"><strong>Files:</strong> Metadata only</p>
                      <p className="text-sm text-blue-800"><strong>Focus:</strong> Content compression</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Memory Clusters */}
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Memory Clusters</h4>
                <div className="space-y-2">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <div className="flex items-center space-x-2 mb-1">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      <span className="text-sm font-medium text-green-800">Forensic Evidence</span>
                    </div>
                    <p className="text-xs text-green-700">5 nodes • 2 unexplored</p>
                  </div>
                  <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                    <div className="flex items-center space-x-2 mb-1">
                      <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                      <span className="text-sm font-medium text-purple-800">Witness Testimony</span>
                    </div>
                    <p className="text-xs text-purple-700">3 nodes • 1 contradiction</p>
                  </div>
                  <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                    <div className="flex items-center space-x-2 mb-1">
                      <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                      <span className="text-sm font-medium text-orange-800">Timeline</span>
                    </div>
                    <p className="text-xs text-orange-700">4 nodes • verified sequence</p>
                  </div>
                </div>
              </div>

              {/* Hot Spots */}
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Hot Spots</h4>
                <div className="space-y-2">
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-lg">🔥</span>
                      <span className="text-sm font-medium text-red-800">Crime Scene Analysis</span>
                    </div>
                    <p className="text-xs text-red-700">Hub node with 8 connections</p>
                  </div>
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-lg">⚡</span>
                      <span className="text-sm font-medium text-yellow-800">Suspect Identification</span>
                    </div>
                    <p className="text-xs text-yellow-700">Hub node with 6 connections</p>
                  </div>
                </div>
              </div>

              {/* Navigation Suggestions */}
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Navigation Suggestions</h4>
                <div className="space-y-2">
                  {agentPerspective === 'planner' && (
                    <>
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <p className="text-sm text-gray-700">• Focus on gaps in investigation</p>
                      </div>
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <p className="text-sm text-gray-700">• Identify areas needing more analysis</p>
                      </div>
                    </>
                  )}
                  {agentPerspective === 'executor' && (
                    <>
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <p className="text-sm text-gray-700">• Deep dive into specific evidence</p>
                      </div>
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <p className="text-sm text-gray-700">• Cross-reference multiple sources</p>
                      </div>
                    </>
                  )}
                  {agentPerspective === 'synthesizer' && (
                    <>
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <p className="text-sm text-gray-700">• Look for patterns across clusters</p>
                      </div>
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <p className="text-sm text-gray-700">• Identify conflicting evidence</p>
                      </div>
                    </>
                  )}
                  {agentPerspective === 'summarization' && (
                    <>
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <p className="text-sm text-gray-700">• Start with high-confidence nodes</p>
                      </div>
                      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <p className="text-sm text-gray-700">• Focus on completed analyses</p>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Similarity Connections */}
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Similarity Connections</h4>
                <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
                  <p className="text-sm text-indigo-800 mb-2">Beyond parent-child relationships:</p>
                  <div className="space-y-1">
                    <p className="text-xs text-indigo-700">• Content similarity: 0.85</p>
                    <p className="text-xs text-indigo-700">• Keyword overlap: fingerprint, DNA</p>
                    <p className="text-xs text-indigo-700">• Evidence correlation: high</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <TaskDetailPanel 
          task={selectedTask} 
          onClose={closeTaskDetailPanel} 
        />
        
        {/* Overlay background when task panel is open */}
        {selectedTask && (
          <div 
            className="fixed inset-0 bg-black bg-opacity-25 z-40"
            onClick={closeTaskDetailPanel}
          />
        )}
      </div>
    </div>
  );
};

export default JobSpecificTreeView; 