#!/usr/bin/env python3
"""
FastAPI server for AI Agent Memory Tree System
Serves tree data and statistics to the frontend visualization
"""

import os
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import json
import asyncio
import logging
import time
from pathlib import Path
import shutil

# Add backend to path for imports
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tree import MemoryTree, MemoryNode, NodeStatus
from tasklist import TaskQueue
from gemini_client import GeminiClient
from main_document_analysis import DocumentAnalysisSystem

class AnalysisRequest(BaseModel):
    selected_files: List[str] = []

app = FastAPI(
    title="AI Agent Memory Tree API",
    description="API for serving memory tree visualization data",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Fixed ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
memory_tree: Optional[MemoryTree] = None
task_queue: Optional[TaskQueue] = None
current_db_path: Optional[str] = None
auto_refresh_task: Optional[asyncio.Task] = None

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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_analysis_summary(analysis_results, final_conclusion, analysis_system):
    """Generate a comprehensive analysis summary for display"""
    try:
        # Get document analyzer summary
        doc_analyzer = analysis_system.document_analyzer if analysis_system else None
        doc_summary = doc_analyzer.get_document_summary() if doc_analyzer else {}
        
        # Get memory tree statistics
        tree_stats = analysis_system.memory_tree.get_tree_statistics() if analysis_system and analysis_system.memory_tree else {}
        
        # Get task queue statistics  
        queue_stats = analysis_system.task_queue.get_queue_statistics() if analysis_system and analysis_system.task_queue else {}
        
        # Extract key findings from analysis results
        key_findings = []
        evidence_found = []
        
        for result in analysis_results or []:
            if hasattr(result, 'result') and result.result:
                # Extract key points from result
                result_text = str(result.result)
                if len(result_text) > 100:
                    key_findings.append(result_text[:200] + "...")
                else:
                    key_findings.append(result_text)
        
        # Get recent nodes from memory tree for evidence summary
        if analysis_system and analysis_system.memory_tree:
            recent_nodes = analysis_system.memory_tree.get_recent_nodes(limit=10)
            for node in recent_nodes:
                if hasattr(node, 'name') and hasattr(node, 'description'):
                    if any(keyword in node.name.lower() for keyword in ['evidence', 'finding', 'analysis']):
                        evidence_found.append({
                            "type": node.name,
                            "description": node.description[:150] + "..." if len(node.description) > 150 else node.description
                        })
        
        summary = {
            "case_overview": {
                "files_analyzed": doc_summary.get('total_documents', 0),
                "document_types": doc_summary.get('document_types', []),
                "total_characters": doc_summary.get('total_characters', 0)
            },
            "analysis_metrics": {
                "total_nodes_created": tree_stats.get('total_nodes', 0),
                "analysis_depth": tree_stats.get('max_depth', 0),
                "tasks_completed": queue_stats.get('completed_tasks', 0),
                "tasks_failed": queue_stats.get('failed_tasks', 0)
            },
            "key_findings": key_findings[:5],  # Top 5 findings
            "evidence_summary": evidence_found[:5],  # Top 5 evidence items
            "conclusion": final_conclusion or "Analysis completed successfully",
            "case_status": "Analysis Complete - Ready for Review"
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating analysis summary: {e}")
        return {
            "case_overview": {"files_analyzed": 0, "document_types": [], "total_characters": 0},
            "analysis_metrics": {"total_nodes_created": 0, "analysis_depth": 0, "tasks_completed": 0, "tasks_failed": 0},
            "key_findings": [],
            "evidence_summary": [],
            "conclusion": "Analysis completed with limited summary data available",
            "case_status": "Analysis Complete"
        }

def get_newest_database() -> Optional[str]:
    """Find the newest investigation database"""
    try:
        if not os.path.exists("db"):
            return None
            
        db_files = []
        for filename in os.listdir("db"):
            if filename.startswith("investigation_") and filename.endswith(".db"):
                filepath = os.path.join("db", filename)
                mtime = os.path.getmtime(filepath)
                db_files.append((filename, mtime))
        
        if not db_files:
            return None
            
        # Sort by modification time and get the newest
        latest_db = sorted(db_files, key=lambda x: x[1])[-1][0]
        return f"db/{latest_db}"
        
    except Exception as e:
        logger.error(f"Error finding newest database: {e}")
        return None

async def auto_refresh_checker():
    """Background task that checks for newer databases and auto-refreshes"""
    global current_db_path, memory_tree
    last_db_mtime = None
    
    while True:
        try:
            await asyncio.sleep(3)  # Check every 3 seconds for faster detection
            
            # Check if current database has been modified (new nodes added)
            if current_db_path and os.path.exists(current_db_path):
                current_mtime = os.path.getmtime(current_db_path)
                if last_db_mtime is None:
                    last_db_mtime = current_mtime
                elif current_mtime > last_db_mtime:
                    logger.info(f"🔄 Current database {current_db_path} has been updated, reloading...")
                    last_db_mtime = current_mtime
                    
                    # Reload the current database to pick up new nodes
                    if memory_tree:
                        memory_tree.load_from_database()
                        logger.info(f"✅ Reloaded tree with {len(memory_tree.nodes)} nodes")
                        
                        # Broadcast update to all connected clients
                        if manager.active_connections:
                            await broadcast_tree_update()
            
            newest_db = get_newest_database()
            if newest_db and newest_db != current_db_path:
                # Check if database is at least 2 seconds old (to ensure it's populated)
                db_age = time.time() - os.path.getmtime(newest_db)
                if db_age < 2:
                    logger.info(f"🕐 Database {newest_db} is too new ({db_age:.1f}s), waiting...")
                    continue
                
                # Test if the database has actual data
                try:
                    from tree import MemoryTree as TestTree
                    test_tree = TestTree(newest_db)
                    if not test_tree.root_id:
                        logger.info(f"📭 Database {newest_db} has no root data, skipping")
                        continue
                    
                    logger.info(f"🔄 Auto-refresh: Switching to populated database {newest_db}")
                    old_db = current_db_path
                    initialize_system()
                    
                    if current_db_path != old_db:
                        logger.info(f"✅ Successfully switched from {old_db} to {current_db_path}")
                        
                        # Reset modification time tracking for new database
                        last_db_mtime = os.path.getmtime(current_db_path) if os.path.exists(current_db_path) else None
                        
                        # Broadcast update to all connected clients
                        if manager.active_connections:
                            await manager.broadcast(json.dumps({
                                "type": "database_refresh",
                                "message": f"Switched to newer database: {newest_db}",
                                "old_db": old_db,
                                "new_db": current_db_path
                            }))
                            
                            # Send immediate tree update
                            await broadcast_tree_update()
                    else:
                        logger.info(f"🔄 Already using the newest database: {current_db_path}")
                        
                except Exception as e:
                    logger.error(f"❌ Error testing database {newest_db}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in auto-refresh checker: {e}")
            await asyncio.sleep(10)

def initialize_system():
    """Initialize the memory tree and task queue"""
    global memory_tree, task_queue, current_db_path
    
    try:
        logger.info(f"🔄 Initializing system (current_db: {current_db_path})")
        # Ensure db directory exists
        os.makedirs("db", exist_ok=True)
        
        # Find the most recent database files
        newest_db = get_newest_database()
        
        if newest_db:
            # Use the most recent investigation database
            current_db_path = newest_db
            logger.info(f"📊 Loading database: {current_db_path}")
            memory_tree = MemoryTree(current_db_path)
            
            # Find corresponding task queue
            filename = os.path.basename(current_db_path)
            timestamp = filename.replace("investigation_", "").replace(".db", "")
            task_db = f"db/tasks_{timestamp}.db"
            if os.path.exists(task_db):
                task_queue = TaskQueue(task_db)
                logger.info(f"📋 Loading task queue: {task_db}")
            else:
                task_queue = TaskQueue("db/task_queue.db")  # fallback
                logger.info("📋 Using fallback task queue")
        else:
            # Create new instances with default paths
            logger.info("🆕 Creating new memory tree and task queue")
            current_db_path = "db/memory_tree.db"
            memory_tree = MemoryTree(current_db_path)
            task_queue = TaskQueue("db/task_queue.db")
            
        # Verify the tree has data
        if memory_tree and hasattr(memory_tree, 'root_id') and memory_tree.root_id:
            root_node = memory_tree.get_node(memory_tree.root_id)
            if root_node:
                logger.info(f"✅ Memory tree loaded with root: {root_node.name}")
            else:
                logger.warning("⚠️ Memory tree has root_id but no root node found")
        else:
            logger.warning("⚠️ Memory tree has no root_id")
            
    except Exception as e:
        logger.error(f"❌ Error initializing system: {e}")
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
    global auto_refresh_task
    try:
        initialize_system()
        
        # Start auto-refresh background task
        auto_refresh_task = asyncio.create_task(auto_refresh_checker())
        print("🔄 Auto-refresh task started")
        
        print("✅ API server initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing API server: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global auto_refresh_task
    if auto_refresh_task:
        auto_refresh_task.cancel()
        try:
            await auto_refresh_task
        except asyncio.CancelledError:
            pass
        print("🛑 Auto-refresh task stopped")

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

# Global variable to track running analysis
analysis_system: Optional[DocumentAnalysisSystem] = None
analysis_running = False
current_session_files: List[str] = []  # Track files uploaded in current session
last_analysis_summary: Optional[Dict] = None  # Store last analysis summary

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a case file for analysis"""
    global current_session_files
    try:
        # Ensure case_files directory exists
        case_files_dir = Path("case_files")
        case_files_dir.mkdir(exist_ok=True)
        
        # Save the uploaded file
        file_path = case_files_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Track this file as part of current session
        if file.filename not in current_session_files:
            current_session_files.append(file.filename)
        
        logger.info(f"📁 Uploaded file: {file.filename} ({file.size} bytes)")
        logger.info(f"📋 Current session files: {current_session_files}")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"File '{file.filename}' uploaded successfully",
                "filename": file.filename,
                "size": file.size,
                "path": str(file_path),
                "session_files": current_session_files
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.post("/api/upload-and-analyze")
async def upload_and_analyze(files: List[UploadFile] = File(...)):
    """Upload multiple case files and immediately start analysis"""
    global current_session_files, analysis_running, analysis_system
    
    try:
        if analysis_running:
            return JSONResponse(
                status_code=409,
                content={"message": "Analysis already running. Please wait for it to complete."}
            )
        
        # Clear session first
        current_session_files.clear()
        
        # Ensure case_files directory exists
        case_files_dir = Path("case_files")
        case_files_dir.mkdir(exist_ok=True)
        
        uploaded_files = []
        total_size = 0
        
        # Save all uploaded files
        for file in files:
            file_path = case_files_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Track this file in current session
            current_session_files.append(file.filename)
            uploaded_files.append({
                "filename": file.filename,
                "size": file.size
            })
            total_size += file.size
            
            logger.info(f"📁 Uploaded for analysis: {file.filename} ({file.size} bytes)")
        
        logger.info(f"📋 Session set to {len(current_session_files)} files: {current_session_files}")
        
        # Check for GEMINI_API_KEY
        if not os.getenv("GEMINI_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY environment variable not set"
            )
        
        # Start analysis immediately
        analysis_running = True
        analysis_system = DocumentAnalysisSystem(session_files=current_session_files)
        
        # Run analysis in background
        asyncio.create_task(run_analysis_background())
        
        return JSONResponse(
            status_code=202,
            content={
                "message": f"{len(uploaded_files)} files uploaded and analysis started",
                "files": uploaded_files,
                "total_files": len(uploaded_files),
                "total_size": total_size,
                "session_files": current_session_files,
                "analysis_status": "running"
            }
        )
        
    except HTTPException:
        analysis_running = False
        raise
    except Exception as e:
        analysis_running = False
        logger.error(f"❌ Upload and analyze error: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading and analyzing files: {str(e)}")

@app.post("/api/upload/multiple")
async def upload_multiple_files(files: List[UploadFile] = File(...)):
    """Upload multiple case files for analysis"""
    try:
        # Ensure case_files directory exists
        case_files_dir = Path("case_files")
        case_files_dir.mkdir(exist_ok=True)
        
        uploaded_files = []
        
        for file in files:
            # Save the uploaded file
            file_path = case_files_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_files.append({
                "filename": file.filename,
                "size": file.size,
                "path": str(file_path)
            })
            
            logger.info(f"📁 Uploaded file: {file.filename} ({file.size} bytes)")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Successfully uploaded {len(uploaded_files)} files",
                "files": uploaded_files
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Multiple upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading files: {str(e)}")

@app.get("/api/files")
async def list_case_files():
    """List all uploaded case files"""
    try:
        case_files_dir = Path("case_files")
        if not case_files_dir.exists():
            return JSONResponse(
                status_code=200,
                content={"files": [], "message": "No case files directory found"}
            )
        
        files = []
        for file_path in case_files_dir.glob("*.txt"):
            file_stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "size": file_stat.st_size,
                "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                "path": str(file_path)
            })
        
        return JSONResponse(
            status_code=200,
            content={"files": files, "count": len(files)}
        )
        
    except Exception as e:
        logger.error(f"❌ Error listing files: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

@app.delete("/api/files/{filename}")
async def delete_case_file(filename: str):
    """Delete a case file"""
    try:
        file_path = Path("case_files") / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        
        file_path.unlink()
        logger.info(f"🗑️ Deleted file: {filename}")
        
        return JSONResponse(
            status_code=200,
            content={"message": f"File '{filename}' deleted successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

@app.post("/api/analysis/start")
async def start_document_analysis(request: Optional[AnalysisRequest] = None):
    """Start document analysis on selected case files"""
    global analysis_system, analysis_running, current_session_files
    
    try:
        if analysis_running:
            return JSONResponse(
                status_code=409,
                content={"message": "Analysis is already running", "status": "running"}
            )
        
        # Determine which files to analyze
        if request and request.selected_files:
            # Use selected files from request
            selected_files = request.selected_files
            if not selected_files:
                raise HTTPException(
                    status_code=400, 
                    detail="No files selected for analysis"
                )
        else:
            # Fall back to session files if no selection provided
            if not current_session_files:
                # If no session files, use all available files in case_files directory
                case_files_dir = Path("case_files")
                all_files = list(case_files_dir.glob("*.txt"))
                if not all_files:
                    raise HTTPException(
                        status_code=400, 
                        detail="No .txt files found in case_files directory"
                    )
                selected_files = [f.name for f in all_files]
            else:
                selected_files = current_session_files
            
        # Verify the selected files actually exist
        case_files_dir = Path("case_files")
        missing_files = []
        for filename in selected_files:
            if not (case_files_dir / filename).exists():
                missing_files.append(filename)
        
        if missing_files:
            raise HTTPException(
                status_code=400,
                detail=f"Selected files not found: {missing_files}"
            )
        
        # Update session files to selected files
        current_session_files = selected_files
        
        # Check for GEMINI_API_KEY
        if not os.getenv("GEMINI_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY environment variable not set"
            )
        
        logger.info("🔬 Starting document analysis...")
        logger.info(f"📋 Analyzing selected files: {selected_files}")
        analysis_running = True
        
        # Initialize and start the analysis system with session-specific files
        analysis_system = DocumentAnalysisSystem(session_files=current_session_files)
        
        # Run analysis in background
        asyncio.create_task(run_analysis_background())
        
        return JSONResponse(
            status_code=202,
            content={
                "message": "Document analysis started successfully",
                "status": "running",
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        analysis_running = False
        raise
    except Exception as e:
        analysis_running = False
        logger.error(f"❌ Error starting analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting analysis: {str(e)}")

async def run_analysis_background():
    """Run the document analysis in the background"""
    global analysis_system, analysis_running, last_analysis_summary
    
    try:
        if not analysis_system:
            logger.error("No analysis system initialized")
            return
        
        # Initialize the system
        success = await analysis_system.initialize_system()
        if not success:
            logger.error("Failed to initialize analysis system")
            return
        
        # Broadcast start message
        await manager.broadcast(json.dumps({
            "type": "analysis_status",
            "data": {
                "status": "running",
                "message": "Document analysis started",
                "timestamp": datetime.now().isoformat()
            }
        }))
        
        # Run the analysis
        logger.info("🔍 Running document analysis...")
        analysis_results, final_conclusion = await analysis_system.analyze_documents()
        
        # Generate summary from results
        logger.info("📊 Generating analysis summary...")
        analysis_summary = generate_analysis_summary(analysis_results, final_conclusion, analysis_system)
        
        # Store summary globally for retrieval
        last_analysis_summary = analysis_summary
        logger.info(f"✅ Analysis summary generated and stored: {len(analysis_summary.get('key_findings', []))} findings")
        
        # Broadcast completion message with summary
        await manager.broadcast(json.dumps({
            "type": "analysis_completed", 
            "data": {
                "status": "completed",
                "message": "Document analysis completed successfully",
                "conclusion": final_conclusion,
                "summary": analysis_summary,
                "timestamp": datetime.now().isoformat()
            }
        }))
        
        # Broadcast final tree update
        await broadcast_tree_update()
        
        logger.info("✅ Document analysis completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Background analysis error: {e}")
        import traceback
        traceback.print_exc()
        
        # Broadcast error message
        await manager.broadcast(json.dumps({
            "type": "analysis_status",
            "data": {
                "status": "error",
                "message": f"Analysis failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        }))
        
    finally:
        analysis_running = False
        if analysis_system:
            await analysis_system.shutdown_system()

@app.get("/api/analysis/status")
async def get_analysis_status():
    """Get the current status of document analysis"""
    global analysis_running, current_session_files
    
    try:
        status = "running" if analysis_running else "idle"
        
        return JSONResponse(
            status_code=200,
            content={
                "status": status,
                "session_files_count": len(current_session_files),
                "session_files": current_session_files,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting analysis status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting analysis status: {str(e)}")

@app.get("/api/analysis/summary")
async def get_analysis_summary():
    """Get the summary of the last completed analysis"""
    global last_analysis_summary
    
    try:
        if not last_analysis_summary:
            return JSONResponse(
                status_code=404,
                content={"message": "No analysis summary available. Please run an analysis first."}
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "summary": last_analysis_summary,
                "timestamp": datetime.now().isoformat(),
                "message": "Analysis summary retrieved successfully"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting analysis summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting analysis summary: {str(e)}")

@app.post("/api/session/clear")
async def clear_session():
    """Clear current session and start fresh"""
    global current_session_files, analysis_running
    
    try:
        if analysis_running:
            return JSONResponse(
                status_code=409,
                content={"message": "Cannot clear session while analysis is running"}
            )
        
        # Clear session files
        old_files = current_session_files.copy()
        current_session_files.clear()
        
        logger.info(f"🗑️ Cleared session files: {old_files}")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Session cleared successfully",
                "cleared_files": old_files,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error clearing session: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing session: {str(e)}")

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