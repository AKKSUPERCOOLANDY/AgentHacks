import React, { useMemo, useCallback, useState, useEffect, useRef } from 'react';
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  addEdge,
  Controls,
  Background,
  MiniMap,
  Handle,
  Position,
} from 'reactflow';
import type { Connection, Edge, Node } from 'reactflow';
import 'reactflow/dist/style.css';

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

interface TaskData {
  pending: Task[];
  completed: Task[];
  failed: Task[];
  stats: {
    pending_tasks: number;
    in_progress_tasks: number;
    completed_tasks: number;
    failed_tasks: number;
    total_tasks: number;
  };
}

interface TaskFlowViewerProps {
  onTaskClick?: (task: Task) => void;
}

// Custom task node component
const TaskNode = React.memo(({ data }: { data: any }) => {
  // Add safety checks for data
  if (!data || !data.task) {
    return (
      <div className="min-w-[250px] max-w-[300px] rounded-lg border-2 border-red-300 bg-red-100 p-3">
        <div className="text-red-800 text-sm">Invalid task data</div>
      </div>
    );
  }

  const getStatusColor = (status: string, priority: number) => {
    // Use different shades based on priority (1=low, 4=critical)
    const baseColors = {
      pending: ['bg-sky-200', 'bg-sky-300', 'bg-sky-400', 'bg-sky-500'],
      in_progress: ['bg-blue-400', 'bg-blue-500', 'bg-blue-600', 'bg-blue-700'],
      completed: ['bg-green-300', 'bg-green-400', 'bg-green-500', 'bg-green-600'],
      failed: ['bg-red-400', 'bg-red-500', 'bg-red-600', 'bg-red-700'],
      blocked: ['bg-gray-300', 'bg-gray-400', 'bg-gray-500', 'bg-gray-600']
    };
    
    const colorArray = baseColors[status as keyof typeof baseColors] || baseColors.pending;
    const priorityIndex = Math.min(Math.max((priority || 2) - 1, 0), 3);
    return colorArray[priorityIndex];
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✓';
      case 'in_progress': return '⚡';
      case 'failed': return '✗';
      case 'pending': return '⏳';
      case 'blocked': return '🚫';
      default: return '?';
    }
  };

  const getPriorityLabel = (priority: number) => {
    switch (priority) {
      case 1: return 'Low';
      case 2: return 'Med';
      case 3: return 'High';
      case 4: return 'Crit';
      default: return 'Med';
    }
  };

  const formatDuration = (minutes?: number) => {
    if (!minutes) return '';
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  return (
    <div className="relative">
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-gray-300 border-2 border-white"
      />
      
      <div
        className={`
          min-w-[250px] max-w-[300px] rounded-lg border-2 border-white shadow-lg cursor-pointer
          transition-all duration-200 hover:shadow-xl hover:scale-105
          ${getStatusColor(data.status, data.priority)}
        `}
        onClick={() => data.onTaskClick?.(data.task)}
      >
        <div className="p-3 text-gray-800">
          {/* Header with status and priority */}
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-lg font-bold">
                {getStatusIcon(data.status)}
              </span>
              <span className="px-2 py-1 bg-white bg-opacity-60 text-xs rounded font-semibold">
                {getPriorityLabel(data.priority)}
              </span>
            </div>
            {data.actual_duration && (
              <span className="text-xs bg-white bg-opacity-50 px-2 py-1 rounded">
                {formatDuration(data.actual_duration)}
              </span>
            )}
          </div>
          
          {/* Task description */}
          <h3 className="font-semibold text-sm leading-tight mb-2">
            {(data.description || 'No description').length > 60 ? 
              (data.description || 'No description').substring(0, 60) + '...' : 
              (data.description || 'No description')}
          </h3>
          
          {/* Dependencies count */}
          {(data.dependencies || []).length > 0 && (
            <div className="text-xs text-gray-700 opacity-80">
              Depends on {(data.dependencies || []).length} task{(data.dependencies || []).length > 1 ? 's' : ''}
            </div>
          )}
          
          {/* Error message for failed tasks */}
          {data.status === 'failed' && data.error_message && (
            <div className="text-xs text-red-800 bg-red-100 rounded px-2 py-1 mt-2">
              {data.error_message.length > 50 ? data.error_message.substring(0, 50) + '...' : data.error_message}
            </div>
          )}
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-gray-300 border-2 border-white"
      />
    </div>
  );
});

// Define nodeTypes outside component to prevent React Flow warnings
const nodeTypes = {
  task: TaskNode,
};

