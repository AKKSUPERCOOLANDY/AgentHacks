#!/usr/bin/env python3
"""
AI Agent Memory Tree System - Document Analysis Mode

This version starts with an empty memory tree and has agents
read real case documents to build the investigation from scratch.
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Add backend to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gemini_client import GeminiClient
from tree import MemoryTree, MemoryNode
from tasklist import TaskQueue, Task, TaskPriority
from agents import AgentSystem
from agentview import AgentViewController
from document_analyzer import DocumentAnalyzer

# Set up comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('document_analysis.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DocumentAnalysisSystem:
    """Main system for document-based investigation analysis"""
    
    def __init__(self, session_files: list = None):
        self.gemini_client = None
        self.memory_tree = None
        self.task_queue = None
        self.agent_system = None
        self.document_analyzer = None
        self.synthesis_task = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_files = session_files or []  # Only analyze these specific files
        
    async def initialize_system(self):
        """Initialize all system components"""
        logger.info("🚀 Initializing Document Analysis System...")
        
        try:
            # Initialize Gemini client
            logger.info("📡 Setting up Gemini AI client...")
            self.gemini_client = GeminiClient()
            
            # Always create a fresh database for new analysis runs
            db_name = f"db/investigation_{self.session_id}.db"
            queue_db_name = f"db/tasks_{self.session_id}.db"
            logger.info(f"🌳 Creating new database: {db_name}")
            
            self.memory_tree = MemoryTree(db_name)
            logger.info("Memory tree connected (new fresh analysis starting)")
            
            # Initialize document analyzer
            logger.info("📄 Setting up document analyzer...")
            self.document_analyzer = DocumentAnalyzer("case_files")
            
            # Load only session-specific files if specified
            if self.session_files:
                documents = self.document_analyzer.load_specific_files(self.session_files)
                logger.info(f"📋 Loaded {len(documents)} session-specific documents: {list(documents.keys())}")
            else:
                documents = self.document_analyzer.load_case_files()
                logger.info(f"📋 Loaded {len(documents)} case documents")
            
            if not documents:
                error_msg = "No session files found!" if self.session_files else "No case documents found!"
                logger.error(f"❌ {error_msg}")
                return False
            
            # Initialize task queue with same timestamp as memory tree
            logger.info(f"📋 Setting up task queue (database: {queue_db_name})...")
            self.task_queue = TaskQueue(queue_db_name)
            
            # Initialize agent view controller
            logger.info("🎯 Setting up agent view controller...")
            self.view_controller = AgentViewController(self.memory_tree, self.task_queue)
            
            # Initialize agent system
            logger.info("🤖 Initializing agent system...")
            self.agent_system = AgentSystem(
                self.gemini_client, 
                self.memory_tree, 
                self.task_queue,
                self.view_controller
            )
            
            # Give executor access to document analyzer
            self.agent_system.executor.context_bank['document_analyzer'] = self.document_analyzer
            
            # Start the agent system
            logger.info("▶️  Starting agent system...")
            self.synthesis_task = await self.agent_system.start_system()
            
            logger.info("✅ System initialization complete!")
            logger.info(f"📊 Session ID: {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            return False
    
    async def analyze_documents(self):
        """Have agents analyze documents and build memory tree from scratch"""
        logger.info("📊 Starting document analysis...")
        
        # Get document summary for agents
        doc_summary = self.document_analyzer.get_document_summary()
        doc_types = self.document_analyzer.get_document_types()
        
        logger.info(f"Documents to analyze: {doc_summary['total_documents']}")
        for doc in doc_summary['documents']:
            doc_type = doc_types.get(doc['filename'], 'unknown')
            logger.info(f"  - {doc['filename']} ({doc_type}): {doc['size_lines']} lines")
        
        # Create initial document analysis tasks
        print("📋 Adding 3 document analysis tasks...")
        for doc_info in doc_summary['documents']:
            # Get the actual document content
            doc_content = self.document_analyzer.get_document_content(doc_info['filename'])
            
            task = Task(
                description=f"Analyze {doc_info['type']}: {doc_info['filename']}",
                instructions=f"""
                Analyze this case file document and extract key information for the investigation.
                
                DOCUMENT TYPE: {doc_info['type']}
                FILENAME: {doc_info['filename']}
                
                DOCUMENT CONTENT:
                {doc_content}
                
                Extract and organize:
                1. Key people mentioned (suspects, witnesses, victims)
                2. Physical evidence described
                3. Timeline information
                4. Locations and settings
                5. Relationships and motives
                6. Inconsistencies or notable details
                
                Build memory tree nodes to organize this information logically.
                Focus on what is EXPLICITLY stated in the document text above.
                """,
                priority=TaskPriority.HIGH
            )
            self.task_queue.add_task(task)
        
        # Add a dynamic case resolution task based on uploaded files
        file_count = doc_summary['total_documents']
        case_resolution_task = Task(
            description=f"Analyze and Solve the Case",
            instructions=f"""
            Based on all evidence from the {file_count} case files that have been analyzed, provide a comprehensive case analysis:
            
            ANALYSIS REQUIRED:
            1. SUMMARY: What type of case is this and what are the key facts?
            2. PEOPLE: Who are the main individuals involved (victims, suspects, witnesses)?
            3. EVIDENCE: What are the most critical pieces of evidence?
            4. TIMELINE: What is the sequence of events?
            5. ANALYSIS: What conclusions can be drawn from the evidence?
            6. RECOMMENDATIONS: What further investigative steps would be beneficial?
            
            Use ONLY the information that has been extracted from the uploaded case files.
            Focus on connecting evidence and identifying patterns or inconsistencies.
            If this is a criminal case, identify potential suspects and motives.
            If this is a missing person case, focus on last known activities and potential leads.
            
            CONCLUSION: Present your complete analysis with evidence supporting each finding.
            This should be a thorough, professional case analysis based on the available documents.
            """,
            priority=TaskPriority.CRITICAL
        )
        self.task_queue.add_task(case_resolution_task)
        
        # Execute document analysis with proper stopping conditions
        logger.info("🔍 Executing document analysis...")
        results = []
        final_conclusion = None
        max_iterations = 100  # Safety limit
        iteration = 0
        
        while iteration < max_iterations:
            # Check for conclusion BEFORE getting next task
            conclusion_found, conclusion_text = self._check_for_forced_conclusion()
            if conclusion_found:
                logger.info("🏁 IMMEDIATE STOP: Conclusion detected before task processing")
                final_conclusion = conclusion_text
                break
                
            next_task = self.task_queue.get_next_task()
            if not next_task:
                logger.info("📋 No more tasks in queue")
                break
            
            iteration += 1
            logger.info(f"📖 [{iteration}] Analyzing: {next_task.description}")
            
            # Execute task
            result = await self.agent_system.executor.execute_task(next_task)
            results.append(result)
            
            # IMMEDIATE CHECK: After task execution
            conclusion_found, conclusion_text = self._check_for_forced_conclusion()
            if conclusion_found:
                logger.info("🏁 IMMEDIATE STOP: Conclusion detected after task execution")
                final_conclusion = conclusion_text
                # Mark task as completed quickly and exit immediately
                if result.success:
                    self.task_queue.mark_completed(next_task.id, result.result)
                break
            
            # Update task status
            if result.success:
                self.task_queue.mark_completed(next_task.id, result.result)
                logger.info(f"✅ [{iteration}] Completed: {next_task.description}")
                
                # Get synthesis guidance
                synthesis_result = await self.agent_system.synthesis.perform_synthesis()
                
                # Check if synthesis recommends stopping IMMEDIATELY
                if synthesis_result:
                    confidence = synthesis_result.get('confidence_level', 0)
                    recommendation = synthesis_result.get('strategic_recommendation', 'CONTINUE')
                    
                    if confidence >= 0.8 or recommendation == 'CONCLUDE':
                        logger.info(f"🎯 Synthesis recommends immediate stopping (confidence: {confidence:.2f})")
                        final_conclusion = f"Investigation concluded via synthesis with confidence {confidence:.2f}"
                        break
                
                # ONLY refine plan if synthesis doesn't recommend conclusion
                if not synthesis_result or (synthesis_result.get('confidence_level', 0) < 0.8 and synthesis_result.get('strategic_recommendation', 'CONTINUE') != 'CONCLUDE'):
                    await self.agent_system.planner.refine_plan(next_task, result.result, synthesis_result)
                
            else:
                self.task_queue.mark_failed(next_task.id, result.result)
                logger.error(f"❌ [{iteration}] Failed: {next_task.description}")
            
            # Small delay to see progress
            await asyncio.sleep(1)
        
        logger.info(f"📊 Document analysis complete! ({iteration} iterations)")
        return results, final_conclusion
    
    def _check_for_forced_conclusion(self) -> tuple[bool, str]:
        """Check if a forced conclusion has been generated by agents"""
        try:
            # Check agent context for conclusions (not tree nodes)
            if hasattr(self.agent_system, 'planner') and self.agent_system.planner:
                if "final_conclusion" in self.agent_system.planner.context_bank:
                    conclusion_text = self.agent_system.planner.context_bank["final_conclusion"]
                    logger.info("🎯 Found conclusion in planner context")
                    return True, conclusion_text
            
            if hasattr(self.agent_system, 'synthesis') and self.agent_system.synthesis:
                if "synthesis_conclusion" in self.agent_system.synthesis.context_bank:
                    conclusion_text = self.agent_system.synthesis.context_bank["synthesis_conclusion"]
                    logger.info("🎯 Found conclusion in synthesis context")
                    return True, conclusion_text
            
            # Also check if conclusion task exists in queue
            if self.task_queue and self.task_queue.has_conclusion_task():
                logger.info("🎯 Found conclusion task in queue")
                return True, "Investigation conclusion task identified in queue"
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error checking for forced conclusion: {e}")
            return False, ""
    
    async def build_investigation_plan(self):
        """Have agents create an investigation plan based on the analyzed documents"""
        logger.info("🎯 Building investigation plan from analyzed documents...")
        
        # Get current tree state
        tree_stats = self.memory_tree.get_tree_statistics()
        tree_view = self.memory_tree.serialize_tree()
        
        logger.info(f"Memory tree now has {tree_stats['total_nodes']} nodes from document analysis")
        
        # Create investigation planning query
        investigation_query = """
        Based on the case documents you've analyzed and the memory tree you've built, 
        create a comprehensive investigation plan. Focus on:
        
        1. Key suspects and their motives
        2. Critical evidence that needs further analysis
        3. Timeline gaps that need to be filled
        4. Witness credibility assessments
        5. Next investigative steps
        
        Use only the information you've extracted from the documents.
        """
        
        # Process through agent system
        result = await self.agent_system.process_query(investigation_query)
        
        logger.info("🎯 Investigation plan complete!")
        return result
    
    def display_results(self):
        """Display the final investigation results"""
        logger.info("📈 Final Investigation Results:")
        
        # Memory tree statistics
        tree_stats = self.memory_tree.get_tree_statistics()
        logger.info(f"📊 Memory Tree: {tree_stats['total_nodes']} nodes, depth {tree_stats['max_depth']}")
        
        # Task statistics
        queue_stats = self.task_queue.get_queue_statistics()
        logger.info(f"📋 Tasks: {queue_stats['completed_tasks']} completed, {queue_stats['failed_tasks']} failed")
        
        # Show memory tree structure
        logger.info("🌳 Investigation Memory Tree:")
        tree_view = self.memory_tree.serialize_tree()
        print("\n" + "="*60)
        print("INVESTIGATION MEMORY TREE (Built from Documents)")
        print("="*60)
        print(tree_view)
        print("="*60)
        
        # Show document analysis summary
        logger.info("📄 Document Analysis Summary:")
        doc_types = self.document_analyzer.get_document_types()
        for filename, doc_type in doc_types.items():
            logger.info(f"  ✓ {filename} ({doc_type}) - analyzed and integrated")
    
    async def shutdown_system(self):
        """Gracefully shutdown the system"""
        logger.info("🛑 Shutting down system...")
        
        if self.agent_system:
            self.agent_system.stop_system()
        
        if self.synthesis_task:
            self.synthesis_task.cancel()
            try:
                await self.synthesis_task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ System shutdown complete")


async def main():
    """Main entry point for document analysis"""
    logger.info("🎯 AI Agent Document Analysis System - Starting...")
    
    # Check environment
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("❌ GEMINI_API_KEY environment variable not set!")
        logger.info("Please set your Gemini API key: export GEMINI_API_KEY='your_key_here'")
        return
    
    # Check for case files
    case_files_dir = Path("case_files")
    if not case_files_dir.exists() or not list(case_files_dir.glob("*.txt")):
        logger.error("❌ No case files found!")
        logger.info("Please add .txt case files to the 'case_files' directory")
        return
    
    system = DocumentAnalysisSystem()
    
    try:
        # Initialize system
        success = await system.initialize_system()
        if not success:
            logger.error("Failed to initialize system")
            return
        
        print("\n" + "="*80)
        print("🕵️  AI AGENT DOCUMENT ANALYSIS SYSTEM")
        print("="*80)
        print("📄 Reading case documents...")
        print("🤖 Agents will analyze documents and build investigation tree from scratch")
        print("🌳 Starting with EMPTY memory tree")
        print("="*80)
        
        # Analyze documents
        analysis_results, final_conclusion = await system.analyze_documents()
        
        # Check if investigation was force-concluded during document analysis
        if final_conclusion:
            logger.info("🏁 Investigation concluded during document analysis - skipping further phases")
            
            # Display the final conclusion separately
            print("\n" + "="*80)
            print("🏁 FINAL INVESTIGATION CONCLUSION")
            print("="*80)
            print(final_conclusion)
            print("="*80)
        else:
            # Build investigation plan
            investigation_result = await system.build_investigation_plan()
        
        # Display results
        system.display_results()
        
        logger.info("🎉 Document analysis completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("🛑 System interrupted by user")
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await system.shutdown_system()


if __name__ == "__main__":
    # Run the document analysis system
    asyncio.run(main()) 