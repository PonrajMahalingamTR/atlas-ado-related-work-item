#!/usr/bin/env python3
"""
Advanced LLM Response Parser for Azure DevOps AI Studio

This module provides a robust, intelligent parser for LLM responses that can handle
dynamic response formats and accurately extract work item relationships with confidence scores.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ParsedWorkItem:
    """Represents a parsed work item from LLM response."""
    id: int
    title: str
    work_item_type: str
    state: str
    confidence: str
    relationship_type: str
    reasoning: str
    evidence: str
    impact: str
    priority: str = "Not specified"
    assigned_to: str = "Unknown"
    area_path: str = ""
    iteration_path: str = ""
    description: str = ""
    created_date: str = ""

@dataclass
class ParsedAnalysis:
    """Represents the complete parsed analysis from LLM response."""
    high_confidence_items: List[ParsedWorkItem]
    medium_confidence_items: List[ParsedWorkItem]
    low_confidence_items: List[ParsedWorkItem]
    relationship_patterns: List[str]
    risk_assessment: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    opportunities: List[Dict[str, Any]]
    summary: Dict[str, Any]

class AdvancedLLMResponseParser:
    """
    Advanced parser for LLM responses with intelligent pattern recognition
    and dynamic format adaptation.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Comprehensive work item ID patterns
        self.work_item_patterns = [
            r'- \*\*ID:\s*(\d+)',  # - **ID:** 12345
            r'### \d+\. ID:\s*(\d+)',  # ### 1. ID: 12345
            r'#(\d+)',  # #12345
            r'ID:\s*(\d+)',  # ID: 12345
            r'Work Item\s*(\d+)',  # Work Item 12345
            r'Item\s*(\d+)',  # Item 12345
            r'\b(\d{6,})\b',  # 6+ digit numbers
            r'\[(\d+)\]',  # [12345]
            r'\((\d+)\)',  # (12345)
        ]
        
        # Confidence level indicators
        self.confidence_indicators = {
            'high': [
                'high confidence', 'high-confidence', 'highly confident',
                'strong relationship', 'direct relationship', 'clear relationship',
                'definitive', 'certain', 'confirmed', 'explicit'
            ],
            'medium': [
                'medium confidence', 'medium-confidence', 'moderate confidence',
                'probable', 'likely', 'suggested', 'indicated', 'appears to be',
                'seems related', 'possibly related', 'potential relationship'
            ],
            'low': [
                'low confidence', 'low-confidence', 'possible', 'might be',
                'could be', 'uncertain', 'unclear', 'speculative', 'tentative',
                'weak relationship', 'indirect relationship'
            ]
        }
        
        # Relationship type patterns
        self.relationship_patterns = {
            'dependency': ['dependency', 'depends on', 'prerequisite', 'required by', 'blocked by'],
            'blocking': ['blocking', 'blocks', 'prevents', 'impedes', 'hinders'],
            'related': ['related', 'associated', 'connected', 'linked', 'similar'],
            'parent': ['parent', 'epic', 'feature', 'contains', 'includes'],
            'child': ['child', 'subtask', 'task', 'story', 'part of'],
            'bug_fix': ['bug', 'fix', 'defect', 'issue', 'problem'],
            'technical': ['technical', 'implementation', 'code', 'architecture', 'design'],
            'business': ['business', 'functional', 'requirement', 'feature', 'user']
        }
    
    def parse_response(self, llm_response: str, all_work_items: List[Any], selected_work_item: Any) -> ParsedAnalysis:
        """
        Parse LLM response and extract structured analysis data.
        
        Args:
            llm_response: Raw LLM response text
            all_work_items: List of all available work items
            selected_work_item: The selected work item being analyzed
            
        Returns:
            ParsedAnalysis: Structured analysis data
        """
        try:
            self.logger.info("Starting advanced LLM response parsing")
            
            # DEBUG: Print full raw LLM response
            print("\n" + "="*100)
            print("FULL RAW LLM RESPONSE:")
            print("="*100)
            try:
                print(llm_response)
            except UnicodeEncodeError:
                # Handle Unicode characters that can't be displayed in Windows console
                safe_response = llm_response.encode('ascii', 'replace').decode('ascii')
                print(safe_response)
            print("="*100)
            print("END OF RAW LLM RESPONSE")
            print("="*100 + "\n")
            
            # Debug: Log the raw LLM response
            self.logger.debug(f"Raw LLM response (first 500 chars): {llm_response[:500]}")
            self.logger.debug(f"Raw LLM response (last 500 chars): {llm_response[-500:]}")
            
            # Normalize the response
            normalized_response = self._normalize_response(llm_response)
            
            # Extract work items with confidence scores
            work_items = self._extract_work_items_with_confidence(normalized_response, all_work_items, selected_work_item)
            
            # Categorize by confidence
            high_confidence = [item for item in work_items if item.confidence == 'high']
            medium_confidence = [item for item in work_items if item.confidence == 'medium']
            low_confidence = [item for item in work_items if item.confidence == 'low']
            
            # Extract analysis sections
            relationship_patterns = self._extract_relationship_patterns(normalized_response)
            risk_assessment = self._extract_risk_assessment(normalized_response)
            dependencies = self._extract_dependencies(normalized_response)
            recommendations = self._extract_recommendations(normalized_response)
            opportunities = self._extract_opportunities(normalized_response)
            
            # Generate summary
            summary = self._generate_summary(work_items, relationship_patterns, risk_assessment, recommendations)
            
            self.logger.info(f"Parsing completed: {len(high_confidence)} high, {len(medium_confidence)} medium, {len(low_confidence)} low confidence items")
            
            return ParsedAnalysis(
                high_confidence_items=high_confidence,
                medium_confidence_items=medium_confidence,
                low_confidence_items=low_confidence,
                relationship_patterns=relationship_patterns,
                risk_assessment=risk_assessment,
                dependencies=dependencies,
                recommendations=recommendations,
                opportunities=opportunities,
                summary=summary
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            # Return empty analysis on error
            return ParsedAnalysis(
                high_confidence_items=[],
                medium_confidence_items=[],
                low_confidence_items=[],
                relationship_patterns=[],
                risk_assessment=[],
                dependencies=[],
                recommendations=[],
                opportunities=[],
                summary={'error': str(e)}
            )
    
    def _normalize_response(self, response: str) -> str:
        """Normalize the LLM response for consistent parsing."""
        # Handle Unicode characters that might cause issues
        try:
            # Replace problematic Unicode characters
            response = response.replace('→', '->')
            response = response.replace('←', '<-')
            response = response.replace('↑', '^')
            response = response.replace('↓', 'v')
            response = response.replace('•', '*')
        except UnicodeError:
            # Fallback to ASCII-safe version
            response = response.encode('ascii', 'replace').decode('ascii')
        
        # Remove excessive whitespace
        response = re.sub(r'\n\s*\n', '\n\n', response)
        
        # Standardize section headers
        response = re.sub(r'#+\s*(HIGH|MEDIUM|LOW)\s*CONFIDENCE', r'## \1 CONFIDENCE', response, flags=re.IGNORECASE)
        response = re.sub(r'#+\s*(RELATIONSHIP|RISK|RECOMMENDATION)', r'## \1', response, flags=re.IGNORECASE)
        
        return response
    
    def _extract_work_items_with_confidence(self, response: str, all_work_items: List[Any], selected_work_item: Any) -> List[ParsedWorkItem]:
        """Extract work items with intelligent confidence detection."""
        work_items = []
        
        # Split response into sections
        sections = self._split_into_sections(response)
        
        for section in sections:
            confidence = self._detect_confidence_from_section(section)
            work_item_ids = self._extract_work_item_ids(section)
            
            for work_item_id in work_item_ids:
                if work_item_id == selected_work_item.id:
                    continue  # Skip the selected work item itself
                
                # Find the work item in all_work_items
                work_item = self._find_work_item_by_id(work_item_id, all_work_items)
                if not work_item:
                    continue
                
                # Extract additional details from the section
                relationship_type = self._extract_relationship_type(section, work_item_id)
                reasoning = self._extract_reasoning(section, work_item_id)
                # Format the reasoning to ensure proper bullet point display
                reasoning = self._format_reasoning_text(reasoning)
                evidence = self._extract_evidence(section, work_item_id)
                impact = self._extract_impact(section, work_item_id)
                
                # Create parsed work item
                parsed_item = ParsedWorkItem(
                    id=work_item_id,
                    title=self._get_work_item_field(work_item, 'System.Title', 'No Title'),
                    work_item_type=self._get_work_item_field(work_item, 'System.WorkItemType', 'Unknown'),
                    state=self._get_work_item_field(work_item, 'System.State', 'Unknown'),
                    confidence=confidence,
                    relationship_type=relationship_type,
                    reasoning=reasoning,
                    evidence=evidence,
                    impact=impact,
                    priority=self._get_work_item_field(work_item, 'Microsoft.VSTS.Common.Priority', 'Not specified'),
                    assigned_to=self._get_assigned_to(work_item),
                    area_path=self._get_work_item_field(work_item, 'System.AreaPath', ''),
                    iteration_path=self._get_work_item_field(work_item, 'System.IterationPath', ''),
                    description=self._get_work_item_field(work_item, 'System.Description', ''),
                    created_date=self._get_work_item_field(work_item, 'System.CreatedDate', '')
                )
                
                work_items.append(parsed_item)
        
        return work_items
    
    def _split_into_sections(self, response: str) -> List[str]:
        """Split response into logical sections for analysis."""
        sections = []
        
        # Split by confidence level headers (handle both ## and ### formats, and plain text)
        confidence_pattern = r'(?:#{2,3}\s*)?(HIGH|MEDIUM|LOW)\s*CONFIDENCE(?:\s+RELATIONSHIPS)?'
        parts = re.split(confidence_pattern, response, flags=re.IGNORECASE)
        
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                section = f"## {parts[i]} CONFIDENCE\n{parts[i + 1]}"
                sections.append(section)
        
        # If no confidence sections found, split by other patterns
        if not sections:
            # Look for work item lists
            work_item_pattern = r'(- \*\*ID:|### \d+\. ID:|#\d+|ID:\s*\d+)'
            parts = re.split(work_item_pattern, response)
            
            current_section = ""
            for part in parts:
                if re.match(work_item_pattern, part):
                    if current_section:
                        sections.append(current_section)
                    current_section = part
                else:
                    current_section += part
            
            if current_section:
                sections.append(current_section)
        
        return sections
    
    def _detect_confidence_from_section(self, section: str) -> str:
        """Detect confidence level from section content using multiple strategies."""
        section_lower = section.lower()
        
        # Check for explicit confidence indicators
        for confidence, indicators in self.confidence_indicators.items():
            for indicator in indicators:
                if indicator in section_lower:
                    return confidence
        
        # Check section headers (handle both ## and ### formats)
        if 'HIGH CONFIDENCE' in section.upper() and ('##' in section or '###' in section):
            return 'high'
        elif 'MEDIUM CONFIDENCE' in section.upper() and ('##' in section or '###' in section):
            return 'medium'
        elif 'LOW CONFIDENCE' in section.upper() and ('##' in section or '###' in section):
            return 'low'
        
        # Check for confidence keywords in context
        high_keywords = ['directly related', 'strong relationship', 'dependency', 'prerequisite', 'blocking']
        medium_keywords = ['related', 'similar', 'associated', 'part of', 'related to']
        low_keywords = ['possible', 'might be', 'could be', 'uncertain', 'unclear']
        
        if any(keyword in section_lower for keyword in high_keywords):
            return 'high'
        elif any(keyword in section_lower for keyword in medium_keywords):
            return 'medium'
        elif any(keyword in section_lower for keyword in low_keywords):
            return 'low'
        
        # Default to medium confidence
        return 'medium'
    
    def _extract_work_item_ids(self, text: str) -> List[int]:
        """Extract work item IDs using comprehensive pattern matching."""
        work_item_ids = set()
        
        for pattern in self.work_item_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    work_item_id = int(match)
                    if work_item_id > 0:  # Valid work item ID
                        work_item_ids.add(work_item_id)
                except ValueError:
                    continue
        
        return list(work_item_ids)
    
    def _find_work_item_by_id(self, work_item_id: int, all_work_items: List[Any]) -> Optional[Any]:
        """Find work item by ID in the list of all work items."""
        for item in all_work_items:
            if hasattr(item, 'id') and item.id == work_item_id:
                return item
            elif isinstance(item, dict) and item.get('id') == work_item_id:
                return item
        return None
    
    def _extract_relationship_type(self, section: str, work_item_id: int) -> str:
        """Extract relationship type from section content."""
        section_lower = section.lower()
        
        for relationship_type, keywords in self.relationship_patterns.items():
            if any(keyword in section_lower for keyword in keywords):
                return relationship_type
        
        return 'related'
    
    def _extract_reasoning(self, section: str, work_item_id: int) -> str:
        """Extract reasoning for the relationship with focus on bullet point format."""
        # Debug logging
        self.logger.debug(f"Extracting reasoning for work item {work_item_id} from section: {section[:200]}...")
        self.logger.debug(f"Full section for work item {work_item_id}: {section}")
        
        # Additional debug: Check if the work item ID appears in the section
        if f"- ID: {work_item_id}" in section:
            self.logger.debug(f"Found '- ID: {work_item_id}' in section")
        elif f"ID: {work_item_id}" in section:
            self.logger.debug(f"Found 'ID: {work_item_id}' in section")
        else:
            self.logger.debug(f"Work item ID {work_item_id} not found in section")
        
        # First, try to find the work item ID in the section
        work_item_id_str = str(work_item_id)
        
        # Look for the work item ID followed by various patterns
        patterns_to_try = [
            # Pattern 1: "- ID: {id}" followed by "Why This Work Item Is Relevant:" with ALL bullet points (with proper indentation) - handle both • and *
            rf'- ID: {work_item_id_str}.*?- Why This Work Item Is Relevant:.*?((?:\n\s+[•*]\s*[^\n]+)+)',
            # Pattern 2: "- ID: {id}" followed by "Why This Work Item Is Relevant" with ALL bullet points (old format with proper indentation) - handle both • and *
            rf'- ID: {work_item_id_str}.*?Why This Work Item Is Relevant:.*?((?:\n\s+[•*]\s*[^\n]+)+)',
            # Pattern 3: "- ID: {id}" followed by any content with ALL bullet points (with proper indentation) - handle both • and *
            rf'- ID: {work_item_id_str}.*?((?:\n\s+[•*]\s*[^\n]+)+)',
            # Pattern 4: Direct ID followed by "Why This Work Item Is Relevant:" with ALL bullet points (new format with proper indentation) - handle both • and *
            rf'{work_item_id_str}.*?- Why This Work Item Is Relevant:.*?((?:\n\s+[•*]\s*[^\n]+)+)',
            # Pattern 5: Direct ID followed by "Why This Work Item Is Relevant" with ALL bullet points (old format with proper indentation) - handle both • and *
            rf'{work_item_id_str}.*?Why This Work Item Is Relevant:.*?((?:\n\s+[•*]\s*[^\n]+)+)',
            # Pattern 6: Direct ID followed by any content with ALL bullet points (with proper indentation) - handle both • and *
            rf'{work_item_id_str}.*?((?:\n\s+[•*]\s*[^\n]+)+)',
            # Pattern 7: ID followed by "Why This Work Item Is Relevant" without bullet points
            rf'{work_item_id_str}.*?Why This Work Item Is Relevant:.*?([^.\n]{{50,300}}?)(?:\n|$)',
            # Pattern 8: ID followed by any meaningful content
            rf'{work_item_id_str}.*?([^.\n]{{50,300}}?)(?:\n|$)',
            # Pattern 9: ID followed by raw text (like "Testing completion is required...")
            rf'{work_item_id_str}.*?([A-Z][^.\n]{{20,200}}?)(?:\n|$)',
            # Pattern 10: ID followed by raw output like "**Title:** [DEV] PL Accessibility..."
            rf'{work_item_id_str}.*?(\*\*.*?\*\*.*?)(?:\n|$)',
        ]
        
        for i, pattern in enumerate(patterns_to_try):
            matches = re.findall(pattern, section, re.IGNORECASE | re.DOTALL)
            self.logger.debug(f"Pattern {i+1} ({pattern[:50]}...) matches: {len(matches)} results")
            if matches:
                self.logger.debug(f"Pattern {i+1} matched content: {matches[0][:200]}...")
                match = matches[0]
                self.logger.debug(f"Pattern {i+1} matched: {match}")
                
                # If it's a tuple (bullet points), extract them
                if isinstance(match, tuple):
                    bullet_points = []
                    for item in match:
                        if item and item.strip() and len(item.strip()) > 10:
                            bullet_points.append(item.strip())
                    
                    if bullet_points:
                        # Format as user-friendly bullet points
                        formatted_reasoning = "Why this work item is relevant:\n"
                        for point in bullet_points:
                            formatted_reasoning += f"• {point}\n"
                        result = formatted_reasoning.strip()
                        if len(result) > 20:
                            self.logger.debug(f"Returning bullet points for work item {work_item_id}: {result}")
                            return result
                
                # If it's a string (single content), check if it contains bullet points
                elif isinstance(match, str):
                    # Check if the string contains bullet points (• or *)
                    if '•' in match or '*' in match:
                        # Split by bullet points and format (handle both • and *)
                        bullet_lines = []
                        if '•' in match:
                            bullet_lines = [line.strip() for line in match.split('•') if line.strip()]
                        elif '*' in match:
                            bullet_lines = [line.strip() for line in match.split('*') if line.strip()]
                        
                        self.logger.debug(f"Found {len(bullet_lines)} bullet lines for work item {work_item_id}: {bullet_lines}")
                        if bullet_lines:
                            formatted_reasoning = "Why this work item is relevant:\n"
                            for point in bullet_lines:
                                formatted_reasoning += f"• {point}\n"
                            result = formatted_reasoning.strip()
                            if len(result) > 20:
                                self.logger.debug(f"Returning bullet points for work item {work_item_id}: {result}")
                                return result
                    else:
                        # No bullet points found, this shouldn't happen with our patterns
                        self.logger.debug(f"No bullet points found in match for work item {work_item_id}: {match[:100]}...")
                    
                    # If it's a regular string without bullet points
                    if len(match.strip()) > 20:
                        # Check if it's raw output like "**Title:** [DEV] PL Accessibility..."
                        if match.strip().startswith('**') and '**' in match.strip():
                            # Extract meaningful content from raw output
                            # Remove markdown formatting and extract the actual content
                            cleaned_match = re.sub(r'\*\*([^*]+)\*\*', r'\1', match.strip())
                            # Look for meaningful sentences after the formatting
                            sentences = cleaned_match.split('. ')
                            if len(sentences) > 1:
                                formatted_reasoning = "Why this work item is relevant:\n"
                                for sentence in sentences[:4]:  # Limit to 4 bullet points
                                    sentence = sentence.strip()
                                    if sentence and not sentence.endswith('.'):
                                        sentence += '.'
                                    if len(sentence) > 20:
                                        formatted_reasoning += f"• {sentence}\n"
                                result = formatted_reasoning.strip()
                                self.logger.debug(f"Returning formatted raw output for work item {work_item_id}: {result}")
                                return result
                        else:
                            # Single sentence from raw output
                            cleaned_match = re.sub(r'\*\*([^*]+)\*\*', r'\1', match.strip())
                            formatted_reasoning = f"Why this work item is relevant:\n• {cleaned_match}"
                            self.logger.debug(f"Returning single sentence from raw output for work item {work_item_id}: {formatted_reasoning}")
                            return formatted_reasoning
                    else:
                        # Try to convert to bullet points if it contains multiple sentences
                        sentences = match.split('. ')
                        if len(sentences) > 1:
                            formatted_reasoning = "Why this work item is relevant:\n"
                            for sentence in sentences[:4]:  # Limit to 4 bullet points
                                sentence = sentence.strip()
                                if sentence and not sentence.endswith('.'):
                                    sentence += '.'
                                if len(sentence) > 20:
                                    formatted_reasoning += f"• {sentence}\n"
                            result = formatted_reasoning.strip()
                            self.logger.debug(f"Returning converted bullet points for work item {work_item_id}: {result}")
                            return result
                        else:
                            self.logger.debug(f"Returning single content for work item {work_item_id}: {match.strip()}")
                            return match.strip()
        
        # If no specific reasoning found, look for general analysis text in the section
        if section and len(section.strip()) > 50:
            # Extract meaningful content from the section
            lines = section.split('\n')
            meaningful_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-') and len(line) > 20:
                    meaningful_lines.append(line)
            
            if meaningful_lines:
                # Join meaningful lines and return as reasoning
                reasoning_text = ' '.join(meaningful_lines[:3])  # Take first 3 meaningful lines
                if len(reasoning_text) > 10:  # Ensure we have meaningful content
                    # Try to convert to bullet points
                    sentences = reasoning_text.split('. ')
                    if len(sentences) > 1:
                        formatted_reasoning = "Why this work item is relevant:\n"
                        for sentence in sentences[:4]:
                            sentence = sentence.strip()
                            if sentence and not sentence.endswith('.'):
                                sentence += '.'
                            if len(sentence) > 20:
                                formatted_reasoning += f"• {sentence}\n"
                        return formatted_reasoning.strip()
                    else:
                        return reasoning_text
        
        # Special case: If the section contains raw text like "Testing completion is required...", format it
        if section and len(section.strip()) > 20 and len(section.strip()) < 200:
            # Check if it's a single meaningful sentence
            if (not section.startswith('#') and 
                not section.startswith('-') and 
                not section.startswith('*') and
                not section.startswith('ID:') and
                not section.startswith('Title:') and
                not section.startswith('Type:') and
                not section.startswith('State:') and
                not section.startswith('Priority:') and
                not section.startswith('Relationship Type:') and
                not section.startswith('**')):
                # Format as a bullet point
                formatted_reasoning = f"Why this work item is relevant:\n• {section.strip()}"
                self.logger.debug(f"Returning formatted raw text for work item {work_item_id}: {formatted_reasoning}")
                return formatted_reasoning
        
        # Additional fallback: Look for any meaningful text in the section that could be reasoning
        if section and len(section.strip()) > 20:
            # Look for sentences that start with capital letters and are meaningful
            sentences = section.split('. ')
            meaningful_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if (sentence and 
                    len(sentence) > 20 and 
                    sentence[0].isupper() and 
                    not sentence.startswith('#') and 
                    not sentence.startswith('-') and 
                    not sentence.startswith('*') and
                    not sentence.startswith('ID:') and
                    not sentence.startswith('Title:') and
                    not sentence.startswith('Type:') and
                    not sentence.startswith('State:') and
                    not sentence.startswith('Priority:') and
                    not sentence.startswith('Relationship Type:')):
                    meaningful_sentences.append(sentence)
            
            if meaningful_sentences:
                # Format as bullet points
                formatted_reasoning = "Why this work item is relevant:\n"
                for sentence in meaningful_sentences[:4]:  # Limit to 4 bullet points
                    if not sentence.endswith('.'):
                        sentence += '.'
                    formatted_reasoning += f"• {sentence}\n"
                result = formatted_reasoning.strip()
                self.logger.debug(f"Returning extracted meaningful sentences for work item {work_item_id}: {result}")
                return result
        
        # Final fallback: Look for any text that could be reasoning, including raw output
        if section and len(section.strip()) > 20:
            # Check if it's raw output like "**Title:** [DEV] PL Accessibility..."
            if '**' in section and 'Title:' in section:
                # Extract meaningful content from raw output
                cleaned_section = re.sub(r'\*\*([^*]+)\*\*', r'\1', section)
                # Look for meaningful sentences
                sentences = cleaned_section.split('. ')
                meaningful_sentences = []
                for sentence in sentences:
                    sentence = sentence.strip()
                    if (sentence and 
                        len(sentence) > 20 and 
                        not sentence.startswith('Title:') and
                        not sentence.startswith('Type:') and
                        not sentence.startswith('State:') and
                        not sentence.startswith('Priority:') and
                        not sentence.startswith('Relationship Type:')):
                        meaningful_sentences.append(sentence)
                
                if meaningful_sentences:
                    # Format as bullet points
                    formatted_reasoning = "Why this work item is relevant:\n"
                    for sentence in meaningful_sentences[:4]:  # Limit to 4 bullet points
                        if not sentence.endswith('.'):
                            sentence += '.'
                        formatted_reasoning += f"• {sentence}\n"
                    result = formatted_reasoning.strip()
                    self.logger.debug(f"Returning formatted raw output for work item {work_item_id}: {result}")
                    return result
            
            # Check if it's a single meaningful sentence like "Testing completion is required..."
            if (len(section.strip()) < 200 and 
                section.strip()[0].isupper() and 
                not section.startswith('#') and 
                not section.startswith('-') and 
                not section.startswith('*') and
                not section.startswith('ID:') and
                not section.startswith('Title:') and
                not section.startswith('Type:') and
                not section.startswith('State:') and
                not section.startswith('Priority:') and
                not section.startswith('Relationship Type:')):
                # Format as a bullet point
                formatted_reasoning = f"Why this work item is relevant:\n• {section.strip()}"
                self.logger.debug(f"Returning single meaningful sentence for work item {work_item_id}: {formatted_reasoning}")
                return formatted_reasoning
        
        # Final fallback: Generate a basic reasoning based on work item context
        fallback_reasoning = f"Work item #{work_item_id} is related based on shared context, requirements, or technical dependencies with the selected work item."
        self.logger.warning(f"Using fallback reasoning for work item {work_item_id} - no specific reasoning found in section")
        return fallback_reasoning
    
    def _format_reasoning_text(self, text: str) -> str:
        """Format reasoning text to ensure proper bullet point display."""
        if not text or len(text.strip()) < 10:
            return text
        
        # If text already has bullet points, ensure proper formatting
        if '•' in text or 'Why this work item is relevant' in text:
            return text
        
        # If text is a single paragraph, try to convert it to bullet points
        # Look for sentences that could be bullet points
        sentences = text.split('. ')
        if len(sentences) > 1:
            formatted_text = "Why this work item is relevant:\n"
            for sentence in sentences[:4]:  # Limit to 4 bullet points
                sentence = sentence.strip()
                if sentence and not sentence.endswith('.'):
                    sentence += '.'
                if len(sentence) > 20:  # Only include meaningful sentences
                    formatted_text += f"• {sentence}\n"
            return formatted_text.strip()
        
        # If it's a single sentence, format it as a bullet point
        if len(text.strip()) > 20:
            return f"Why this work item is relevant:\n• {text.strip()}"
        
        return text
    
    def _extract_evidence(self, section: str, work_item_id: int) -> str:
        """Extract evidence supporting the relationship."""
        # Look for evidence patterns
        evidence_patterns = [
            rf'(\d+).*?(?:evidence|support|indicates)[:\s]*(.+?)(?:\n|$)',
            rf'(\d+).*?(?:based on|according to)[:\s]*(.+?)(?:\n|$)',
            rf'(\d+).*?(?:shows|demonstrates)[:\s]*(.+?)(?:\n|$)'
        ]
        
        for pattern in evidence_patterns:
            matches = re.findall(pattern, section, re.IGNORECASE | re.DOTALL)
            for match_id, evidence in matches:
                if int(match_id) == work_item_id:
                    return evidence.strip()
        
        return "Analysis of work item content and context"
    
    def _extract_impact(self, section: str, work_item_id: int) -> str:
        """Extract impact of the relationship."""
        # Look for impact patterns
        impact_patterns = [
            rf'(\d+).*?(?:impact|affects|influences)[:\s]*(.+?)(?:\n|$)',
            rf'(\d+).*?(?:consequence|result)[:\s]*(.+?)(?:\n|$)',
            rf'(\d+).*?(?:significance|importance)[:\s]*(.+?)(?:\n|$)'
        ]
        
        for pattern in impact_patterns:
            matches = re.findall(pattern, section, re.IGNORECASE | re.DOTALL)
            for match_id, impact in matches:
                if int(match_id) == work_item_id:
                    return impact.strip()
        
        return "Relationship may affect project planning and execution"
    
    def _extract_relationship_patterns(self, response: str) -> List[str]:
        """Extract relationship patterns from the response."""
        patterns = []
        
        # Look for pattern analysis sections
        pattern_sections = re.findall(r'## RELATIONSHIP PATTERNS.*?(?=##|\Z)', response, re.IGNORECASE | re.DOTALL)
        
        for section in pattern_sections:
            # Extract bullet points or numbered lists
            lines = section.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('- ') or line.startswith('* ') or re.match(r'^\d+\.', line):
                    patterns.append(line)
        
        return patterns
    
    def _extract_risk_assessment(self, response: str) -> List[Dict[str, Any]]:
        """Extract risk assessment from the response."""
        risks = []
        
        # Look for risk assessment sections
        risk_sections = re.findall(r'RISK ASSESSMENT.*?(?=DEPENDENCIES|RECOMMENDATIONS|OPPORTUNITIES|\Z)', response, re.IGNORECASE | re.DOTALL)
        self.logger.debug(f"Found {len(risk_sections)} risk assessment sections")
        
        for section in risk_sections:
            # Look for structured risk entries with Risk X pattern (no markdown)
            risk_pattern = r'Risk (\d+):\s*\n- Risk Category:\s*([^\n]+)\n- Risk Level:\s*([^\n]+)\n- Risk Description:\s*([^\n]+)\n- Impact:\s*([^\n]+)\n- Mitigation:\s*([^\n]+)'
            matches = re.findall(risk_pattern, section, re.IGNORECASE | re.DOTALL)
            self.logger.debug(f"Risk pattern matches: {len(matches)}")
            
            for match in matches:
                risks.append({
                    'title': f"Risk {match[0]}: {match[1].strip()}",
                    'description': match[3].strip(),
                    'severity': match[2].strip().lower(),
                    'impact': match[4].strip(),
                    'mitigation': match[5].strip()
                })
            
            # Alternative pattern for different formatting
            if not risks:
                risk_pattern_alt = r'Risk (\d+):\s*\n- Risk Category:\s*([^\n]+)\n- Risk Level:\s*([^\n]+)\n- Risk Description:\s*([^\n]+)\n- Impact:\s*([^\n]+)\n- Mitigation:\s*([^\n]+)'
                matches_alt = re.findall(risk_pattern_alt, section, re.IGNORECASE | re.DOTALL)
                self.logger.debug(f"Risk alt pattern matches: {len(matches_alt)}")
                
                for match in matches_alt:
                    risks.append({
                        'title': f"Risk {match[0]}: {match[1].strip()}",
                        'description': match[3].strip(),
                        'severity': match[2].strip().lower(),
                        'impact': match[4].strip(),
                        'mitigation': match[5].strip()
                    })
            
            # Simple pattern for exact format from terminal
            if not risks:
                simple_pattern = r'Risk (\d+):\s*\n- Risk Category:\s*([^\n]+)\n- Risk Level:\s*([^\n]+)\n- Risk Description:\s*([^\n]+)\n- Impact:\s*([^\n]+)\n- Mitigation:\s*([^\n]+)'
                simple_matches = re.findall(simple_pattern, section, re.IGNORECASE | re.DOTALL)
                self.logger.debug(f"Risk simple pattern matches: {len(simple_matches)}")
                
                for match in simple_matches:
                    risks.append({
                        'title': f"Risk {match[0]}: {match[2].strip()}",
                        'description': match[4].strip(),
                        'severity': match[3].strip().lower(),
                        'impact': match[5].strip(),
                        'mitigation': match[6].strip()
                    })
            
            # Fallback to simple list extraction
            if not risks:
                # Simple fallback - just add a generic risk if none found
                risks.append({
                    'title': 'Risk Identified',
                    'description': 'Risk assessment required',
                    'severity': 'medium',
                    'impact': 'Potential impact on project',
                    'mitigation': 'Review and address'
                })
        
        self.logger.debug(f"Final extracted risks: {len(risks)} items")
        for i, risk in enumerate(risks):
            self.logger.debug(f"Risk {i+1}: {risk.get('title', 'No title')} - {risk.get('severity', 'No severity')}")
        return risks
    
    def _extract_recommendations(self, response: str) -> List[Dict[str, Any]]:
        """Extract recommendations from the response."""
        recommendations = []
        
        # Look for recommendations sections
        rec_sections = re.findall(r'RECOMMENDATIONS.*?(?=OPPORTUNITIES|\Z)', response, re.IGNORECASE | re.DOTALL)
        
        for section in rec_sections:
            # Look for structured recommendation entries with Recommendation X pattern (no markdown)
            rec_pattern = r'Recommendation (\d+):\s*\n- Recommendation Type:\s*([^\n]+)\n- Priority Level:\s*([^\n]+)\n- Recommendation Description:\s*([^\n]+)\n- Rationale:\s*([^\n]+)\n- Implementation:\s*([^\n]+)'
            matches = re.findall(rec_pattern, section, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                recommendations.append({
                    'title': f"Recommendation {match[0]}: {match[1].strip()}",
                    'description': match[3].strip(),
                    'priority': match[2].strip().lower(),
                    'rationale': match[4].strip(),
                    'implementation': match[5].strip()
                })
            
            # Alternative pattern for different formatting
            if not recommendations:
                rec_pattern_alt = r'Recommendation (\d+):\s*\n- Recommendation Type:\s*([^\n]+)\n- Priority Level:\s*([^\n]+)\n- Recommendation Description:\s*([^\n]+)\n- Rationale:\s*([^\n]+)\n- Implementation:\s*([^\n]+)'
                matches_alt = re.findall(rec_pattern_alt, section, re.IGNORECASE | re.DOTALL)
                self.logger.debug(f"Rec alt pattern matches: {len(matches_alt)}")
                
                for match in matches_alt:
                    recommendations.append({
                        'title': f"Recommendation {match[0]}: {match[1].strip()}",
                        'description': match[3].strip(),
                        'priority': match[2].strip().lower(),
                        'rationale': match[4].strip(),
                        'implementation': match[5].strip()
                    })
            
            # Simple pattern for exact format from terminal
            if not recommendations:
                simple_pattern = r'Recommendation (\d+):\s*\n- Recommendation Type:\s*([^\n]+)\n- Priority Level:\s*([^\n]+)\n- Recommendation Description:\s*([^\n]+)\n- Rationale:\s*([^\n]+)\n- Implementation:\s*([^\n]+)'
                simple_matches = re.findall(simple_pattern, section, re.IGNORECASE | re.DOTALL)
                self.logger.debug(f"Rec simple pattern matches: {len(simple_matches)}")
                
                for match in simple_matches:
                    recommendations.append({
                        'title': f"Recommendation {match[0]}: {match[2].strip()}",
                        'description': match[4].strip(),
                        'priority': match[3].strip().lower(),
                        'rationale': match[5].strip(),
                        'implementation': match[6].strip()
                    })
            
            # Fallback to simple list extraction
            if not recommendations:
                # Simple fallback - just add a generic recommendation if none found
                recommendations.append({
                    'title': 'Recommendation',
                    'description': 'Recommendation required',
                    'priority': 'medium',
                    'rationale': 'Important for project success',
                    'implementation': 'Review and implement'
                })
        
        self.logger.debug(f"Final extracted recommendations: {len(recommendations)} items")
        for i, rec in enumerate(recommendations):
            self.logger.debug(f"Recommendation {i+1}: {rec.get('title', 'No title')} - {rec.get('priority', 'No priority')}")
        return recommendations
    
    def _extract_dependencies(self, response: str) -> List[Dict[str, Any]]:
        """Extract dependencies from the response."""
        dependencies = []
        
        # Look for dependencies sections
        dep_sections = re.findall(r'DEPENDENCIES.*?(?=RECOMMENDATIONS|OPPORTUNITIES|\Z)', response, re.IGNORECASE | re.DOTALL)
        
        for section in dep_sections:
            # Look for structured dependency entries with Dependency X pattern (no markdown)
            dep_pattern = r'Dependency (\d+):\s*\n- Dependency Type:\s*([^\n]+)\n- Dependency Level:\s*([^\n]+)\n- Dependency Description:\s*([^\n]+)\n- Impact:\s*([^\n]+)\n- Action Required:\s*([^\n]+)'
            matches = re.findall(dep_pattern, section, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                dependencies.append({
                    'title': f"Dependency {match[0]}: {match[1].strip()}",
                    'description': match[3].strip(),
                    'type': match[2].strip().lower(),
                    'impact': match[4].strip(),
                    'actionRequired': match[5].strip()
                })
            
            # Alternative pattern for different formatting
            if not dependencies:
                dep_pattern_alt = r'Dependency (\d+):\s*\n- Dependency Type:\s*([^\n]+)\n- Dependency Level:\s*([^\n]+)\n- Dependency Description:\s*([^\n]+)\n- Impact:\s*([^\n]+)\n- Action Required:\s*([^\n]+)'
                matches_alt = re.findall(dep_pattern_alt, section, re.IGNORECASE | re.DOTALL)
                self.logger.debug(f"Dep alt pattern matches: {len(matches_alt)}")
                
                for match in matches_alt:
                    dependencies.append({
                        'title': f"Dependency {match[0]}: {match[1].strip()}",
                        'description': match[3].strip(),
                        'type': match[2].strip().lower(),
                        'impact': match[4].strip(),
                        'actionRequired': match[5].strip()
                    })
            
            # Simple pattern for exact format from terminal
            if not dependencies:
                simple_pattern = r'Dependency (\d+):\s*\n- Dependency Type:\s*([^\n]+)\n- Dependency Level:\s*([^\n]+)\n- Dependency Description:\s*([^\n]+)\n- Impact:\s*([^\n]+)\n- Action Required:\s*([^\n]+)'
                simple_matches = re.findall(simple_pattern, section, re.IGNORECASE | re.DOTALL)
                self.logger.debug(f"Dep simple pattern matches: {len(simple_matches)}")
                
                for match in simple_matches:
                    dependencies.append({
                        'title': f"Dependency {match[0]}: {match[2].strip()}",
                        'description': match[4].strip(),
                        'type': match[3].strip().lower(),
                        'impact': match[5].strip(),
                        'actionRequired': match[6].strip()
                    })
            
            # Fallback to simple list extraction
            if not dependencies:
                # Simple fallback - just add a generic dependency if none found
                dependencies.append({
                    'title': 'Dependency',
                    'description': 'Dependency identified',
                    'type': 'medium',
                    'impact': 'Potential impact on project',
                    'actionRequired': 'Review and address'
                })
        
        self.logger.debug(f"Final extracted dependencies: {len(dependencies)} items")
        for i, dep in enumerate(dependencies):
            self.logger.debug(f"Dependency {i+1}: {dep.get('title', 'No title')} - {dep.get('type', 'No type')}")
        return dependencies
    
    def _extract_opportunities(self, response: str) -> List[Dict[str, Any]]:
        """Extract opportunities from the response."""
        opportunities = []
        
        # Look for opportunities sections
        opp_sections = re.findall(r'OPPORTUNITIES.*?(?=\Z)', response, re.IGNORECASE | re.DOTALL)
        
        for section in opp_sections:
            # Look for structured opportunity entries with Opportunity X pattern (no markdown)
            opp_pattern = r'Opportunity (\d+):\s*\n- Opportunity Type:\s*([^\n]+)\n- Opportunity Level:\s*([^\n]+)\n- Opportunity Description:\s*([^\n]+)\n- Benefits:\s*([^\n]+)\n- Action Required:\s*([^\n]+)'
            matches = re.findall(opp_pattern, section, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                opportunities.append({
                    'title': f"Opportunity {match[0]}: {match[1].strip()}",
                    'description': match[3].strip(),
                    'level': match[2].strip().lower(),
                    'benefits': match[4].strip(),
                    'actionRequired': match[5].strip()
                })
            
            # Alternative pattern for different formatting
            if not opportunities:
                opp_pattern_alt = r'Opportunity (\d+):\s*\n- Opportunity Type:\s*([^\n]+)\n- Opportunity Level:\s*([^\n]+)\n- Opportunity Description:\s*([^\n]+)\n- Benefits:\s*([^\n]+)\n- Action Required:\s*([^\n]+)'
                matches_alt = re.findall(opp_pattern_alt, section, re.IGNORECASE | re.DOTALL)
                self.logger.debug(f"Opp alt pattern matches: {len(matches_alt)}")
                
                for match in matches_alt:
                    opportunities.append({
                        'title': f"Opportunity {match[0]}: {match[1].strip()}",
                        'description': match[3].strip(),
                        'level': match[2].strip().lower(),
                        'benefits': match[4].strip(),
                        'actionRequired': match[5].strip()
                    })
            
            # Simple pattern for exact format from terminal
            if not opportunities:
                simple_pattern = r'Opportunity (\d+):\s*\n- Opportunity Type:\s*([^\n]+)\n- Opportunity Level:\s*([^\n]+)\n- Opportunity Description:\s*([^\n]+)\n- Benefits:\s*([^\n]+)\n- Action Required:\s*([^\n]+)'
                simple_matches = re.findall(simple_pattern, section, re.IGNORECASE | re.DOTALL)
                self.logger.debug(f"Opp simple pattern matches: {len(simple_matches)}")
                
                for match in simple_matches:
                    opportunities.append({
                        'title': f"Opportunity {match[0]}: {match[2].strip()}",
                        'description': match[4].strip(),
                        'level': match[3].strip().lower(),
                        'benefits': match[5].strip(),
                        'actionRequired': match[6].strip()
                    })
            
            # Fallback to simple list extraction
            if not opportunities:
                # Simple fallback - just add a generic opportunity if none found
                opportunities.append({
                    'title': 'Opportunity',
                    'description': 'Opportunity identified',
                    'level': 'medium',
                    'benefits': 'Potential benefits for project',
                    'actionRequired': 'Review and implement'
                })
        
        self.logger.debug(f"Final extracted opportunities: {len(opportunities)} items")
        for i, opp in enumerate(opportunities):
            self.logger.debug(f"Opportunity {i+1}: {opp.get('title', 'No title')} - {opp.get('level', 'No level')}")
        return opportunities
    
    def _generate_summary(self, work_items: List[ParsedWorkItem], patterns: List[str], risks: List[str], recommendations: List[str]) -> Dict[str, Any]:
        """Generate summary statistics."""
        return {
            'total_related_items': len(work_items),
            'high_confidence_items': len([item for item in work_items if item.confidence == 'high']),
            'medium_confidence_items': len([item for item in work_items if item.confidence == 'medium']),
            'low_confidence_items': len([item for item in work_items if item.confidence == 'low']),
            'relationship_patterns_found': len(patterns),
            'risks_identified': len(risks),
            'recommendations_generated': len(recommendations),
            'parsing_timestamp': datetime.now().isoformat()
        }
    
    def _get_work_item_field(self, work_item: Any, field_name: str, default: str = '') -> str:
        """Safely get a field from a work item object."""
        try:
            if hasattr(work_item, 'fields'):
                return work_item.fields.get(field_name, default)
            elif isinstance(work_item, dict):
                return work_item.get(field_name, default)
            else:
                return default
        except:
            return default
    
    def _get_assigned_to(self, work_item: Any) -> str:
        """Get assigned to information from work item."""
        try:
            if hasattr(work_item, 'fields'):
                assigned_to = work_item.fields.get('System.AssignedTo', {})
                if isinstance(assigned_to, dict):
                    return assigned_to.get('displayName', 'Unassigned')
                return str(assigned_to) if assigned_to else 'Unassigned'
            elif isinstance(work_item, dict):
                assigned_to = work_item.get('System.AssignedTo', {})
                if isinstance(assigned_to, dict):
                    return assigned_to.get('displayName', 'Unassigned')
                return str(assigned_to) if assigned_to else 'Unassigned'
            else:
                return 'Unassigned'
        except:
            return 'Unassigned'

def convert_parsed_analysis_to_dict(parsed_analysis: ParsedAnalysis, raw_analysis: str = None) -> Dict[str, Any]:
    """Convert ParsedAnalysis to dictionary format for API response."""
    
    def convert_work_item(work_item: ParsedWorkItem) -> Dict[str, Any]:
        return {
            'id': work_item.id,
            'title': work_item.title,
            'type': work_item.work_item_type,
            'state': work_item.state,
            'assignedTo': work_item.assigned_to,
            'areaPath': work_item.area_path,
            'iterationPath': work_item.iteration_path,
            'description': work_item.description,
            'confidence': work_item.confidence,
            'relationshipType': work_item.relationship_type,
            'reasoning': work_item.reasoning,
            'evidence': work_item.evidence,
            'impact': work_item.impact,
            'priority': work_item.priority,
            'createdDate': work_item.created_date if hasattr(work_item, 'created_date') else 'N/A',
            'lastUpdated': 'Recently'
        }
    
    result = {
        'highConfidenceItems': [convert_work_item(item) for item in parsed_analysis.high_confidence_items],
        'mediumConfidenceItems': [convert_work_item(item) for item in parsed_analysis.medium_confidence_items],
        'lowConfidenceItems': [convert_work_item(item) for item in parsed_analysis.low_confidence_items],
        'relationshipPatterns': parsed_analysis.relationship_patterns,
        'riskAssessment': parsed_analysis.risk_assessment,
        'dependencies': parsed_analysis.dependencies,
        'recommendations': parsed_analysis.recommendations,
        'opportunities': parsed_analysis.opportunities,
        'summary': parsed_analysis.summary
    }
    
    # Add raw analysis text if provided
    if raw_analysis:
        result['analysis'] = raw_analysis
        result['analysisResults'] = raw_analysis  # Keep both for backward compatibility
    
    return result

# Example usage and testing
if __name__ == "__main__":
    # Test the parser with sample data
    parser = AdvancedLLMResponseParser()
    
    sample_response = """
    ## HIGH CONFIDENCE RELATIONSHIPS
    - **ID:** 2213654 - Direct dependency for authentication system
    - **ID:** 2172541 - Prerequisite for user management features
    
    ## MEDIUM CONFIDENCE RELATIONSHIPS  
    - **ID:** 2174716 - Related to security implementation
    - **ID:** 2225022 - Associated with user interface components
    
    ## LOW CONFIDENCE RELATIONSHIPS
    - **ID:** 2174701 - Possible connection through shared components
    
    ## RELATIONSHIP PATTERNS ANALYSIS
    - Primary Patterns: Authentication and security related items
    - Dependency Clusters: User management feature group
    
    ## RISK ASSESSMENT
    - High-Risk Dependencies: Authentication system must be completed first
    - Blocking Issues: Security implementation could delay progress
    
    ## RECOMMENDATIONS
    - Coordinate with security team
    - Prioritize authentication dependencies
    """
    
    # Mock work items
    class MockWorkItem:
        def __init__(self, id, title, work_item_type, state):
            self.id = id
            self.fields = {
                'System.Title': title,
                'System.WorkItemType': work_item_type,
                'System.State': state,
                'System.AssignedTo': {'displayName': 'Test User'},
                'System.AreaPath': 'Test\\Area',
                'System.IterationPath': 'Test\\Sprint 1',
                'System.Description': 'Test description'
            }
    
    mock_work_items = [
        MockWorkItem(2213654, "Authentication System", "Epic", "Active"),
        MockWorkItem(2172541, "User Management", "Feature", "New"),
        MockWorkItem(2174716, "Security Implementation", "Task", "Active"),
        MockWorkItem(2225022, "UI Components", "Task", "New"),
        MockWorkItem(2174701, "Shared Components", "Task", "Closed")
    ]
    
    selected_work_item = MockWorkItem(12345, "Selected Item", "User Story", "Active")
    
    # Parse the response
    result = parser.parse_response(sample_response, mock_work_items, selected_work_item)
    
    print("=== PARSING RESULTS ===")
    print(f"High confidence items: {len(result.high_confidence_items)}")
    print(f"Medium confidence items: {len(result.medium_confidence_items)}")
    print(f"Low confidence items: {len(result.low_confidence_items)}")
    print(f"Relationship patterns: {len(result.relationship_patterns)}")
    print(f"Risks identified: {len(result.risk_assessment)}")
    print(f"Recommendations: {len(result.recommendations)}")
    
    # Convert to dict format
    dict_result = convert_parsed_analysis_to_dict(result)
    print(f"\n=== DICT FORMAT ===")
    print(json.dumps(dict_result, indent=2))

