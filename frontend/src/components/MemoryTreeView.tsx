import React, { useState, useEffect, useRef } from 'react';
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

const MemoryTreeView: React.FC = () => {
  const [treeData, setTreeData] = useState<TreeNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);
  const [treeStats, setTreeStats] = useState<TreeStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const wsRef = useRef<WebSocket | null>(null);

  const fetchTreeData = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('📡 Fetching tree data from API...');
      
      // Test basic connectivity first
      const testResponse = await fetch('http://localhost:8000/test');
      console.log('🔗 Test endpoint response:', testResponse.status);
      
      // Fetch tree data from backend API
      const [treeResponse, statsResponse] = await Promise.all([
        fetch('http://localhost:8000/api/tree'),
        fetch('http://localhost:8000/api/tree/stats')
      ]);
      
      console.log('📊 Tree API status:', treeResponse.status);
      console.log('📈 Stats API status:', statsResponse.status);
      
      if (!treeResponse.ok || !statsResponse.ok) {
        throw new Error(`API error: Tree ${treeResponse.status}, Stats ${statsResponse.status}`);
      }
      
      const treeResult = await treeResponse.json();
      const statsResult = await statsResponse.json();
      
      console.log('📊 API Response - Tree:', treeResult);
      console.log('📊 API Response - Stats:', statsResult);
      
      // Use real data from API
      if (treeResult.data) {
        console.log('🌳 Setting real tree data from API:', treeResult.data.name);
        setTreeData(treeResult.data);
        setIsLoading(false);
        setError(null);
      } else {
        console.log('⚠️ No tree data from API, received:', treeResult);
        setError('No tree data available from server');
        setIsLoading(false);
      }
      
      if (statsResult.data) {
        console.log('📈 Setting real stats data from API:', statsResult.data);
        setTreeStats(statsResult.data);
      } else {
        console.log('⚠️ No stats data from API, received:', statsResult);
      }
      
    } catch (err) {
      console.error('❌ Failed to fetch data from API:', err);
      console.error('❌ Error details:', {
        message: err instanceof Error ? err.message : 'Unknown error',
        stack: err instanceof Error ? err.stack : undefined
      });
      setError(`Failed to connect to server: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setIsLoading(false);
    }
  };

  // WebSocket connection management
  const connectWebSocket = () => {
    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      console.log('🔌 Attempting WebSocket connection...');
      const ws = new WebSocket('ws://localhost:8000/ws');
      
      ws.onopen = () => {
        console.log('🔌 WebSocket connected successfully');
        setIsConnected(true);
        setError(null);
        // Don't set loading to false here, wait for actual data
      };

      ws.onmessage = (event) => {
        try {
          console.log('📨 WebSocket RAW message received:', event.data);
          const message = JSON.parse(event.data);
          console.log('📨 WebSocket PARSED message:', message);
          
          if (message.type === 'connection_status') {
            console.log('🔌 WebSocket connection confirmed:', message.data.message);
            setIsConnected(true);
            setError(null);
            setIsLoading(false);
          }
          
          if (message.type === 'tree_update') {
            console.log('📡 Received real-time tree update from:', message.data.source || 'server');
            console.log('📡 Tree update data structure:', {
              hasTree: !!message.data.tree,
              hasStats: !!message.data.stats,
              treeName: message.data.tree?.name,
              dataKeys: Object.keys(message.data || {})
            });
            
            // Use real tree data
            if (message.data.tree) {
              console.log('🌳 Setting real tree data from WebSocket:', message.data.tree.name);
              console.log('🌳 Tree data structure:', {
                id: message.data.tree.id,
                name: message.data.tree.name,
                childrenCount: message.data.tree.children?.length || 0,
                status: message.data.tree.status
              });
              setTreeData(message.data.tree);
              setIsLoading(false);
              setError(null);
            } else {
              console.log('⚠️ No tree data in WebSocket update');
            }
            
            // Use real stats data
            if (message.data.stats) {
              console.log('📊 Setting real stats data from WebSocket:', message.data.stats);
              setTreeStats(message.data.stats);
            } else {
              console.log('⚠️ No stats data in WebSocket update');
            }
            
            setLastUpdate(new Date().toLocaleTimeString());
            setIsConnected(true);
          }
          
        } catch (err) {
          console.error('❌ Error parsing WebSocket message:', err);
          console.log('📨 Raw unparseable message:', event.data);
        }
      };

      ws.onclose = (event) => {
        console.log('🔌 WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;
        
        // Only reconnect if it wasn't a manual close (code 1000) and autoRefresh is on
        if (event.code !== 1000 && autoRefresh) {
          console.log('🔄 Will attempt reconnection in 5 seconds...');
          setTimeout(() => {
            if (autoRefresh && !wsRef.current) {
              connectWebSocket();
            }
          }, 5000);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setIsConnected(false);
        
        // Don't try API fallback if we already have tree data from API
        console.log('🔄 WebSocket failed, but keeping existing data if available');
      };

      wsRef.current = ws;
      
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err);
      setIsConnected(false);
      
      // Don't override API data, just log the WebSocket failure
      console.log('🔄 WebSocket connection failed, continuing with API-only mode');
    }
  };

  useEffect(() => {
    // Start with loading state
    console.log('🚀 Initializing memory tree component');
    setIsLoading(true);
    
    // Always fetch initial data via API first (this is reliable)
    console.log('📊 Fetching initial data via API...');
    fetchTreeData();
    
    // Then establish WebSocket for real-time updates if auto-refresh is enabled
    if (autoRefresh) {
      console.log('🔄 Will establish WebSocket for real-time updates after initial load');
      const timer = setTimeout(() => {
        connectWebSocket();
      }, 2000); // Give API call time to complete first
      
      return () => {
        clearTimeout(timer);
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
      };
    }
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [autoRefresh]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleNodeClick = (nodeData: TreeNode) => {
    setSelectedNode(nodeData);
  };

  const closeDetailPanel = () => {
    setSelectedNode(null);
  };

  const handleManualRefresh = () => {
    if (isConnected && wsRef.current?.readyState === WebSocket.OPEN) {
      // WebSocket is connected, data is already real-time
      setLastUpdate(new Date().toLocaleTimeString());
    } else {
      // WebSocket not connected, fall back to API call
      fetchTreeData();
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

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center">
          <div className="relative">
            <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-200 border-t-blue-600 mx-auto mb-6"></div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-6 h-6 bg-blue-600 rounded-full animate-pulse"></div>
            </div>
          </div>
          <p className="text-blue-700 font-medium text-lg">Loading Memory Tree...</p>
          <p className="text-blue-600 text-sm mt-2">
            {isConnected ? 'Connected to real-time updates' : 'Connecting to backend...'}
          </p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-gradient-to-br from-red-50 to-pink-100">
        <div className="text-center max-w-md mx-auto p-8">
          <div className="text-red-500 text-6xl mb-6">🔌</div>
          <h3 className="text-red-800 font-semibold text-xl mb-4">Connection Error</h3>
          <p className="text-red-600 mb-6">{error}</p>
          <div className="space-y-3">
            <button
              onClick={fetchTreeData}
              className="bg-red-600 text-white px-6 py-3 rounded-lg hover:bg-red-700 transition-colors font-medium"
            >
              🔄 Retry Connection
            </button>
            <p className="text-red-500 text-sm">
              Make sure the backend server is running on port 8000
            </p>
          </div>
        </div>
      </div>
    );
  }

  // No data state
  if (!treeData) {
    return (
      <div className="flex items-center justify-center h-full bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="text-center max-w-md mx-auto p-8">
          <div className="text-gray-400 text-6xl mb-6">🌳</div>
          <h3 className="text-gray-700 font-semibold text-xl mb-4">No Tree Data Available</h3>
          <p className="text-gray-600 mb-6">
            The memory tree is empty or the backend hasn't processed any data yet.
          </p>
          <button
            onClick={handleManualRefresh}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            🔄 Check for Data
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full">
      {/* Controls Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <div className="flex items-center">
              <h2 className="text-xl font-semibold text-gray-900">Memory Tree Visualization</h2>
              {/* Connection Status */}
              {isConnected && (
                <span className="ml-3 px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full flex items-center">
                  <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></span>
                  LIVE
                </span>
              )}
              {!isConnected && autoRefresh && (
                <span className="ml-3 px-2 py-1 text-xs bg-amber-100 text-amber-800 rounded-full flex items-center">
                  <span className="w-2 h-2 bg-amber-500 rounded-full mr-1 animate-pulse"></span>
                  RECONNECTING
                </span>
              )}
            </div>
            
            {/* Tree Stats */}
            {treeStats && (
              <div className="flex items-center space-x-4 text-sm">
                <span className="text-gray-600">
                  <span className="font-medium">{treeStats.total_nodes}</span> nodes
                </span>
                <span className="text-gray-600">
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
                {lastUpdate && (
                  <span className="text-blue-600 text-xs">
                    Updated: {lastUpdate}
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center space-x-3">
            {/* Auto-refresh toggle */}
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-600">
                {isConnected ? 'Real-time' : 'Auto-refresh'}
              </span>
            </label>

            {/* Manual refresh button */}
            <button
              onClick={handleManualRefresh}
              className="bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 transition-colors text-sm flex items-center space-x-1"
            >
              <span>{isConnected ? '📡' : '🔄'}</span>
              <span>{isConnected ? 'Live' : 'Refresh'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Tree Visualization */}
      <div className={`h-full ${selectedNode ? 'pr-96' : ''} transition-all duration-300`}>
        <TreeViewer 
          data={treeData} 
          onNodeClick={handleNodeClick}
        />
      </div>

      {/* Detail Panel */}
      <NodeDetailPanel 
        node={selectedNode} 
        onClose={closeDetailPanel}
      />
    </div>
  );
};

export default MemoryTreeView; 