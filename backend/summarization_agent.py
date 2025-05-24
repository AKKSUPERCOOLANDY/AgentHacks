#!/usr/bin/env python3
"""
Dedicated Summarization Agent for Case Investigation Analysis
Generates comprehensive summaries from memory tree data
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SummarizationAgent:
    """
    Specialized agent that generates comprehensive case summaries
    from the investigation memory tree and analysis results
    """
    
    def __init__(self, gemini_client, memory_tree, task_queue=None):
        self.gemini_client = gemini_client
        self.memory_tree = memory_tree
        self.task_queue = task_queue
        self.agent_name = "SummarizationAgent"
        
    async def generate_comprehensive_summary(self, analysis_results=None, final_conclusion=None) -> Dict[str, Any]:
        """Generate a comprehensive case summary from all available data"""
        try:
            # Gather all data sources
            tree_data = self._extract_tree_intelligence()
            evidence_analysis = self._analyze_evidence_patterns()
            suspect_analysis = self._analyze_suspects_and_motives()
            timeline_analysis = self._reconstruct_timeline()
            
            # Generate AI-powered insights
            ai_insights = await self._generate_ai_insights(tree_data)
            
            # Compile comprehensive summary - CONCLUSION FIRST for better UX
            summary = {
                "conclusion": self._generate_final_conclusion(final_conclusion),
                "case_status": self._determine_case_status(),
                "investigation_confidence": self._calculate_confidence_score(),
                "case_overview": self._build_case_overview(),
                "analysis_metrics": self._build_analysis_metrics(),
                "key_findings": self._extract_key_findings(tree_data),
                "evidence_summary": evidence_analysis,
                "suspect_analysis": suspect_analysis,
                "timeline_reconstruction": timeline_analysis,
                "ai_insights": ai_insights,
                "next_steps": self._recommend_next_steps()
            }
            
            logger.info(f"[{self.agent_name}] Generated comprehensive summary with {len(summary['key_findings'])} findings")
            return summary
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error generating summary: {e}")
            return self._generate_fallback_summary(final_conclusion)
    
    def _extract_tree_intelligence(self) -> Dict[str, Any]:
        """Extract structured intelligence from the memory tree"""
        if not self.memory_tree:
            return {}
            
        try:
            nodes = list(self.memory_tree.nodes.values())  # Use .nodes attribute instead
            tree_data = {
                "total_nodes": len(nodes),
                "evidence_nodes": [],
                "analysis_nodes": [],
                "witness_nodes": [],
                "suspect_nodes": [],
                "timeline_nodes": []
            }
            
            for node in nodes:
                node_name = node.name.lower()
                node_data = {
                    "id": node.id,
                    "name": node.name,
                    "description": node.description,
                    "status": node.status.value if hasattr(node.status, 'value') else str(node.status)
                }
                
                if any(keyword in node_name for keyword in ['evidence', 'fingerprint', 'fabric', 'physical']):
                    tree_data["evidence_nodes"].append(node_data)
                elif any(keyword in node_name for keyword in ['analysis', 'synthesis', 'correlation']):
                    tree_data["analysis_nodes"].append(node_data)
                elif any(keyword in node_name for keyword in ['witness', 'statement', 'testimony']):
                    tree_data["witness_nodes"].append(node_data)
                elif any(keyword in node_name for keyword in ['suspect', 'motive', 'alibi']):
                    tree_data["suspect_nodes"].append(node_data)
                elif any(keyword in node_name for keyword in ['timeline', 'time', 'sequence', 'chronology']):
                    tree_data["timeline_nodes"].append(node_data)
            
            return tree_data
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error extracting tree intelligence: {e}")
            return {}
    
    def _analyze_evidence_patterns(self) -> List[Dict[str, str]]:
        """Analyze evidence patterns and generate structured evidence summary"""
        evidence_summary = []
        
        try:
            tree_data = self._extract_tree_intelligence()
            evidence_nodes = tree_data.get("evidence_nodes", [])
            
            for node in evidence_nodes:
                # Clean up evidence title and extract type
                clean_title = node["name"]
                evidence_type = "Evidence"
                
                # Remove common prefixes and extract type
                if clean_title.startswith("Evidence Analysis:"):
                    clean_title = clean_title.replace("Evidence Analysis:", "").strip()
                    evidence_type = "Analysis"
                
                # Enhanced evidence type detection
                title_lower = clean_title.lower()
                if "fingerprint" in title_lower or "print" in title_lower:
                    evidence_type = "Fingerprint"
                elif "fabric" in title_lower or "cloth" in title_lower or "textile" in title_lower:
                    evidence_type = "Fabric"
                elif "blood" in title_lower or "dna" in title_lower or "biological" in title_lower:
                    evidence_type = "Blood"
                elif "weapon" in title_lower or "paperweight" in title_lower or "crystal" in title_lower:
                    evidence_type = "Weapon"
                elif "footprint" in title_lower or "shoe" in title_lower or "foot" in title_lower:
                    evidence_type = "Footprint"
                elif "window" in title_lower or "entry" in title_lower or "break" in title_lower:
                    evidence_type = "Entry Point"
                elif "statement" in title_lower or "witness" in title_lower or "testimony" in title_lower:
                    evidence_type = "Witness"
                elif "location" in title_lower or "scene" in title_lower or "room" in title_lower:
                    evidence_type = "Location"
                elif "time" in title_lower or "timeline" in title_lower or "chronology" in title_lower:
                    evidence_type = "Timeline"
                
                evidence_summary.append({
                    "id": node["id"],  # Add unique ID for frontend interaction
                    "title": clean_title,  # Cleaned evidence name
                    "type": evidence_type,  # Evidence type for tagging
                    "description": node["description"],  # Full description (frontend will handle display)
                    "status": node["status"]
                })
                
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error analyzing evidence: {e}")
            
        return evidence_summary  # Return all evidence items
    
    def _analyze_suspects_and_motives(self) -> List[Dict[str, str]]:
        """Analyze suspects, motives, and relationships"""
        suspect_analysis = []
        
        try:
            tree_data = self._extract_tree_intelligence()
            suspect_nodes = tree_data.get("suspect_nodes", [])
            witness_nodes = tree_data.get("witness_nodes", [])
            
            # Analyze suspects
            for node in suspect_nodes:
                suspect_analysis.append({
                    "type": "Suspect Analysis",
                    "subject": self._extract_person_name(node["name"]),
                    "analysis": node["description"][:200] + "..." if len(node["description"]) > 200 else node["description"]
                })
            
            # Analyze witness information for suspect intelligence
            for node in witness_nodes:
                if any(keyword in node["description"].lower() for keyword in ['suspect', 'saw', 'observed', 'noticed']):
                    suspect_analysis.append({
                        "type": "Witness Intelligence",
                        "subject": self._extract_person_name(node["name"]),
                        "analysis": node["description"][:200] + "..." if len(node["description"]) > 200 else node["description"]
                    })
                    
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error analyzing suspects: {e}")
            
        return suspect_analysis[:3]  # Return top 3 suspect analyses
    
    def _reconstruct_timeline(self) -> List[Dict[str, str]]:
        """Reconstruct timeline of events from available data"""
        timeline = []
        
        try:
            tree_data = self._extract_tree_intelligence()
            timeline_nodes = tree_data.get("timeline_nodes", [])
            
            for node in timeline_nodes:
                timeline.append({
                    "event": node["name"],
                    "details": node["description"][:150] + "..." if len(node["description"]) > 150 else node["description"],
                    "source": "Investigation Analysis"
                })
                
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error reconstructing timeline: {e}")
            
        return timeline[:5]  # Return top 5 timeline events
    
    def _extract_person_name(self, text: str) -> str:
        """Extract person name from node text"""
        # Simple extraction - look for common name patterns
        words = text.split()
        for i, word in enumerate(words):
            if word.lower() in ['witness', 'statement', 'analysis']:
                if i + 1 < len(words):
                    return words[i + 1]
        return "Unknown Person"
    
    async def _generate_ai_insights(self, tree_data: Dict) -> List[str]:
        """Generate AI-powered insights from tree data"""
        insights = []
        
        try:
            if not self.gemini_client:
                return ["AI insights unavailable - no client connection"]
            
            # Prepare context for AI analysis
            context = f"""
            Based on the investigation data:
            - Total nodes analyzed: {tree_data.get('total_nodes', 0)}
            - Evidence items: {len(tree_data.get('evidence_nodes', []))}
            - Witness statements: {len(tree_data.get('witness_nodes', []))}
            - Suspect analyses: {len(tree_data.get('suspect_nodes', []))}
            
            Generate 3-5 key investigative insights about patterns, connections, and conclusions.
            Focus on who likely committed the murder and why.
            """
            
            prompt = f"""
            You are a criminal investigation AI analyzing a murder case.
            
            {context}
            
            Provide exactly 3-5 bullet points of key insights:
            1. Primary suspect identification
            2. Strongest evidence connections  
            3. Motive analysis
            4. Investigation gaps or next steps
            5. Confidence in conclusions
            
            Format as simple bullet points starting with •
            """
            
            response = self.gemini_client.generate_content(contents=prompt)
            if response:
                lines = str(response).strip().split('\n')
                insights = [line.strip() for line in lines if line.strip().startswith('•')]
                
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error generating AI insights: {e}")
            insights = ["AI analysis pending - processing investigation data"]
            
        return insights[:5]  # Ensure max 5 insights
    
    def _generate_final_conclusion(self, provided_conclusion: str = None) -> str:
        """Generate or enhance the final case conclusion"""
        if provided_conclusion:
            return provided_conclusion
            
        try:
            tree_data = self._extract_tree_intelligence()
            
            if not self.gemini_client:
                return "Investigation analysis completed. All available evidence has been processed and documented."
            
            # Build detailed context with actual evidence content
            evidence_details = []
            for node in tree_data.get('evidence_nodes', []):  # ALL evidence nodes
                evidence_details.append(f"- {node['name']}: {node['description']}")
            
            analysis_details = []
            for node in tree_data.get('analysis_nodes', []):  # ALL analysis nodes
                analysis_details.append(f"- {node['name']}: {node['description']}")
            
            witness_details = []
            for node in tree_data.get('witness_nodes', []):  # ALL witness nodes
                witness_details.append(f"- {node['name']}: {node['description']}")
            
            suspect_details = []
            for node in tree_data.get('suspect_nodes', []):  # ALL suspect nodes
                suspect_details.append(f"- {node['name']}: {node['description']}")
            
            timeline_details = []
            for node in tree_data.get('timeline_nodes', []):  # ALL timeline nodes
                timeline_details.append(f"- {node['name']}: {node['description']}")
            
            context = f"""
