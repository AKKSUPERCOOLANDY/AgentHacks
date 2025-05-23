import json
import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from uuid import uuid4
from pathlib import Path


class TaskStatus(Enum):
    """Status of a task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Priority levels for tasks"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Task:
    """Individual task in the task management system"""
    
    def __init__(self, description: str, instructions: str, priority: TaskPriority = TaskPriority.MEDIUM):
        self.id: str = str(uuid4())
        self.description: str = description
        self.instructions: str = instructions
        self.priority: TaskPriority = priority
        self.dependencies: List[str] = []  # Task IDs that must complete first
        self.status: TaskStatus = TaskStatus.PENDING
        self.created_at: datetime = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.estimated_duration: Optional[int] = None  # in minutes
        self.actual_duration: Optional[int] = None  # in minutes
        self.context_requirements: List[str] = []  # Context keys needed for execution
        self.metadata: Dict[str, Any] = {}
        self.result: Optional[str] = None
        self.error_message: Optional[str] = None
        self.retry_count: int = 0
        self.max_retries: int = 3
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization"""
        return {
            'id': self.id,
            'description': self.description,
            'instructions': self.instructions,
            'priority': self.priority.value,
            'dependencies': self.dependencies,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'estimated_duration': self.estimated_duration,
            'actual_duration': self.actual_duration,
            'context_requirements': self.context_requirements,
            'metadata': self.metadata,
            'result': self.result,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary"""
        task = cls(data['description'], data['instructions'], TaskPriority(data['priority']))
        task.id = data['id']
        task.dependencies = data['dependencies']
        task.status = TaskStatus(data['status'])
        task.created_at = datetime.fromisoformat(data['created_at'])
        task.started_at = datetime.fromisoformat(data['started_at']) if data['started_at'] else None
        task.completed_at = datetime.fromisoformat(data['completed_at']) if data['completed_at'] else None
        task.estimated_duration = data['estimated_duration']
        task.actual_duration = data['actual_duration']
        task.context_requirements = data['context_requirements']
        task.metadata = data['metadata']
        task.result = data['result']
        task.error_message = data['error_message']
        task.retry_count = data['retry_count']
        task.max_retries = data['max_retries']
        return task
    
    def start_execution(self):
        """Mark task as started"""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = datetime.now()
    
    def complete_execution(self, result: str):
        """Mark task as completed with result"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result
        if self.started_at:
            self.actual_duration = int((self.completed_at - self.started_at).total_seconds() / 60)
    
    def fail_execution(self, error_message: str):
        """Mark task as failed with error message"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error_message
        self.retry_count += 1
    
    def can_retry(self) -> bool:
        """Check if task can be retried"""
        return self.retry_count < self.max_retries and self.status == TaskStatus.FAILED
    
    def reset_for_retry(self):
        """Reset task for retry"""
        if self.can_retry():
            self.status = TaskStatus.PENDING
            self.started_at = None
            self.completed_at = None
            self.error_message = None


class TaskQueue:
    """Dynamic task queue with dependency management"""
    
    def __init__(self, db_path: str = "task_queue.db"):
        self.tasks: Dict[str, Task] = {}
        self.execution_order: List[str] = []
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []
        self.db_path = db_path
        self._init_database()
        self.load_from_database()
    
    def _init_database(self):
        """Initialize SQLite database for persistence"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queue_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_task(self, task: Task, after_task_id: Optional[str] = None) -> str:
        """Add task with optional dependency"""
        if after_task_id and after_task_id not in self.tasks:
            raise ValueError(f"Dependency task {after_task_id} not found")
        
        # Add dependency if specified
        if after_task_id:
            task.dependencies.append(after_task_id)
        
        self.tasks[task.id] = task
        self._update_execution_order()
        self._save_to_database()
        return task.id
    
    def add_dependency(self, task_id: str, dependency_id: str) -> bool:
        """Add a dependency to an existing task"""
        if task_id not in self.tasks or dependency_id not in self.tasks:
            return False
        
        # Check for circular dependencies
        if self._creates_circular_dependency(task_id, dependency_id):
            return False
        
        self.tasks[task_id].dependencies.append(dependency_id)
        self._update_execution_order()
        self._save_to_database()
        return True
    
    def _creates_circular_dependency(self, task_id: str, new_dependency_id: str) -> bool:
        """Check if adding a dependency would create a circular dependency"""
        visited = set()
        
        def _has_path_to(from_id: str, to_id: str) -> bool:
            if from_id == to_id:
                return True
            if from_id in visited:
                return False
            
            visited.add(from_id)
            task = self.tasks.get(from_id)
            if not task:
                return False
            
            for dep_id in task.dependencies:
                if _has_path_to(dep_id, to_id):
                    return True
            return False
        
        return _has_path_to(new_dependency_id, task_id)
    
    def get_next_task(self) -> Optional[Task]:
        """Get highest priority available task"""
        available_tasks = self._get_available_tasks()
        
        if not available_tasks:
            return None
        
        # Sort by priority (highest first), then by creation time (oldest first)
        available_tasks.sort(key=lambda t: (-t.priority.value, t.created_at))
        return available_tasks[0]
    
    def _get_available_tasks(self) -> List[Task]:
        """Get tasks that are ready to be executed"""
        available = []
        
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            dependencies_met = all(
                self.tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
                if dep_id in self.tasks
            )
            
            if dependencies_met:
                available.append(task)
        
        return available
    
    def mark_completed(self, task_id: str, result: str) -> bool:
        """Mark task as completed and update queue"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.complete_execution(result)
        
        if task_id not in self.completed_tasks:
            self.completed_tasks.append(task_id)
        
        # Remove from failed tasks if it was there
        if task_id in self.failed_tasks:
            self.failed_tasks.remove(task_id)
        
        self._update_execution_order()
        self._save_to_database()
        return True
    
    def mark_failed(self, task_id: str, error_message: str) -> bool:
        """Mark task as failed"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.fail_execution(error_message)
        
        if task_id not in self.failed_tasks:
            self.failed_tasks.append(task_id)
        
        self._save_to_database()
        return True
    
    def retry_failed_task(self, task_id: str) -> bool:
        """Retry a failed task"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if not task.can_retry():
            return False
        
        task.reset_for_retry()
        if task_id in self.failed_tasks:
            self.failed_tasks.remove(task_id)
        
        self._update_execution_order()
        self._save_to_database()
        return True
    
    def reorganize_queue(self, new_tasks: List[Task]) -> List[str]:
        """Dynamic queue restructuring based on new information"""
        added_task_ids = []
        
        for task in new_tasks:
            # Check if task already exists (avoid duplicates)
            existing_task = self._find_similar_task(task)
            if existing_task:
                # Update existing task instead of adding duplicate
                self._update_task(existing_task.id, task)
            else:
                task_id = self.add_task(task)
                added_task_ids.append(task_id)
        
        return added_task_ids
    
    def _find_similar_task(self, task: Task) -> Optional[Task]:
        """Find if a similar task already exists"""
        for existing_task in self.tasks.values():
            if (existing_task.description.lower() == task.description.lower() and
                existing_task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]):
                return existing_task
        return None
    
    def _update_task(self, task_id: str, updated_task: Task):
        """Update an existing task with new information"""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        task.instructions = updated_task.instructions
        task.priority = updated_task.priority
        task.context_requirements = updated_task.context_requirements
        task.metadata.update(updated_task.metadata)
        
        self._update_execution_order()
        self._save_to_database()
    
    def _update_execution_order(self):
        """Update the execution order based on dependencies and priorities"""
        # Topological sort with priority consideration
        self.execution_order = self._topological_sort()
    
    def _topological_sort(self) -> List[str]:
        """Perform topological sort of tasks considering dependencies"""
        in_degree = {task_id: 0 for task_id in self.tasks}
        
        # Calculate in-degrees
        for task in self.tasks.values():
            for dep_id in task.dependencies:
                if dep_id in in_degree:
                    in_degree[task.id] += 1
        
        # Find tasks with no dependencies
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # Sort by priority within the same dependency level
            queue.sort(key=lambda tid: -self.tasks[tid].priority.value)
            current = queue.pop(0)
            result.append(current)
            
            # Update in-degrees for dependent tasks
            for task in self.tasks.values():
                if current in task.dependencies:
                    in_degree[task.id] -= 1
                    if in_degree[task.id] == 0:
                        queue.append(task.id)
        
        return result
    
    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks"""
        return [task for task in self.tasks.values() if task.status == TaskStatus.PENDING]
    
    def get_completed_tasks(self) -> List[Task]:
        """Get all completed tasks"""
        return [task for task in self.tasks.values() if task.status == TaskStatus.COMPLETED]
    
    def get_failed_tasks(self) -> List[Task]:
        """Get all failed tasks"""
        return [task for task in self.tasks.values() if task.status == TaskStatus.FAILED]
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """Get statistics about the task queue"""
        total_tasks = len(self.tasks)
        pending_tasks = len(self.get_pending_tasks())
        completed_tasks = len(self.get_completed_tasks())
        failed_tasks = len(self.get_failed_tasks())
        in_progress_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS])
        
        # Calculate average completion time
        completed = self.get_completed_tasks()
        avg_duration = None
        if completed:
            durations = [t.actual_duration for t in completed if t.actual_duration]
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        return {
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completion_rate': completed_tasks / total_tasks if total_tasks > 0 else 0,
            'average_duration_minutes': avg_duration,
            'available_tasks': len(self._get_available_tasks())
        }
    
    def export_queue_data(self) -> Dict[str, Any]:
        """Export queue data for visualization or analysis"""
        return {
            'tasks': {task_id: task.to_dict() for task_id, task in self.tasks.items()},
            'execution_order': self.execution_order,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'statistics': self.get_queue_statistics()
        }
    
    def clear_completed_tasks(self):
        """Remove completed tasks from the queue (keeps them in database)"""
        completed_ids = [task.id for task in self.get_completed_tasks()]
        for task_id in completed_ids:
            if task_id in self.tasks:
                del self.tasks[task_id]
            if task_id in self.execution_order:
                self.execution_order.remove(task_id)
        
        self._save_to_database()
    
    def _save_to_database(self):
        """Save current queue state to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute('DELETE FROM tasks')
        cursor.execute('DELETE FROM queue_metadata')
        
        # Save tasks
        for task_id, task in self.tasks.items():
            cursor.execute(
                'INSERT INTO tasks (id, data) VALUES (?, ?)',
                (task_id, json.dumps(task.to_dict()))
            )
        
        # Save metadata
        metadata = {
            'execution_order': self.execution_order,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks
        }
        cursor.execute(
            'INSERT INTO queue_metadata (key, value) VALUES (?, ?)',
            ('queue_data', json.dumps(metadata))
        )
        
        conn.commit()
        conn.close()
    
    def load_from_database(self):
        """Load queue state from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Load tasks
            cursor.execute('SELECT id, data FROM tasks')
            rows = cursor.fetchall()
            
            self.tasks = {}
            for task_id, data_json in rows:
                task_data = json.loads(data_json)
                self.tasks[task_id] = Task.from_dict(task_data)
            
            # Load metadata
            cursor.execute('SELECT value FROM queue_metadata WHERE key = ?', ('queue_data',))
            metadata_result = cursor.fetchone()
            if metadata_result:
                metadata = json.loads(metadata_result[0])
                self.execution_order = metadata.get('execution_order', [])
                self.completed_tasks = metadata.get('completed_tasks', [])
                self.failed_tasks = metadata.get('failed_tasks', [])
            
        except sqlite3.OperationalError:
            # Database doesn't exist yet or is empty
            pass
        
        conn.close()


