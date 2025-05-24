import React, { useState, useEffect, useRef } from 'react';
import { useAppContext } from '../contexts/AppContext';
import TreeViewer from './TreeViewer';
import NodeDetailPanel from './NodeDetailPanel';

interface TreeNode {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  created_at: string;
  children?: TreeNode[];
}

interface TreeStats {
  total_nodes: number;
  max_depth: number;
  nodes_by_status: Record<string, number>;
}

const JobSpecificTreeView: React.FC = () => {
  const { jobHistory } = useAppContext();
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [treeData, setTreeData] = useState<TreeNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);
  const [treeStats, setTreeStats] = useState<TreeStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const wsRef = useRef<WebSocket | null>(null);

  // Filter completed jobs based on search term
  const filteredJobs = jobHistory.filter(job => 
    job.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    job.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Get selected job object
  const selectedJobObject = jobHistory.find(job => job.id === selectedJob);

  // Fetch tree data for a specific job
  const fetchJobTreeData = async (jobId: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      console.log(`📡 Fetching tree data for job: ${jobId}`);
      
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
          setIsLoading(false);
          setError(null);
        } else {
          setError('No tree data available for this job');
          setIsLoading(false);
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
        console.log(`🌳 Setting tree data for job: ${jobId}`);
        setTreeData(treeResult.data);
        setIsLoading(false);
        setError(null);
      } else {
        console.log('⚠️ No tree data from API, received:', treeResult);
        setError(`No tree data available for job: ${selectedJobObject?.name || jobId}`);
        setIsLoading(false);
      }
      
      if (statsResult.data) {
        console.log('📈 Setting stats data from API:', statsResult.data);
        setTreeStats(statsResult.data);
      }
      
      setLastUpdate(new Date().toLocaleTimeString());
      
    } catch (err) {
      console.error('❌ Failed to fetch data from API:', err);
      setError(`Failed to load tree for job: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setIsLoading(false);
    }
  };

  // Handle job selection
  const handleJobSelect = (jobId: string) => {
    setSelectedJob(jobId);
    setSelectedNode(null); // Clear selected node when switching jobs
    fetchJobTreeData(jobId);
  };

  // Handle node click
  const handleNodeClick = (nodeData: TreeNode) => {
    setSelectedNode(nodeData);
  };

  // Close detail panel
  const closeDetailPanel = () => {
    setSelectedNode(null);
  };

  // Manual refresh for current job
  const handleManualRefresh = () => {
    if (selectedJob) {
      fetchJobTreeData(selectedJob);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'in_progress': return 'text-yellow-600';
      case 'failed': return 'text-red-600';
      case 'pending': return 'text-gray-600';
      default: return 'text-gray-600';
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

  return (
    <div className="h-full flex flex-col">
      {/* Job Selection Header */}
      <div className="bg-white border-b border-gray-200 p-4 flex-shrink-0">
        <div className="max-w-4xl mx-auto">
          
          {jobHistory.length === 0 ? (
            <div className="text-center py-8">
              <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Completed Jobs</h3>
              <p className="text-gray-600 mb-4">Run a job to view its analysis tree</p>
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
              <div className="mb-4">
                <div className="relative">
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search for jobs..."
                    className="w-full px-4 py-3 pl-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                  />
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                </div>
              </div>

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
                      <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {job.name}
                        </p>
                        <p className="text-xs text-gray-500">
                          Completed {formatDate(job.completedAt)}
                        </p>
                        <div className="flex items-center mt-1">
                          <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                            job.status === 'completed' ? 'bg-green-500' : 'bg-gray-400'
                          }`}></span>
                          <span className="text-xs text-gray-500 capitalize">{job.status}</span>
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

              {/* Selected Job Info */}
              {selectedJob && selectedJobObject && (
                <div className="bg-blue-50 rounded-lg p-4 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="text-blue-600 text-xl">🌳</div>
                    <div>
                      <p className="text-sm font-medium text-blue-900">
                        Viewing tree for: {selectedJobObject.name}
                      </p>
                      <p className="text-xs text-blue-600">
                        Completed: {formatDate(selectedJobObject.completedAt)}
                      </p>
                      {lastUpdate && (
                        <p className="text-xs text-blue-600">
                          Last updated: {lastUpdate}
                        </p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={handleManualRefresh}
                    disabled={isLoading}
                    className="text-white px-3 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed flex items-center space-x-1"
                    style={{ backgroundColor: isLoading ? '#9CA3AF' : '#56A3B1' }}
                    onMouseEnter={e => !isLoading && ((e.target as HTMLElement).style.backgroundColor = '#3A6B80')}
                    onMouseLeave={e => !isLoading && ((e.target as HTMLElement).style.backgroundColor = '#56A3B1')}
                  >
                    <span>{isLoading ? '⏳' : '🔄'}</span>
                    <span>{isLoading ? 'Loading...' : 'Refresh'}</span>
                  </button>
                </div>
              )}

              {/* Tree Stats */}
              {treeStats && selectedJob && (
                <div className="mt-4 flex items-center space-x-6 text-sm text-gray-600">
                  <span>
                    <span className="font-medium">{treeStats.total_nodes}</span> nodes
                  </span>
                  <span>
                    <span className="font-medium">{treeStats.max_depth}</span> levels deep
                  </span>
                  <div className="flex items-center space-x-2">
                    {Object.entries(treeStats.nodes_by_status).map(([status, count]) => (
                      count > 0 && (
                        <span key={status} className={`${getStatusColor(status)} font-medium`}>
                          {count} {status}
                        </span>
                      )
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Tree Visualization */}
      <div className="flex-1 relative">
        {!selectedJob ? (
          jobHistory.length > 0 && (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <div className="text-6xl mb-4">🌳</div>
                <h3 className="text-xl font-medium text-gray-900 mb-2">Select a Job</h3>
                <p className="text-gray-600">Choose a completed job above to view its analysis tree</p>
              </div>
            </div>
          )
        ) : isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-200 border-t-blue-600 mx-auto mb-4"></div>
              <p className="text-blue-700 font-medium">Loading tree for {selectedJobObject?.name}...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md mx-auto p-8">
              <div className="text-red-500 text-6xl mb-4">🚫</div>
              <h3 className="text-red-800 font-semibold text-lg mb-2">Tree Not Available</h3>
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
        ) : !treeData ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md mx-auto p-8">
              <div className="text-gray-400 text-6xl mb-4">🌱</div>
              <h3 className="text-gray-700 font-semibold text-lg mb-2">No Tree Data</h3>
              <p className="text-gray-600 mb-4">
                No analysis tree is available for this job yet.
                The tree should have been generated during the job execution.
              </p>
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
            </div>
          </div>
        ) : (
          <div className={`h-full ${selectedNode ? 'pr-96' : ''} transition-all duration-300`}>
            <TreeViewer 
              data={treeData} 
              onNodeClick={handleNodeClick}
            />
          </div>
        )}

        {/* Detail Panel */}
        <NodeDetailPanel 
          node={selectedNode} 
          onClose={closeDetailPanel}
        />
      </div>
    </div>
  );
};

export default JobSpecificTreeView; 