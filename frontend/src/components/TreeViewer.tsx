import React, { useMemo, useCallback } from 'react';
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

interface TreeNode {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  created_at: string;
  children?: TreeNode[];
}

interface TreeViewerProps {
  data: TreeNode | null;
  onNodeClick?: (nodeData: TreeNode) => void;
}

// Custom node component
const CustomNode = ({ data }: { data: any }) => {
  const getStatusColor = (status: string, nodeName: string) => {
    // Check if this is a synthesis analysis node
    if (nodeName.toLowerCase().includes('synthesis analysis')) {
      switch (status) {
        case 'completed': return 'bg-orange-300'; // Less saturated orange
        case 'in_progress': return 'bg-orange-400';
        case 'failed': return 'bg-red-500';
        case 'pending': return 'bg-orange-200';
        default: return 'bg-orange-200';
      }
    }
    
    // Check if this is a task node (contains "task" or other task indicators)
    if (nodeName.toLowerCase().includes('task') || 
        nodeName.toLowerCase().includes('evidence') ||
        nodeName.toLowerCase().includes('investigation')) {
    switch (status) {
        case 'completed': return 'bg-sky-300'; // Lighter logo color
        case 'in_progress': return 'bg-sky-400';
        case 'failed': return 'bg-red-500';
        case 'pending': return 'bg-sky-200';
        default: return 'bg-sky-200';
    }
    }
    
    // Default colors for other node types
    switch (status) {
      case 'completed': return 'bg-blue-500';
      case 'in_progress': return 'bg-blue-600';
      case 'failed': return 'bg-red-500';
      case 'pending': return 'bg-gray-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✓';
      case 'in_progress': return '●';
      case 'failed': return '✗';
      case 'pending': return '⏳';
      default: return '?';
    }
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
          min-w-[200px] rounded-lg border-2 border-white shadow-lg cursor-pointer
          transition-all duration-200 hover:shadow-xl hover:scale-105
          ${getStatusColor(data.status, data.name)}
        `}
        onClick={() => data.onNodeClick?.(data.nodeData)}
      >
        <div className="p-4 text-white">
          <div className="flex items-center space-x-2">
            <span className="text-lg font-bold">
              {getStatusIcon(data.status)}
            </span>
            <h3 className="font-semibold text-sm leading-tight">
              {data.name}
            </h3>
          </div>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-gray-300 border-2 border-white"
      />
    </div>
  );
};

// Make synthesis analysis names more descriptive
const getDescriptiveName = (name: string): string => {
  // Make synthesis analysis more descriptive
  if (name.toLowerCase().includes('synthesis analysis')) {
    const match = name.match(/synthesis analysis\s*#?(\d+)/i);
    if (match) {
      const number = match[1];
      return `Deep Analysis Phase ${number}`;
    }
    return 'Comprehensive Analysis';
  }
  
  // Return original name for other node types
  return name;
};

const nodeTypes = {
  custom: CustomNode,
};

const TreeViewer: React.FC<TreeViewerProps> = ({ data, onNodeClick }) => {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!data) return { nodes: [], edges: [] };

    const nodes: Node[] = [];
    const edges: Edge[] = [];
    let nodeId = 0;

    // Convert tree data to React Flow format
    const convertToFlowFormat = (
      node: TreeNode, 
      x: number = 0, 
      y: number = 0, 
      parentId?: string
    ) => {
      const currentId = `node-${nodeId++}`;
      
      nodes.push({
        id: currentId,
        type: 'custom',
        position: { x, y },
        data: {
          name: getDescriptiveName(node.name),
          description: node.description,
          status: node.status,
          nodeData: node,
          onNodeClick,
        },
            });

      if (parentId) {
        edges.push({
          id: `edge-${parentId}-${currentId}`,
          source: parentId,
          target: currentId,
          type: 'smoothstep',
          style: {
            strokeWidth: 2,
            stroke: '#6366f1',
          },
          animated: true,
        });
      }

      // Position children
      if (node.children && node.children.length > 0) {
        const childSpacing = 150;
        const startY = y - ((node.children.length - 1) * childSpacing) / 2;
        
        node.children.forEach((child, index) => {
          convertToFlowFormat(
            child,
            x + 300,
            startY + index * childSpacing,
            currentId
          );
        });
      }
    };

    convertToFlowFormat(data, 100, 300);
    return { nodes, edges };
  }, [data, onNodeClick]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <div className="mb-4">
            <div className="animate-spin w-12 h-12 border-4 border-gray-200 rounded-full mx-auto"
                 style={{ borderTopColor: '#56A3B1' }}>
            </div>
          </div>
          <p>Loading graph data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full">
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
          minZoom: 0.5,
          maxZoom: 1.5,
        }}
        className="bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100"
      >
        <Controls className="bg-white border border-gray-200 rounded-lg shadow-lg" />
        <MiniMap 
          className="bg-white border border-gray-200 rounded-lg shadow-lg"
          nodeColor={(node) => {
            const nodeName = node.data?.name || '';
            const status = node.data?.status || 'pending';
            
            // Use the exact same logic as the main tree visualization
            // Check if this is a synthesis analysis node
            if (nodeName.toLowerCase().includes('synthesis analysis')) {
              switch (status) {
                case 'completed': return '#fdba74'; // orange-300
                case 'in_progress': return '#fb923c'; // orange-400
                case 'failed': return '#ef4444';
                case 'pending': return '#fed7aa'; // orange-200
                default: return '#fed7aa';
              }
            }
            
            // Check if this is a task node (contains "task" or other task indicators)
            if (nodeName.toLowerCase().includes('task') || 
                nodeName.toLowerCase().includes('evidence') ||
                nodeName.toLowerCase().includes('investigation')) {
              switch (status) {
                case 'completed': return '#7dd3fc'; // sky-300
                case 'in_progress': return '#38bdf8'; // sky-400
                case 'failed': return '#ef4444';
                case 'pending': return '#bae6fd'; // sky-200
                default: return '#bae6fd';
              }
            }
            
            // Default colors for other node types
            switch (status) {
              case 'completed': return '#3b82f6';
              case 'in_progress': return '#2563eb';
              case 'failed': return '#ef4444';
              case 'pending': return '#6b7280';
              default: return '#6b7280';
            }
          }}
        />
        <Background 
          gap={20} 
          size={1} 
          color="#e2e8f0"
        />
      </ReactFlow>
    </div>
  );
};

export default TreeViewer; 