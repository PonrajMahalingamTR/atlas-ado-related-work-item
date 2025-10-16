"""
Text Preprocessing Module

This module handles text preprocessing for work items before embedding generation.
It includes HTML/Markdown stripping, noise reduction, and text normalization.
"""

import re
import html
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import unicodedata
from bs4 import BeautifulSoup
import markdown
from .config import PreprocessingConfig

logger = logging.getLogger(__name__)

@dataclass
class PreprocessingResult:
    """Result of text preprocessing."""
    original_text: str
    processed_text: str
    preprocessing_steps: List[str]
    text_length_before: int
    text_length_after: int
    success: bool
    error: Optional[str] = None

class TextPreprocessor:
    """Text preprocessor for work item content."""
    
    def __init__(self, config: PreprocessingConfig):
        self.config = config
        self._html_parser = BeautifulSoup
        self._markdown_parser = markdown.Markdown()
        
        # Common boilerplate patterns to remove
        self.boilerplate_patterns = [
            r'As a user,?\s+I want\s+',
            r'As a\s+\w+,\s+I want\s+',
            r'Given\s+that\s+',
            r'When\s+I\s+',
            r'Then\s+I\s+',
            r'Acceptance criteria:?\s*',
            r'Definition of done:?\s*',
            r'User story:?\s*',
            r'Task:?\s*',
            r'Bug:?\s*',
            r'Epic:?\s*',
            r'Feature:?\s*',
        ]
        
        # Compile regex patterns for efficiency
        self._compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.boilerplate_patterns]
    
    def preprocess_work_item(self, work_item: Dict[str, Any]) -> PreprocessingResult:
        """Preprocess a single work item."""
        try:
            # Extract and combine text fields
            text_fields = self._extract_text_fields(work_item)
            combined_text = self._combine_text_fields(text_fields)
            
            if not combined_text or len(combined_text.strip()) < self.config.min_text_length:
                return PreprocessingResult(
                    original_text=combined_text,
                    processed_text="",
                    preprocessing_steps=["text_too_short"],
                    text_length_before=len(combined_text),
                    text_length_after=0,
                    success=False,
                    error="Text too short for processing"
                )
            
            # Apply preprocessing steps
            processed_text = combined_text
            steps_applied = []
            
            # HTML stripping
            if self.config.remove_html:
                processed_text = self._remove_html(processed_text)
                steps_applied.append("html_removed")
            
            # Markdown stripping
            if self.config.remove_markdown:
                processed_text = self._remove_markdown(processed_text)
                steps_applied.append("markdown_removed")
            
            # Code block removal
            if self.config.remove_code_blocks:
                processed_text = self._remove_code_blocks(processed_text)
                steps_applied.append("code_blocks_removed")
            
            # URL removal
            if self.config.remove_urls:
                processed_text = self._remove_urls(processed_text)
                steps_applied.append("urls_removed")
            
            # Email removal
            if self.config.remove_emails:
                processed_text = self._remove_emails(processed_text)
                steps_applied.append("emails_removed")
            
            # Boilerplate removal
            processed_text = self._remove_boilerplate(processed_text)
            steps_applied.append("boilerplate_removed")
            
            # Whitespace normalization
            if self.config.normalize_whitespace:
                processed_text = self._normalize_whitespace(processed_text)
                steps_applied.append("whitespace_normalized")
            
            # Truncate if too long
            if len(processed_text) > self.config.max_text_length:
                processed_text = processed_text[:self.config.max_text_length]
                steps_applied.append("text_truncated")
            
            # Final validation
            if len(processed_text.strip()) < self.config.min_text_length:
                return PreprocessingResult(
                    original_text=combined_text,
                    processed_text="",
                    preprocessing_steps=steps_applied,
                    text_length_before=len(combined_text),
                    text_length_after=0,
                    success=False,
                    error="Text too short after preprocessing"
                )
            
            return PreprocessingResult(
                original_text=combined_text,
                processed_text=processed_text.strip(),
                preprocessing_steps=steps_applied,
                text_length_before=len(combined_text),
                text_length_after=len(processed_text),
                success=True
            )
        
        except Exception as e:
            logger.error(f"Error preprocessing work item {work_item.get('id', 'unknown')}: {str(e)}")
            return PreprocessingResult(
                original_text=work_item.get('title', ''),
                processed_text="",
                preprocessing_steps=[],
                text_length_before=0,
                text_length_after=0,
                success=False,
                error=str(e)
            )
    
    def preprocess_work_items(self, work_items: List[Dict[str, Any]]) -> List[PreprocessingResult]:
        """Preprocess multiple work items."""
        results = []
        for work_item in work_items:
            result = self.preprocess_work_item(work_item)
            results.append(result)
        
        successful_count = sum(1 for r in results if r.success)
        logger.info(f"Preprocessed {len(work_items)} work items: {successful_count} successful")
        
        return results
    
    def _extract_text_fields(self, work_item: Dict[str, Any]) -> Dict[str, str]:
        """Extract relevant text fields from work item."""
        fields = {}
        
        # Title (highest priority)
        if 'title' in work_item:
            fields['title'] = str(work_item['title'])
        elif 'fields' in work_item and 'System.Title' in work_item['fields']:
            fields['title'] = str(work_item['fields']['System.Title'])
        
        # Description (high priority)
        if 'description' in work_item:
            fields['description'] = str(work_item['description'])
        elif 'fields' in work_item and 'System.Description' in work_item['fields']:
            fields['description'] = str(work_item['fields']['System.Description'])
        
        # Acceptance Criteria (high priority)
        if 'fields' in work_item and 'Microsoft.VSTS.Common.AcceptanceCriteria' in work_item['fields']:
            fields['acceptance_criteria'] = str(work_item['fields']['Microsoft.VSTS.Common.AcceptanceCriteria'])
        
        # Repro Steps (for bugs)
        if 'fields' in work_item and 'Microsoft.VSTS.TCM.ReproSteps' in work_item['fields']:
            fields['repro_steps'] = str(work_item['fields']['Microsoft.VSTS.TCM.ReproSteps'])
        
        # System Info (for bugs)
        if 'fields' in work_item and 'Microsoft.VSTS.Build.FoundIn' in work_item['fields']:
            fields['found_in'] = str(work_item['fields']['Microsoft.VSTS.Build.FoundIn'])
        
        # Business Value (for user stories)
        if 'fields' in work_item and 'Microsoft.VSTS.Common.BusinessValue' in work_item['fields']:
            fields['business_value'] = str(work_item['fields']['Microsoft.VSTS.Common.BusinessValue'])
        
        # Tags (medium priority)
        if 'tags' in work_item:
            fields['tags'] = str(work_item['tags'])
        elif 'fields' in work_item and 'System.Tags' in work_item['fields']:
            fields['tags'] = str(work_item['fields']['System.Tags'])
        
        # Work Item Type (medium priority)
        if 'workItemType' in work_item:
            fields['work_item_type'] = str(work_item['workItemType'])
        elif 'fields' in work_item and 'System.WorkItemType' in work_item['fields']:
            fields['work_item_type'] = str(work_item['fields']['System.WorkItemType'])
        
        # Area Path (medium priority)
        if 'fields' in work_item and 'System.AreaPath' in work_item['fields']:
            fields['area_path'] = str(work_item['fields']['System.AreaPath'])
        
        # Iteration Path (low priority)
        if 'fields' in work_item and 'System.IterationPath' in work_item['fields']:
            fields['iteration_path'] = str(work_item['fields']['System.IterationPath'])
        
        # State (low priority)
        if 'state' in work_item:
            fields['state'] = str(work_item['state'])
        elif 'fields' in work_item and 'System.State' in work_item['fields']:
            fields['state'] = str(work_item['fields']['System.State'])
        
        return fields
    
    def _combine_text_fields(self, fields: Dict[str, str]) -> str:
        """Combine text fields into a single text block."""
        # Order of importance for combining - prioritize content over metadata
        field_order = [
            'title',
            'description', 
            'acceptance_criteria',
            'repro_steps',
            'business_value',
            'found_in',
            'work_item_type',
            'area_path',
            'tags',
            'iteration_path',
            'state'
        ]
        
        combined_parts = []
        for field_name in field_order:
            if field_name in fields and fields[field_name].strip():
                combined_parts.append(fields[field_name].strip())
        
        return '\n\n'.join(combined_parts)
    
    def _remove_html(self, text: str) -> str:
        """Remove HTML tags and entities."""
        try:
            # Parse HTML and extract text
            soup = self._html_parser(text, 'html.parser')
            text = soup.get_text()
            
            # Decode HTML entities
            text = html.unescape(text)
            
            return text
        except Exception as e:
            logger.warning(f"Error removing HTML: {str(e)}")
            return text
    
    def _remove_markdown(self, text: str) -> str:
        """Remove markdown formatting."""
        try:
            # Convert markdown to HTML first, then extract text
            html_text = self._markdown_parser.convert(text)
            soup = self._html_parser(html_text, 'html.parser')
            return soup.get_text()
        except Exception as e:
            logger.warning(f"Error removing markdown: {str(e)}")
            return text
    
    def _remove_code_blocks(self, text: str) -> str:
        """Remove code blocks and inline code."""
        # Remove fenced code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'~~~[\s\S]*?~~~', '', text)
        
        # Remove inline code
        text = re.sub(r'`[^`]+`', '', text)
        
        return text
    
    def _remove_urls(self, text: str) -> str:
        """Remove URLs from text."""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.sub(url_pattern, '', text)
    
    def _remove_emails(self, text: str) -> str:
        """Remove email addresses from text."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.sub(email_pattern, '', text)
    
    def _remove_boilerplate(self, text: str) -> str:
        """Remove common boilerplate text patterns."""
        for pattern in self._compiled_patterns:
            text = pattern.sub('', text)
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace characters."""
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Normalize unicode characters
        text = unicodedata.normalize('NFKC', text)
        
        return text
    
    def get_preprocessing_stats(self, results: List[PreprocessingResult]) -> Dict[str, Any]:
        """Get statistics about preprocessing results."""
        total_items = len(results)
        successful_items = sum(1 for r in results if r.success)
        failed_items = total_items - successful_items
        
        # Calculate average text length reduction
        length_reductions = []
        for result in results:
            if result.success and result.text_length_before > 0:
                reduction = (result.text_length_before - result.text_length_after) / result.text_length_before
                length_reductions.append(reduction)
        
        avg_reduction = sum(length_reductions) / len(length_reductions) if length_reductions else 0
        
        # Count preprocessing steps
        step_counts = {}
        for result in results:
            for step in result.preprocessing_steps:
                step_counts[step] = step_counts.get(step, 0) + 1
        
        return {
            "total_items": total_items,
            "successful_items": successful_items,
            "failed_items": failed_items,
            "success_rate": successful_items / total_items if total_items > 0 else 0,
            "average_length_reduction": avg_reduction,
            "step_counts": step_counts
        }



