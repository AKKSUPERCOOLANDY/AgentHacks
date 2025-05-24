import React from 'react';

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

interface TaskDetailPanelProps {
  task: Task | null;
  onClose: () => void;
}

const TaskDetailPanel: React.FC<TaskDetailPanelProps> = ({ task, onClose }) => {
  if (!task) return null;

  const getStatusBadge = (status: string) => {
    const statusClasses = {
      completed: 'bg-green-100 text-green-800 border-green-200',
      in_progress: 'bg-blue-100 text-blue-800 border-blue-200',
      failed: 'bg-red-100 text-red-800 border-red-200',
      pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      blocked: 'bg-gray-100 text-gray-800 border-gray-200',
    };

    const statusIcons = {
      completed: '✅',
      in_progress: '⚡',
      failed: '❌',
      pending: '⏳',
      blocked: '🚫',
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

  const getPriorityBadge = (priority: number) => {
    const priorityClasses = {
      1: 'bg-gray-100 text-gray-800 border-gray-200',
      2: 'bg-blue-100 text-blue-800 border-blue-200',
      3: 'bg-orange-100 text-orange-800 border-orange-200',
      4: 'bg-red-100 text-red-800 border-red-200',
    };

    const priorityLabels = {
      1: 'Low',
      2: 'Medium',
      3: 'High',
      4: 'Critical',
    };

    return (
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${
        priorityClasses[priority as keyof typeof priorityClasses] || priorityClasses[2]
      }`}>
        {priorityLabels[priority as keyof typeof priorityLabels] || 'Medium'} Priority
      </span>
    );
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Not set';
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

  const formatDuration = (minutes?: number) => {
    if (!minutes) return 'N/A';
    if (minutes < 60) return `${minutes} minutes`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours} hours`;
  };

  const calculateProgress = () => {
    if (task.status === 'completed') return 100;
    if (task.status === 'failed') return 0;
    if (task.status === 'in_progress') return 50;
    return 0;
  };

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-2xl border-l border-gray-200 z-50 overflow-y-auto">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900">Task Details</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Status and Priority */}
        <div className="flex items-center space-x-3 mb-6">
          {getStatusBadge(task.status)}
          {getPriorityBadge(task.priority)}
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Progress</span>
            <span className="text-sm text-gray-500">{calculateProgress()}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-300 ${
                task.status === 'completed' ? 'bg-green-500' :
                task.status === 'failed' ? 'bg-red-500' :
                task.status === 'in_progress' ? 'bg-blue-500' :
                'bg-gray-400'
              }`}
              style={{ width: `${calculateProgress()}%` }}
            ></div>
          </div>
        </div>

        {/* Task Description */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Description</h3>
          <p className="text-gray-700 leading-relaxed">{task.description}</p>
        </div>

        {/* Instructions */}
        {task.instructions && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Instructions</h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-gray-700 text-sm leading-relaxed">{task.instructions}</p>
            </div>
          </div>
        )}

        {/* Timing Information */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Timing</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Created:</span>
              <span className="text-sm font-medium">{formatDate(task.created_at)}</span>
            </div>
            {task.started_at && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Started:</span>
                <span className="text-sm font-medium">{formatDate(task.started_at)}</span>
              </div>
            )}
            {task.completed_at && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Completed:</span>
                <span className="text-sm font-medium">{formatDate(task.completed_at)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Duration:</span>
              <span className="text-sm font-medium">{formatDuration(task.actual_duration)}</span>
            </div>
          </div>
        </div>

        {/* Dependencies */}
        {task.dependencies.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Dependencies</h3>
            <div className="space-y-2">
              {task.dependencies.map((depId, index) => (
                <div key={depId} className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                  <div className="text-sm font-medium text-blue-900">Dependency {index + 1}</div>
                  <div className="text-xs text-blue-700 font-mono">{depId}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Context Requirements */}
        {task.context_requirements.length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Context Requirements</h3>
            <div className="flex flex-wrap gap-2">
              {task.context_requirements.map((req, index) => (
                <span key={index} className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm">
                  {req}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Result */}
        {task.result && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Result</h3>
            <div className="bg-green-50 rounded-lg p-4 border border-green-200">
              <p className="text-green-800 text-sm leading-relaxed">{task.result}</p>
            </div>
          </div>
        )}

        {/* Error Message */}
        {task.error_message && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Error Details</h3>
            <div className="bg-red-50 rounded-lg p-4 border border-red-200">
              <p className="text-red-800 text-sm leading-relaxed">{task.error_message}</p>
              <div className="mt-2 text-xs text-red-600">
                Retry {task.retry_count} of {task.max_retries}
              </div>
            </div>
          </div>
        )}

        {/* Metadata */}
        {Object.keys(task.metadata).length > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Metadata</h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <pre className="text-xs text-gray-700 overflow-x-auto">
                {JSON.stringify(task.metadata, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {/* Task ID */}
        <div className="pt-4 border-t border-gray-200">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Task ID:</span>
            <span className="text-xs font-mono text-gray-800 bg-gray-100 px-2 py-1 rounded">
              {task.id}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaskDetailPanel; 