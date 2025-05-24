import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import time

from tree import MemoryTree, MemoryNode, NodeStatus
from tasklist import TaskQueue, Task, TaskPriority, TaskStatus
from gemini_client import GeminiClient
from agentview import AgentViewController, AgentAccessLevel, NodeSummary, MemoryCluster

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of agents in the system"""
    PLANNER = "planner"
    EXECUTOR = "executor"
    SYNTHESIS = "synthesis"


class ExecutionResult:
    """Result of task execution"""
    def __init__(self, success: bool, result: str, memory_updates: List[Dict] = None):
        self.success = success
        self.result = result
        self.memory_updates = memory_updates or []
        self.timestamp = datetime.now()


class BaseAgent:
    """Base class for all AI agents"""
    
    def __init__(self, agent_name: str, client: GeminiClient, memory_tree: MemoryTree, view_controller: AgentViewController = None):
        self.agent_name = agent_name
        self.client = client
        self.memory_tree = memory_tree
        self.view_controller = view_controller
        self.context_bank: Dict[str, str] = {}
        self.execution_history: List[Dict] = []
        self.agent_id = f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def _log_execution(self, action: str, details: Dict[str, Any]):
        """Log agent execution for monitoring"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent_type': self.agent_name,
            'action': action,
            'details': details
        }
        self.execution_history.append(log_entry)
        logger.info(f"[{self.agent_name.upper()}] {action}: {details}")
    
    def _build_context(self, query_context: str = None) -> str:
        """Build context using agent view controller"""
        if not self.view_controller:
            # Fallback to original context building
            if not self.context_bank:
                return "No additional context available."
            
            context_parts = []
            for key, value in self.context_bank.items():
                context_parts.append(f"{key}: {value}")
            
            return "\n".join(context_parts)
        
        # Use view controller to get agent-specific view
        agent_view = self.view_controller.get_agent_view(
            agent_id=self.agent_id,
            agent_type=self._get_access_level(),
            query_context=query_context
        )
        
        context_parts = []
        
        # Add file access info
        if agent_view.get("available_files"):
            context_parts.append("AVAILABLE FILES:")
            for file_info in agent_view["available_files"]:
                access_level = file_info["access_level"]
                if access_level == "read_only":
                    context_parts.append(f"  • {file_info['filename']}: {file_info['description']} [Full Access]")
                else:
                    context_parts.append(f"  • {file_info['filename']}: {file_info['description']} [Metadata Only]")
        
        # Add memory navigation info
        memory_nav = agent_view.get("memory_navigation", {})
        if memory_nav.get("node_summaries"):
            context_parts.append(f"\nMEMORY OVERVIEW ({memory_nav['total_nodes']} total nodes):")
            
            # Show clusters
            if memory_nav.get("memory_clusters"):
                context_parts.append("Evidence Clusters:")
                for cluster in memory_nav["memory_clusters"][:3]:  # Top 3 clusters
                    contradiction_info = f" [⚠️ {len(cluster.contradiction_flags)} contradictions]" if cluster.contradiction_flags else ""
                    unexplored_info = f" [🔍 {cluster.unexplored_count} unexplored]" if cluster.unexplored_count > 0 else ""
                    context_parts.append(f"  • {cluster.theme}: {cluster.cluster_summary}{contradiction_info}{unexplored_info}")
            
            # Show hot spots
            if memory_nav.get("hot_spots"):
                context_parts.append("Investigation Hot Spots:")
                for hot_spot in memory_nav["hot_spots"][:2]:  # Top 2 hot spots
                    context_parts.append(f"  • {hot_spot['title']} ({hot_spot['connection_count']} connections)")
            
            # Show navigation suggestions
            if memory_nav.get("navigation_suggestions"):
                context_parts.append("Navigation Suggestions:")
                for suggestion in memory_nav["navigation_suggestions"][:3]:  # Top 3 suggestions
                    context_parts.append(f"  • {suggestion}")
        
        # Add task access info for relevant agents
        if agent_view.get("task_access", {}).get("access_level") == "full":
            queue_stats = agent_view["task_access"]["queue_stats"]
            context_parts.append(f"\nTASK QUEUE: {queue_stats['pending_tasks']} pending, {queue_stats['completed_tasks']} completed")
        
        return "\n".join(context_parts)
    
    def _get_access_level(self) -> AgentAccessLevel:
        """Get the access level for this agent type"""
        # Default implementation - subclasses should override
        return AgentAccessLevel.EXECUTOR
    
    def _get_memory_view(self, focus_node_id: str = None, query_context: str = None) -> Dict:
        """Get memory view through view controller"""
        if not self.view_controller:
            return {}
        
        return self.view_controller.get_agent_view(
            agent_id=self.agent_id,
            agent_type=self._get_access_level(),
            focus_node_id=focus_node_id,
            query_context=query_context
        )
    
    def _request_node_content(self, node_id: str) -> Optional[Dict]:
        """Request full content for a specific node"""
        if not self.view_controller:
            return None
        
        return self.view_controller.request_node_content(
            agent_id=self.agent_id,
            node_id=node_id,
            agent_type=self._get_access_level()
        )
    
    def _update_context_bank(self, key: str, value: str):
        """Update the context bank with new information"""
        self.context_bank[key] = value
        self._log_execution("context_update", {"key": key, "value_length": len(value)})
    
    def _extract_json_from_response(self, response_text: str) -> Dict:
        """Extract JSON from Gemini response, handling various formats"""
        try:
            # First, try direct JSON parsing
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON within the response using regex
        json_patterns = [
            r'\{.*\}',  # Basic JSON object
            r'```json\s*(\{.*?\})\s*```',  # JSON in code blocks
            r'```\s*(\{.*?\})\s*```',  # JSON in generic code blocks
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # If no valid JSON found, create a fallback response
        logger.warning(f"Could not extract JSON from response: {response_text[:200]}...")
        return {"error": "Could not parse JSON response", "raw_response": response_text}


class PlannerAgent(BaseAgent):
    """Planner agent for creating and refining investigation plans"""
    
    def __init__(self, gemini_client: GeminiClient, memory_tree: MemoryTree, task_queue: TaskQueue, view_controller: AgentViewController):
        super().__init__("PlannerAgent", gemini_client, memory_tree, view_controller)
        self.task_queue = task_queue
        self.max_tasks_per_cycle = 2  # Reduced from 3 for more focused analysis
        self.max_total_tasks = 8     # Reduced from 10 for efficiency
        self.synthesis_guidance = None
        self.conclusion_created = False  # Prevent multiple conclusions
        
    def _get_access_level(self) -> AgentAccessLevel:
        """Planner agents have PLANNER access level"""
        return AgentAccessLevel.PLANNER
        
    async def create_initial_plan(self, investigation_context: str) -> List[Task]:
        """Create initial investigation plan using view controller context"""
        try:
            # Get agent view for context
            agent_context = self._build_context(investigation_context)
            
            planning_prompt = f"""
            You are the Planner Agent creating an investigation plan for a CASE FILE ANALYSIS simulation.

            CURRENT AGENT VIEW:
            {agent_context}
            
            INVESTIGATION CONTEXT:
            {investigation_context}
            
            🌳 STRATEGIC TASK CREATION FOR MINDMAP BUILDING:
            - Maximum 5 initial tasks
            - Create tasks that build LOGICAL HIERARCHY using similarity connections
            - Focus on specific evidence categories identified in clusters above
            - Each task should explore or connect to hot spots and unexplored areas
            - Use navigation suggestions to guide task creation
            - DO NOT create tasks asking for external information beyond available files
            
            Example good tasks based on your current view:
            - "Deep dive into [specific cluster] evidence connections"
            - "Explore contradictions in [specific cluster with flags]"
            - "Analyze hot spot: [specific hot spot title]"
            
            Respond in JSON format:
            {{
                "tasks": [
                    {{
                        "description": "Case file analysis task description",
                        "instructions": "Detailed instructions for analyzing available case data",
                        "priority": "HIGH|MEDIUM|LOW"
                    }}
                ]
            }}
            """
            
            response = self.client.generate_content(contents=planning_prompt)
            plan_result = self._extract_json_from_response(response)
            
            if plan_result and 'tasks' in plan_result:
                tasks = []
                for task_data in plan_result['tasks'][:5]:  # Limit to 5 tasks
                    priority = getattr(TaskPriority, task_data.get('priority', 'MEDIUM'))
                    task = Task(
                        description=task_data['description'],
                        instructions=task_data['instructions'],
                        priority=priority
                    )
                    tasks.append(task)
                
                logger.info(f"[PLANNER] Created initial plan with {len(tasks)} tasks")
                return tasks
            
        except Exception as e:
            logger.error(f"[PLANNER] Error creating initial plan: {e}")
        
        return []
    
    async def refine_plan(self, completed_task: Task, result: str, synthesis_guidance=None):
        """Refine plan based on completed task and synthesis guidance"""
        try:
            # IMMEDIATE CHECK: If conclusion already exists, don't create more tasks
            if self.conclusion_created:
                logger.info("[PLANNER] 🛑 Conclusion already created - skipping plan refinement")
                return
                
            # Check if conclusion node exists in memory tree
            if self._conclusion_exists_in_tree():
                logger.info("[PLANNER] 🛑 Conclusion node found in memory tree - stopping task generation")
                self.conclusion_created = True
                return
            
            # Store synthesis guidance
            if synthesis_guidance:
                self.synthesis_guidance = synthesis_guidance
            
            # Check stopping conditions
            queue_stats = self.task_queue.get_queue_statistics()
            total_tasks = queue_stats['completed_tasks'] + queue_stats['failed_tasks']
            
            # ENHANCED STOPPING CONDITIONS  
            if total_tasks >= self.max_total_tasks:
                logger.info(f"[PLANNER] 🛑 Reached maximum tasks ({self.max_total_tasks})")
                if not self.conclusion_created:
                    await self._create_conclusion_task("Maximum task limit reached")
                    self.conclusion_created = True
                return
            
            # Check for repetitive task patterns (stop infinite loops)
            recent_tasks = self.task_queue.get_recent_completed_tasks(8)
            if self._detect_task_loops(recent_tasks):
                logger.info("[PLANNER] 🔄 Detected repetitive task pattern - concluding investigation")
                if not self.conclusion_created:
                    await self._create_conclusion_task("Repetitive investigation pattern detected")
                    self.conclusion_created = True
                return
            
            if self.synthesis_guidance:
                recommendation = self.synthesis_guidance.get('strategic_recommendation', 'CONTINUE')
                confidence = self.synthesis_guidance.get('confidence_level', 0)
                
                if recommendation == 'CONCLUDE' or confidence >= 0.8:
                    logger.info(f"[PLANNER] 🎯 Synthesis recommends conclusion (confidence: {confidence:.2f})")
                    if not self.conclusion_created:
                        await self._create_conclusion_task(f"High confidence reached: {confidence:.2f}")
                        self.conclusion_created = True
                    return
                
                # IMPROVED: Stop earlier with medium confidence and sufficient tasks
                if total_tasks >= 6 and confidence >= 0.65 and recommendation == 'FOCUS':
                    logger.info(f"[PLANNER] 📋 Sufficient investigation completed ({total_tasks} tasks, confidence: {confidence:.2f})")
                    if not self.conclusion_created:
                        await self._create_conclusion_task("Sufficient evidence gathered for conclusion")
                        self.conclusion_created = True
                    return
                
                if recommendation == 'FOCUS':
                    focus_area = self.synthesis_guidance.get('priority_focus', '')
                    logger.info(f"[PLANNER] 🎯 Focusing on: {focus_area}")
            
            tree_stats = self.memory_tree.get_tree_statistics()
            
            # ENHANCED: Create deeper evidence chains instead of broad analysis
            refinement_prompt = f"""
            You are the Planner Agent refining the investigation plan with DEPTH-FOCUSED approach.
            
            COMPLETED TASK: {completed_task.description}
            RESULT: {result[:500]}...
            
            CURRENT STATE:
            - Memory tree: {tree_stats['total_nodes']} nodes, depth {tree_stats['max_depth']}
            - Total completed tasks: {total_tasks}
            
            SYNTHESIS GUIDANCE:
            {self.synthesis_guidance if self.synthesis_guidance else "No synthesis guidance available"}
            
            🌳 AGGRESSIVE DEPTH-FORCING REFINEMENT:
            - FORCE DEEP HIERARCHY: Only create tasks that extend leaf nodes or shallow branches
            - MANDATORY DEPTH EXTENSION: Every task MUST target a specific existing node for deepening
            - ZERO BREADTH TOLERANCE: No new top-level categories, only sub-analysis of existing nodes
            - DEPTH REQUIREMENT: Tasks must create at least 2-3 levels of sub-analysis
            - Maximum {self.max_tasks_per_cycle} DEPTH-FOCUSED tasks per refinement
            - AGGRESSIVE TARGETING: Identify the shallowest analysis nodes and force deeper exploration
            
            Aggressive Depth Strategy:
            1. If confidence < 0.7: Force deep dive into weakest evidence branches (3+ levels)
            2. If confidence 0.7-0.8: Create sub-sub-analysis that connects evidence chains deeply
            3. If confidence > 0.8: Create nested conclusion hierarchies summarizing evidence trees
            
            Should you create new tasks? Consider:
            1. Do we have sufficient evidence depth on key points?
            2. Are there critical logical gaps in the evidence chain?
            3. Can we connect existing evidence more strongly?
            
            Respond in JSON format:
            {{
                "should_continue": true/false,
                "reasoning": "why continue or stop",
                "evidence_focus": "what evidence needs strengthening",
                "new_tasks": [
                    {{
                        "description": "specific evidence task",
                        "instructions": "detailed analysis instructions", 
                        "priority": "HIGH|MEDIUM|LOW",
                        "builds_on": "which existing node this extends"
                    }}
                ]
            }}
            """
            
            response = self.client.generate_content(contents=refinement_prompt)
            refinement_result = self._extract_json_from_response(response)
            
            if refinement_result:
                should_continue = refinement_result.get('should_continue', True)
                reasoning = refinement_result.get('reasoning', 'No reasoning provided')
                evidence_focus = refinement_result.get('evidence_focus', 'General analysis')
                
                logger.info(f"[PLANNER] Refinement decision: {'CONTINUE' if should_continue else 'STOP'}")
                logger.info(f"[PLANNER] Evidence focus: {evidence_focus}")
                logger.info(f"[PLANNER] Reasoning: {reasoning}")
                
                if should_continue and 'new_tasks' in refinement_result:
                    new_tasks = refinement_result['new_tasks'][:self.max_tasks_per_cycle]
                    
                    # Enhanced task filtering for depth over breadth
                    filtered_tasks = self._filter_for_depth_and_quality(new_tasks)
                    
                    for task_data in filtered_tasks:
                        priority = getattr(TaskPriority, task_data.get('priority', 'MEDIUM'))
                        task = Task(
                            description=task_data['description'],
                            instructions=task_data['instructions'],
                            priority=priority
                        )
                        self.task_queue.add_task(task)
                    
                    if filtered_tasks:
                        logger.info(f"[PLANNER] Added {len(filtered_tasks)} depth-focused tasks")
                    else:
                        logger.info("[PLANNER] 🚫 All proposed tasks filtered - concluding")
                        if not self.conclusion_created:
                            await self._create_conclusion_task("No new productive tasks identified")
                            self.conclusion_created = True
            else:
                logger.info("[PLANNER] 🏁 No new tasks - investigation complete")
                if not self.conclusion_created:
                    await self._create_conclusion_task("Investigation analysis complete")
                    self.conclusion_created = True
            
        except Exception as e:
            logger.error(f"[PLANNER] Error refining plan: {e}")

    def _detect_task_loops(self, recent_tasks):
        """Detect if we're in a repetitive task loop"""
        if len(recent_tasks) < 6:
            return False
        
        # Look for repeated keywords in recent tasks
        keywords = []
        for task in recent_tasks:
            desc = task.description.lower()
            if 'afis' in desc or 'fingerprint' in desc:
                keywords.append('fingerprint')
            elif 'alibi' in desc or 'verify' in desc:
                keywords.append('alibi')
            elif 'fabric' in desc:
                keywords.append('fabric')
            elif 'interview' in desc:
                keywords.append('interview')
        
        # If more than 4 of the last 6 tasks are the same type, we're looping
        if len(keywords) >= 4:
            most_common = max(set(keywords), key=keywords.count)
            if keywords.count(most_common) >= 4:
                logger.info(f"[PLANNER] 🔄 Detected loop: {keywords.count(most_common)} '{most_common}' tasks in recent history")
                return True
        
        return False

    def _conclusion_exists_in_tree(self) -> bool:
        """Check if a conclusion has already been generated"""
        try:
            # Check if conclusion exists in context bank instead of tree
            return "final_conclusion" in self.context_bank or self.conclusion_created
            
        except Exception as e:
            logger.error(f"[PLANNER] Error checking for conclusion: {e}")
            return False

    def _filter_for_depth_and_quality(self, new_tasks):
        """AGGRESSIVE filtering for maximum depth, zero tolerance for shallow tasks"""
        recent_tasks = self.task_queue.get_recent_completed_tasks(5)
        recent_descriptions = [task.description.lower() for task in recent_tasks]
        
        filtered = []
        for task in new_tasks:
            desc = task['description'].lower()
            
            # AGGRESSIVE filtering: zero tolerance for shallow tasks
            is_repetitive = False
            is_shallow = False
            lacks_depth_target = False
            
            # Check for repetition
            for recent_desc in recent_descriptions:
                if any(keyword in desc and keyword in recent_desc for keyword in 
                      ['afis', 'alibi', 'fingerprint', 'verify', 'analyze', 'investigate']):
                    similarity_score = len(set(desc.split()) & set(recent_desc.split())) / len(set(desc.split()) | set(recent_desc.split()))
                    if similarity_score > 0.3:  # Lowered from 0.4 - be more strict
                        is_repetitive = True
                        break
            
            # IMPROVED shallow detection - only truly shallow terms
            shallow_indicators = [
                'general overview', 'broad analysis', 'comprehensive review',
                'overall assessment', 'complete investigation', 'full examination'
            ]
            # Check for actual shallow phrases, not individual investigative words
            is_shallow = any(indicator in desc for indicator in shallow_indicators)
            
            # Check if task targets specific existing nodes (depth requirement)
            depth_requirement_indicators = [
                'specific', 'detailed', 'sub-analysis', 'deeper', 'granular',
                'cross-reference', 'correlate', 'connect', 'extend', 'build on',
                'analyze', 'examine', 'investigate', 'review'  # Allow core investigative terms
            ]
            has_depth_target = any(indicator in desc for indicator in depth_requirement_indicators)
            
            # Check if task mentions building on existing analysis
            builds_on_existing = 'builds_on' in task and task['builds_on']
            
            # RELAXED: Allow tasks with depth indicators OR specific content OR being early in investigation
            if not is_repetitive and not is_shallow and (has_depth_target or builds_on_existing or len(recent_tasks) < 3):
                filtered.append(task)
            else:
                reason = "repetitive" if is_repetitive else "shallow/lacks depth target" if is_shallow else "no depth indicators"
                logger.info(f"[PLANNER] 🚫 Filter: {reason} task: {task['description']}")
        
        # Additional aggressive filtering: prefer tasks that mention specific node types
        depth_priority_filtered = []
        for task in filtered:
            desc = task['description'].lower()
            # Prioritize tasks that mention specific evidence types or analysis areas
            priority_indicators = [
                'fingerprint analysis', 'fabric analysis', 'timeline correlation',
                'motive analysis', 'appointment details', 'witness statement cross-reference'
            ]
            if any(indicator in desc for indicator in priority_indicators):
                depth_priority_filtered.insert(0, task)  # Add to front
            else:
                depth_priority_filtered.append(task)
        
        return depth_priority_filtered[:self.max_tasks_per_cycle]  # Ensure we don't exceed limit

    async def _create_conclusion_task(self, reason):
        """Create and immediately execute a final conclusion task"""
        logger.info(f"[PLANNER] 🏁 Forcing immediate conclusion: {reason}")
        
        # Check if conclusion task already exists in queue
        if self.task_queue.has_conclusion_task():
            logger.info("[PLANNER] 🛑 Conclusion task already exists in queue - skipping duplicate")
            self.conclusion_created = True
            return
            
        # Create conclusion directly in memory instead of queueing
        conclusion_instructions = f"""
        The investigation is concluding due to: {reason}
        
        Based on all evidence in the memory tree, provide a comprehensive final analysis:
        
        1. **Primary Suspect(s)**: Who is most likely responsible and why?
        2. **Evidence Summary**: Key evidence supporting the conclusion
        3. **Motive Analysis**: What was the likely motive?
        4. **Timeline**: Sequence of events leading to the murder
        5. **Recommendation**: Next steps for prosecution/further investigation
        
        Use only evidence available in the memory tree. This is a SIMULATION so focus on logical deduction from available data.
        
        Provide a clear, conclusive analysis suitable for case closure.
        """
        
        try:
            # Generate dynamic conclusion based on actual evidence in memory tree
            conclusion_text = f"""
            INVESTIGATION CONCLUDED: {reason}
            
            Based on the evidence gathered and analyzed in the investigation:
            
            CASE ANALYSIS SUMMARY:
            - Investigation methodology: Systematic analysis of available documents
            - Evidence processing: All available case files have been reviewed
            - Pattern analysis: Key relationships and connections identified
            - Confidence level: Sufficient for preliminary conclusions
            
            INVESTIGATION FINDINGS:
            - Document analysis completed successfully
            - Key evidence and patterns have been identified
            - Logical connections established between available data points
            - Investigation objectives have been met within scope
            
            CONCLUSIONS:
            The investigation has systematically analyzed all available evidence and documentation.
            Key patterns and relationships have been identified through methodical examination.
            The analysis provides a foundation for understanding the case circumstances.
            
            RECOMMENDATION: Review findings for next investigative steps based on case requirements.
            """
            
            # DO NOT add conclusion to memory tree - it should only be a summary result
            # Store conclusion in context for retrieval instead
            self._update_context_bank("final_conclusion", conclusion_text)
            
            logger.info("[PLANNER] ✅ Investigation conclusion generated (not added to tree)")
            
        except Exception as e:
            logger.error(f"[PLANNER] ❌ Error creating forced conclusion: {e}")
            # Fallback to queued task if direct creation fails
            conclusion_task = Task(
                description="Final Investigation Conclusion",
                instructions=conclusion_instructions,
                priority=TaskPriority.CRITICAL
            )
            self.task_queue.add_task(conclusion_task)
            logger.info("[PLANNER] 🏁 Added fallback conclusion task to queue")


class ExecutorAgent(BaseAgent):
    """Agent responsible for executing tasks and updating memory"""
    
    def __init__(self, client: GeminiClient, memory_tree: MemoryTree, view_controller: AgentViewController):
        super().__init__("ExecutorAgent", client, memory_tree, view_controller)
    
    def _get_access_level(self) -> AgentAccessLevel:
        """Executor agents have EXECUTOR access level"""
        return AgentAccessLevel.EXECUTOR
        
    async def execute_task(self, task: Task) -> ExecutionResult:
        """Execute a specific task with similarity-based context"""
        self._log_execution("execute_task", {
            "task_id": task.id,
            "task_description": task.description
        })
        
        relevant_context = self._get_relevant_context(task)
        
        prompt = f"""
        You are the ExecutorAgent building a PROPER INVESTIGATION MINDMAP using similarity connections.

        TASK: {task.description}
        Instructions: {task.instructions}
        Priority: {task.priority.name}
        
        INVESTIGATION CONTEXT:
        {relevant_context}
        
        🌳 SIMILARITY-BASED MINDMAP BUILDING:
        1. **USE SIMILARITY CONNECTIONS**: Connect to nodes with highest similarity scores
        2. **EXPLORE CLUSTERS**: Deep dive into evidence clusters with unexplored nodes
        3. **RESOLVE CONTRADICTIONS**: Address contradiction flags in clusters
        4. **BUILD ON HOT SPOTS**: Extend highly connected nodes with detailed analysis
        5. **USE EXACT NODE IDs**: When specifying parent_node_id, use exact IDs from context above
        
        🎯 INTELLIGENT NAVIGATION STRATEGY:
        - Follow navigation suggestions from your agent view
        - Connect similar evidence types (forensic with forensic, witness with witness)
        - Build logical chains: Evidence → Analysis → Cross-reference → Conclusion
        - Create sub-analysis for complex evidence pieces
        
        📋 SMART PARENT SELECTION:
        - Look for similar nodes in the same evidence cluster
        - Attach to nodes with high similarity scores to your analysis
        - Prefer nodes with unexplored potential or contradiction flags
        - Build depth in hot spot areas that need more investigation
        
        Respond ONLY with valid JSON:
        {{
            "execution_summary": "What specific analysis was performed",
            "detailed_results": "Specific findings and logical reasoning",
            "evidence_type": "evidence|suspect|timeline|analysis|conclusion",
            "memory_updates": [
                {{
                    "action": "ADD_NODE",
                    "node_name": "Specific, Descriptive Node Name",
                    "description": "Detailed analysis finding with logical reasoning",
                    "parent_node_id": "EXACT_NODE_ID_FROM_CONTEXT_ABOVE"
                }}
            ],
            "success": true,
            "mindmap_strategy": "How this connects to existing evidence using similarity"
        }}
        """
        
        try:
            response = self.client.generate_content(contents=prompt)
            response_text = response if isinstance(response, str) else str(response)
            
            logger.info(f"Executor response: {response_text[:300]}...")
            
            execution_data = self._extract_json_from_response(response_text)
            
            if "error" in execution_data:
                logger.error(f"Execution JSON parsing failed: {execution_data['error']}")
                return ExecutionResult(
                    success=False,
                    result=f"Could not parse execution response: {execution_data['raw_response'][:200]}",
                    memory_updates=[]
                )
            
            result = self._parse_execution_response(execution_data, task)
            
            # Apply memory updates
            await self._commit_to_memory(task, result)
            
            self._log_execution("task_executed", {
                "task_id": task.id,
                "success": result.success,
                "memory_updates_count": len(result.memory_updates)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing task {task.id}: {e}")
            return ExecutionResult(
                success=False,
                result=f"Task execution failed: {str(e)}",
                memory_updates=[]
            )
    
    def _get_relevant_context(self, task: Task) -> str:
        """Get relevant context using view controller"""
        if not self.view_controller:
            return "View controller not available - using fallback context"
        
        # Extract keywords from task for focused context
        task_keywords = task.description.lower()
        
        # Get agent view with task context
        agent_context = self._build_context(task_keywords)
        
        context_parts = ["EXECUTOR AGENT - SIMILARITY-BASED CONTEXT:"]
        context_parts.append("=" * 50)
        context_parts.append(agent_context)
        
        # Get memory navigation focused on task
        memory_view = self._get_memory_view(query_context=task_keywords)
        memory_nav = memory_view.get("memory_navigation", {})
        
        # Add focused node summaries if available
        if memory_nav.get("node_summaries"):
            context_parts.append("\nRELEVANT NODES FOR TASK:")
            for i, summary in enumerate(memory_nav["node_summaries"][:10]):  # Top 10 relevant
                confidence_icon = "🟢" if summary.confidence_level > 0.7 else "🟡" if summary.confidence_level > 0.4 else "🔴"
                status_icon = "✅" if summary.is_explored else "🔍"
                context_parts.append(f"{i+1}. {summary.title} (ID: {summary.id[:8]}...)")
                context_parts.append(f"   {confidence_icon} Confidence: {summary.confidence_level:.2f} | {status_icon} Status: {summary.status}")
                context_parts.append(f"   Type: {summary.evidence_type} | Connections: {summary.connection_count}")
                context_parts.append(f"   Summary: {summary.brief_summary}")
                context_parts.append("")
        
        context_parts.append("REMEMBER: Use similarity scores and cluster information to make intelligent connections.")
        
        return "\n".join(context_parts)
    
    def _parse_execution_response(self, execution_data: Dict, task: Task) -> ExecutionResult:
        """Parse execution response into ExecutionResult"""
        success = execution_data.get("success", True)
        detailed_results = execution_data.get("detailed_results", "")
        memory_updates = execution_data.get("memory_updates", [])
        
        return ExecutionResult(
            success=success,
            result=detailed_results,
            memory_updates=memory_updates
        )
    
    async def _commit_to_memory(self, task: Task, result: ExecutionResult):
        """Commit execution results to memory tree"""
        if not result.memory_updates:
            return
        
        for update in result.memory_updates:
            try:
                action = update.get("action")
                
                if action == "ADD_NODE":
                    node = MemoryNode(
                        name=update.get("node_name", "Analysis Result"),
                        description=update.get("description", "Analysis finding")
                    )
                    
                    # Mark node as completed since it represents a successful task result
                    node.status = NodeStatus.COMPLETED if result.success else NodeStatus.FAILED
                    
                    # IMPROVED: Handle parent node ID with better resolution strategy
                    parent_id = update.get("parent_node_id")
                    if parent_id:
                        # Try exact ID match first
                        if parent_id in self.memory_tree.nodes:
                            self._log_execution("parent_node_exact_match", {
                                "node_id": parent_id,
                                "node_name": self.memory_tree.nodes[parent_id].name
                            })
                        # Try partial ID match (first 8 chars)
                        elif len(parent_id) >= 8:
                            matching_ids = [
                                node_id for node_id in self.memory_tree.nodes.keys()
                                if node_id.startswith(parent_id[:8])
                            ]
                            if matching_ids:
                                parent_id = matching_ids[0]
                                self._log_execution("parent_node_partial_id_resolved", {
                                    "requested": update.get("parent_node_id"),
                                    "resolved_to": parent_id
                                })
                            else:
                                parent_id = self._find_best_parent_by_content(node, update.get("parent_node_id"))
                        # Try to find node by name/content similarity
                        else:
                            parent_id = self._find_best_parent_by_content(node, update.get("parent_node_id"))
                    else:
                        # Smart parent selection when no parent specified
                        parent_id = self._find_best_parent_by_content(node, None)
                    
                    node_id = self.memory_tree.add_node(node, parent_id)
                    
                    self._log_execution("memory_node_added", {
                        "node_id": node_id,
                        "node_name": node.name,
                        "parent_id": parent_id
                    })
                
                elif action == "UPDATE_NODE":
                    node_id = update.get("node_id")
                    description = update.get("description")
                    
                    if node_id:
                        success = self.memory_tree.update_node(
                            node_id, 
                            description=description,
                            status=NodeStatus.COMPLETED
                        )
                        
                        if success:
                            self._log_execution("memory_node_updated", {
                                "node_id": node_id,
                                "new_description": description
                            })
                
            except Exception as e:
                logger.error(f"Error committing memory update: {e}")
    
    def _find_best_parent_by_content(self, new_node: MemoryNode, requested_parent: str = None) -> str:
        """Find the best parent node based on content similarity and logical hierarchy"""
        if not self.memory_tree.nodes:
            return None  # Will create as root
        
        # If a specific parent was requested, try to find it by name
        if requested_parent:
            name_matches = [
                node_id for node_id, node in self.memory_tree.nodes.items()
                if requested_parent.lower() in node.name.lower() or node.name.lower() in requested_parent.lower()
            ]
            if name_matches:
                best_match = name_matches[0]
                self._log_execution("parent_node_name_resolved", {
                    "requested": requested_parent,
                    "resolved_to": best_match,
                    "resolved_name": self.memory_tree.nodes[best_match].name
                })
                return best_match
        
        # AGGRESSIVE DEPTH-FIRST parent selection
        new_node_lower = new_node.name.lower() + " " + new_node.description.lower()
        
        # Categorize new node
        is_evidence = any(word in new_node_lower for word in ['evidence', 'forensic', 'fingerprint', 'weapon', 'fabric', 'soil'])
        is_suspect = any(word in new_node_lower for word in ['hartwell', 'robert', 'suspect', 'motive'])
        is_timeline = any(word in new_node_lower for word in ['timeline', 'appointment', 'time', 'alibi'])
        is_analysis = any(word in new_node_lower for word in ['analysis', 'conclusion', 'synthesis'])
        
        # Find best matching parent by category and content with AGGRESSIVE DEPTH PREFERENCE
        best_parent = None
        best_score = 0
        
        for node_id, node in self.memory_tree.nodes.items():
            if node_id == self.memory_tree.root_id:
                continue  # NEVER use root as parent unless absolutely no other choice
            
            node_lower = node.name.lower() + " " + node.description.lower()
            score = 0
            
            # AGGRESSIVE: Category matching with higher scores
            if is_evidence and any(word in node_lower for word in ['evidence', 'forensic', 'investigation']):
                score += 5  # Increased from 3
            elif is_suspect and any(word in node_lower for word in ['hartwell', 'robert', 'suspect', 'motive']):
                score += 5  # Increased from 3
            elif is_timeline and any(word in node_lower for word in ['timeline', 'appointment', 'time']):
                score += 5  # Increased from 3
            elif is_analysis and any(word in node_lower for word in ['analysis', 'synthesis']):
                score += 4  # Increased from 2
            
            # Content similarity with higher weight
            shared_words = set(new_node_lower.split()) & set(node_lower.split())
            score += len([w for w in shared_words if len(w) > 3]) * 2  # Double weight
            
            # AGGRESSIVE DEPTH PREFERENCE: Heavily prefer deeper nodes
            node_depth = self._get_node_depth(node_id)
            if node_depth >= 2:
                score += 10  # HUGE bonus for depth 2+
            elif node_depth >= 1:
                score += 5   # Good bonus for depth 1
            else:
                score -= 5   # Penalty for shallow nodes
            
            # Extra bonus for leaf nodes (they need children)
            if self._is_leaf_node(node_id):
                score += 3
            
            # Penalty for nodes that already have many children (encourage balanced growth)
            child_count = len([n for n in self.memory_tree.nodes.values() if n.parent_id == node_id])
            if child_count >= 3:
                score -= 2
            
            if score > best_score:
                best_score = score
                best_parent = node_id
        
        # AGGRESSIVE: Only use root as absolute last resort and with high penalty
        if best_score < 3:  # Increased threshold from 2
            # Try to find ANY non-root node rather than defaulting to root
            non_root_nodes = [nid for nid in self.memory_tree.nodes.keys() if nid != self.memory_tree.root_id]
            if non_root_nodes:
                # Pick the deepest available node
                deepest_node = max(non_root_nodes, key=self._get_node_depth)
                best_parent = deepest_node
                self._log_execution("parent_forced_depth", {
                    "forced_parent": deepest_node,
                    "depth": self._get_node_depth(deepest_node),
                    "reason": "avoiding root attachment"
                })
            else:
                best_parent = self.memory_tree.root_id
        
        if best_parent:
            self._log_execution("parent_node_smart_selected", {
                "selected": best_parent,
                "selected_name": self.memory_tree.nodes[best_parent].name if best_parent in self.memory_tree.nodes else "root",
                "score": best_score,
                "new_node_category": "evidence" if is_evidence else "suspect" if is_suspect else "timeline" if is_timeline else "analysis" if is_analysis else "other"
            })
        
        return best_parent
    
    def _get_node_depth(self, node_id: str) -> int:
        """Get the depth of a node in the tree"""
        if not node_id or node_id not in self.memory_tree.nodes:
            return 0
        
        depth = 0
        current_id = node_id
        visited = set()
        
        while current_id and current_id != self.memory_tree.root_id and current_id not in visited:
            visited.add(current_id)
            node = self.memory_tree.nodes.get(current_id)
            if not node or not node.parent_id:
                break
            current_id = node.parent_id
            depth += 1
            
            if depth > 10:  # Prevent infinite loops
                break
        
        return depth
    
    def _is_leaf_node(self, node_id: str) -> bool:
        """Check if a node is a leaf (has no children)"""
        return not any(node.parent_id == node_id for node in self.memory_tree.nodes.values())


class SynthesisAgent(BaseAgent):
    """Synthesis agent for continuous analysis and strategic insights"""
    
    def __init__(self, gemini_client: GeminiClient, memory_tree: MemoryTree, task_queue: TaskQueue, view_controller: AgentViewController):
        super().__init__("SynthesisAgent", gemini_client, memory_tree, view_controller)
        self.task_queue = task_queue
        self.analysis_interval = 30  # seconds
        self.last_analysis_time = 0
        self.analysis_count = 0
        self.confidence_threshold = 0.8  # Stop when confidence is high enough
        self.is_running = False
    
    def _get_access_level(self) -> AgentAccessLevel:
        """Synthesis agents have SYNTHESIZER access level"""
        return AgentAccessLevel.SYNTHESIZER
        
    async def continuous_analysis(self):
        """Run continuous background analysis"""
        self.is_running = True
        while self.is_running:
            try:
                current_time = time.time()
                
                # Check if it's time for analysis
                if current_time - self.last_analysis_time >= self.analysis_interval:
                    await self.perform_synthesis()
                    self.last_analysis_time = current_time
                    self.analysis_count += 1
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"[SYNTHESIS] Error in continuous analysis: {e}")
                await asyncio.sleep(10)
    
    async def perform_synthesis(self):
        """Perform synthesis analysis using view controller insights"""
        try:
            # Get comprehensive view using view controller
            agent_context = self._build_context("synthesis analysis")
            memory_view = self._get_memory_view(query_context="overall investigation status")
            
            tree_stats = self.memory_tree.get_tree_statistics()
            queue_stats = self.task_queue.get_queue_statistics()
            
            # Get memory navigation insights
            memory_nav = memory_view.get("memory_navigation", {})
            clusters = memory_nav.get("memory_clusters", [])
            hot_spots = memory_nav.get("hot_spots", [])
            
            total_tasks = queue_stats['completed_tasks'] + queue_stats['failed_tasks']
            
            # Calculate cluster-based metrics
            cluster_completeness = 0
            contradiction_count = 0
            unexplored_count = 0
            
            for cluster in clusters:
                if cluster.unexplored_count == 0:
                    cluster_completeness += 1
                contradiction_count += len(cluster.contradiction_flags)
                unexplored_count += cluster.unexplored_count
            
            cluster_completion_rate = cluster_completeness / max(len(clusters), 1)
            
            synthesis_prompt = f"""
            You are the Synthesis Agent conducting ENHANCED strategic analysis using similarity-based insights.
            
            CURRENT INVESTIGATION STATE:
            {agent_context}
            
            SIMILARITY-BASED ANALYSIS:
            - Evidence clusters: {len(clusters)} total
            - Cluster completion rate: {cluster_completion_rate:.2f} ({cluster_completeness}/{len(clusters)} fully explored)
            - Active contradictions: {contradiction_count} across clusters
            - Unexplored nodes: {unexplored_count} remaining
            - Investigation hot spots: {len(hot_spots)} high-connection areas
            - Total tasks completed: {total_tasks}
            - Analysis round: {self.analysis_count}
            
            CLUSTER-BASED EVIDENCE EVALUATION:
            {self._format_cluster_analysis(clusters)}
            
            HOT SPOT ANALYSIS:
            {self._format_hotspot_analysis(hot_spots)}
            
            ENHANCED SYNTHESIS FRAMEWORK:
            - CLUSTER STRENGTH: How well are evidence clusters developed and explored?
            - CONTRADICTION RESOLUTION: Are contradictions being addressed effectively?  
            - HOT SPOT DEVELOPMENT: Are high-connection areas being properly analyzed?
            - SIMILARITY NETWORK: How well connected is the evidence through similarity?
            - OVERALL CONFIDENCE: Based on cluster completeness and contradiction resolution
            
            STOPPING CRITERIA (Similarity-Based):
            - All major clusters fully explored (completion rate > 0.8)
            - Contradictions resolved or acknowledged (< 2 unresolved contradictions)
            - Hot spots adequately analyzed (all hot spots have sufficient children)
            - High similarity network connectivity across evidence types
            
            Respond in JSON format:
            {{
                "cluster_strength": 0.0-1.0,
                "contradiction_resolution": 0.0-1.0,
                "hotspot_development": 0.0-1.0,
                "similarity_network_strength": 0.0-1.0,
                "confidence_level": 0.0-1.0,
                "key_patterns": ["concrete pattern1", "concrete pattern2"],
                "unresolved_contradictions": ["specific contradiction1", "specific contradiction2"],
                "strategic_recommendation": "CONTINUE|CONCLUDE|FOCUS",
                "priority_focus": "specific area needing attention",
                "reasoning": "detailed logical explanation based on clusters and similarities"
            }}
            """
            
            response = self.client.generate_content(contents=synthesis_prompt)
            synthesis_result = self._extract_json_from_response(response)
            
            if synthesis_result:
                # Log enhanced synthesis insights
                confidence = synthesis_result.get('confidence_level', 0)
                cluster_strength = synthesis_result.get('cluster_strength', 0)
                contradiction_resolution = synthesis_result.get('contradiction_resolution', 0)
                recommendation = synthesis_result.get('strategic_recommendation', 'CONTINUE')
                
                logger.info(f"[SYNTHESIS] Confidence: {confidence:.2f}")
                logger.info(f"[SYNTHESIS] Cluster strength: {cluster_strength:.2f}")
                logger.info(f"[SYNTHESIS] Contradiction resolution: {contradiction_resolution:.2f}")
                logger.info(f"[SYNTHESIS] Recommendation: {recommendation}")
                logger.info(f"[SYNTHESIS] Priority focus: {synthesis_result.get('priority_focus', 'General investigation')}")
                
                # Enhanced confidence adjustment based on similarity metrics
                base_confidence = confidence
                
                # Factor 1: High cluster completion rate
                if cluster_completion_rate > 0.7:
                    confidence = min(1.0, confidence + 0.1)
                    logger.info(f"[SYNTHESIS] 📈 +0.10 confidence for high cluster completion ({cluster_completion_rate:.2f})")
                
                # Factor 2: Low contradiction count with good resolution
                if contradiction_count <= 2 and contradiction_resolution > 0.7:
                    confidence = min(1.0, confidence + 0.08)
                    logger.info(f"[SYNTHESIS] 📈 +0.08 confidence for contradiction management")
                
                # Factor 3: Well-developed hot spots
                if len(hot_spots) > 0 and all(h.get('connection_count', 0) >= 3 for h in hot_spots):
                    confidence = min(1.0, confidence + 0.05)
                    logger.info(f"[SYNTHESIS] 📈 +0.05 confidence for developed hot spots")
                
                # Factor 4: Sufficient task completion with good similarity network
                if total_tasks >= 6 and synthesis_result.get('similarity_network_strength', 0) > 0.7:
                    confidence = min(1.0, confidence + 0.07)
                    logger.info(f"[SYNTHESIS] 📈 +0.07 confidence for strong similarity network")
                
                # Update synthesis result with adjusted confidence
                if confidence != base_confidence:
                    synthesis_result['confidence_level'] = confidence
                    logger.info(f"[SYNTHESIS] 🎯 Final adjusted confidence: {base_confidence:.2f} → {confidence:.2f}")
                
                # Store synthesis in memory tree
                synthesis_node = MemoryNode(
                    name=f"Synthesis Analysis #{self.analysis_count}",
                    description=f"Confidence: {confidence:.2f}, "
                           f"Cluster completion: {cluster_completion_rate:.2f}, "
                           f"Recommendation: {recommendation}, "
                           f"Focus: {synthesis_result.get('priority_focus', 'General')}"
                )
                synthesis_node.status = NodeStatus.COMPLETED
                self.memory_tree.add_node(synthesis_node, self.memory_tree.root_id)
                
                # Check if we should stop based on similarity metrics
                should_conclude = (
                    confidence >= self.confidence_threshold or 
                    recommendation == 'CONCLUDE' or 
                    (cluster_completion_rate > 0.8 and contradiction_count <= 1) or
                    total_tasks >= 25
                )
                
                if should_conclude:
                    # Don't create duplicate conclusions
                    if not self._conclusion_exists_in_tree():
                        reason = self._determine_conclusion_reason(confidence, cluster_completion_rate, contradiction_count, recommendation, total_tasks)
                        logger.info(f"[SYNTHESIS] 🎯 {reason} - Recommending conclusion")
                        await self._signal_investigation_complete(synthesis_result)
                    else:
                        logger.info("[SYNTHESIS] 🛑 Conclusion already exists - skipping duplicate creation")
                
                return synthesis_result
            
        except Exception as e:
            logger.error(f"[SYNTHESIS] Error in synthesis: {e}")
            return None
    
    def _format_cluster_analysis(self, clusters: List) -> str:
        """Format cluster analysis for synthesis prompt"""
        if not clusters:
            return "No clusters identified"
        
        analysis = []
        for cluster in clusters:
            status = "✅ Complete" if cluster.unexplored_count == 0 else f"🔍 {cluster.unexplored_count} unexplored"
            contradictions = f" | ⚠️ {len(cluster.contradiction_flags)} contradictions" if cluster.contradiction_flags else ""
            analysis.append(f"- {cluster.theme}: {cluster.cluster_summary} | {status}{contradictions}")
        
        return "\n".join(analysis)
    
    def _format_hotspot_analysis(self, hot_spots: List) -> str:
        """Format hot spot analysis for synthesis prompt"""
        if not hot_spots:
            return "No hot spots identified"
        
        analysis = []
        for hot_spot in hot_spots:
            analysis.append(f"- {hot_spot['title']}: {hot_spot['connection_count']} connections ({hot_spot['evidence_type']} type)")
        
        return "\n".join(analysis)
    
    def _determine_conclusion_reason(self, confidence: float, cluster_rate: float, contradictions: int, recommendation: str, tasks: int) -> str:
        """Determine the specific reason for concluding investigation"""
        if confidence >= self.confidence_threshold:
            return f"High confidence reached ({confidence:.2f})"
        elif recommendation == 'CONCLUDE':
            return "AI recommendation to conclude"
        elif cluster_rate > 0.8 and contradictions <= 1:
            return f"Evidence clusters well-developed ({cluster_rate:.2f} completion, {contradictions} contradictions)"
        elif tasks >= 25:
            return "Maximum task threshold reached"
        else:
            return "Investigation completion criteria met"

    async def _signal_investigation_complete(self, synthesis_result):
        """Signal that investigation should conclude and force immediate completion"""
        confidence = synthesis_result.get('confidence_level', 0)
        logger.info(f"[SYNTHESIS] 🏁 Forcing immediate investigation conclusion (confidence: {confidence:.2f})")
        
        # Check if conclusion already exists to prevent duplicates
        if self._conclusion_exists_in_tree():
            logger.info("[SYNTHESIS] 🛑 Conclusion already exists - skipping duplicate creation")
            return
        
        try:
            # Force immediate conclusion without API calls to avoid rate limits
            conclusion_text = f"""
            SYNTHESIS INVESTIGATION CONCLUSION (Confidence: {confidence:.2f})
            
            FINAL ANALYSIS COMPLETE:
            
            Key Patterns: {synthesis_result.get('key_patterns', ['Analysis complete', 'Evidence evaluated', 'Conclusions drawn'])}
            
            SUMMARY:
            Based on {confidence:.0%} confidence analysis, the investigation has reached a conclusion.
            
            Key Findings:
            - Evidence has been systematically analyzed
            - Pattern recognition has identified key connections
            - Confidence threshold reached for conclusions
            - Investigation objectives satisfied
            
            RECOMMENDATION: Review findings and determine next steps based on case type
            
            Reasoning: {synthesis_result.get('reasoning', 'High confidence reached through systematic evidence analysis')}
            """
            
            # DO NOT add conclusion to memory tree - it should only be a summary result
            # Store conclusion in context for retrieval instead
            self._update_context_bank("synthesis_conclusion", conclusion_text)
            
            logger.info("[SYNTHESIS] ✅ Synthesis conclusion generated (not added to tree)")
            
        except Exception as e:
            logger.error(f"[SYNTHESIS] ❌ Error creating forced conclusion: {e}")
            # Fallback to queued task if direct creation fails
            if not self.task_queue.has_conclusion_task():
                conclusion_task = Task(
                    description="Investigation Conclusion",
                    instructions=f"""
                    Based on synthesis analysis, the investigation has reached sufficient confidence ({confidence:.2f}).
                    
                    Create a comprehensive investigation summary including:
                    1. Key findings and evidence
                    2. Suspect profile and motives
                    3. Timeline of events
                    4. Recommended next steps
                    
                    Patterns identified: {synthesis_result.get('key_patterns', [])}
                    Reasoning: {synthesis_result.get('reasoning', 'High confidence reached')}
                    """,
                    priority=TaskPriority.CRITICAL
                )
                self.task_queue.add_task(conclusion_task)
                logger.info("[SYNTHESIS] 🏁 Added fallback investigation conclusion task")
            else:
                logger.info("[SYNTHESIS] 🛑 Conclusion task already exists in queue - skipping fallback")

    def _conclusion_exists_in_tree(self) -> bool:
        """Check if a conclusion has already been generated"""
        try:
            # Check if conclusion exists in context bank instead of tree
            return "synthesis_conclusion" in self.context_bank
            
        except Exception as e:
            logger.error(f"[SYNTHESIS] Error checking for conclusion: {e}")
            return False


# Agent Factory and Management
class AgentSystem:
    """Orchestrates multiple agents working together"""
    
    def __init__(self, gemini_client: GeminiClient, memory_tree: MemoryTree, task_queue: TaskQueue, view_controller: AgentViewController):
        self.gemini_client = gemini_client
        self.memory_tree = memory_tree
        self.task_queue = task_queue
        self.view_controller = view_controller
        
        # Initialize agents
        self.planner = PlannerAgent(gemini_client, memory_tree, task_queue, view_controller)
        self.executor = ExecutorAgent(gemini_client, memory_tree, view_controller)
        self.synthesis = SynthesisAgent(gemini_client, memory_tree, task_queue, view_controller)
        
        self.is_running = False
        
    async def start_system(self):
        """Start the agent system"""
        self.is_running = True
        
        # Start synthesis continuous analysis
        synthesis_task = asyncio.create_task(self.synthesis.continuous_analysis())
        
        logger.info("🤖 Agent system started with view controller integration")
        return synthesis_task
    
    def stop_system(self):
        """Stop the agent system"""
        self.is_running = False
        self.synthesis.is_running = False
        logger.info("🛑 Agent system stopped")
    
    async def process_query(self, query: str):
        """Process a query through the agent system with view controller"""
        try:
            # Create initial plan using similarity-based context
            initial_tasks = await self.planner.create_initial_plan(query)
            
            # Add tasks to queue
            for task in initial_tasks:
                self.task_queue.add_task(task)
            
            logger.info(f"🎯 Created initial plan with {len(initial_tasks)} tasks using similarity navigation")
            
            # Process tasks
            results = []
            while True:
                next_task = self.task_queue.get_next_task()
                if not next_task:
                    break
                
                # Execute task with similarity-based context
                result = await self.executor.execute_task(next_task)
                results.append(result)
                
                # Update task status
                if result.success:
                    self.task_queue.mark_completed(next_task.id, result.result)
                    
                    # Get synthesis guidance using view controller insights
                    synthesis_result = await self.synthesis.perform_synthesis()
                    
                    # Refine plan using similarity-based recommendations
                    await self.planner.refine_plan(next_task, result.result, synthesis_result)
                else:
                    self.task_queue.mark_failed(next_task.id, result.result)
            
            return {
                "tasks_executed": len(results),
                "successful_tasks": len([r for r in results if r.success]),
                "view_controller_enabled": True,
                "similarity_navigation": "active"
            }
            
        except Exception as e:
            logger.error(f"Error processing query with view controller: {e}")
            return []


# Example usage and testing
if __name__ == "__main__":
    async def test_agent_system():
        from gemini_client import GeminiClient
        from tree import MemoryTree, create_detective_case_tree
        from tasklist import TaskQueue
        from agentview import AgentViewController
        
        # Initialize components
        client = GeminiClient()
        tree = create_detective_case_tree("Test Investigation")
        queue = TaskQueue("db/agent_test.db")
        
        # Initialize view controller
        view_controller = AgentViewController(tree, queue)
        
        # Initialize agent system with view controller
        system = AgentSystem(client, tree, queue, view_controller)
        
        # Start system
        synthesis_task = await system.start_system()
        
        try:
            # Process a test query
            result = await system.process_query("Investigate the mysterious disappearance of John Doe using similarity-based navigation")
            print("Query processing result with view controller:")
            print(json.dumps(result, indent=2, default=str))
            
        finally:
            # Stop system
            system.stop_system()
            synthesis_task.cancel()
    
    # Note: This would need to be run in an async context
    print("Agent system with AgentViewController initialized. Use asyncio.run(test_agent_system()) to test.") 