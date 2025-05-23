"""
Document Analyzer for AI Agent Memory Tree System

This module handles reading and preprocessing case documents
for analysis by the AI agents.
"""

import os
import glob
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DocumentAnalyzer:
    """Handles reading and preprocessing case documents"""
    
    def __init__(self, case_files_dir: str = "case_files"):
        self.case_files_dir = case_files_dir
        self.documents: Dict[str, str] = {}
        
    def load_case_files(self) -> Dict[str, str]:
        """Load all .txt files from the case files directory"""
        case_files_path = Path(self.case_files_dir)
        
        if not case_files_path.exists():
            logger.warning(f"Case files directory {case_files_path} does not exist")
            return {}
        
        documents = {}
        
        # Find all .txt files
        txt_files = list(case_files_path.glob("*.txt"))
        
        logger.info(f"Found {len(txt_files)} case files to analyze")
        
        for file_path in txt_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    documents[file_path.name] = content
                    logger.info(f"Loaded case file: {file_path.name} ({len(content)} characters)")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
        
        self.documents = documents
        return documents
    
    def load_specific_files(self, filenames: List[str]) -> Dict[str, str]:
        """Load only specific files from the case files directory"""
        case_files_path = Path(self.case_files_dir)
        
        if not case_files_path.exists():
            logger.warning(f"Case files directory {case_files_path} does not exist")
            return {}
        
        documents = {}
        
        logger.info(f"Loading specific files: {filenames}")
        
        for filename in filenames:
            file_path = case_files_path / filename
            
            if not file_path.exists():
                logger.warning(f"Specified file {filename} not found")
                continue
                
            if not filename.endswith('.txt'):
                logger.warning(f"Skipping non-text file: {filename}")
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    documents[filename] = content
                    logger.info(f"Loaded session file: {filename} ({len(content)} characters)")
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
        
        self.documents = documents
        return documents
    
    def get_document_summary(self) -> Dict[str, Any]:
        """Get summary of all loaded documents"""
        # Get document types
        doc_types = self.get_document_types()
        
        return {
            'total_documents': len(self.documents),
            'document_types': list(set(doc_types.values())),
            'total_characters': sum(len(content) for content in self.documents.values()),
            'documents': [
                {
                    'filename': filename,
                    'type': doc_types.get(filename, 'unknown'),
                    'size': len(content),
                    'size_lines': len(content.split('\n'))
                }
                for filename, content in self.documents.items()
            ]
        }
    
    def get_document_content(self, filename: str) -> str:
        """Get the full text content of a specific document"""
        if filename in self.documents:
            return self.documents[filename]
        return f"Document '{filename}' not found"
    
    def search_documents(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for a term across all documents"""
        results = []
        
        for filename, content in self.documents.items():
            lines = content.split('\n')
            matches = []
            
            for line_num, line in enumerate(lines, 1):
                if search_term.lower() in line.lower():
                    matches.append({
                        'line_number': line_num,
                        'line_content': line.strip(),
                        'context': self._get_line_context(lines, line_num - 1, 2)
                    })
            
            if matches:
                results.append({
                    'filename': filename,
                    'match_count': len(matches),
                    'matches': matches
                })
        
        return results
    
    def _get_line_context(self, lines: List[str], line_index: int, context_size: int = 2) -> List[str]:
        """Get context lines around a specific line"""
        start = max(0, line_index - context_size)
        end = min(len(lines), line_index + context_size + 1)
        return lines[start:end]
    
    def get_document_types(self) -> Dict[str, str]:
        """Identify the type of each document based on content analysis"""
        document_types = {}
        
        for filename, content in self.documents.items():
            content_lower = content.lower()
            
            if 'police department' in content_lower and 'case report' in content_lower:
                document_types[filename] = 'police_report'
            elif 'witness statement' in content_lower and 'interview' in content_lower:
                document_types[filename] = 'witness_statement'
            elif 'forensic' in content_lower and 'evidence' in content_lower:
                document_types[filename] = 'forensic_report'
            elif 'autopsy' in content_lower or 'medical examiner' in content_lower:
                document_types[filename] = 'medical_report'
            elif 'financial' in content_lower or 'bank' in content_lower:
                document_types[filename] = 'financial_record'
            else:
                document_types[filename] = 'unknown'
        
        return document_types
    
    def extract_key_entities(self, document_content: str) -> Dict[str, List[str]]:
        """Extract key entities from document content"""
        entities = {
            'people': [],
            'locations': [],
            'dates': [],
            'times': [],
            'evidence': [],
            'phone_numbers': [],
            'addresses': []
        }
        
        lines = document_content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Extract names (simple heuristic - capitalized words)
            words = line.split()
            for i, word in enumerate(words):
                if word.istitle() and len(word) > 2:
                    # Check if it's likely a person's name
                    if i < len(words) - 1 and words[i + 1].istitle():
                        full_name = f"{word} {words[i + 1]}"
                        if full_name not in entities['people']:
                            entities['people'].append(full_name)
            
            # Extract addresses (simple pattern matching)
            if 'street' in line.lower() or 'drive' in line.lower() or 'avenue' in line.lower():
                entities['addresses'].append(line.strip())
            
            # Extract phone numbers (simple pattern)
            import re
            phone_pattern = r'\(\d{3}\) \d{3}-\d{4}'
            phones = re.findall(phone_pattern, line)
            entities['phone_numbers'].extend(phones)
            
            # Extract dates (simple patterns)
            date_patterns = [
                r'January \d{1,2}, \d{4}',
                r'February \d{1,2}, \d{4}',
                r'March \d{1,2}, \d{4}',
                r'April \d{1,2}, \d{4}',
                r'May \d{1,2}, \d{4}',
                r'June \d{1,2}, \d{4}',
                r'July \d{1,2}, \d{4}',
                r'August \d{1,2}, \d{4}',
                r'September \d{1,2}, \d{4}',
                r'October \d{1,2}, \d{4}',
                r'November \d{1,2}, \d{4}',
                r'December \d{1,2}, \d{4}'
            ]
            
            for pattern in date_patterns:
                dates = re.findall(pattern, line)
                entities['dates'].extend(dates)
            
            # Extract times
            time_pattern = r'\d{1,2}:\d{2}(?:\s?(?:AM|PM|hours))?'
            times = re.findall(time_pattern, line, re.IGNORECASE)
            entities['times'].extend(times)
        
        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities


# Example usage and testing
if __name__ == "__main__":
    analyzer = DocumentAnalyzer()
    
    # Load documents
    documents = analyzer.load_case_files()
    print(f"Loaded {len(documents)} documents")
    
    # Get summary
    summary = analyzer.get_document_summary()
    print("\nDocument Summary:")
    for doc in summary['documents']:
        print(f"- {doc['filename']}: {doc['size_lines']} lines, {doc['size']} chars")
    
    # Identify document types
    doc_types = analyzer.get_document_types()
    print("\nDocument Types:")
    for filename, doc_type in doc_types.items():
        print(f"- {filename}: {doc_type}")
    
    # Search example - use dynamic search based on actual content
    if documents:
        # Get first few words from first document for a realistic search
        first_doc = list(documents.values())[0]
        words = first_doc.split()[:10]
        search_term = next((word for word in words if len(word) > 4 and word.isalpha()), "investigation")
        search_results = analyzer.search_documents(search_term)
        print(f"\nSearch results for '{search_term}': {len(search_results)} documents")
    else:
        print("\nNo documents to search")
    
    # Extract entities from first document
    if documents:
        first_doc = list(documents.values())[0]
        entities = analyzer.extract_key_entities(first_doc)
        print(f"\nEntities found:")
        for entity_type, items in entities.items():
            if items:
                print(f"- {entity_type}: {items[:3]}...")  # Show first 3 items 