MURDER INVESTIGATION COMPLETE - FULL CASE ANALYSIS:

EVIDENCE FINDINGS ({len(tree_data.get('evidence_nodes', []))} items):
{chr(10).join(evidence_details) if evidence_details else "No evidence nodes found"}

ANALYSIS CONCLUSIONS ({len(tree_data.get('analysis_nodes', []))} items):
{chr(10).join(analysis_details) if analysis_details else "No analysis nodes found"}

WITNESS INFORMATION ({len(tree_data.get('witness_nodes', []))} items):
{chr(10).join(witness_details) if witness_details else "No witness nodes found"}

SUSPECT INFORMATION ({len(tree_data.get('suspect_nodes', []))} items):
{chr(10).join(suspect_details) if suspect_details else "No suspect nodes found"}

TIMELINE ANALYSIS ({len(tree_data.get('timeline_nodes', []))} items):
{chr(10).join(timeline_details) if timeline_details else "No timeline nodes found"}
            """
            
            prompt = f"""
You are a detective analyzing a completed murder investigation. Based on the comprehensive evidence below:

{context}

Provide a definitive 3-4 sentence conclusion identifying:
1. WHO likely committed the murder (specific suspect name if mentioned)
2. WHAT the probable motive was 
3. HOW strong the case is for prosecution
4. KEY evidence supporting the conclusion