// Helper functions for positioning and styling
const getXPositionForStatus = (status: string): number => {
  switch (status) {
    case 'pending': return 50;
    case 'in_progress': return 450;
    case 'completed': return 850;
    case 'failed': return 1250;
    default: return 50;
  }
};

const getEdgeColor = (sourceStatus: string, targetStatus: string): string => {
  if (sourceStatus === 'completed' && targetStatus === 'in_progress') return '#10b981'; // green to blue
  if (sourceStatus === 'completed' && targetStatus === 'pending') return '#6366f1'; // green to purple
  if (sourceStatus === 'failed') return '#ef4444'; // red
  return '#64748b'; // gray default
};

const TaskFlowViewer: React.FC<TaskFlowViewerProps> = ({ onTaskClick }) => {
  const [taskData, setTaskData] = useState<TaskData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSilentUpdating, setIsSilentUpdating] = useState(false);
  const lastTaskFetchTimeRef = useRef<number>(0);

  // Fetch task data
  const fetchTaskData = async (silent: boolean = false) => {
    // Debouncing: prevent calls that are too close together (less than 2 seconds apart for tasks)
    const now = Date.now();
    const timeSinceLastFetch = now - lastTaskFetchTimeRef.current;
    
    if (silent && timeSinceLastFetch < 2000) {
      console.log(`⚡ TaskFlow: Skipping fetch due to debouncing (${timeSinceLastFetch}ms since last fetch)`);
      return;
    }
    
    lastTaskFetchTimeRef.current = now;
    
    console.log(`🚀 ${silent ? 'Silent polling' : 'Initial fetch'} for task data...`);
    if (!silent) {
      setLoading(true);
    } else {
      setIsSilentUpdating(true);
    }
    setError(null);
    try {
      console.log('📡 Making API call to http://localhost:8000/api/tasks');
      const response = await fetch('http://localhost:8000/api/tasks');
      console.log('📥 Response received:', response.status, response.ok);
      
      if (!response.ok) throw new Error('Failed to fetch tasks');
      
      const result = await response.json();
      console.log('📄 Raw API result:', result);
      console.log('📊 result.data:', result.data);
      console.log('📋 Setting taskData to:', result.data);
      
      setTaskData(result.data);
      console.log('✅ taskData set successfully');
    } catch (err) {
      console.error('❌ Error in fetchTaskData:', err);
      if (!silent) {
        setError(err instanceof Error ? err.message : 'Failed to load tasks');
      }
    } finally {
      if (!silent) {
        setLoading(false);
      } else {
        setIsSilentUpdating(false);
      }
      console.log('🏁 fetchTaskData completed');
    }
  };

  // Poll for updates
  useEffect(() => {
    console.log('🚀 TaskFlowViewer: Setting up polling');
    fetchTaskData(false); // Initial fetch with loading
    
    const interval = setInterval(() => {
      console.log('🔄 TaskFlowViewer: Silent polling update');
      fetchTaskData(true); // Silent polling every 5 seconds
    }, 5000);
    
    return () => {
      console.log('🛑 TaskFlowViewer: Cleaning up polling interval');
      clearInterval(interval);
    };
  }, []);

  // Debug taskData changes
  useEffect(() => {
    console.log('🔍 taskData state changed:', taskData);
  }, [taskData]);

  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    console.log('🔄 Processing task data:', taskData);
    
    if (!taskData) {
      console.log('⚠️ No task data available');
      return { nodes: [], edges: [] };
    }

    try {
      const allTasks = [...taskData.pending, ...taskData.completed, ...taskData.failed];
      console.log('📝 All tasks combined:', allTasks.length, allTasks);
      
      const nodes: Node[] = [];
      const edges: Edge[] = [];

      // Create a map for quick task lookup
      const taskMap = new Map(allTasks.map(task => [task.id, task]));

      // Group tasks by status for layout
      const statusGroups = {
        pending: taskData.pending || [],
        in_progress: allTasks.filter(t => t.status === 'in_progress') || [],
        completed: taskData.completed || [],
        failed: taskData.failed || [],
      };
      
      console.log('📊 Status groups:', statusGroups);
      
      let yOffset = 50; // Start with some top margin
      const taskSpacing = 200;

      // Layout tasks by status
      Object.entries(statusGroups).forEach(([status, tasks]) => {
        console.log(`Processing ${status} tasks:`, tasks.length);
        
        if (!tasks || tasks.length === 0) return;

        // Sort by priority and creation time
        const sortedTasks = [...tasks].sort((a, b) => {
          if (a.priority !== b.priority) return b.priority - a.priority; // Higher priority first
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime(); // Earlier first
        });

        sortedTasks.forEach((task, index) => {
          if (!task || !task.id) {
            return; // Skip invalid tasks
          }
          
          console.log(`Adding node for task: ${task.id} - ${task.description}`);
          
          nodes.push({
            id: task.id,
            type: 'task',
            position: { 
              x: getXPositionForStatus(status), // Fixed X position per status
              y: yOffset + index * taskSpacing // Stack vertically
            },
            data: {
              task,
              description: task.description || 'No description',
              status: task.status || 'pending',
              priority: task.priority || 2,
              dependencies: task.dependencies || [],
              actual_duration: task.actual_duration,
              error_message: task.error_message,
              onTaskClick,
            },
          });
        });
      });

      // Create edges for dependencies
      allTasks.forEach(task => {
        if (!task || !task.dependencies) return;
        
        task.dependencies.forEach(depId => {
          if (taskMap.has(depId)) {
            const depTask = taskMap.get(depId);
            if (depTask) {
              edges.push({
                id: `edge-${depId}-${task.id}`,
                source: depId,
                target: task.id,
                type: 'smoothstep',
                style: {
                  strokeWidth: 2,
                  stroke: getEdgeColor(depTask.status, task.status),
                },
                animated: task.status === 'in_progress',
              });
            }
          }
        });
      });

      console.log('🎯 Final nodes:', nodes.length, nodes);
      console.log('🔗 Final edges:', edges.length, edges);

      return { nodes, edges };
    } catch (error) {
      console.error('❌ Error processing task data:', error);
      return { nodes: [], edges: [] };
    }
  }, [taskData, onTaskClick]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync nodes and edges when initialNodes/initialEdges change
  useEffect(() => {
    console.log('🔄 Syncing nodes:', initialNodes.length, 'nodes');
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    console.log('🔄 Syncing edges:', initialEdges.length, 'edges');
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  if (loading && !taskData) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-gray-200 rounded-full mx-auto"
               style={{ borderTopColor: '#56A3B1' }}>
          </div>
          <p className="mt-4">Loading task queue...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-500">
        <div className="text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <p className="font-medium">Failed to load task queue</p>
          <p className="text-sm mt-2">{error}</p>
          <button 
            onClick={() => fetchTaskData(false)}
            className="mt-4 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col">
      {/* Status Legend */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h3 className="text-lg font-semibold text-gray-900">Task Queue Flow</h3>
            {isSilentUpdating && (
              <div className="flex items-center space-x-2 bg-blue-50 border border-blue-200 rounded-lg px-2 py-1">
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></div>
                <span className="text-xs font-medium text-blue-700">Updating</span>
              </div>
            )}
          </div>
          <div className="flex items-center space-x-4 text-sm">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-sky-400 rounded"></div>
              <span>Pending ({taskData?.stats?.pending_tasks || 0})</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-blue-600 rounded"></div>
              <span>In Progress ({taskData?.stats?.in_progress_tasks || 0})</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded"></div>
              <span>Completed ({taskData?.stats?.completed_tasks || 0})</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-red-500 rounded"></div>
              <span>Failed ({taskData?.stats?.failed_tasks || 0})</span>
            </div>
          </div>
        </div>
      </div>

      {/* React Flow */}
      <div className="flex-1">
        {nodes.length === 0 && !loading ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <div className="text-4xl mb-4">📋</div>
              <p className="font-medium">No tasks available</p>
              <p className="text-sm mt-2">Tasks will appear here when they are created</p>
            </div>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{
              padding: 0.1,
              minZoom: 0.3,
              maxZoom: 1.2,
            }}
            className="bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100"
          >
            <Controls className="bg-white border border-gray-200 rounded-lg shadow-lg" />
            <MiniMap 
              className="bg-white border border-gray-200 rounded-lg shadow-lg"
              nodeColor={(node) => {
                const status = node.data?.status || 'pending';
                const priority = node.data?.priority || 2;
                switch (status) {
                  case 'pending': return ['#bae6fd', '#7dd3fc', '#38bdf8', '#0ea5e9'][Math.min(priority - 1, 3)];
                  case 'in_progress': return ['#60a5fa', '#3b82f6', '#2563eb', '#1d4ed8'][Math.min(priority - 1, 3)];
                  case 'completed': return ['#86efac', '#4ade80', '#22c55e', '#16a34a'][Math.min(priority - 1, 3)];
                  case 'failed': return ['#f87171', '#ef4444', '#dc2626', '#b91c1c'][Math.min(priority - 1, 3)];
                  default: return '#94a3b8';
                }
              }}
            />
            <Background 
              gap={20} 
              size={1} 
              color="#e2e8f0"
            />
          </ReactFlow>
        )}
      </div>
    </div>
  );
};

export default TaskFlowViewer; 