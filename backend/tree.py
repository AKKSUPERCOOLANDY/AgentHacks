import json
import sqlite3
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4
from pathlib import Path


class NodeStatus(Enum):
    """Status of a memory node"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class MemoryNode:
    """Individual node in the memory tree"""
    
    def __init__(self, name: str, description: str = ""):
        self.id: str = str(uuid4())
        self.name: str = name
        self.description: str = description
        self.parent_id: Optional[str] = None
        self.children_ids: List[str] = []
        self.created_at: datetime = datetime.now()
        self.metadata: Dict[str, Any] = {}
        self.status: NodeStatus = NodeStatus.PENDING
        self.execution_result: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
            'children_ids': self.children_ids,
            'created_at': self.created_at.isoformat(),
            'metadata': self.metadata,
            'status': self.status.value,
            'execution_result': self.execution_result
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryNode':
        """Create node from dictionary"""
        node = cls(data['name'], data['description'])
        node.id = data['id']
        node.parent_id = data['parent_id']
        node.children_ids = data['children_ids']
        node.created_at = datetime.fromisoformat(data['created_at'])
        node.metadata = data['metadata']
        node.status = NodeStatus(data['status'])
        node.execution_result = data['execution_result']
        return node


class MemoryTree:
    """Tree-based memory structure for AI agents"""
    
    def __init__(self, db_path: str = "db/memory_tree.db"):
        self.nodes: Dict[str, MemoryNode] = {}
        self.root_id: Optional[str] = None
        self.db_path = db_path
        self._init_database()
        self.load_from_database()
    
    def _init_database(self):
        """Initialize SQLite database for persistence"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tree_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    # Core Operations
    def add_node(self, node: MemoryNode, parent_id: Optional[str] = None) -> str:
        """Add a node to the tree"""
        if parent_id and parent_id not in self.nodes:
            raise ValueError(f"Parent node {parent_id} not found")
        
        # Set parent-child relationships
        if parent_id:
            node.parent_id = parent_id
            self.nodes[parent_id].children_ids.append(node.id)
        else:
            # This is a root node
            if self.root_id is None:
                self.root_id = node.id
        
        self.nodes[node.id] = node
        self._save_to_database()
        return node.id
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its children"""
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        
        # Remove all children recursively
        for child_id in node.children_ids[:]:  # Copy list to avoid modification during iteration
            self.remove_node(child_id)
        
        # Remove from parent's children list
        if node.parent_id and node.parent_id in self.nodes:
            self.nodes[node.parent_id].children_ids.remove(node.id)
        
        # Update root if necessary
        if self.root_id == node_id:
            self.root_id = None
        
        del self.nodes[node_id]
        self._save_to_database()
        return True
    
    def update_node(self, node_id: str, **kwargs) -> bool:
        """Update node properties"""
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)
        
        self._save_to_database()
        return True
    
    def get_node(self, node_id: str) -> Optional[MemoryNode]:
        """Get a specific node by ID"""
        return self.nodes.get(node_id)
    
    # View Generation
    def get_subtree(self, node_id: str, depth: int = 3) -> Dict:
        """Get subtree from a specific node with limited depth"""
        if node_id not in self.nodes:
            return {}
        
        def _build_subtree(current_id: str, current_depth: int) -> Dict:
            if current_depth <= 0:
                return {}
            
            node = self.nodes[current_id]
            result = {
                'id': node.id,
                'name': node.name,
                'description': node.description,
                'status': node.status.value,
                'children': {}
            }
            
            for child_id in node.children_ids:
                result['children'][child_id] = _build_subtree(child_id, current_depth - 1)
            
            return result
        
        return _build_subtree(node_id, depth)
    
    def get_siblings(self, node_id: str) -> List[MemoryNode]:
        """Get all sibling nodes (same parent)"""
        if node_id not in self.nodes:
            return []
        
        node = self.nodes[node_id]
        if not node.parent_id:
            return []  # Root node has no siblings
        
        parent = self.nodes[node.parent_id]
        siblings = []
        for child_id in parent.children_ids:
            if child_id != node_id:
                siblings.append(self.nodes[child_id])
        
        return siblings
    
    def get_path_to_root(self, node_id: str) -> List[MemoryNode]:
        """Get path from node to root"""
        if node_id not in self.nodes:
            return []
        
        path = []
        current_id = node_id
        
        while current_id:
            node = self.nodes[current_id]
            path.append(node)
            current_id = node.parent_id
        
        return path
    
    def get_leaves(self) -> List[MemoryNode]:
        """Get all leaf nodes (nodes with no children)"""
        leaves = []
        for node in self.nodes.values():
            if not node.children_ids:
                leaves.append(node)
        return leaves
    
    # Analysis
    def find_nodes_by_keyword(self, keyword: str) -> List[MemoryNode]:
        """Find nodes containing keyword in name or description"""
        keyword_lower = keyword.lower()
        matching_nodes = []
        
        for node in self.nodes.values():
            if (keyword_lower in node.name.lower() or 
                keyword_lower in node.description.lower()):
                matching_nodes.append(node)
        
        return matching_nodes
    
    def get_tree_statistics(self) -> Dict[str, Any]:
        """Get comprehensive tree statistics for connected tree nodes only"""
        # Get only connected nodes (nodes reachable from root)
        connected_nodes = self._get_connected_nodes()
        
        stats = {
            'total_nodes': len(connected_nodes),
            'root_children': len(self._get_children(self.root_id)) if self.root_id else 0,
            'max_depth': self._calculate_max_depth(),
            'nodes_by_status': self._count_connected_nodes_by_status(connected_nodes),
            'average_children': self._calculate_average_children_connected(connected_nodes),
            'leaf_nodes': len([n for n in connected_nodes if not self._get_children(n.id)])
        }
        return stats
    
    def _get_connected_nodes(self) -> List[MemoryNode]:
        """Get all nodes connected to the tree (reachable from root)"""
        if not self.root_id or self.root_id not in self.nodes:
            return []
        
        connected = []
        visited = set()
        
        def traverse(node_id: str):
            if node_id in visited or node_id not in self.nodes:
                return
            
            visited.add(node_id)
            connected.append(self.nodes[node_id])
            
            # Traverse children
            for child_id in self.nodes[node_id].children_ids:
                traverse(child_id)
        
        traverse(self.root_id)
        return connected
    
    def _count_connected_nodes_by_status(self, connected_nodes: List[MemoryNode]) -> Dict[str, int]:
        """Count connected nodes by their status"""
        status_counts = {}
        for node in connected_nodes:
            status = node.status.value if hasattr(node.status, 'value') else str(node.status)
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts
    
    def _calculate_average_children_connected(self, connected_nodes: List[MemoryNode]) -> float:
        """Calculate average number of children per connected node"""
        if not connected_nodes:
            return 0.0
        
        total_children = sum(len(self._get_children(node.id)) for node in connected_nodes)
        return total_children / len(connected_nodes)
    
    def _calculate_max_depth(self) -> int:
        """Calculate the maximum depth of the tree"""
        if not self.nodes:
            return 0
        
        def get_depth(node_id: str, visited: set = None) -> int:
            if visited is None:
                visited = set()
            
            if node_id in visited:
                return 0  # Avoid infinite loops
            
            visited.add(node_id)
            node = self.nodes.get(node_id)
            if not node:
                return 0
            
            children = self._get_children(node_id)
            if not children:
                return 1
            
            max_child_depth = max(get_depth(child.id, visited.copy()) for child in children)
            return 1 + max_child_depth
        
        # Find root nodes and calculate depth from each
        root_nodes = [n for n in self.nodes.values() if n.parent_id is None]
        if not root_nodes:
            return 1
        
        return max(get_depth(root.id) for root in root_nodes)
    
    def _count_nodes_by_status(self) -> Dict[str, int]:
        """Count nodes by their status"""
        status_counts = {}
        for node in self.nodes.values():
            status = node.status.value if hasattr(node.status, 'value') else str(node.status)
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts
    
    def _calculate_average_children(self) -> float:
        """Calculate average number of children per node"""
        if not self.nodes:
            return 0.0
        
        total_children = sum(len(self._get_children(node.id)) for node in self.nodes.values())
        return total_children / len(self.nodes)
    
    def _get_children(self, node_id: str) -> List[MemoryNode]:
        """Get all child nodes of a given node"""
        if node_id not in self.nodes:
            return []
        
        node = self.nodes[node_id]
        children = []
        for child_id in node.children_ids:
            if child_id in self.nodes:
                children.append(self.nodes[child_id])
        
        return children
    
    def export_visualization_data(self) -> Dict:
        """Export tree data for visualization"""
        if not self.root_id:
            return {}
        
        def _build_viz_node(node_id: str) -> Dict:
            node = self.nodes[node_id]
            children = [_build_viz_node(child_id) for child_id in node.children_ids]
            
            return {
                'id': node.id,
                'name': node.name,
                'description': node.description[:100] + "..." if len(node.description) > 100 else node.description,
                'status': node.status.value,
                'created_at': node.created_at.isoformat(),
                'children': children
            }
        
        return _build_viz_node(self.root_id)
    
    # String Serialization
    def serialize_tree(self) -> str:
        """Convert tree to hierarchical string format for AI consumption"""
        if not self.root_id:
            return "Empty tree"
        
        return self._recursive_serialize(self.root_id, indent=0)
    
    def _recursive_serialize(self, node_id: str, indent: int) -> str:
        """Recursively serialize tree nodes"""
        node = self.nodes[node_id]
        prefix = "  " * indent
        status_symbol = self._get_status_symbol(node.status)
        result = f"{prefix}{status_symbol}[{node.name}]: {node.description}\n"
        
        for child_id in node.children_ids:
            result += self._recursive_serialize(child_id, indent + 1)
        
        return result
    
    def _get_status_symbol(self, status: NodeStatus) -> str:
        """Get visual symbol for node status"""
        symbols = {
            NodeStatus.PENDING: "⏳",
            NodeStatus.IN_PROGRESS: "🔄",
            NodeStatus.COMPLETED: "✅",
            NodeStatus.FAILED: "❌"
        }
        return symbols.get(status, "❓")
    
    def get_current_view(self, max_depth: int = 5) -> str:
        """Get a current view of the tree for AI agents"""
        if not self.root_id:
            return "No memory tree exists yet."
        
        header = f"Memory Tree Overview (Total nodes: {len(self.nodes)})\n"
        header += "=" * 50 + "\n"
        
        tree_string = self.serialize_tree()
        
        # Limit depth if tree is too large
        lines = tree_string.split('\n')
        filtered_lines = []
        for line in lines:
            depth = (len(line) - len(line.lstrip())) // 2
            if depth <= max_depth:
                filtered_lines.append(line)
        
        return header + '\n'.join(filtered_lines)
    
    # Persistence
    def save_to_json(self, filepath: str):
        """Save tree to JSON file"""
        tree_data = {
            'root_id': self.root_id,
            'nodes': {node_id: node.to_dict() for node_id, node in self.nodes.items()}
        }
        
        with open(filepath, 'w') as f:
            json.dump(tree_data, f, indent=2)
    
    def load_from_json(self, filepath: str):
        """Load tree from JSON file"""
        if not Path(filepath).exists():
            return
        
        with open(filepath, 'r') as f:
            tree_data = json.load(f)
        
        self.root_id = tree_data.get('root_id')
        self.nodes = {}
        
        for node_id, node_data in tree_data.get('nodes', {}).items():
            self.nodes[node_id] = MemoryNode.from_dict(node_data)
    
    def _save_to_database(self):
        """Save current tree state to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute('DELETE FROM nodes')
        cursor.execute('DELETE FROM tree_metadata')
        
        # Save nodes
        for node_id, node in self.nodes.items():
            cursor.execute(
                'INSERT INTO nodes (id, data) VALUES (?, ?)',
                (node_id, json.dumps(node.to_dict()))
            )
        
        # Save metadata
        cursor.execute(
            'INSERT INTO tree_metadata (key, value) VALUES (?, ?)',
            ('root_id', self.root_id or '')
        )
        
        conn.commit()
        conn.close()
    
    def load_from_database(self):
        """Load tree state from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Load nodes
            cursor.execute('SELECT id, data FROM nodes')
            rows = cursor.fetchall()
            
            self.nodes = {}
            for node_id, data_json in rows:
                node_data = json.loads(data_json)
                self.nodes[node_id] = MemoryNode.from_dict(node_data)
            
            # Load metadata
            cursor.execute('SELECT value FROM tree_metadata WHERE key = ?', ('root_id',))
            root_result = cursor.fetchone()
            self.root_id = root_result[0] if root_result and root_result[0] else None
            
        except sqlite3.OperationalError:
            # Database doesn't exist yet or is empty
            pass
        
        conn.close()

    def get_recent_nodes(self, limit: int = 10) -> List[MemoryNode]:
        """Get the most recently created nodes"""
        # Sort nodes by creation time (using node ID as proxy since it's UUID-based)
        sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.created_at if hasattr(n, 'created_at') else n.id, reverse=True)
        return sorted_nodes[:limit]


# Utility functions for easy tree creation
def create_root_node(name: str, description: str = "") -> MemoryNode:
    """Create a root node for a new tree"""
    return MemoryNode(name, description)


def create_detective_case_tree(case_name: str) -> MemoryTree:
    """Create a pre-structured tree for detective cases"""
    tree = MemoryTree()
    
    # Create root node
    root = create_root_node(case_name, f"Investigation of {case_name}")
    tree.add_node(root)
    
    # Create main investigation branches
    evidence_node = MemoryNode("Evidence Analysis", "Analysis of all physical and digital evidence")
    witness_node = MemoryNode("Witness Statements", "Collection and analysis of witness testimonies")
    timeline_node = MemoryNode("Timeline Construction", "Building chronological sequence of events")
    suspects_node = MemoryNode("Suspect Analysis", "Investigation of potential suspects")
    
    tree.add_node(evidence_node, root.id)
    tree.add_node(witness_node, root.id)
    tree.add_node(timeline_node, root.id)
    tree.add_node(suspects_node, root.id)
    
    return tree


# Example usage and testing
if __name__ == "__main__":
    # Create a test tree
    tree = MemoryTree("db/test_tree.db")
    
    # Add root node
    root = create_root_node("Test Investigation", "Testing the memory tree system")
    tree.add_node(root)
    
    # Add some child nodes
    child1 = MemoryNode("Evidence Collection", "Gather all available evidence")
    child2 = MemoryNode("Witness Interviews", "Interview all potential witnesses")
    
    tree.add_node(child1, root.id)
    tree.add_node(child2, root.id)
    
    # Add grandchild
    grandchild = MemoryNode("Physical Evidence", "Analyze physical evidence from crime scene")
    tree.add_node(grandchild, child1.id)
    
    # Test operations
    print("Tree Structure:")
    print(tree.serialize_tree())
    
    print("\nTree Statistics:")
    print(tree.get_tree_statistics())
    
    print("\nVisualization Data:")
    print(json.dumps(tree.export_visualization_data(), indent=2)) 