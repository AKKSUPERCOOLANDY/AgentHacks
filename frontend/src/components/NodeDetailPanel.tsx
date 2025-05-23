import React from 'react';

interface TreeNode {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  created_at: string;
  children?: TreeNode[];
}

interface NodeDetailPanelProps {
  node: TreeNode | null;
  onClose: () => void;
}

const NodeDetailPanel: React.FC<NodeDetailPanelProps> = ({ node, onClose }) => {
  if (!node) return null;

  const getStatusBadge = (status: string) => {
    const statusClasses = {
      completed: 'bg-green-100 text-green-800 border-green-200',
      in_progress: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      failed: 'bg-red-100 text-red-800 border-red-200',
      pending: 'bg-gray-100 text-gray-800 border-gray-200',
    };

    const statusIcons = {
      completed: '✅',
      in_progress: '🔄',
      failed: '❌',
      pending: '⏳',
    };

    return (
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${
        statusClasses[status as keyof typeof statusClasses] || statusClasses.pending
      }`}>
        <span className="mr-1">
          {statusIcons[status as keyof typeof statusIcons] || '❓'}
        </span>
        {status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ')}
      </span>
    );
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-xl border-l border-gray-200 z-50 overflow-y-auto">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Node Details</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close panel"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Node Information */}
        <div className="space-y-6">
          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
            {getStatusBadge(node.status)}
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Name</label>
            <p className="text-gray-900 font-medium">{node.name}</p>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                {node.description || 'No description available'}
              </p>
            </div>
          </div>

          {/* Created At */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Created</label>
            <p className="text-gray-600">{formatDate(node.created_at)}</p>
          </div>

          {/* Node ID */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Node ID</label>
            <div className="bg-gray-50 rounded-lg p-3">
              <code className="text-sm text-gray-600 font-mono break-all">{node.id}</code>
            </div>
          </div>

          {/* Children Count */}
          {node.children && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Children</label>
              <div className="flex items-center space-x-2">
                <span className="text-2xl">🌿</span>
                <span className="text-gray-900 font-medium">
                  {node.children.length} child node{node.children.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <div className="space-y-3">
            <button className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors">
              Export Node Data
            </button>
            <button className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 transition-colors">
              View in Tree Context
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NodeDetailPanel; 