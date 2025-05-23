#!/usr/bin/env python3
"""
AI Agent Memory Tree System - Main Entry Point

This file orchestrates the complete AI agent system with memory trees,
task queues, and multi-agent collaboration for complex investigations.
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
from tree import MemoryTree, create_detective_case_tree
from tasklist import TaskQueue
from agents import AgentSystem

# Set up comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class SystemController:
    """Main system controller for the AI Agent Memory Tree System"""
    
    def __init__(self):
        self.gemini_client = None
        self.memory_tree = None
        self.task_queue = None
        self.agent_system = None
        self.synthesis_task = None
        
    async def initialize_system(self, case_name: str = "Test Investigation"):
        """Initialize all system components"""
        logger.info("🚀 Initializing AI Agent Memory Tree System...")
        
        try:
            # Initialize Gemini client
            logger.info("📡 Setting up Gemini AI client...")
            self.gemini_client = GeminiClient()
            
            # Initialize memory tree with detective case
            logger.info("🌳 Creating memory tree structure...")
            self.memory_tree = create_detective_case_tree(case_name)
            logger.info(f"Memory tree initialized with {len(self.memory_tree.nodes)} nodes")
            
            # Initialize task queue
            logger.info("📋 Setting up task queue...")
            self.task_queue = TaskQueue("main_system.db")
            
            # Initialize agent system
            logger.info("🤖 Initializing agent system...")
            self.agent_system = AgentSystem(
                self.gemini_client, 
                self.memory_tree, 
                self.task_queue
            )
            
            # Start the agent system
            logger.info("▶️  Starting agent system...")
            self.synthesis_task = await self.agent_system.start_system()
            
            logger.info("✅ System initialization complete!")
            return True
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            return False
    
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
    
    async def process_investigation_query(self, query: str):
        """Process a complete investigation query"""
        if not self.agent_system:
            logger.error("System not initialized!")
            return None
        
        logger.info(f"🔍 Processing investigation query: {query}")
        
        try:
            # Process the query through the agent system
            result = await self.agent_system.process_query(query)
            
            logger.info("📊 Query processing complete!")
            logger.info(f"Tasks executed: {result['tasks_executed']}")
            logger.info(f"Successful tasks: {result['successful_tasks']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing query: {e}")
            return None
    
    def display_system_status(self):
        """Display current system status"""
        logger.info("📈 Current System Status:")
        
        if self.memory_tree:
            tree_stats = self.memory_tree.get_tree_statistics()
            logger.info(f"Memory Tree - Nodes: {tree_stats['total_nodes']}, Depth: {tree_stats['max_depth']}")
        
        if self.task_queue:
            queue_stats = self.task_queue.get_queue_statistics()
            logger.info(f"Task Queue - Total: {queue_stats['total_tasks']}, Pending: {queue_stats['pending_tasks']}, Completed: {queue_stats['completed_tasks']}")
        
        if self.agent_system:
            logger.info("Agent System - Running ✅")
        
        logger.info("=" * 50)


async def test_planner_agent():
    """Test the Planner Agent individually"""
    logger.info("🧪 Testing Planner Agent...")
    
    # Initialize components
    client = GeminiClient()
    tree = create_detective_case_tree("Planner Test")
    queue = TaskQueue("planner_test.db")
    
    # Create planner agent
    from agents import PlannerAgent
    planner = PlannerAgent(client, tree, queue)
    
    # Test plan creation
    query = "Investigate a missing person case for Sarah Johnson"
    tasks = await planner.create_initial_plan(query)
    
    logger.info(f"✅ Planner created {len(tasks)} tasks:")
    for i, task in enumerate(tasks, 1):
        logger.info(f"  {i}. {task.description} (Priority: {task.priority.name})")
    
    return tasks


async def test_executor_agent():
    """Test the Executor Agent individually"""
    logger.info("🧪 Testing Executor Agent...")
    
    # Initialize components
    client = GeminiClient()
    tree = create_detective_case_tree("Executor Test")
    
    # Create executor agent
    from agents import ExecutorAgent, Task, TaskPriority
    executor = ExecutorAgent(client, tree)
    
    # Create a test task
    test_task = Task(
        description="Analyze the initial missing person report",
        instructions="Review the missing person report for Sarah Johnson and extract key details including last known location, timeline, and potential witnesses",
        priority=TaskPriority.HIGH
    )
    
    # Execute the task
    result = await executor.execute_task(test_task)
    
    logger.info(f"✅ Task execution result - Success: {result.success}")
    logger.info(f"Result: {result.result[:200]}..." if len(result.result) > 200 else f"Result: {result.result}")
    logger.info(f"Memory updates: {len(result.memory_updates)}")
    
    return result


async def test_synthesis_agent():
    """Test the Synthesis Agent individually"""
    logger.info("🧪 Testing Synthesis Agent...")
    
    # Initialize components
    client = GeminiClient()
    tree = create_detective_case_tree("Synthesis Test")
    
    # Add some test data to the tree
    from tree import MemoryNode, NodeStatus
    evidence_node = MemoryNode("Security Camera Footage", "CCTV footage from the mall showing Sarah at 3:47 PM")
    evidence_node.status = NodeStatus.COMPLETED
    tree.add_node(evidence_node)
    
    witness_node = MemoryNode("Witness Statement", "Mall employee saw Sarah talking to unknown person")
    witness_node.status = NodeStatus.COMPLETED
    tree.add_node(witness_node)
    
    # Create synthesis agent
    from agents import SynthesisAgent
    synthesis = SynthesisAgent(client, tree)
    
    # Perform analysis
    analysis = await synthesis._perform_analysis()
    
    logger.info("✅ Synthesis analysis complete:")
    logger.info(f"Patterns found: {len(analysis.get('key_patterns', []))}")
    logger.info(f"Information gaps: {len(analysis.get('information_gaps', []))}")
    logger.info(f"Strategic insights: {analysis.get('strategic_insights', 'None')[:100]}...")
    
    return analysis


async def run_detective_case_demo():
    """Run a complete detective case demonstration"""
    logger.info("🕵️ Starting Detective Case Demo...")
    
    controller = SystemController()
    
    try:
        # Initialize system
        success = await controller.initialize_system("Missing Person: Sarah Johnson")
        if not success:
            logger.error("Failed to initialize system")
            return
        
        controller.display_system_status()
        
        # Detective case scenario
        investigation_queries = [
            "Investigate the missing person case for Sarah Johnson. She was last seen at downtown mall on Friday afternoon.",
            "Analyze any security camera footage from the mall and surrounding areas",
            "Interview witnesses who may have seen Sarah at the mall",
            "Check Sarah's phone records and social media activity for clues"
        ]
        
        # Process each investigation query
        for i, query in enumerate(investigation_queries, 1):
            logger.info(f"🔍 Processing Query {i}/{len(investigation_queries)}")
            logger.info(f"Query: {query}")
            
            result = await controller.process_investigation_query(query)
            
            if result:
                logger.info(f"✅ Query {i} completed successfully")
                logger.info(f"Tasks executed: {result['tasks_executed']}")
                logger.info(f"Success rate: {result['successful_tasks']}/{result['tasks_executed']}")
                
                # Display memory tree growth
                tree_stats = result['tree_statistics']
                logger.info(f"Memory tree now has {tree_stats['total_nodes']} nodes")
                
                # Wait a bit between queries for synthesis
                await asyncio.sleep(2)
            else:
                logger.error(f"❌ Query {i} failed")
        
        # Final system status
        logger.info("🏁 Final System Status:")
        controller.display_system_status()
        
        # Display final memory tree
        logger.info("🌳 Final Memory Tree Structure:")
        tree_view = controller.memory_tree.serialize_tree()
        logger.info(tree_view)
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
    
    finally:
        await controller.shutdown_system()


async def run_individual_agent_tests():
    """Run individual agent tests"""
    logger.info("🧪 Running Individual Agent Tests...")
    
    try:
        # Test each agent individually
        await test_planner_agent()
        await asyncio.sleep(1)
        
        await test_executor_agent()
        await asyncio.sleep(1)
        
        await test_synthesis_agent()
        
        logger.info("✅ All individual agent tests completed!")
        
    except Exception as e:
        logger.error(f"❌ Agent tests failed: {e}")


async def main():
    """Main entry point"""
    logger.info("🎯 AI Agent Memory Tree System - Starting...")
    
    # Check environment
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("❌ GEMINI_API_KEY environment variable not set!")
        logger.info("Please set your Gemini API key: export GEMINI_API_KEY='your_key_here'")
        return
    
    try:
        # Choose what to run
        print("\n" + "="*60)
        print("🤖 AI Agent Memory Tree System")
        print("="*60)
        print("Choose an option:")
        print("1. Run complete detective case demo")
        print("2. Run individual agent tests")
        print("3. Run both")
        print("="*60)
        
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == "1":
            await run_detective_case_demo()
        elif choice == "2":
            await run_individual_agent_tests()
        elif choice == "3":
            await run_individual_agent_tests()
            await asyncio.sleep(2)
            await run_detective_case_demo()
        else:
            logger.info("Invalid choice. Running detective case demo by default.")
            await run_detective_case_demo()
        
        logger.info("🎉 System execution completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("🛑 System interrupted by user")
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main()) 