Write as a confident investigative conclusion based on ALL the evidence provided.
            """
            
            response = self.gemini_client.generate_content(contents=prompt)
            if response:
                return str(response).strip()
                
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error generating conclusion: {e}")
            
        return "Investigation concluded. Analysis indicates strong evidence patterns supporting case resolution."
    
    def _build_case_overview(self) -> Dict[str, Any]:
        """Build case overview section"""
        try:
            # Count available case files
            case_files_dir = "case_files"
            files_analyzed = 0
            document_types = []
            
            if hasattr(self.memory_tree, 'document_analyzer') and self.memory_tree.document_analyzer:
                doc_summary = self.memory_tree.document_analyzer.get_document_summary()
                files_analyzed = doc_summary.get('total_documents', 0)
                document_types = doc_summary.get('document_types', [])
            else:
                # Fallback: check case files directory
                import os
                if os.path.exists(case_files_dir):
                    files_analyzed = len([f for f in os.listdir(case_files_dir) if f.endswith('.txt')])
                    document_types = ['Police Report', 'Witness Statements', 'Evidence Reports']
            
            return {
                "files_analyzed": files_analyzed,
                "document_types": document_types,
                "investigation_type": "Homicide Investigation",
                "case_id": f"CASE-{datetime.now().strftime('%Y%m%d')}"
            }
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error building case overview: {e}")
            return {"files_analyzed": 0, "document_types": [], "investigation_type": "Unknown", "case_id": "UNKNOWN"}
    
    def _build_analysis_metrics(self) -> Dict[str, int]:
        """Build analysis metrics section"""
        try:
            if not self.memory_tree:
                return {"total_nodes_created": 0, "analysis_depth": 0, "tasks_completed": 0, "tasks_failed": 0}
            
            tree_stats = self.memory_tree.get_tree_statistics()
            queue_stats = self.task_queue.get_queue_statistics() if self.task_queue else {}
            
            return {
                "total_nodes_created": tree_stats.get('total_nodes', 0),
                "analysis_depth": tree_stats.get('max_depth', 0),
                "tasks_completed": queue_stats.get('completed_tasks', 0),
                "tasks_failed": queue_stats.get('failed_tasks', 0)
            }
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error building metrics: {e}")
            return {"total_nodes_created": 0, "analysis_depth": 0, "tasks_completed": 0, "tasks_failed": 0}
    
    def _extract_key_findings(self, tree_data: Dict) -> List[Dict[str, str]]:
        """Extract key findings from tree analysis with clean titles"""
        findings = []
        
        try:
            # Generate findings from analysis nodes with clean titles
            analysis_nodes = tree_data.get("analysis_nodes", [])
            for node in analysis_nodes[:3]:  # Top 3 analysis nodes
                # Generate a clean title from the node name
                clean_title = self._generate_clean_title(node["name"], "analysis")
                findings.append({
                    "title": clean_title,
                    "description": node["description"],
                    "source_type": "analysis"
                })
            
            # Add evidence-based findings with clean titles
            evidence_nodes = tree_data.get("evidence_nodes", [])
            for node in evidence_nodes[:2]:  # Top 2 evidence findings
                clean_title = self._generate_clean_title(node["name"], "evidence")
                findings.append({
                    "title": clean_title,
                    "description": node["description"],
                    "source_type": "evidence"
                })
                
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error extracting findings: {e}")
            
        return findings[:5]  # Max 5 findings
    
    def _generate_clean_title(self, raw_name: str, finding_type: str) -> str:
        """Generate clean, professional titles for findings"""
        clean_title = raw_name
        
        # Remove common prefixes
        prefixes_to_remove = [
            "Evidence Analysis:", "Analysis:", "Investigation:",
            "Synthesis Analysis #", "Deep Analysis Phase", 
            "Task #", "Node #"
        ]
        
        for prefix in prefixes_to_remove:
            if clean_title.startswith(prefix):
                clean_title = clean_title.replace(prefix, "").strip()
        
        # Extract key information from the title for more specific naming
        title_lower = clean_title.lower()
        
        # Generate highly descriptive titles based on content and context
        if finding_type == "analysis":
            # Suspect-related analysis
            if "robert" in title_lower and "blackwood" in title_lower:
                if "motive" in title_lower or "will" in title_lower:
                    clean_title = "Robert Blackwood Inheritance Motive Analysis"
                elif "timeline" in title_lower or "discrepancies" in title_lower:
                    clean_title = "Robert Blackwood Timeline Inconsistencies"
                elif "window" in title_lower:
                    clean_title = "Robert Blackwood's Window Observation"
                else:
                    clean_title = "Robert Blackwood Suspect Analysis"
            elif "thomas" in title_lower and "hartwell" in title_lower:
                clean_title = "Thomas Hartwell Suspect Investigation"
            elif "margaret" in title_lower and "blackwood" in title_lower:
                clean_title = "Margaret Blackwood Witness Analysis"
            elif "elena" in title_lower and "rodriguez" in title_lower:
                clean_title = "Elena Rodriguez Housekeeper Analysis"
            
            # Evidence-specific analysis
            elif "paperweight" in title_lower or ("crystal" in title_lower and "weapon" in title_lower):
                clean_title = "Crystal Paperweight Murder Weapon Analysis"
            elif "fingerprint" in title_lower:
                if "desk" in title_lower:
                    clean_title = "Desk Surface Fingerprint Analysis"
                elif "unidentified" in title_lower or "unknown" in title_lower:
                    clean_title = "Unidentified Fingerprint Investigation"
                else:
                    clean_title = "Fingerprint Evidence Analysis"
            elif "fabric" in title_lower or "textile" in title_lower:
                if "torn" in title_lower or "fragment" in title_lower:
                    clean_title = "Torn Fabric Fragment Analysis"
                else:
                    clean_title = "Fabric Evidence Investigation"
            elif "footprint" in title_lower or "muddy" in title_lower:
                clean_title = "Crime Scene Footprint Analysis"
            elif "window" in title_lower and "entry" in title_lower:
                clean_title = "Library Window Entry Point Investigation"
            elif "blood" in title_lower:
                clean_title = "Blood Evidence Analysis"
            
            # General analysis types
            elif "motive" in title_lower:
                clean_title = "Suspect Motive Investigation"
            elif "timeline" in title_lower or "chronology" in title_lower:
                clean_title = "Crime Timeline Reconstruction"
            elif "witness" in title_lower:
                clean_title = "Witness Statement Analysis"
            elif "scene" in title_lower:
                clean_title = "Crime Scene Investigation"
            elif "background" in title_lower:
                clean_title = "Suspect Background Investigation"
            elif "alibi" in title_lower:
                clean_title = "Alibi Verification Analysis"
            
        elif finding_type == "evidence":
            # More specific evidence titles
            if "fingerprint" in title_lower:
                if "crystal" in title_lower or "paperweight" in title_lower:
                    clean_title = "Paperweight Fingerprint Evidence"
                elif "desk" in title_lower:
                    clean_title = "Desk Surface Fingerprint Evidence"
                elif "unidentified" in title_lower:
                    clean_title = "Unidentified Fingerprint Evidence"
                else:
                    clean_title = "Fingerprint Evidence"
            elif "fabric" in title_lower:
                clean_title = "Fabric Fragment Evidence"
            elif "blood" in title_lower:
                clean_title = "Blood Spatter Evidence"
            elif "footprint" in title_lower:
                clean_title = "Muddy Footprint Evidence"
            elif "weapon" in title_lower or "paperweight" in title_lower:
                clean_title = "Murder Weapon Evidence"
        
        # Fallback: clean up the original name
        if not clean_title or len(clean_title) < 5 or clean_title == raw_name:
            # Try to extract meaningful parts from the original name
            clean_title = raw_name.replace(":", "").replace("#", "").strip()
            
            # If it's still generic, make it more descriptive
            if clean_title.lower().startswith("synthesis analysis"):
                clean_title = "Investigation Analysis Summary"
            elif len(clean_title) > 50:
                clean_title = clean_title[:50] + "..."
        
        return clean_title
    
    def _calculate_confidence_score(self) -> float:
        """Calculate investigation confidence score"""
        try:
            tree_data = self._extract_tree_intelligence()
            
            # Base confidence factors
            evidence_factor = min(len(tree_data.get("evidence_nodes", [])) * 0.2, 1.0)
            witness_factor = min(len(tree_data.get("witness_nodes", [])) * 0.15, 0.8)
            analysis_factor = min(len(tree_data.get("analysis_nodes", [])) * 0.1, 0.7)
            
            confidence = evidence_factor + witness_factor + analysis_factor
            return round(min(confidence, 1.0), 2)
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error calculating confidence: {e}")
            return 0.75  # Default moderate confidence
    
    def _recommend_next_steps(self) -> List[str]:
        """Recommend next investigative steps"""
        recommendations = []
        
        try:
            tree_data = self._extract_tree_intelligence()
            confidence = self._calculate_confidence_score()
            
            if confidence > 0.8:
                recommendations = [
                    "Prepare case file for prosecution review",
                    "Finalize evidence documentation",
                    "Schedule suspect interrogation"
                ]
            elif confidence > 0.6:
                recommendations = [
                    "Gather additional supporting evidence",
                    "Interview additional witnesses",
                    "Verify suspect alibis"
                ]
            else:
                recommendations = [
                    "Expand evidence collection",
                    "Re-examine crime scene",
                    "Investigate alternative suspects"
                ]
                
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error generating recommendations: {e}")
            recommendations = ["Continue standard investigation procedures"]
            
        return recommendations
    
    def _determine_case_status(self) -> str:
        """Determine current case status"""
        try:
            confidence = self._calculate_confidence_score()
            
            if confidence > 0.85:
                return "Ready for Prosecution"
            elif confidence > 0.7:
                return "Strong Evidence - Near Resolution"
            elif confidence > 0.5:
                return "Moderate Evidence - Investigation Ongoing"
            else:
                return "Requires Additional Investigation"
                
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error determining status: {e}")
            return "Investigation Complete"
    
    def _generate_fallback_summary(self, final_conclusion: str = None) -> Dict[str, Any]:
        """Generate fallback summary when full analysis fails"""
        return {
            "case_overview": {"files_analyzed": 0, "document_types": [], "investigation_type": "Unknown"},
            "analysis_metrics": {"total_nodes_created": 0, "analysis_depth": 0, "tasks_completed": 0, "tasks_failed": 0},
            "key_findings": ["Analysis completed with limited data"],
            "evidence_summary": [],
            "suspect_analysis": [],
            "timeline_reconstruction": [],
            "ai_insights": ["Summary generation encountered technical difficulties"],
            "conclusion": final_conclusion or "Investigation analysis completed",
            "investigation_confidence": 0.5,
            "next_steps": ["Review analysis results"],
            "case_status": "Analysis Complete"
        } 