# Utility functions for task creation
def create_investigation_task(description: str, instructions: str, priority: TaskPriority = TaskPriority.MEDIUM) -> Task:
    """Create a task for investigation work"""
    task = Task(description, instructions, priority)
    task.context_requirements = ["memory_tree_access", "investigation_tools"]
    return task


def create_analysis_task(description: str, instructions: str, data_source: str) -> Task:
    """Create a task for data analysis"""
    task = Task(description, instructions, TaskPriority.HIGH)
    task.context_requirements = ["memory_tree_access", "analysis_tools"]
    task.metadata["data_source"] = data_source
    return task


def create_synthesis_task(description: str, instructions: str, dependencies: List[str]) -> Task:
    """Create a task for synthesizing results from multiple sources"""
    task = Task(description, instructions, TaskPriority.MEDIUM)
    task.dependencies = dependencies
    task.context_requirements = ["memory_tree_access", "synthesis_tools"]
    return task


# Example usage and testing
if __name__ == "__main__":
    # Create a test task queue
    queue = TaskQueue("test_queue.db")
    
    # Create some test tasks
    task1 = create_investigation_task(
        "Analyze crime scene photos",
        "Examine all photos for evidence, anomalies, and clues",
        TaskPriority.HIGH
    )
    
    task2 = create_investigation_task(
        "Interview witness statements",
        "Review all witness statements for consistency and new leads",
        TaskPriority.MEDIUM
    )
    
    task3 = create_synthesis_task(
        "Cross-reference evidence",
        "Compare physical evidence with witness statements",
        []
    )
    
    # Add tasks to queue
    queue.add_task(task1)
    queue.add_task(task2)
    task3_id = queue.add_task(task3)
    
    # Add dependencies
    queue.add_dependency(task3_id, task1.id)
    queue.add_dependency(task3_id, task2.id)
    
    # Test queue operations
    print("Queue Statistics:")
    print(json.dumps(queue.get_queue_statistics(), indent=2))
    
    print("\nNext task to execute:")
    next_task = queue.get_next_task()
    if next_task:
        print(f"- {next_task.description} (Priority: {next_task.priority.name})")
    
    print("\nExecution order:")
    for i, task_id in enumerate(queue.execution_order):
        task = queue.tasks[task_id]
        print(f"{i+1}. {task.description}")
    
    # Simulate task completion
    if next_task:
        queue.mark_completed(next_task.id, "Crime scene analysis completed. Found suspicious footprint.")
        print(f"\nCompleted task: {next_task.description}")
        print("Updated statistics:")
        print(json.dumps(queue.get_queue_statistics(), indent=2)) 