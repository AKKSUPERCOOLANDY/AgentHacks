import React, { useMemo } from 'react';
import Tree from 'react-d3-tree';

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

const TreeViewer: React.FC<TreeViewerProps> = ({ data, onNodeClick }) => {
  const treeData = useMemo(() => {
    if (!data) return null;
    
    const convertToD3Format = (node: TreeNode): any => ({
      name: node.name,
      attributes: {
        id: node.id,
        description: node.description,
        status: node.status,
        created_at: node.created_at,
      },
      children: node.children?.map(convertToD3Format) || []
    });

    return convertToD3Format(data);
  }, [data]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'url(#greenGradient)';
      case 'in_progress': return 'url(#blueGradient)';
      case 'failed': return 'url(#redGradient)';
      case 'pending': return 'url(#grayGradient)';
      default: return 'url(#grayGradient)';
    }
  };

  const getStatusGlow = (status: string) => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'in_progress': return '#3b82f6';
      case 'failed': return '#ef4444';
      case 'pending': return '#6b7280';
      default: return '#6b7280';
    }
  };

  const getStatusSymbol = (status: string) => {
    switch (status) {
      case 'completed': return '✅';
      case 'in_progress': return '🔄';
      case 'failed': return '❌';
      case 'pending': return '⏳';
      default: return '❓';
    }
  };

  const renderCustomNodeElement = ({ nodeDatum, toggleNode }: any) => (
    <g>
      {/* Gradient Definitions */}
      <defs>
        <radialGradient id="greenGradient" cx="30%" cy="30%">
          <stop offset="0%" stopColor="#34d399" />
          <stop offset="100%" stopColor="#059669" />
        </radialGradient>
        <radialGradient id="blueGradient" cx="30%" cy="30%">
          <stop offset="0%" stopColor="#60a5fa" />
          <stop offset="100%" stopColor="#2563eb" />
        </radialGradient>
        <radialGradient id="redGradient" cx="30%" cy="30%">
          <stop offset="0%" stopColor="#f87171" />
          <stop offset="100%" stopColor="#dc2626" />
        </radialGradient>
        <radialGradient id="grayGradient" cx="30%" cy="30%">
          <stop offset="0%" stopColor="#9ca3af" />
          <stop offset="100%" stopColor="#4b5563" />
        </radialGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
          <feMerge> 
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
        <filter id="shadow">
          <feDropShadow dx="2" dy="4" stdDeviation="3" floodOpacity="0.3"/>
        </filter>
        <linearGradient id="linkGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>

      {/* Outer glow ring */}
      <circle
        r={32}
        fill="none"
        stroke={getStatusGlow(nodeDatum.attributes?.status || 'pending')}
        strokeWidth={2}
        opacity={0.3}
        filter="url(#glow)"
        style={{ 
          cursor: 'pointer',
          animation: 'pulse 2s infinite'
        }}
      />
      
      {/* Main node circle */}
      <circle
        r={28}
        fill={getStatusColor(nodeDatum.attributes?.status || 'pending')}
        stroke="#ffffff"
        strokeWidth={3}
        filter="url(#shadow)"
        style={{ 
          cursor: 'pointer',
          transition: 'all 0.3s ease',
        }}
        onClick={() => {
          toggleNode();
          if (onNodeClick && nodeDatum.attributes) {
            onNodeClick({
              id: nodeDatum.attributes.id,
              name: nodeDatum.name,
              description: nodeDatum.attributes.description,
              status: nodeDatum.attributes.status,
              created_at: nodeDatum.attributes.created_at,
            });
          }
        }}
        onMouseEnter={(e) => {
          (e.target as SVGCircleElement).setAttribute('r', '32');
        }}
        onMouseLeave={(e) => {
          (e.target as SVGCircleElement).setAttribute('r', '28');
        }}
      />
      
      {/* Status symbol in center */}
      <text
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize="20"
        fill="white"
        fontWeight="bold"
        style={{ 
          pointerEvents: 'none',
          textShadow: '0 1px 3px rgba(0,0,0,0.5)'
        }}
      >
        {getStatusSymbol(nodeDatum.attributes?.status || 'pending')}
      </text>
      
      {/* Node name with background */}
      <rect
        x={-80}
        y={38}
        width={160}
        height={24}
        fill="rgba(255,255,255,0.95)"
        stroke="rgba(0,0,0,0.1)"
        strokeWidth={1}
        rx={12}
        filter="url(#shadow)"
        style={{ pointerEvents: 'none' }}
      />
      <text
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize="13"
        fontWeight="600"
        fill="#1f2937"
        y={50}
        style={{ pointerEvents: 'none' }}
      >
        {nodeDatum.name.length > 18 
          ? `${nodeDatum.name.substring(0, 18)}...` 
          : nodeDatum.name}
      </text>
      
      {/* Description with background */}
      <rect
        x={-90}
        y={68}
        width={180}
        height={20}
        fill="rgba(248,250,252,0.9)"
        stroke="rgba(0,0,0,0.05)"
        strokeWidth={1}
        rx={10}
        style={{ pointerEvents: 'none' }}
      />
      <text
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize="11"
        fill="#6b7280"
        y={78}
        style={{ pointerEvents: 'none' }}
      >
        {nodeDatum.attributes?.description?.length > 25 
          ? `${nodeDatum.attributes.description.substring(0, 25)}...`
          : nodeDatum.attributes?.description || ''}
      </text>
    </g>
  );

  if (!treeData) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <div className="text-4xl mb-4">🌳</div>
          <p>No tree data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative">
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.7; }
        }
        .tree-link {
          stroke: url(#linkGradient);
          stroke-width: 3;
          fill: none;
          opacity: 0.6;
          transition: all 0.3s ease;
        }
        .tree-link:hover {
          stroke-width: 4;
          opacity: 1;
        }
      `}</style>

      {/* Animated background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 rounded-2xl shadow-2xl">
        <div className="absolute inset-0 opacity-30" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23e0e7ff' fill-opacity='0.3'%3E%3Cpath d='m36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
        }} />
      </div>

      {/* Tree container with glassy effect */}
      <div className="relative z-10 w-full h-full backdrop-blur-sm bg-white/20 rounded-2xl border border-white/30 shadow-xl overflow-hidden">
        <Tree
          data={treeData}
          renderCustomNodeElement={renderCustomNodeElement}
          orientation="horizontal"
          translate={{ x: 150, y: 300 }}
          nodeSize={{ x: 320, y: 200 }}
          separation={{ siblings: 1.8, nonSiblings: 2.5 }}
          pathFunc="diagonal"
          collapsible={true}
          initialDepth={3}
          pathClassFunc={() => "tree-link"}
          zoom={0.9}
          scaleExtent={{ min: 0.2, max: 3 }}
        />
      </div>
    </div>
  );
};

export default TreeViewer; 