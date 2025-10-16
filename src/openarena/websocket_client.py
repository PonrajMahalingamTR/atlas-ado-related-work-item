#!/usr/bin/env python3
"""
OpenArena WebSocket Client
Connects to OpenArena via WebSocket for LLM-powered backlog refinement
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from websockets.sync.client import connect
import asyncio
from datetime import datetime
from pathlib import Path
from .config.settings import get_config

class OpenArenaWebSocketClient:
    """WebSocket client for Thomson Reuters OpenArena API"""
    
    def __init__(self, esso_token: str = None, base_url: str = None):
        """
        Initialize OpenArena WebSocket client
        
        Args:
            esso_token: ESSO token without 'Bearer' keyword (optional, will use config if not provided)
            base_url: WebSocket base URL (optional, will use config if not provided)
        """
        # Get configuration
        self.config = get_config()
        
        # Use provided values or fall back to config
        self.esso_token = esso_token or self.config.esso_token
        self.base_url = base_url or self.config.websocket_base_url
        
        if not self.esso_token:
            raise ValueError("ESSO token is required. Set OPENARENA_ESSO_TOKEN in env_config.py or pass it to constructor.")
        
        # Extract token without 'bearer ' prefix for query parameter
        self.esso_token_raw = self.esso_token[7:] if self.esso_token.startswith('bearer ') else self.esso_token
        self.ws_url = f"{self.base_url}/?Authorization={self.esso_token_raw}"
        self.logger = logging.getLogger(__name__)
        
        # Get workflow IDs from config
        self.workflow_ids = {
            'claude41opus': self.config.get_workflow_id('claude41opus'),
            'gpt5': self.config.get_workflow_id('gpt5'),
            'gemini25pro': self.config.get_workflow_id('gemini25pro'),
            'llama3_70b': self.config.get_workflow_id('llama3_70b'),
            'gpt4': self.config.get_workflow_id('gpt4'),
            'gpt4_turbo': self.config.get_workflow_id('gpt4_turbo'),
            'gpt35': self.config.get_workflow_id('gpt35'),
            'azure_openai': self.config.get_workflow_id('azure_openai'),
            'azuredevopsagent': self.config.get_workflow_id('azuredevopsagent')
        }
    
    def _receive_with_timeout(self, ws, timeout_seconds):
        """Receive message with timeout using threading"""
        import threading
        import queue
        
        result_queue = queue.Queue()
        error_queue = queue.Queue()
        
        def receive_worker():
            try:
                message = ws.recv()
                result_queue.put(('success', message))
            except Exception as e:
                error_queue.put(('error', str(e)))
        
        # Start receiver thread
        receiver_thread = threading.Thread(target=receive_worker, daemon=True)
        receiver_thread.start()
        
        # Wait for result or timeout
        try:
            # Check result queue first
            try:
                result_type, result = result_queue.get(timeout=timeout_seconds)
                if result_type == 'success':
                    return result
                else:
                    raise Exception(result)
            except queue.Empty:
                # Timeout occurred
                raise Exception(f"Receive timeout after {timeout_seconds} seconds")
        except Exception as e:
            # Check if there was an error in the worker thread
            try:
                error_type, error_msg = error_queue.get_nowait()
                if error_type == 'error':
                    raise Exception(error_msg)
            except queue.Empty:
                pass
            raise e
    
    def _handle_large_message(self, query: str, workflow_id: str, is_persistence_allowed: bool,
                            current_size: int, max_size: int, safe_size: int) -> Tuple[str, Dict[str, Any]]:
        """
        Handle messages that are too large by implementing intelligent chunking strategies.
        
        Args:
            query: Original query string
            workflow_id: Workflow ID to use
            is_persistence_allowed: Whether persistence is allowed
            current_size: Current message size in bytes
            max_size: Maximum allowed message size
            safe_size: Safe message size limit
            
        Returns:
            Tuple of (answer, cost_tracker) or None if chunking fails
        """
        self.logger.info(f"Attempting intelligent message chunking (current: {current_size}, target: {safe_size})")
        
        # Strategy 1: Smart truncation - remove less important data
        truncated_query = self._truncate_query_intelligently(query, safe_size)
        if truncated_query:
            self.logger.info("Using smart truncation strategy")
            return self._send_chunked_query(workflow_id, truncated_query, is_persistence_allowed)
        
        # Strategy 2: Summary approach - create a high-level summary
        summary_query = self._create_summary_query(query, safe_size)
        if summary_query:
            self.logger.info("Using summary strategy")
            return self._send_chunked_query(workflow_id, summary_query, is_persistence_allowed)
        
        # Strategy 3: Minimal approach - send only essential information
        minimal_query = self._create_minimal_query(query, safe_size)
        if minimal_query:
            self.logger.info("Using minimal strategy")
            return self._send_chunked_query(workflow_id, minimal_query, is_persistence_allowed)
        
        self.logger.error("All chunking strategies failed")
        return None
    
    def _send_chunked_query(self, workflow_id: str, chunked_query: str, is_persistence_allowed: bool) -> Tuple[str, Dict[str, Any]]:
        """Send a chunked query and return the result."""
        msg = {
            "action": "SendMessage",
            "workflow_id": workflow_id,
            "query": chunked_query,
            "is_persistence_allowed": is_persistence_allowed
        }
        
        msg_json = json.dumps(msg)
        msg_size = len(msg_json.encode('utf-8'))
        max_frame_size = int(os.getenv('OPENARENA_MAX_MESSAGE_SIZE', '1000000'))
        
        self.logger.info(f"Sending chunked message: {msg_size} bytes")
        
        try:
            ws = connect(self.ws_url, max_size=max_frame_size)
            ws.send(msg_json)
            
            answer = ""
            cost_tracker = {}
            eof = False
            timeout_seconds = self.config.timeout
            start_time = datetime.now()
            
            while not eof:
                # Check for timeout
                elapsed_time = (datetime.now() - start_time).total_seconds()
                if elapsed_time > timeout_seconds:
                    self.logger.error(f"WebSocket query timeout after {timeout_seconds} seconds")
                    ws.close()
                    return "", {"error": f"Query timeout after {timeout_seconds} seconds"}
                
                try:
                    remaining_timeout = max(10, timeout_seconds - elapsed_time)
                    message = self._receive_with_timeout(ws, remaining_timeout)
                    
                    try:
                        message_data = json.loads(message)
                        for model, value in message_data.items():
                            if "answer" in value:
                                answer += value["answer"]
                            elif "cost_track" in value:
                                cost_tracker = value['cost_track']
                                eof = True
                                # Add metadata about chunking
                                cost_tracker['chunking_applied'] = True
                                cost_tracker['original_size'] = len(msg_json.encode('utf-8'))
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse message as JSON: {e}")
                        continue
                        
                except Exception as recv_error:
                    self.logger.error(f"Error receiving message: {recv_error}")
                    # Check if it's a timeout error
                    if "timeout" in str(recv_error).lower():
                        self.logger.error(f"WebSocket receive timeout after {elapsed_time:.2f} seconds (configured timeout: {timeout_seconds}s)")
                    break
            
            ws.close()
            self.logger.info(f"Chunked query completed. Answer length: {len(answer)}")
            return answer, cost_tracker
            
        except Exception as e:
            self.logger.error(f"Chunked WebSocket connection failed: {e}")
            return "", {"error": str(e)}
    
    def _truncate_query_intelligently(self, query: str, target_size: int) -> str:
        """
        Truncate the query intelligently by removing less important data while preserving structure.
        """
        # Calculate approximate target query length (accounting for JSON overhead)
        base_overhead = 200  # Approximate JSON structure overhead
        target_query_length = target_size - base_overhead
        
        if len(query) <= target_query_length:
            return query
        
        self.logger.info(f"Truncating query from {len(query)} to ~{target_query_length} characters")
        
        # Strategy: Find the work items section and truncate it intelligently
        lines = query.split('\n')
        truncated_lines = []
        char_count = 0
        work_items_section_started = False
        preserved_header = True
        work_items_included = 0
        
        for line in lines:
            # Always preserve the system prompt header
            if not work_items_section_started and ('SELECTED WORK ITEM' in line or 'ALL WORK ITEMS FOR ANALYSIS' in line):
                work_items_section_started = True
            
            # If we haven't started the work items section, include the line
            if not work_items_section_started:
                if char_count + len(line) < target_query_length * 0.6:  # Use 60% for header
                    truncated_lines.append(line)
                    char_count += len(line) + 1
                continue
            
            # In work items section, be selective
            if work_items_section_started:
                # Include important structural lines
                if any(keyword in line for keyword in ['ID:', 'Title:', 'Type:', 'State:', 'Priority:']):
                    if char_count + len(line) < target_query_length:
                        truncated_lines.append(line)
                        char_count += len(line) + 1
                        if 'ID:' in line:
                            work_items_included += 1
                # Skip long description lines if we're running out of space
                elif 'Description:' in line and char_count > target_query_length * 0.8:
                    truncated_lines.append("Description: [Truncated for size limits]")
                    char_count += 50
                else:
                    if char_count + len(line) < target_query_length:
                        truncated_lines.append(line)
                        char_count += len(line) + 1
                    else:
                        # Add truncation notice
                        truncated_lines.append(f"\n[TRUNCATED: Showing {work_items_included} work items due to size limits]")
                        break
        
        truncated_query = '\n'.join(truncated_lines)
        self.logger.info(f"Truncated query to {len(truncated_query)} characters, included {work_items_included} work items")
        
        return truncated_query if len(truncated_query) < len(query) else None
    
    def _create_summary_query(self, query: str, target_size: int) -> str:
        """
        Create a summary version of the query with only essential information.
        """
        target_query_length = target_size - 200  # Account for JSON overhead
        
        if len(query) <= target_query_length:
            return query
        
        self.logger.info(f"Creating summary query (target: {target_query_length} characters)")
        
        # Extract key components
        lines = query.split('\n')
        selected_work_item = ""
        work_items_summary = []
        
        current_section = "none"
        current_item = {}
        
        for line in lines:
            if "SELECTED WORK ITEM" in line:
                current_section = "selected"
                continue
            elif "ALL WORK ITEMS FOR ANALYSIS" in line:
                current_section = "all_items"
                continue
            
            if current_section == "selected" and line.strip():
                selected_work_item += line + "\n"
                if len(selected_work_item) > 1000:  # Limit selected item description
                    selected_work_item = selected_work_item[:1000] + "...[truncated]"
                    current_section = "none"
            
            elif current_section == "all_items" and line.strip():
                if line.startswith("ID:"):
                    if current_item:
                        work_items_summary.append(current_item)
                    current_item = {"id": line}
                elif line.startswith("Title:"):
                    current_item["title"] = line
                elif line.startswith("Type:"):
                    current_item["type"] = line
                elif line.startswith("State:"):
                    current_item["state"] = line
                elif line.startswith("Priority:"):
                    current_item["priority"] = line
                # Skip descriptions and other details for summary
        
        if current_item:
            work_items_summary.append(current_item)
        
        # Create concise summary query
        summary_query = f"""
