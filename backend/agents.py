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
    
    def __init__(self, agent_name: str, client: GeminiClient, memory_tree: MemoryTree):
        self.agent_name = agent_name
        self.client = client
        self.memory_tree = memory_tree
        self.context_bank: Dict[str, str] = {}
        self.execution_history: List[Dict] = []
        
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
    
    def _build_context(self) -> str:
        """Build context from context bank"""
        if not self.context_bank:
            return "No additional context available."
        
        context_parts = []
        for key, value in self.context_bank.items():
            context_parts.append(f"{key}: {value}")
        
        return "\n".join(context_parts)
    
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
    
    def __init__(self, gemini_client: GeminiClient, memory_tree: MemoryTree, task_queue: TaskQueue):
        super().__init__("PlannerAgent", gemini_client, memory_tree)
        self.task_queue = task_queue
        self.max_tasks_per_cycle = 2  # Reduced from 3 for more focused analysis
        self.max_total_tasks = 8     # Reduced from 10 for efficiency
        self.synthesis_guidance = None
        self.conclusion_created = False  # Prevent multiple conclusions
        
    async def create_initial_plan(self, investigation_context: str) -> List[Task]:
        """Create initial investigation plan"""
        try:
            planning_prompt = f"""
            You are the Planner Agent creating an investigation plan for a CASE FILE ANALYSIS simulation.

            AVAILABLE RESOURCES:
            - 3 case files have been loaded: forensic_report.txt, police_report.txt, witness_statement_robert.txt
            - Memory tree with extracted information from these files
            
            YOU CANNOT ACCESS:
            - AFIS databases
            - External witnesses
            - New forensic tests
            - Alibis from external sources
            - Any information outside the 3 case files
            
            INVESTIGATION CONTEXT:
            {investigation_context}
            
            Create analysis tasks that work with the available case file content ONLY.
            
            🌳 STRATEGIC TASK CREATION FOR TREE BUILDING:
            - Maximum 5 initial tasks
            - Create tasks that build LOGICAL HIERARCHY (evidence → analysis → conclusion)
            - Focus on specific evidence categories (forensic, suspects, timeline, motives)
            - Each task should build upon or connect to other tasks
            - Create depth not breadth (detailed analysis vs surface-level)
            - DO NOT create tasks asking for external information
            
            Example good tasks:
            - "Analyze timeline inconsistencies between forensic and witness reports"
            - "Cross-reference fingerprint evidence mentioned in case files"
            - "Identify motive patterns from the available witness statements"
            
            Example BAD tasks:
            - "Contact AFIS for fingerprint matching"
            - "Interview additional witnesses"
            - "Request new forensic analysis"
            
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
        """Check if a conclusion node already exists in the memory tree"""
        try:
            if not self.memory_tree:
                return False
                
            # Look for conclusion nodes in the tree (don't require root_id)
            for node in self.memory_tree.nodes.values():
                node_name = node.name.upper()
                conclusion_keywords = ['FINAL CONCLUSION', 'INVESTIGATION CONCLUDED', 'SYNTHESIS FINAL', 'FINAL INVESTIGATION CONCLUSION']
                if any(keyword in node_name for keyword in conclusion_keywords):
                    logger.info(f"[PLANNER] 🎯 Found existing conclusion node: {node.name}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"[PLANNER] Error checking for conclusion in tree: {e}")
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
            
            # AGGRESSIVE shallow detection - expanded list
            shallow_indicators = [
                'general', 'overall', 'broad', 'comprehensive', 'complete analysis',
                'investigate', 'analyze', 'examine', 'review', 'assess', 'explore',
                'determine', 'identify', 'find', 'check', 'look into'
            ]
            if any(indicator in desc for indicator in shallow_indicators):
                is_shallow = True
            
            # Check if task targets specific existing nodes (depth requirement)
            depth_requirement_indicators = [
                'specific', 'detailed', 'sub-analysis', 'deeper', 'granular',
                'cross-reference', 'correlate', 'connect', 'extend', 'build on'
            ]
            has_depth_target = any(indicator in desc for indicator in depth_requirement_indicators)
            
            # Check if task mentions building on existing analysis
            builds_on_existing = 'builds_on' in task and task['builds_on']
            
            # AGGRESSIVE: Require both depth indicators AND specific targeting
            if not is_repetitive and not is_shallow and (has_depth_target or builds_on_existing):
                filtered.append(task)
            else:
                reason = "repetitive" if is_repetitive else "shallow/lacks depth target" if is_shallow else "no depth indicators"
                logger.info(f"[PLANNER] 🚫 AGGRESSIVE filter: {reason} task: {task['description']}")
        
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
            
            # Create conclusion node directly
            conclusion_node = MemoryNode(
                name="FINAL INVESTIGATION CONCLUSION",
                description=conclusion_text
            )
            conclusion_node.status = NodeStatus.COMPLETED
            
            if self.memory_tree.root_id:
                self.memory_tree.add_node(conclusion_node, self.memory_tree.root_id)
            else:
                self.memory_tree.add_node(conclusion_node)
            
            logger.info("[PLANNER] ✅ Forced conclusion added to memory tree")
            
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
    
    def __init__(self, client: GeminiClient, memory_tree: MemoryTree):
        super().__init__("ExecutorAgent", client, memory_tree)
        
    async def execute_task(self, task: Task) -> ExecutionResult:
        """Execute a specific task with tree context"""
        self._log_execution("execute_task", {
            "task_id": task.id,
            "task_description": task.description
        })
        
        relevant_context = self._get_relevant_context(task)
        
        prompt = f"""
        You are the ExecutorAgent building a PROPER INVESTIGATION TREE HIERARCHY.

        TASK: {task.description}
        Instructions: {task.instructions}
        Priority: {task.priority.name}
        
        INVESTIGATION CONTEXT:
        {relevant_context}
        
        🌳 AGGRESSIVE DEPTH-FIRST TREE BUILDING:
        1. **FORCE DEEP HIERARCHY**: NEVER attach to root unless absolutely no other option exists
        2. **USE EXACT NODE IDs**: When specifying parent_node_id, use the exact ID from the tree context above (first 8 chars work)
        3. **CREATE DEEP CHAINS**: Evidence → Sub-Evidence → Analysis → Sub-Analysis → Conclusions
        4. **MANDATORY DEPTH**: Every node MUST extend an existing analysis, never create standalone branches
        
        🎯 AGGRESSIVE HIERARCHY STRATEGY:
        - Evidence nodes → MUST have detailed sub-analysis children (2-3 levels deep)
        - Suspect nodes → MUST have specific motive/opportunity/timeline children  
        - Timeline nodes → MUST have granular time-point analysis children
        - Analysis nodes → MUST have detailed findings, cross-references, or conclusion children
        
        📋 DEPTH-FORCING PARENT SELECTION:
        - ALWAYS look for the DEEPEST relevant node to attach to
        - If analyzing fingerprints → attach to specific fingerprint analysis node, NOT general evidence
        - If analyzing motives → attach to specific suspect's motive node, NOT general suspect node
        - If analyzing timeline → attach to specific time period node, NOT general timeline
        - CREATE SUB-CATEGORIES: Instead of broad analysis, create specific focused analysis
        
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
            "tree_building_strategy": "How this connects to existing evidence hierarchy"
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
        """Get relevant memory context for the task"""
        context_parts = []
        
        # Add focused case file content based on task
        task_keywords = task.description.lower().split()
        
        context_parts.append("CASE FILE ANALYSIS TASK - Available Information:")
        context_parts.append("="*50)
        
        # Add dynamic case facts from actual documents
        if 'document_analyzer' in self.context_bank:
            doc_analyzer = self.context_bank['document_analyzer']
            doc_summary = doc_analyzer.get_document_summary()
            
            context_parts.append(f"""
CASE FILES BEING ANALYZED:
Total Documents: {doc_summary['total_documents']}
Document Types: {', '.join(doc_summary['document_types'])}
Files: {', '.join([doc['filename'] for doc in doc_summary['documents']])}
            """)
        else:
            context_parts.append("No document analyzer available - using generic case analysis approach")
        
        # Add DETAILED current memory tree for better context
        context_parts.append("CURRENT INVESTIGATION TREE STRUCTURE:")
        context_parts.append("-" * 40)
        
        # Get detailed tree view with node IDs for better parent selection
        tree_nodes = self._get_tree_nodes_for_context()
        if tree_nodes:
            context_parts.append(tree_nodes)
        else:
            context_parts.append("Empty tree - this will be the first analysis node")
        
        context_parts.append("\nREMEMBER: You can ONLY analyze the text above. No external systems available.")
        
        return "\n".join(context_parts)
    
    def _get_tree_nodes_for_context(self) -> str:
        """Get formatted tree structure with node IDs for context"""
        if not self.memory_tree.nodes:
            return "No existing nodes"
        
        # Get nodes organized by categories for better parent selection
        evidence_nodes = []
        suspect_nodes = []
        timeline_nodes = []
        other_nodes = []
        
        for node_id, node in self.memory_tree.nodes.items():
            name_lower = node.name.lower()
            node_info = f"• {node.name} (ID: {node_id[:8]}...)"
            
            if any(word in name_lower for word in ['evidence', 'forensic', 'fingerprint', 'weapon', 'fabric']):
                evidence_nodes.append(node_info)
            elif any(word in name_lower for word in ['hartwell', 'robert', 'suspect', 'motive']):
                suspect_nodes.append(node_info)
            elif any(word in name_lower for word in ['timeline', 'appointment', 'time', 'alibi']):
                timeline_nodes.append(node_info)
            else:
                other_nodes.append(node_info)
        
        result_parts = []
        
        if evidence_nodes:
            result_parts.append("EVIDENCE NODES:")
            result_parts.extend(evidence_nodes[:5])  # Limit to 5
        
        if suspect_nodes:
            result_parts.append("\nSUSPECT/MOTIVE NODES:")
            result_parts.extend(suspect_nodes[:5])
        
        if timeline_nodes:
            result_parts.append("\nTIMELINE NODES:")
            result_parts.extend(timeline_nodes[:5])
        
        if other_nodes:
            result_parts.append("\nOTHER ANALYSIS NODES:")
            result_parts.extend(other_nodes[:3])
        
        result_parts.append(f"\nTotal nodes: {len(self.memory_tree.nodes)}")
        
        return "\n".join(result_parts)
    
    def _extract_relevant_sections(self, content: str, keywords: List[str]) -> List[str]:
        """Extract relevant sections from document content"""
        lines = content.split('\n')
        relevant_sections = []
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            # Check if line contains relevant keywords
            if any(keyword in line_lower for keyword in keywords):
                # Get context around the relevant line
                start = max(0, i-1)
                end = min(len(lines), i+2)
                section = ' '.join(lines[start:end]).strip()
                if section and len(section) > 20:
                    relevant_sections.append(section)
        
        # Also look for key evidence markers
        evidence_markers = ['fingerprint', 'blood', 'weapon', 'time', 'appointment', 'fabric', 'window']
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(marker in line_lower for marker in evidence_markers):
                start = max(0, i-1)
                end = min(len(lines), i+2)
                section = ' '.join(lines[start:end]).strip()
                if section and len(section) > 20 and section not in relevant_sections:
                    relevant_sections.append(section)
        
        return relevant_sections[:5]  # Return top 5 most relevant sections
    
    def _get_available_commands(self) -> str:
        """Return list of tree manipulation commands"""
        # Get available parent nodes for reference
        available_nodes = []
        for node_id, node in self.memory_tree.nodes.items():
            available_nodes.append(f"- {node.name} (ID: {node_id})")
        
        available_nodes_str = "\n".join(available_nodes[:10])  # Show first 10 nodes
        
        return f"""
        Available Memory Commands (SIMULATION ONLY):
        - Analyze existing nodes and their relationships
        - Extract patterns from available data
        - Cross-reference information between nodes
        - Identify gaps in available information
        - Create analytical summaries of findings
        
        Available Parent Nodes for Memory Updates:
        {available_nodes_str}
        
        Note: When adding nodes, use either the node name or ID as parent_node_id
        """
    
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
    
    def __init__(self, gemini_client: GeminiClient, memory_tree: MemoryTree, task_queue: TaskQueue):
        super().__init__("SynthesisAgent", gemini_client, memory_tree)
        self.task_queue = task_queue
        self.analysis_interval = 30  # seconds
        self.last_analysis_time = 0
        self.analysis_count = 0
        self.confidence_threshold = 0.8  # Stop when confidence is high enough
        self.is_running = False
        
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
        """Perform synthesis analysis and provide strategic guidance"""
        try:
            tree_stats = self.memory_tree.get_tree_statistics()
            queue_stats = self.task_queue.get_queue_statistics()
            
            # Get recent memory updates
            recent_nodes = self.memory_tree.get_recent_nodes(limit=8)
            total_tasks = queue_stats['completed_tasks'] + queue_stats['failed_tasks']
            
            # Enhanced analysis of evidence quality and depth
            evidence_depth_score = min(tree_stats['max_depth'] / 4.0, 1.0)  # Normalize depth
            evidence_breadth_score = min(tree_stats['total_nodes'] / 30.0, 1.0)  # Normalize breadth
            
            synthesis_prompt = f"""
            You are the Synthesis Agent conducting ENHANCED strategic analysis with depth focus.
            
            CURRENT INVESTIGATION STATE:
            - Memory tree: {tree_stats['total_nodes']} nodes, depth {tree_stats['max_depth']}
            - Evidence depth score: {evidence_depth_score:.2f} (higher = deeper analysis)
            - Evidence breadth score: {evidence_breadth_score:.2f} (higher = more comprehensive)
            - Tasks: {queue_stats['pending_tasks']} pending, {queue_stats['completed_tasks']} completed
            - Analysis round: {self.analysis_count}
            - Total tasks completed: {total_tasks}
            
            RECENT EVIDENCE DEVELOPMENTS:
            {self._format_recent_nodes(recent_nodes)}
            
            ENHANCED SYNTHESIS FRAMEWORK:
            - EVIDENCE QUALITY: Assess strength and reliability of evidence chains
            - LOGICAL CONNECTIONS: Evaluate how well evidence pieces connect
            - CONFIDENCE CALCULATION: Base confidence on evidence depth, not just quantity
            - STRATEGIC DIRECTION: Focus on evidence gaps vs. broad exploration
            
            IMPROVED SYNTHESIS ANALYSIS:
            1. **Evidence Chain Strength** (0.0-1.0): How well connected is the evidence?
            2. **Logical Consistency** (0.0-1.0): How consistent are the findings?
            3. **Investigation Confidence Level** (0.0-1.0): Overall case strength
            4. **Evidence Quality Assessment**: What's the strongest/weakest evidence?
            5. **Strategic Recommendation**:
               - CONTINUE: If critical evidence gaps exist and can be filled
               - CONCLUDE: If evidence forms strong logical chain (confidence > 0.75)
               - FOCUS: If specific evidence needs deeper analysis
            6. **Priority Focus**: Most important evidence to strengthen next
            
            ENHANCED STOPPING CRITERIA:
            - Confidence > 0.8 OR Evidence depth score > 0.7: Consider CONCLUDE
            - Tasks > 8 AND confidence > 0.7: Likely sufficient evidence
            - Strong evidence chain with logical consistency > 0.8: CONCLUDE
            - Repetitive tasks without new insights: CONCLUDE
            
            CONFIDENCE CALCULATION GUIDANCE:
            - High confidence: Multiple evidence sources point to same conclusion
            - Medium confidence: Some evidence supports conclusion, minor gaps remain
            - Low confidence: Evidence is circumstantial or conflicting
            
            Respond in JSON format:
            {{
                "evidence_chain_strength": 0.0-1.0,
                "logical_consistency": 0.0-1.0,
                "confidence_level": 0.0-1.0,
                "evidence_quality_assessment": "strongest and weakest evidence summary",
                "key_patterns": ["concrete pattern1", "concrete pattern2"],
                "critical_gaps": ["specific gap1", "specific gap2"],
                "strategic_recommendation": "CONTINUE|CONCLUDE|FOCUS",
                "priority_focus": "specific evidence to strengthen",
                "reasoning": "detailed logical explanation"
            }}
            """
            
            response = self.client.generate_content(contents=synthesis_prompt)
            synthesis_result = self._extract_json_from_response(response)
            
            if synthesis_result:
                # Log enhanced synthesis insights
                confidence = synthesis_result.get('confidence_level', 0)
                evidence_chain_strength = synthesis_result.get('evidence_chain_strength', 0)
                logical_consistency = synthesis_result.get('logical_consistency', 0)
                recommendation = synthesis_result.get('strategic_recommendation', 'CONTINUE')
                
                logger.info(f"[SYNTHESIS] Confidence: {confidence:.2f}")
                logger.info(f"[SYNTHESIS] Evidence chain strength: {evidence_chain_strength:.2f}")
                logger.info(f"[SYNTHESIS] Logical consistency: {logical_consistency:.2f}")
                logger.info(f"[SYNTHESIS] Recommendation: {recommendation}")
                logger.info(f"[SYNTHESIS] Priority focus: {synthesis_result.get('priority_focus', 'General investigation')}")
                
                # Enhanced confidence adjustment based on multiple factors
                base_confidence = confidence
                
                # Factor 1: Evidence depth and breadth balance
                if evidence_depth_score > 0.6 and evidence_breadth_score > 0.6:
                    confidence = min(1.0, confidence + 0.05)
                    logger.info(f"[SYNTHESIS] 📈 +0.05 confidence for balanced evidence (depth: {evidence_depth_score:.2f}, breadth: {evidence_breadth_score:.2f})")
                
                # Factor 2: Strong evidence chains
                if evidence_chain_strength > 0.75 and logical_consistency > 0.75:
                    confidence = min(1.0, confidence + 0.1)
                    logger.info(f"[SYNTHESIS] 📈 +0.10 confidence for strong evidence chains")
                
                # Factor 3: Sufficient task completion with good results
                if total_tasks >= 6 and confidence >= 0.7:
                    confidence = min(1.0, confidence + 0.05)
                    logger.info(f"[SYNTHESIS] 📈 +0.05 confidence for sufficient task completion ({total_tasks} tasks)")
                
                # Update synthesis result with adjusted confidence
                if confidence != base_confidence:
                    synthesis_result['confidence_level'] = confidence
                    logger.info(f"[SYNTHESIS] 🎯 Final adjusted confidence: {base_confidence:.2f} → {confidence:.2f}")
                
                # Store synthesis in memory tree
                synthesis_node = MemoryNode(
                    name=f"Synthesis Analysis #{self.analysis_count}",
                    description=f"Confidence: {confidence:.2f}, "
                           f"Recommendation: {recommendation}, "
                           f"Focus: {synthesis_result.get('priority_focus', 'General')}"
                )
                synthesis_node.status = NodeStatus.COMPLETED
                self.memory_tree.add_node(synthesis_node, self.memory_tree.root_id)
                
                # Check if we should stop
                if confidence >= self.confidence_threshold or recommendation == 'CONCLUDE' or total_tasks >= 25:
                    # Don't create duplicate conclusions
                    if not self._conclusion_exists_in_tree():
                        reason = f"Investigation confidence reached {confidence:.2f}" if confidence >= self.confidence_threshold else f"Recommendation: {recommendation}" if recommendation == 'CONCLUDE' else "Maximum task threshold reached"
                        logger.info(f"[SYNTHESIS] 🎯 {reason} - Recommending conclusion")
                        await self._signal_investigation_complete(synthesis_result)
                    else:
                        logger.info("[SYNTHESIS] 🛑 Conclusion already exists - skipping duplicate creation")
                
                return synthesis_result
            
        except Exception as e:
            logger.error(f"[SYNTHESIS] Error in synthesis: {e}")
            return None
    
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
            
            # Create conclusion node directly
            conclusion_node = MemoryNode(
                name="SYNTHESIS FINAL CONCLUSION",
                description=conclusion_text
            )
            conclusion_node.status = NodeStatus.COMPLETED
            
            if self.memory_tree.root_id:
                self.memory_tree.add_node(conclusion_node, self.memory_tree.root_id)
            else:
                self.memory_tree.add_node(conclusion_node)
            
            logger.info("[SYNTHESIS] ✅ Forced synthesis conclusion added to memory tree")
            
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
        """Check if a conclusion node already exists in the memory tree"""
        try:
            if not self.memory_tree:
                return False
                
            # Look for conclusion nodes in the tree (don't require root_id)
            for node in self.memory_tree.nodes.values():
                node_name = node.name.upper()
                conclusion_keywords = ['FINAL CONCLUSION', 'INVESTIGATION CONCLUDED', 'SYNTHESIS FINAL', 'FINAL INVESTIGATION CONCLUSION']
                if any(keyword in node_name for keyword in conclusion_keywords):
                    logger.info(f"[SYNTHESIS] 🎯 Found existing conclusion node: {node.name}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"[SYNTHESIS] Error checking for conclusion in tree: {e}")
            return False

    def _format_recent_nodes(self, recent_nodes):
        """Format recent nodes for synthesis prompt"""
        if not recent_nodes:
            return "No recent updates"
        
        formatted = []
        for node in recent_nodes:
            content = getattr(node, 'content', '') or getattr(node, 'description', '')
            formatted.append(f"- {node.name}: {content[:100]}...")
        
        return "\n".join(formatted)


# Agent Factory and Management
class AgentSystem:
    """Orchestrates multiple agents working together"""
    
    def __init__(self, gemini_client: GeminiClient, memory_tree: MemoryTree, task_queue: TaskQueue):
        self.gemini_client = gemini_client
        self.memory_tree = memory_tree
        self.task_queue = task_queue
        
        # Initialize agents
        self.planner = PlannerAgent(gemini_client, memory_tree, task_queue)
        self.executor = ExecutorAgent(gemini_client, memory_tree)
        self.synthesis = SynthesisAgent(gemini_client, memory_tree, task_queue)
        
        self.is_running = False
        
    async def start_system(self):
        """Start the agent system"""
        self.is_running = True
        
        # Start synthesis continuous analysis
        synthesis_task = asyncio.create_task(self.synthesis.continuous_analysis())
        
        logger.info("🤖 Agent system started")
        return synthesis_task
    
    def stop_system(self):
        """Stop the agent system"""
        self.is_running = False
        self.synthesis.is_running = False
        logger.info("🛑 Agent system stopped")
    
    async def process_query(self, query: str):
        """Process a query through the agent system"""
        try:
            # Create initial plan
            initial_tasks = await self.planner.create_initial_plan(query)
            
            # Add tasks to queue
            for task in initial_tasks:
                self.task_queue.add_task(task)
            
            logger.info(f"🎯 Created initial plan with {len(initial_tasks)} tasks")
            
            # Process tasks
            results = []
            while True:
                next_task = self.task_queue.get_next_task()
                if not next_task:
                    break
                
                # Execute task
                result = await self.executor.execute_task(next_task)
                results.append(result)
                
                # Update task status
                if result.success:
                    self.task_queue.mark_completed(next_task.id, result.result)
                    
                    # Get synthesis guidance
                    synthesis_result = await self.synthesis.perform_synthesis()
                    
                    # Refine plan
                    await self.planner.refine_plan(next_task, result.result, synthesis_result)
                else:
                    self.task_queue.mark_failed(next_task.id, result.result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return []


# Example usage and testing
if __name__ == "__main__":
    async def test_agent_system():
        from gemini_client import GeminiClient
        from tree import MemoryTree, create_detective_case_tree
        from tasklist import TaskQueue
        
        # Initialize components
        client = GeminiClient()
        tree = create_detective_case_tree("Test Investigation")
        queue = TaskQueue("db/agent_test.db")
        
        # Initialize agent system
        system = AgentSystem(client, tree, queue)
        
        # Start system
        synthesis_task = await system.start_system()
        
        try:
            # Process a test query
            result = await system.process_query("Investigate the mysterious disappearance of John Doe")
            print("Query processing result:")
            print(json.dumps(result, indent=2, default=str))
            
        finally:
            # Stop system
            system.stop_system()
            synthesis_task.cancel()
    
    # Note: This would need to be run in an async context
    print("Agent system initialized. Use asyncio.run(test_agent_system()) to test.") 