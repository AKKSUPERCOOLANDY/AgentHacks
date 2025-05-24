import React, { useState } from 'react';
import TaskFlowViewer from './TaskFlowViewer';
import TaskDetailPanel from './TaskDetailPanel';

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

const TaskQueueView: React.FC = () => {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
  };

  const handleCloseDetailPanel = () => {
    setSelectedTask(null);
  };

  return (
    <div className="h-full w-full relative">
      {/* Main Task Flow Viewer */}
      <TaskFlowViewer onTaskClick={handleTaskClick} />
      
      {/* Task Detail Panel - overlays on the right when a task is selected */}
      <TaskDetailPanel 
        task={selectedTask} 
        onClose={handleCloseDetailPanel} 
      />
      
      {/* Overlay background when panel is open */}
      {selectedTask && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-25 z-40"
          onClick={handleCloseDetailPanel}
        />
      )}
    </div>
  );
};

export default TaskQueueView; 