You are an expert Azure DevOps analyst. Analyze relationships between work items.

SELECTED WORK ITEM:
{selected_work_item}

WORK ITEMS FOR ANALYSIS (Summary - {len(work_items_summary)} total items):
"""
        
        char_budget = target_query_length - len(summary_query) - 500  # Reserve space for instructions
        
        for i, item in enumerate(work_items_summary):
            if i > 50:  # Limit to first 50 items in summary
                summary_query += f"\n[... and {len(work_items_summary) - 50} more items truncated for size limits]"
                break
                
            item_summary = ""
            for key, value in item.items():
                item_summary += value + "\n"
            
            if len(summary_query) + len(item_summary) < char_budget:
                summary_query += item_summary + "\n"
            else:
                summary_query += f"\n[... {len(work_items_summary) - i} more items truncated for size limits]"
                break
        
        summary_query += """
Provide a concise analysis focusing on:
1. Direct dependencies and relationships
2. High-priority related items
3. Key risks and blockers

Due to size limitations, this is a summary analysis. Focus on the most critical relationships.
"""
        
        self.logger.info(f"Created summary query with {len(summary_query)} characters")
        return summary_query if len(summary_query) < len(query) else None
    
    def _create_minimal_query(self, query: str, target_size: int) -> str:
        """
        Create a minimal query with only the most essential information.
        """
        target_query_length = target_size - 200
        
        if len(query) <= target_query_length:
            return query
        
        self.logger.info(f"Creating minimal query (target: {target_query_length} characters)")
        
        # Extract just the selected work item and a few related items
        lines = query.split('\n')
        selected_item_lines = []
        work_item_count = 0
        
        capturing_selected = False
        
        for line in lines:
            if "SELECTED WORK ITEM" in line:
                capturing_selected = True
                selected_item_lines.append(line)
                continue
            elif "ALL WORK ITEMS FOR ANALYSIS" in line:
                capturing_selected = False
                selected_item_lines.append("\nRELATED WORK ITEMS (Minimal set due to size constraints):")
                continue
            
            if capturing_selected:
                selected_item_lines.append(line)
            elif not capturing_selected and line.strip():
                # Only include basic info for related items
                if any(key in line for key in ["ID:", "Title:", "Type:", "Priority:"]) and work_item_count < 20:
                    selected_item_lines.append(line)
                    if "ID:" in line:
                        work_item_count += 1
        
        minimal_query = "\n".join(selected_item_lines)
        minimal_query += f"""

