#!/usr/bin/env python3
"""
FastAPI server for AI Agent Memory Tree System
Serves tree data and statistics to the frontend visualization
"""

import os
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import json
import asyncio

# Add backend to path for imports
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tree import MemoryTree, MemoryNode, NodeStatus
from tasklist import TaskQueue
from gemini_client import GeminiClient

app = FastAPI(
    title="AI Agent Memory Tree API",
    description="API for serving memory tree visualization data",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
memory_tree: Optional[MemoryTree] = None
task_queue: Optional[TaskQueue] = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                await websocket.send_text(message)
        except Exception as e:
            print(f"Failed to send message to WebSocket: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Failed to broadcast to connection: {e}")
                disconnected.append(connection)
        
        # Remove broken connections
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

def initialize_system():
    """Initialize the memory tree and task queue"""
    global memory_tree, task_queue
    
    try:
        # Ensure db directory exists
        os.makedirs("db", exist_ok=True)
        
        # Find the most recent database files
        db_files = []
        if os.path.exists("db"):
            for filename in os.listdir("db"):
                if filename.startswith("investigation_") and filename.endswith(".db"):
                    db_files.append(filename)
        
        if db_files:
            # Use the most recent investigation database
            latest_db = sorted(db_files)[-1]
            db_path = f"db/{latest_db}"
            print(f"📊 Loading database: {db_path}")
            memory_tree = MemoryTree(db_path)
            
            # Find corresponding task queue
            timestamp = latest_db.replace("investigation_", "").replace(".db", "")
            task_db = f"db/tasks_{timestamp}.db"
            if os.path.exists(task_db):
                task_queue = TaskQueue(task_db)
                print(f"📋 Loading task queue: {task_db}")
            else:
                task_queue = TaskQueue("db/task_queue.db")  # fallback
                print("📋 Using fallback task queue")
        else:
            # Create new instances with default paths
            print("🆕 Creating new memory tree and task queue")
            memory_tree = MemoryTree("db/memory_tree.db")
            task_queue = TaskQueue("db/task_queue.db")
            
        # Verify the tree has data
        if memory_tree and hasattr(memory_tree, 'root_id') and memory_tree.root_id:
            root_node = memory_tree.get_node(memory_tree.root_id)
            if root_node:
                print(f"✅ Memory tree loaded with root: {root_node.name}")
            else:
                print("⚠️ Memory tree has root_id but no root node found")
        else:
            print("⚠️ Memory tree has no root_id")
            
    except Exception as e:
        print(f"❌ Error initializing system: {e}")
        # Create minimal fallback instances
        memory_tree = None
        task_queue = None

def convert_node_to_dict(node: MemoryNode, include_children: bool = True) -> Dict[str, Any]:
    """Convert a MemoryNode to a dictionary for JSON serialization"""
    return {
        "id": node.id,
        "name": node.name,
        "description": node.description,
        "status": node.status.value if hasattr(node.status, 'value') else str(node.status),
        "created_at": node.created_at.isoformat() if hasattr(node.created_at, 'isoformat') else str(node.created_at),
        "children": [
            convert_node_to_dict(memory_tree.get_node(child_id), include_children=True) 
            for child_id in node.children_ids 
            if memory_tree.get_node(child_id)
        ] if include_children else []
    }

@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup"""
    try:
        initialize_system()
        print("✅ API server initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing API server: {e}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "AI Agent Memory Tree API", "status": "running"}

@app.get("/test")
async def test():
    """Simple test endpoint"""
    return {
        "message": "API is working", 
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(manager.active_connections)
    }

@app.get("/api/tree")
async def get_tree():
    """Get the complete memory tree"""
    try:
        if not memory_tree or not memory_tree.root_id:
            return JSONResponse(
                status_code=200,
                content={
                    "data": None,
                    "message": "No tree data available"
                }
            )
        
        root_node = memory_tree.get_node(memory_tree.root_id)
        if not root_node:
            return JSONResponse(
                status_code=200,
                content={
                    "data": None,
                    "message": "Root node not found"
                }
            )
        
        tree_data = convert_node_to_dict(root_node)
        
        return JSONResponse(
            status_code=200,
            content={
                "data": tree_data,
                "message": "Tree data retrieved successfully"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tree: {str(e)}")

@app.get("/api/tree/stats")
async def get_tree_stats():
    """Get tree statistics"""
    try:
        if not memory_tree:
            return JSONResponse(
                status_code=200,
                content={
                    "data": {
                        "total_nodes": 0,
                        "max_depth": 0,
                        "nodes_by_status": {}
                    },
                    "message": "No tree data available"
                }
            )
        
        stats = memory_tree.get_tree_statistics()
        
        # Also get task queue stats if available
        task_stats = {}
        if task_queue:
            task_stats = task_queue.get_queue_statistics()
        
        return JSONResponse(
            status_code=200,
            content={
                "data": {
                    **stats,
                    "task_stats": task_stats
                },
                "message": "Statistics retrieved successfully"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(e)}")

@app.get("/api/tree/node/{node_id}")
async def get_node(node_id: str):
    """Get details for a specific node"""
    try:
        if not memory_tree:
            raise HTTPException(status_code=404, detail="Memory tree not available")
        
        node = memory_tree.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        node_data = convert_node_to_dict(node, include_children=False)
        
        # Add additional context
        siblings = memory_tree.get_siblings(node_id)
        path_to_root = memory_tree.get_path_to_root(node_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "data": {
                    **node_data,
                    "siblings_count": len(siblings),
                    "depth_from_root": len(path_to_root) - 1,
                    "has_children": len(node.children_ids) > 0
                },
                "message": "Node details retrieved successfully"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving node: {str(e)}")

@app.get("/api/tasks")
async def get_tasks():
    """Get task queue information"""
    try:
        if not task_queue:
            return JSONResponse(
                status_code=200,
                content={
                    "data": {
                        "pending": [],
                        "completed": [],
                        "failed": [],
                        "stats": {}
                    },
                    "message": "No task queue available"
                }
            )
        
        pending_tasks = [task.to_dict() for task in task_queue.get_pending_tasks()]
        completed_tasks = [task.to_dict() for task in task_queue.get_completed_tasks()]
        failed_tasks = [task.to_dict() for task in task_queue.get_failed_tasks()]
        stats = task_queue.get_queue_statistics()
        
        return JSONResponse(
            status_code=200,
            content={
                "data": {
                    "pending": pending_tasks,
                    "completed": completed_tasks[-10:],  # Last 10 completed
                    "failed": failed_tasks,
                    "stats": stats
                },
                "message": "Task data retrieved successfully"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tasks: {str(e)}")

@app.post("/api/refresh")
async def refresh_data():
    """Refresh/reload the tree and task data"""
    try:
        initialize_system()
        return JSONResponse(
            status_code=200,
            content={
                "message": "Data refreshed successfully",
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing data: {str(e)}")

@app.get("/api/status")
async def get_system_status():
    """Get overall system status"""
    try:
        status = {
            "api_status": "running",
            "memory_tree_loaded": memory_tree is not None,
            "task_queue_loaded": task_queue is not None,
            "timestamp": datetime.now().isoformat()
        }
        
        if memory_tree:
            status["tree_stats"] = memory_tree.get_tree_statistics()
        
        if task_queue:
            status["task_stats"] = task_queue.get_queue_statistics()
        
        return JSONResponse(
            status_code=200,
            content={
                "data": status,
                "message": "System status retrieved successfully"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving status: {str(e)}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        # Send initial connection confirmation
        initial_message = {
            "type": "connection_status",
            "data": {
                "status": "connected",
                "timestamp": datetime.now().isoformat(),
                "message": "WebSocket connection established"
            }
        }
        await manager.send_personal_message(json.dumps(initial_message), websocket)
        
        # Send real data every 5 seconds
        while websocket in manager.active_connections:
            try:
                await asyncio.sleep(5)
                
                # Double-check connection is still active
                if websocket not in manager.active_connections:
                    print("WebSocket no longer in active connections, exiting loop")
                    break
                
                print(f"📡 Preparing real-time update (active connections: {len(manager.active_connections)})")
                
                # Get real tree and stats data
                tree_data = None
                stats_data = {
                    "total_nodes": 0,
                    "max_depth": 0,
                    "nodes_by_status": {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0}
                }
                
                if memory_tree and hasattr(memory_tree, 'root_id') and memory_tree.root_id:
                    try:
                        print(f"🌳 Getting root node: {memory_tree.root_id}")
                        root_node = memory_tree.get_node(memory_tree.root_id)
                        if root_node:
                            print(f"✅ Converting tree data for node: {root_node.name}")
                            tree_data = convert_node_to_dict(root_node)
                            stats_data = memory_tree.get_tree_statistics()
                            print(f"📊 Tree stats: {stats_data}")
                            
                            # Include task stats if available
                            if task_queue and hasattr(task_queue, 'get_queue_statistics'):
                                task_stats = task_queue.get_queue_statistics()
                                stats_data["task_stats"] = task_stats
                                print(f"📋 Task stats: {task_stats}")
                        else:
                            print("⚠️ Root node not found")
                    except Exception as e:
                        print(f"❌ Error getting tree data: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("⚠️ No memory tree or root_id available")
                
                # Send update with real data
                update_message = {
                    "type": "tree_update", 
                    "data": {
                        "tree": tree_data,
                        "stats": stats_data,
                        "timestamp": datetime.now().isoformat(),
                        "source": "real_database" if tree_data else "empty_database"
                    }
                }
                
                await manager.send_personal_message(json.dumps(update_message), websocket)
                print(f"✅ WebSocket update sent successfully (tree_data: {'present' if tree_data else 'none'})")
                
            except Exception as e:
                print(f"❌ WebSocket update loop error: {e}")
                import traceback
                traceback.print_exc()
                break
            
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

async def broadcast_tree_update():
    """Broadcast tree updates to all connected clients"""
    if not memory_tree or not memory_tree.root_id:
        return
        
    root_node = memory_tree.get_node(memory_tree.root_id)
    if not root_node:
        return
        
    tree_data = convert_node_to_dict(root_node)
    stats_data = memory_tree.get_tree_statistics()
    
    if task_queue:
        stats_data["task_stats"] = task_queue.get_queue_statistics()
    
    update_message = {
        "type": "tree_update",
        "data": {
            "tree": tree_data,
            "stats": stats_data,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    await manager.broadcast(json.dumps(update_message))

if __name__ == "__main__":
    print("🚀 Starting AI Agent Memory Tree API Server...")
    print("📊 API Documentation: http://localhost:8000/docs")
    print("🌳 Tree Endpoint: http://localhost:8000/api/tree")
    print("📈 Stats Endpoint: http://localhost:8000/api/tree/stats")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 