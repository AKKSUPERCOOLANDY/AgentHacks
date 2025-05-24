#!/usr/bin/env python3
"""
Agent View Controller - Similarity-Based Memory Navigation System

Controls what files and memory tree content each agent type can see.
Implements a mindmap-style navigation rather than forced tree traversal.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class AgentAccessLevel(Enum):
    """Different access levels for agents"""
    PLANNER = "planner"          # Can see task queue + memory navigation
    EXECUTOR = "executor"        # Memory navigation + file access
    SYNTHESIZER = "synthesizer"  # Task queue + full memory analysis
    SUMMARIZATION = "summarization"  # Read-only memory access


@dataclass
class NodeSummary:
    """Compressed view of a memory node"""
    id: str
    title: str
    brief_summary: str
    evidence_type: str
    confidence_level: float
    timestamp: datetime
    connection_count: int
    status: str
    is_explored: bool = False


@dataclass
class ConnectionInfo:
    """Information about connections between nodes"""
    target_node_id: str
    connection_type: str
    similarity_score: float
    relationship_description: str


@dataclass
class MemoryCluster:
    """Group of related memory nodes"""
    cluster_id: str
    theme: str
    node_ids: List[str]
    cluster_summary: str
    contradiction_flags: List[str]
    unexplored_count: int


class AgentViewController:
    """Controls agent access to files and memory tree"""
    
    def __init__(self, memory_tree, task_queue, case_files_path="case_files/"):
        self.memory_tree = memory_tree
        self.task_queue = task_queue
        self.case_files_path = case_files_path
        
        # Agent focus tracking
        self.agent_focus_contexts: Dict[str, Dict] = {}
        
        # Similarity cache for performance
        self.similarity_cache: Dict[str, List[ConnectionInfo]] = {}
        
        # Available case files
        self.available_files = [
            "forensic_report.txt",
            "police_report.txt", 
            "witness_statement_robert.txt"
        ]
    
    def get_agent_view(self, agent_id: str, agent_type: AgentAccessLevel, 
                      focus_node_id: Optional[str] = None, 
                      query_context: Optional[str] = None) -> Dict[str, Any]:
        """Get customized view for specific agent type"""
        
        view = {
            "agent_id": agent_id,
            "agent_type": agent_type.value,
            "timestamp": datetime.now().isoformat(),
            "available_files": self._get_file_access(agent_type),
            "memory_navigation": self._get_memory_navigation(agent_type, focus_node_id, query_context),
            "task_access": self._get_task_access(agent_type)
        }
        
        # Update agent focus context
        self._update_agent_focus(agent_id, focus_node_id, query_context)
        
        return view
    
    def _get_file_access(self, agent_type: AgentAccessLevel) -> List[Dict[str, str]]:
        """Get file access based on agent type"""
        if agent_type in [AgentAccessLevel.EXECUTOR, AgentAccessLevel.SYNTHESIZER]:
            return [
                {
                    "filename": filename,
                    "description": self._get_file_description(filename),
                    "access_level": "read_only"
                }
                for filename in self.available_files
            ]
        
        # Planner and Summarization agents get file descriptions only
        return [
            {
                "filename": filename,
                "description": self._get_file_description(filename),
                "access_level": "metadata_only"
            }
            for filename in self.available_files
        ]
    
    def _get_file_description(self, filename: str) -> str:
        """Get file description for agent context"""
        descriptions = {
            "forensic_report.txt": "Forensic analysis including fingerprints, DNA, and physical evidence",
            "police_report.txt": "Official incident report with timeline and initial investigation notes",
            "witness_statement_robert.txt": "Eyewitness testimony from Robert Chen"
        }
        return descriptions.get(filename, "Case file")
    
    def _get_memory_navigation(self, agent_type: AgentAccessLevel, 
                              focus_node_id: Optional[str], 
                              query_context: Optional[str]) -> Dict[str, Any]:
        """Get similarity-based memory navigation view"""
        
        # Get all nodes as summaries
        node_summaries = self._generate_node_summaries()
        
        # Generate memory clusters
        clusters = self._generate_memory_clusters(node_summaries)
        
        # Get focused view if focus node provided
        focused_view = None
        if focus_node_id:
            focused_view = self._generate_focused_view(focus_node_id, query_context)
        
        # Find hot spots (highly connected areas)
        hot_spots = self._identify_hot_spots(node_summaries)
        
        return {
            "total_nodes": len(node_summaries),
            "node_summaries": node_summaries[:20],  # Limit initial view
            "memory_clusters": clusters,
            "focused_view": focused_view,
            "hot_spots": hot_spots,
            "navigation_suggestions": self._generate_navigation_suggestions(agent_type, query_context)
        }
    
    def _generate_node_summaries(self) -> List[NodeSummary]:
        """Generate compressed summaries of all memory nodes"""
        summaries = []
        
        if not self.memory_tree or not hasattr(self.memory_tree, 'nodes'):
            return summaries
        
        for node in self.memory_tree.nodes.values():
            summary = NodeSummary(
                id=node.id,
                title=self._clean_node_title(node.name),
                brief_summary=self._create_brief_summary(node.description),
                evidence_type=self._classify_evidence_type(node.name, node.description),
                confidence_level=self._calculate_confidence(node),
                timestamp=node.created_at,
                connection_count=len(node.children_ids),
                status=node.status.value if hasattr(node.status, 'value') else str(node.status),
                is_explored=bool(node.execution_result)
            )
            summaries.append(summary)
        
        # Sort by relevance/recency
        summaries.sort(key=lambda x: (x.confidence_level, x.timestamp), reverse=True)
        return summaries
    
    def _clean_node_title(self, raw_title: str) -> str:
        """Clean and format node titles for better readability"""
        # Remove common prefixes
        cleaned = raw_title
        prefixes_to_remove = [
            "Evidence Analysis:",
            "Task:",
            "Investigation:",
            "Analysis:"
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        return cleaned
    
    def _create_brief_summary(self, description: str) -> str:
        """Create brief summary from full description"""
        if not description:
            return "No details available"
        
        # Take first sentence or first 100 characters
        sentences = description.split('.')
        if sentences and len(sentences[0]) <= 100:
            return sentences[0].strip() + "."
        
        return description[:97] + "..." if len(description) > 100 else description
    
    def _classify_evidence_type(self, name: str, description: str) -> str:
        """Classify evidence type based on content"""
        combined_text = (name + " " + description).lower()
        
        type_keywords = {
            "forensic": ["fingerprint", "dna", "blood", "forensic", "lab", "analysis"],
            "witness": ["witness", "testimony", "statement", "saw", "observed"],
            "physical": ["weapon", "fabric", "object", "found", "collected"],
            "timeline": ["time", "when", "sequence", "chronology", "timeline"],
            "location": ["where", "scene", "location", "room", "place"],
            "suspect": ["suspect", "person", "individual", "accused"],
            "motive": ["motive", "reason", "why", "cause"],
            "contradiction": ["but", "however", "inconsistent", "differs"]
        }
        
        for evidence_type, keywords in type_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                return evidence_type
        
        return "general"
    
    def _calculate_confidence(self, node) -> float:
        """Calculate confidence level for a node"""
        confidence = 0.5  # Base confidence
        
        # Boost confidence based on completion status
        if hasattr(node, 'status'):
            if str(node.status) == "completed":
                confidence += 0.3
            elif str(node.status) == "in_progress":
                confidence += 0.1
        
        # Boost based on having execution results
        if node.execution_result:
            confidence += 0.2
        
        # Boost based on connections
        if hasattr(node, 'children_ids') and len(node.children_ids) > 0:
            confidence += min(0.2, len(node.children_ids) * 0.05)
        
        return min(1.0, confidence)
    
    def _generate_memory_clusters(self, summaries: List[NodeSummary]) -> List[MemoryCluster]:
        """Generate clusters of related memory nodes"""
        clusters = []
        
        # Group by evidence type
        type_groups = {}
        for summary in summaries:
            if summary.evidence_type not in type_groups:
                type_groups[summary.evidence_type] = []
            type_groups[summary.evidence_type].append(summary)
        
        for evidence_type, group_summaries in type_groups.items():
            if len(group_summaries) > 1:  # Only create clusters with multiple nodes
                cluster = MemoryCluster(
                    cluster_id=f"cluster_{evidence_type}",
                    theme=evidence_type.title(),
                    node_ids=[s.id for s in group_summaries],
                    cluster_summary=f"{len(group_summaries)} nodes related to {evidence_type}",
                    contradiction_flags=self._find_contradictions(group_summaries),
                    unexplored_count=len([s for s in group_summaries if not s.is_explored])
                )
                clusters.append(cluster)
        
        return clusters
    
    def _find_contradictions(self, summaries: List[NodeSummary]) -> List[str]:
        """Find potential contradictions in a group of summaries"""
        contradictions = []
        
        # Look for contradictory keywords
        contradiction_patterns = [
            (["positive", "found"], ["negative", "not found"]),
            (["present", "exists"], ["absent", "missing"]),
            (["confirmed", "verified"], ["unconfirmed", "disputed"])
        ]
        
        for pattern_a, pattern_b in contradiction_patterns:
            nodes_a = [s for s in summaries if any(p in s.brief_summary.lower() for p in pattern_a)]
            nodes_b = [s for s in summaries if any(p in s.brief_summary.lower() for p in pattern_b)]
            
            if nodes_a and nodes_b:
                contradictions.append(f"Contradiction: {len(nodes_a)} nodes vs {len(nodes_b)} nodes")
        
        return contradictions
    
    def _generate_focused_view(self, focus_node_id: str, query_context: Optional[str]) -> Dict[str, Any]:
        """Generate focused view around a specific node"""
        if focus_node_id not in self.memory_tree.nodes:
            return None
        
        focus_node = self.memory_tree.nodes[focus_node_id]
        
        # Get similar nodes based on content similarity
        similar_nodes = self._find_similar_nodes(focus_node, query_context)
        
        # Get immediate connections
        immediate_connections = self._get_immediate_connections(focus_node_id)
        
        return {
            "focus_node": {
                "id": focus_node.id,
                "title": self._clean_node_title(focus_node.name),
                "full_content": focus_node.description,
                "metadata": {
                    "status": focus_node.status.value if hasattr(focus_node.status, 'value') else str(focus_node.status),
                    "created": focus_node.created_at.isoformat(),
                    "evidence_type": self._classify_evidence_type(focus_node.name, focus_node.description)
                }
            },
            "similar_nodes": similar_nodes,
            "immediate_connections": immediate_connections,
            "suggested_exploration": self._suggest_exploration_paths(focus_node, query_context)
        }
    
    def _find_similar_nodes(self, focus_node, query_context: Optional[str], limit: int = 5) -> List[Dict]:
        """Find nodes similar to focus node"""
        similar = []
        
        focus_content = (focus_node.name + " " + focus_node.description).lower()
        focus_keywords = set(re.findall(r'\b\w+\b', focus_content))
        
        for node in self.memory_tree.nodes.values():
            if node.id == focus_node.id:
                continue
            
            node_content = (node.name + " " + node.description).lower()
            node_keywords = set(re.findall(r'\b\w+\b', node_content))
            
            # Calculate similarity based on keyword overlap
            overlap = len(focus_keywords.intersection(node_keywords))
            total_keywords = len(focus_keywords.union(node_keywords))
            similarity = overlap / max(total_keywords, 1)
            
            if similarity > 0.1:  # Minimum similarity threshold
                similar.append({
                    "id": node.id,
                    "title": self._clean_node_title(node.name),
                    "brief_summary": self._create_brief_summary(node.description),
                    "similarity_score": similarity,
                    "connection_reason": self._explain_connection(focus_keywords, node_keywords)
                })
        
        # Sort by similarity and return top results
        similar.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similar[:limit]
    
    def _explain_connection(self, keywords1: Set[str], keywords2: Set[str]) -> str:
        """Explain why two nodes are connected"""
        common_keywords = keywords1.intersection(keywords2)
        important_keywords = [k for k in common_keywords if len(k) > 3 and k not in ['the', 'and', 'that', 'this']]
        
        if important_keywords:
            return f"Shared concepts: {', '.join(list(important_keywords)[:3])}"
        return "Related content"
    
    def _get_immediate_connections(self, node_id: str) -> List[Dict]:
        """Get immediate parent/child connections"""
        connections = []
        node = self.memory_tree.nodes[node_id]
        
        # Parent connection
        if node.parent_id and node.parent_id in self.memory_tree.nodes:
            parent = self.memory_tree.nodes[node.parent_id]
            connections.append({
                "type": "parent",
                "id": parent.id,
                "title": self._clean_node_title(parent.name),
                "relationship": "builds upon"
            })
        
        # Child connections
        for child_id in node.children_ids:
            if child_id in self.memory_tree.nodes:
                child = self.memory_tree.nodes[child_id]
                connections.append({
                    "type": "child",
                    "id": child.id,
                    "title": self._clean_node_title(child.name),
                    "relationship": "leads to"
                })
        
        return connections
    
    def _suggest_exploration_paths(self, focus_node, query_context: Optional[str]) -> List[str]:
        """Suggest exploration paths from current node"""
        suggestions = []
        
        # Based on evidence type
        evidence_type = self._classify_evidence_type(focus_node.name, focus_node.description)
        
        type_suggestions = {
            "forensic": ["Look for witness corroboration", "Check physical evidence connections"],
            "witness": ["Cross-reference with forensic evidence", "Look for timeline conflicts"],
            "timeline": ["Verify with witness statements", "Check for gaps or overlaps"],
            "suspect": ["Examine motive evidence", "Check alibis and whereabouts"],
            "physical": ["Look for chain of custody", "Check for similar evidence"]
        }
        
        suggestions.extend(type_suggestions.get(evidence_type, ["Explore related nodes"]))
        
        # Add query-specific suggestions
        if query_context:
            suggestions.append(f"Explore connections related to: {query_context}")
        
        return suggestions[:3]  # Limit to top 3 suggestions
    
    def _identify_hot_spots(self, summaries: List[NodeSummary]) -> List[Dict]:
        """Identify areas with high connection density"""
        hot_spots = []
        
        # Find nodes with high connection counts
        high_connection_nodes = [s for s in summaries if s.connection_count > 2]
        
        for summary in high_connection_nodes:
            hot_spots.append({
                "node_id": summary.id,
                "title": summary.title,
                "connection_count": summary.connection_count,
                "evidence_type": summary.evidence_type,
                "reason": f"Hub node with {summary.connection_count} connections"
            })
        
        return hot_spots[:5]  # Top 5 hot spots
    
    def _generate_navigation_suggestions(self, agent_type: AgentAccessLevel, 
                                       query_context: Optional[str]) -> List[str]:
        """Generate navigation suggestions for agent type"""
        base_suggestions = [
            "Start with high-confidence nodes",
            "Explore unexplored clusters",
            "Look for contradiction flags"
        ]
        
        type_specific = {
            AgentAccessLevel.PLANNER: [
                "Focus on gaps in investigation",
                "Identify areas needing more analysis"
            ],
            AgentAccessLevel.EXECUTOR: [
                "Deep dive into specific evidence",
                "Cross-reference multiple sources"
            ],
            AgentAccessLevel.SYNTHESIZER: [
                "Look for patterns across clusters",
                "Identify conflicting evidence"
            ]
        }
        
        suggestions = base_suggestions + type_specific.get(agent_type, [])
        
        if query_context:
            suggestions.insert(0, f"Search for nodes related to: {query_context}")
        
        return suggestions
    
    def _get_task_access(self, agent_type: AgentAccessLevel) -> Optional[Dict]:
        """Get task queue access based on agent type"""
        if agent_type in [AgentAccessLevel.PLANNER, AgentAccessLevel.SYNTHESIZER]:
            if self.task_queue:
                stats = self.task_queue.get_queue_statistics()
                return {
                    "access_level": "full",
                    "queue_stats": stats,
                    "can_modify": agent_type == AgentAccessLevel.PLANNER
                }
        
        return {
            "access_level": "none",
            "message": "Task queue access restricted for this agent type"
        }
    
    def _update_agent_focus(self, agent_id: str, focus_node_id: Optional[str], 
                           query_context: Optional[str]):
        """Update agent's focus context for better suggestions"""
        if agent_id not in self.agent_focus_contexts:
            self.agent_focus_contexts[agent_id] = {
                "focus_history": [],
                "query_history": [],
                "last_updated": datetime.now()
            }
        
        context = self.agent_focus_contexts[agent_id]
        
        if focus_node_id:
            context["focus_history"].append({
                "node_id": focus_node_id,
                "timestamp": datetime.now()
            })
            # Keep only last 10 focus points
            context["focus_history"] = context["focus_history"][-10:]
        
        if query_context:
            context["query_history"].append({
                "query": query_context,
                "timestamp": datetime.now()
            })
            # Keep only last 5 queries
            context["query_history"] = context["query_history"][-5:]
        
        context["last_updated"] = datetime.now()
    
    def request_node_content(self, agent_id: str, node_id: str, 
                           agent_type: AgentAccessLevel) -> Optional[Dict]:
        """Request full content for a specific node"""
        if node_id not in self.memory_tree.nodes:
            return None
        
        node = self.memory_tree.nodes[node_id]
        
        # Log the request for analytics
        logger.info(f"[AGENT_VIEW] {agent_type.value} agent {agent_id} requested node {node_id}")
        
        return {
            "id": node.id,
            "title": self._clean_node_title(node.name),
            "full_content": node.description,
            "execution_result": node.execution_result,
            "metadata": {
                "status": node.status.value if hasattr(node.status, 'value') else str(node.status),
                "created": node.created_at.isoformat(),
                "evidence_type": self._classify_evidence_type(node.name, node.description),
                "confidence": self._calculate_confidence(node)
            },
            "connections": self._get_immediate_connections(node_id),
            "similar_nodes": self._find_similar_nodes(node, None, 3)
        } 