Analyze the selected work item against the {work_item_count} related items shown above.
Focus only on:
1. Direct blocking dependencies
2. Immediate prerequisites
3. Critical related items

This is a minimal analysis due to message size constraints.
"""
        
        self.logger.info(f"Created minimal query with {len(minimal_query)} characters, {work_item_count} related items")
        return minimal_query if len(minimal_query) < len(query) else None

    def query_workflow(self, workflow_id: str, query: str, is_persistence_allowed: bool = False) -> Tuple[str, Dict[str, Any]]:
        """
        Send query to OpenArena workflow via WebSocket
        
        Args:
            workflow_id: Workflow ID to use
            query: Query string to send
            is_persistence_allowed: Whether to allow persistence
            
        Returns:
            Tuple of (answer, cost_tracker)
        """
        msg = {
            "action": "SendMessage",
            "workflow_id": workflow_id,
            "query": query,
            "is_persistence_allowed": is_persistence_allowed
        }
        
        # Check message size and implement intelligent chunking strategy
        msg_json = json.dumps(msg)
        msg_size = len(msg_json.encode('utf-8'))
        max_frame_size = int(os.getenv('OPENARENA_MAX_MESSAGE_SIZE', '1000000'))
        safe_frame_size = int(os.getenv('OPENARENA_SAFE_MESSAGE_SIZE', '500000'))
        min_frame_size = int(os.getenv('OPENARENA_MIN_MESSAGE_SIZE', '100000'))
        
        self.logger.info(f"Connecting to OpenArena WebSocket: {self.base_url}")
        self.logger.info(f"Sending query to workflow: {workflow_id}")
        # Log query content in a clean format
        debug_full_query = os.getenv('OPENARENA_DEBUG_FULL_QUERY', 'false').lower() == 'true'
        if debug_full_query or len(query) <= 2000:
            self.logger.info("=" * 80)
            self.logger.info("OPENARENA REQUEST")
            self.logger.info("=" * 80)
            self.logger.info(f"Workflow ID: {workflow_id}")
            self.logger.info(f"Query Length: {len(query)} characters")
            self.logger.info("-" * 40)
            self.logger.info(query)
            self.logger.info("-" * 40)
        else:
            self.logger.info("=" * 80)
            self.logger.info("OPENARENA REQUEST (TRUNCATED)")
            self.logger.info("=" * 80)
            self.logger.info(f"Workflow ID: {workflow_id}")
            self.logger.info(f"Query Length: {len(query)} characters")
            self.logger.info("-" * 40)
            self.logger.info(f"{query[:1000]}...")
            self.logger.info(f"...[TRUNCATED - {len(query) - 1000} more characters]...")
            self.logger.info("-" * 40)
        self.logger.info(f"Message size: {msg_size} bytes (max: {max_frame_size}, safe: {safe_frame_size}, min: {min_frame_size} bytes)")
        
        if msg_size > max_frame_size:
            self.logger.warning(f"Message size ({msg_size} bytes) exceeds maximum limit ({max_frame_size} bytes)")
            
            # Try to chunk the message intelligently
            chunked_result = self._handle_large_message(query, workflow_id, is_persistence_allowed, 
                                                      msg_size, max_frame_size, safe_frame_size)
            if chunked_result:
                return chunked_result
            
            # If chunking fails, return error
            self.logger.error(f"Message too large and chunking failed: {msg_size} bytes exceeds all limits")
            return "", {"error": f"Message too large: {msg_size} bytes exceeds WebSocket frame limit. Intelligent chunking failed. Please reduce the dataset size or contact support."}
        
        elif msg_size > safe_frame_size:
            self.logger.warning(f"Message size ({msg_size} bytes) exceeds safe limit ({safe_frame_size} bytes) but within maximum. Proceeding with caution.")
        
        try:
            # Connect using URL with Authorization query parameter
            # Configure WebSocket with larger frame size limit
            ws = connect(self.ws_url, max_size=max_frame_size)
            ws.send(msg_json)
            
            answer = ""
            cost_tracker = {}
            eof = False
            timeout_seconds = self.config.timeout  # Use configurable timeout
            start_time = datetime.now()
            
            self.logger.info(f"Timeout configured: {timeout_seconds} seconds")
            
            while not eof:
                # Check for timeout
                elapsed_time = (datetime.now() - start_time).total_seconds()
                if elapsed_time > timeout_seconds:
                    self.logger.error(f"WebSocket query timeout after {timeout_seconds} seconds")
                    ws.close()
                    return "", {"error": f"Query timeout after {timeout_seconds} seconds"}
                
                try:
                    # Calculate remaining timeout - give more time for LLM processing
                    remaining_timeout = max(10, timeout_seconds - elapsed_time)
                    
                    # Try to receive with timeout
                    message = self._receive_with_timeout(ws, remaining_timeout)
                    self.logger.debug(f"Received: {message}")
                    
                    try:
                        message_data = json.loads(message)
                        for model, value in message_data.items():
                            if "answer" in value:
                                answer += value["answer"]
                            elif "cost_track" in value:
                                cost_tracker = value['cost_track']
                                eof = True
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse message as JSON: {e}")
                        continue
                        
                except Exception as recv_error:
                    self.logger.error(f"Error receiving message: {recv_error}")
                    # Check if it's a timeout error
                    if "timeout" in str(recv_error).lower():
                        self.logger.error(f"WebSocket receive timeout after {elapsed_time:.2f} seconds (configured timeout: {timeout_seconds}s)")
                    # If we can't receive messages, break out of the loop
                    break
            
            ws.close()
            
            # Log response content in a clean format
            debug_full_response = os.getenv('OPENARENA_DEBUG_FULL_RESPONSE', 'false').lower() == 'true'
            self.logger.info("=" * 80)
            self.logger.info("OPENARENA RESPONSE")
            self.logger.info("=" * 80)
            self.logger.info(f"Response Length: {len(answer)} characters")
            self.logger.info("-" * 40)
            
            if debug_full_response or len(answer) <= 2000:
                self.logger.info(answer)
            else:
                self.logger.info(f"{answer[:1000]}...")
                self.logger.info(f"...[TRUNCATED - {len(answer) - 1000} more characters]...")
            
            self.logger.info("-" * 40)
            
            # Log cost information
            if isinstance(cost_tracker, dict):
                if 'total_cost' in cost_tracker:
                    self.logger.info(f"Cost: ${cost_tracker.get('total_cost', 0):.6f}")
                    self.logger.info(f"Input Tokens: {cost_tracker.get('input_token_count', 'N/A')}")
                    self.logger.info(f"Output Tokens: {cost_tracker.get('output_token_count', 'N/A')}")
                elif 'cost' in cost_tracker:
                    self.logger.info(f"Cost: ${cost_tracker.get('cost', 0):.6f}")
                    self.logger.info(f"Tokens: {cost_tracker.get('tokens', 'N/A')}")
                    self.logger.info(f"Model: {cost_tracker.get('model', 'N/A')}")
                else:
                    self.logger.warning(f"Unknown cost format: {cost_tracker}")
            else:
                self.logger.warning(f"Invalid cost tracker: {cost_tracker}")
            
            self.logger.info("=" * 80)
            return answer, cost_tracker
            
        except Exception as e:
            self.logger.error(f"WebSocket connection failed: {e}")
            return "", {"error": str(e)}
    
    async def refine_backlog_items(self, transcript: str, parsed_content: Dict[str, Any], 
                                 model: str = "gpt4o") -> Dict[str, Any]:
        """
        Refine backlog items from meeting transcript using OpenArena
        
        Args:
            transcript: Full meeting transcript
            parsed_content: Previously parsed content
            model: Model to use (gpt4o, gpt4, claude)
            
        Returns:
            Refined backlog items with enhanced details
        """
        self.logger.info("Starting backlog refinement with OpenArena...")
        
        workflow_id = self.workflow_ids.get(model, self.workflow_ids['azure_openai'])
        
        # Create comprehensive refinement prompt
        refinement_prompt = self._create_refinement_prompt(transcript, parsed_content)
        
        # Send query to OpenArena
        answer, cost_tracker = self.query_workflow(workflow_id, refinement_prompt, False)
        
        # Check if websocket query failed and fallback to mock client
        if not answer or "error" in cost_tracker:
            self.logger.warning(f"WebSocket query failed: {cost_tracker.get('error', 'Unknown error')}")
            self.logger.info("Falling back to mock client for testing purposes")
            
            try:
                from .mock_client import MockOpenArenaClient
                mock_client = MockOpenArenaClient()
                answer, cost_tracker = mock_client.query_workflow(workflow_id, refinement_prompt, False)
                self.logger.info("Mock client fallback successful")
                
                # Update the processing method to indicate fallback was used
                processing_method = 'mock_client_fallback'
                
            except Exception as fallback_error:
                self.logger.error(f"Mock client fallback also failed: {fallback_error}")
                # Return minimal structure if everything fails
                return self._create_fallback_refinement()
        else:
            processing_method = 'openarena_websocket'
        
        # Parse the refined response
        refined_items = self._parse_refined_response(answer)
        
        # Enhance with metadata
        refined_items['refinement_metadata'] = {
            'processed_at': datetime.now().isoformat(),
            'model_used': model,
            'workflow_id': workflow_id,
            'cost_tracker': cost_tracker,
            'processing_method': processing_method
        }
        
        return refined_items
    
    def _create_refinement_prompt(self, transcript: str, parsed_content: Dict[str, Any]) -> str:
        """Create detailed prompt for backlog refinement"""
        
        # Truncate transcript if too long (keep first 5000 characters)
        if len(transcript) > 5000:
            transcript = transcript[:5000] + "... [truncated]"
        
        # Simplify parsed content to reduce message size
        simplified_content = {
            'epics': parsed_content.get('epics', [])[:3],  # Keep only first 3
            'features': parsed_content.get('features', [])[:3],
            'user_stories': parsed_content.get('user_stories', [])[:3],
            'action_items': parsed_content.get('action_items', [])[:3],
            'decisions': parsed_content.get('decisions', [])[:3]
        }
        
        prompt = f"""
You are an expert Agile Product Manager. Refine backlog items from this meeting transcript.

TRANSCRIPT (truncated):
{transcript}

CURRENT ITEMS:
{json.dumps(simplified_content, indent=2)}

Provide refined backlog items in this JSON format:

{{
    "refined_epics": [
        {{
            "id": "EPIC-001",
            "title": "Clear title",
            "description": "Description",
            "priority": "High/Medium/Low",
            "status": "Not Started/In Progress/Completed"
        }}
    ],
    "refined_features": [
        {{
            "id": "FEAT-001", 
            "title": "Feature title",
            "description": "Description",
            "epic_id": "EPIC-001",
            "priority": "High/Medium/Low"
        }}
    ],
    "refined_user_stories": [
        {{
            "id": "US-001",
            "title": "As a user, I want...",
            "description": "Description",
            "feature_id": "FEAT-001",
            "acceptance_criteria": ["Criteria 1", "Criteria 2"]
        }}
    ],
    "refined_action_items": [
        {{
            "id": "AI-001",
            "title": "Action item",
            "description": "Description", 
            "assignee": "Person",
            "due_date": "Date"
        }}
    ],
    "refined_decisions": [
        {{
            "id": "DEC-001",
            "title": "Decision title",
            "description": "Description",
            "decision": "What was decided",
            "rationale": "Why"
        }}
    ]
}}

Focus on making items more specific and actionable. If information is not explicitly mentioned, mark it as "To be clarified".
"""
        return prompt
    
    def _parse_refined_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate the refined response from OpenArena"""
        try:
            # Log the raw response for debugging
            self.logger.info(f"Raw response length: {len(response)}")
            self.logger.info(f"Raw response preview: {response[:500]}...")
            
            # Extract JSON from the response (handle markdown code blocks and text)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                self.logger.error("No JSON found in response")
                return self._create_fallback_refinement()
            
            json_str = response[json_start:json_end]
            self.logger.info(f"Extracted JSON preview: {json_str[:200]}...")
            
            # Try to parse JSON response
            refined_items = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['refined_epics', 'refined_features', 'refined_user_stories', 
                             'refined_action_items', 'refined_decisions']
            for field in required_fields:
                if field not in refined_items:
                    refined_items[field] = []
            
            # Add refinement insights if missing
            if 'refinement_insights' not in refined_items:
                refined_items['refinement_insights'] = {
                    'scope_clarity': 'To be assessed',
                    'priority_alignment': 'To be assessed',
                    'resource_needs': [],
                    'timeline_realism': 'To be assessed',
                    'stakeholder_alignment': 'To be assessed',
                    'technical_debt': [],
                    'quality_gates': []
                }
            
            # Add next steps if missing
            if 'next_steps' not in refined_items:
                refined_items['next_steps'] = []
            
            return refined_items
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse refined response as JSON: {e}")
            # Try to extract JSON from response if it's embedded in text
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            
            # Return minimal structure if parsing fails
            return self._create_fallback_refinement()
    
    def _create_fallback_refinement(self) -> Dict[str, Any]:
        """Create fallback refinement when parsing fails"""
        return {
            "refined_epics": [],
            "refined_features": [],
            "refined_user_stories": [],
            "refined_action_items": [],
            "refined_decisions": [],
            "refinement_insights": {
                "scope_clarity": "Unable to assess",
                "priority_alignment": "Unable to assess",
                "resource_needs": [],
                "timeline_realism": "Unable to assess",
                "stakeholder_alignment": "Unable to assess",
                "technical_debt": [],
                "quality_gates": []
            },
            "next_steps": [
                "Schedule follow-up meeting to clarify requirements",
                "Document all decisions in shared repository",
                "Assign ownership for action items"
            ],
            "refinement_metadata": {
                "processed_at": datetime.now().isoformat(),
                "model_used": "fallback",
                "processing_method": "fallback",
                "error": "Response parsing failed"
            }
        }
    
    async def generate_backlog_summary(self, refined_items: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the refined backlog"""
        
        summary = {
            "summary_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_epics": len(refined_items.get('refined_epics', [])),
                "total_features": len(refined_items.get('refined_features', [])),
                "total_user_stories": len(refined_items.get('refined_user_stories', [])),
                "total_action_items": len(refined_items.get('refined_action_items', [])),
                "total_decisions": len(refined_items.get('refined_decisions', []))
            },
            "priority_distribution": {
                "high_priority": {
                    "epics": len([e for e in refined_items.get('refined_epics', []) if e.get('priority', '').lower() == 'high']),
                    "features": len([f for f in refined_items.get('refined_features', []) if f.get('priority', '').lower() == 'high']),
                    "user_stories": len([us for us in refined_items.get('refined_user_stories', []) if us.get('priority', '').lower() == 'high'])
                },
                "medium_priority": {
                    "epics": len([e for e in refined_items.get('refined_epics', []) if e.get('priority', '').lower() == 'medium']),
                    "features": len([f for f in refined_items.get('refined_features', []) if f.get('priority', '').lower() == 'medium']),
                    "user_stories": len([us for us in refined_items.get('refined_user_stories', []) if us.get('priority', '').lower() == 'medium'])
                },
                "low_priority": {
                    "epics": len([e for e in refined_items.get('refined_epics', []) if e.get('priority', '').lower() == 'low']),
                    "features": len([f for f in refined_items.get('refined_features', []) if f.get('priority', '').lower() == 'low']),
                    "user_stories": len([us for us in refined_items.get('refined_user_stories', []) if us.get('priority', '').lower() == 'low'])
                }
            },
            "complexity_distribution": {
                "high_complexity": len([f for f in refined_items.get('refined_features', []) if f.get('complexity', '').lower() == 'high']),
                "medium_complexity": len([f for f in refined_items.get('refined_features', []) if f.get('complexity', '').lower() == 'medium']),
                "low_complexity": len([f for f in refined_items.get('refined_features', []) if f.get('complexity', '').lower() == 'low'])
            },
            "insights": refined_items.get('refinement_insights', {}),
            "next_steps": refined_items.get('next_steps', [])
        }
        
        return summary
    
    def test_timeout(self, timeout_seconds: int = 5) -> bool:
        """Test timeout mechanism with a very short timeout"""
        try:
            test_query = "Test query for timeout mechanism"
            workflow_id = self.workflow_ids['azure_openai']
            
            # Temporarily override config timeout for testing
            original_timeout = self.config.timeout
            self.config.timeout = timeout_seconds
            
            start_time = datetime.now()
            answer, cost_tracker = self.query_workflow(workflow_id, test_query, False)
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            # Restore original timeout
            self.config.timeout = original_timeout
            
            if "error" in cost_tracker and "timeout" in cost_tracker["error"].lower():
                self.logger.info(f"Timeout test successful - query timed out after {elapsed_time:.2f} seconds")
                return True
            elif elapsed_time <= timeout_seconds + 2:  # Allow 2 second buffer
                self.logger.info(f"Timeout test completed within expected time: {elapsed_time:.2f} seconds")
                return True
            else:
                self.logger.warning(f"Timeout test may have issues - took {elapsed_time:.2f} seconds (expected ~{timeout_seconds})")
                return False
                
        except Exception as e:
            self.logger.error(f"Timeout test failed: {e}")
            return False

    def test_connection(self) -> bool:
        """Test connection to OpenArena WebSocket"""
        try:
            test_query = "Hello, this is a test message to verify connection."
            workflow_id = self.workflow_ids['azure_openai']
            
            answer, cost_tracker = self.query_workflow(workflow_id, test_query, False)
            
            if answer and "error" not in cost_tracker:
                self.logger.info("OpenArena WebSocket connection successful")
                return True
            else:
                self.logger.error(f"OpenArena WebSocket test failed: {cost_tracker}")
                return False
                
        except Exception as e:
            self.logger.error(f"OpenArena WebSocket connection failed: {e}")
            return False

# Integration function for existing codebase
async def integrate_with_existing_processor(transcript: str, parsed_content: Dict[str, Any], 
                                          esso_token: str = None) -> Dict[str, Any]:
    """
    Integrate WebSocket client with existing Teams recording processor
    
    Args:
        transcript: Meeting transcript
        parsed_content: Previously parsed content
        esso_token: ESSO token for OpenArena (optional, will use config if not provided)
        
    Returns:
        Refined backlog items
    """
    client = OpenArenaWebSocketClient(esso_token)
    
    # Test connection first
    if not client.test_connection():
        raise Exception("Failed to connect to OpenArena WebSocket")
    
    # Refine backlog items
    refined_items = await client.refine_backlog_items(transcript, parsed_content)
    
    # Generate summary
    summary = await client.generate_backlog_summary(refined_items)
    
    return {
        "refined_items": refined_items,
        "summary": summary,
        "integration_metadata": {
            "integrated_at": datetime.now().isoformat(),
            "client_type": "websocket",
            "status": "success"
        }
    }

# Test function
def test_openarena_websocket_client():
    """Test the OpenArena WebSocket client"""
    # Replace with your actual ESSO token
    ESSO_TOKEN = "<YOUR_ESSO_TOKEN_HERE>"
    
    if ESSO_TOKEN == "<YOUR_ESSO_TOKEN_HERE>":
        print("Please set your ESSO token in the test function")
        return
    
    client = OpenArenaWebSocketClient(ESSO_TOKEN)
    
    # Test connection
    if client.test_connection():
        print("WebSocket connection test successful")
        
        # Test with sample data
        sample_transcript = """
        Today we discussed the user registration epic. We need to implement email verification, 
        password reset functionality, and social media login. The user story for email verification 
        should be high priority. We decided to use OAuth for social media integration.
        """
        
        sample_parsed_content = {
            "epics": [{"title": "User Registration", "description": "User registration system"}],
            "features": [{"title": "Email Verification", "description": "Email verification feature"}],
            "user_stories": []
        }
        
        # Run refinement
        refined_items = asyncio.run(client.refine_backlog_items(sample_transcript, sample_parsed_content))
        print(f"Refinement completed: {len(refined_items.get('refined_epics', []))} epics refined")
    else:
        print("WebSocket connection test failed")

if __name__ == "__main__":
    test_openarena_websocket_client() 