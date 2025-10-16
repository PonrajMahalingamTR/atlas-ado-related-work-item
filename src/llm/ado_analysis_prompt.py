#!/usr/bin/env python3
"""
Azure DevOps Work Item Analysis - LLM System Prompt

This module contains the comprehensive system prompt for OpenArena LLM to analyze
Azure DevOps work items and identify relationships between them.
"""
import logging

logger = logging.getLogger(__name__)

class ADOWorkItemAnalysisPrompt:
    """System prompt generator for ADO work item analysis using OpenArena LLM."""
    
    @staticmethod
    def work_item_to_dict(work_item):
        """
        Convert a WorkItem object to dictionary format.
        
        Args:
            work_item: Azure DevOps WorkItem object
            
        Returns:
            dict: Dictionary representation of the work item
        """
        if isinstance(work_item, dict):
            return work_item  # Already a dictionary
        
        # Extract AssignedTo properly
        assigned_to = work_item.fields.get('System.AssignedTo', 'Unassigned')
        if isinstance(assigned_to, dict) and 'displayName' in assigned_to:
            assigned_to = assigned_to['displayName']
        elif not assigned_to or assigned_to == 'Unassigned':
            assigned_to = 'Unassigned'
        
        # Extract CreatedBy properly
        created_by = work_item.fields.get('System.CreatedBy', 'Unknown')
        if isinstance(created_by, dict) and 'displayName' in created_by:
            created_by = created_by['displayName']
        elif not created_by:
            created_by = 'Unknown'
        
        return {
            'id': work_item.id,
            'title': work_item.fields.get('System.Title', 'No Title'),
            'work_item_type': work_item.fields.get('System.WorkItemType', 'Unknown'),
            'state': work_item.fields.get('System.State', 'Unknown'),
            'priority': work_item.fields.get('Microsoft.VSTS.Common.Priority', 'Not specified'),
            'severity': work_item.fields.get('Microsoft.VSTS.Common.Severity', 'Not specified'),
            'assigned_to': assigned_to,
            'created_by': created_by,
            'created_date': str(work_item.fields.get('System.CreatedDate', 'Unknown')),
            'tags': work_item.fields.get('System.Tags', ''),
            'area_path': work_item.fields.get('System.AreaPath', ''),
            'iteration_path': work_item.fields.get('System.IterationPath', ''),
            'effort': work_item.fields.get('Microsoft.VSTS.Scheduling.Effort', ''),
            'story_points': work_item.fields.get('Microsoft.VSTS.Scheduling.StoryPoints', ''),
            'description': work_item.fields.get('System.Description', 'No description available')
        }
    
    @staticmethod
    def create_system_prompt(selected_work_item_data, all_work_items_data):
        """
        Create a comprehensive system prompt for LLM analysis of ADO work items.
        
        Args:
            selected_work_item_data (dict or WorkItem): Data of the selected work item to analyze
            all_work_items_data (list): List of all available work items data (dicts or WorkItem objects)
            
        Returns:
            str: Complete system prompt for the LLM
        """
        
        # Convert WorkItem objects to dictionaries if needed
        if not isinstance(selected_work_item_data, dict):
            selected_work_item_data = ADOWorkItemAnalysisPrompt.work_item_to_dict(selected_work_item_data)
        
        # Convert all work items to dictionaries if needed
        processed_all_work_items = []
        for item in all_work_items_data:
            if not isinstance(item, dict):
                processed_all_work_items.append(ADOWorkItemAnalysisPrompt.work_item_to_dict(item))
            else:
                processed_all_work_items.append(item)
        
        # Debug: Log the number of work items being processed
        print(f"DEBUG: Processing {len(processed_all_work_items)} work items for LLM analysis")
        if len(processed_all_work_items) > 0:
            print(f"DEBUG: First work item ID: {processed_all_work_items[0].get('id', 'N/A')}")
            print(f"DEBUG: Last work item ID: {processed_all_work_items[-1].get('id', 'N/A')}")
        
        prompt = f"""You are an expert Azure DevOps work item analyst with deep knowledge of software development methodologies, project management, and technical architecture. Your task is to analyze a selected work item and a collection of all available work items to identify meaningful relationships and dependencies.

## CONTEXT
You are analyzing work items from an Azure DevOps project to help development teams understand dependencies, plan work effectively, and identify potential risks or opportunities for optimization.

SELECTED WORK ITEM TO ANALYZE
{ADOWorkItemAnalysisPrompt._format_selected_work_item(selected_work_item_data)}

ALL AVAILABLE WORK ITEMS ({len(processed_all_work_items)} items)
{ADOWorkItemAnalysisPrompt._format_all_work_items(processed_all_work_items)}

ANALYSIS OBJECTIVES
1. Primary Goal: Identify work items that are genuinely related to the selected work item
2. Secondary Goal: Understand the nature and strength of these relationships
3. Tertiary Goal: Provide insights that could help with project planning and risk management

RELATIONSHIP TYPES TO CONSIDER

1. FUNCTIONAL DEPENDENCIES
- Prerequisites: Work items that must be completed before the selected item
- Dependents: Work items that depend on the selected item
- Blocking: Work items that block progress on the selected item

2. BUSINESS LOGIC RELATIONSHIPS
- Process Flow: Items that are part of the same business process
- Feature Groups: Items that implement related features
- User Journey: Items that affect the same user experience

3. TECHNICAL DEPENDENCIES
- Shared Components: Items that use the same libraries, APIs, or services
- Data Dependencies: Items that share data models, databases, or data flows
- Infrastructure: Items that depend on the same infrastructure or deployment

4. HIERARCHICAL RELATIONSHIPS
- Epic-Story: Parent-child relationships in agile planning
- Story-Task: Breakdown relationships
- Feature-Component: High-level to detailed implementation

5. QUALITY & MAINTENANCE
- Bug-Fix: Bugs and their corresponding fixes
- Technical Debt: Items related to code quality improvements
- Testing: Items related to testing the selected work

6. CROSS-FUNCTIONAL RELATIONSHIPS
- UI/UX: Items affecting the same user interface
- Backend/Frontend: Items in different architectural layers
- Integration: Items that need to work together

ANALYSIS CRITERIA

RELATIONSHIP STRENGTH ASSESSMENT
- HIGH CONFIDENCE: Clear, direct relationship with strong evidence
- MEDIUM CONFIDENCE: Probable relationship with some supporting evidence
- LOW CONFIDENCE: Possible relationship with limited evidence

EVIDENCE WEIGHTING
- Title Similarity: Keywords, terminology, and naming conventions
- Description Content: Shared concepts, requirements, or technical details
- Tags & Categories: Common tags, area paths, or iteration paths
- Assigned Teams: Same team or related team assignments
- Timing: Items created or planned in similar timeframes
- Priority/Effort: Similar business importance or complexity

OUTPUT REQUIREMENTS

STRUCTURED ANALYSIS FORMAT

RELATED WORK ITEMS ANALYSIS

HIGH CONFIDENCE RELATIONSHIPS
For each high-confidence relationship, provide:
- ID: [Work Item ID]
- Title: [Full Title]
- Type: [Work Item Type]
- State: [Current State]
- Priority: [Priority Level]
- Relationship Type: [Specific relationship category]
- Why This Work Item Is Relevant: [2-4 bullet points explaining the relevance in user-friendly language]
  • [First reason - be specific about the connection]
  • [Second reason - explain the impact or dependency]
  • [Third reason - mention shared context or requirements]
  • [Fourth reason - if applicable, explain timing or priority alignment]

IMPORTANT FORMATTING: Each bullet point must be on a separate line. Use proper line breaks between each bullet point.

MEDIUM CONFIDENCE RELATIONSHIPS
[Same format as above with 2-4 bullet points explaining relevance]

LOW CONFIDENCE RELATIONSHIPS
[Same format as above with 2-4 bullet points explaining relevance]

RELATIONSHIP PATTERNS ANALYSIS
- Primary Patterns: [Most common types of relationships found]
- Dependency Clusters: [Groups of items that form dependency chains]
- Cross-Team Dependencies: [Relationships spanning multiple teams]
- Technical Debt Indicators: [Items suggesting technical debt or refactoring needs]

DETAILED ANALYSIS SECTIONS

CRITICAL REQUIREMENT: You MUST provide AT LEAST 2 points for EACH section below. If you cannot identify 2 distinct points for any section, you must think more deeply about potential risks, dependencies, recommendations, and opportunities. Each section is MANDATORY and requires multiple insights.

IMPORTANT FORMATTING REQUIREMENTS:
- Do NOT use markdown formatting (no ##, ###, **, or other markdown symbols)
- Use plain text with clear headings and structure
- Use simple bullet points with dashes (-) for lists
- Use clear section headers without markdown symbols
- Format each point as: "Risk 1", "Risk 2", "Dependency 1", "Dependency 2", etc.

RISK ASSESSMENT (MANDATORY: Minimum 2, Maximum 5 points)
Analyze the selected work item and related work items to identify potential risks. You MUST find at least 2 different types of risks:

1. Technical Risks: Code quality, architecture, integration, performance, security
2. Resource Risks: Team capacity, skill gaps, availability, workload distribution
3. Timeline Risks: Deadlines, dependencies, delays, sprint planning
4. External Risks: Third-party dependencies, external team coordination, business changes
5. Process Risks: Workflow bottlenecks, communication gaps, quality assurance

For each risk identified, provide:
- Risk Category: [Technical/Resource/Timeline/External/Process]
- Risk Level: [HIGH/MEDIUM/LOW]
- Risk Description: [Specific, actionable description of the risk]
- Impact: [Concrete impact on project success]
- Mitigation: [Specific steps to address this risk]

DEPENDENCIES (MANDATORY: Minimum 2, Maximum 5 points)
Analyze dependencies that could affect the selected work item. You MUST identify at least 2 different types of dependencies:

1. Technical Dependencies: Code, APIs, infrastructure, tools, libraries
2. Resource Dependencies: Team members, skills, external teams, vendors
3. Timeline Dependencies: Sprint schedules, milestone dependencies, release cycles
4. Process Dependencies: Workflow steps, approvals, testing, deployment
5. Business Dependencies: Requirements, stakeholders, external factors

For each dependency identified, provide:
- Dependency Type: [Technical/Resource/Timeline/Process/Business]
- Dependency Level: [CRITICAL/HIGH/MEDIUM/LOW]
- Dependency Description: [Specific description of the dependency]
- Impact: [How this affects the selected work item]
- Action Required: [Specific actions needed to manage this dependency]

RECOMMENDATIONS (MANDATORY: Minimum 2, Maximum 5 points)
Provide actionable recommendations based on your analysis. You MUST suggest at least 2 different types of recommendations:

1. Immediate Actions: What should be done right now
2. Planning Actions: How to improve project planning and coordination
3. Process Improvements: Workflow, communication, quality processes
4. Technical Actions: Code quality, architecture, testing improvements
5. Risk Mitigation: Specific steps to reduce identified risks

For each recommendation, provide:
- Recommendation Type: [Immediate Action/Planning/Process/Technical/Risk Mitigation]
- Priority Level: [HIGH/MEDIUM/LOW]
- Recommendation Description: [Specific, actionable recommendation]
- Rationale: [Why this recommendation is critical]
- Implementation: [Step-by-step implementation approach]

OPPORTUNITIES (MANDATORY: Minimum 2, Maximum 5 points)
Identify opportunities for improvement and optimization. You MUST find at least 2 different types of opportunities:

1. Efficiency Opportunities: Process improvements, automation, optimization
2. Collaboration Opportunities: Team coordination, knowledge sharing, cross-functional work
3. Learning Opportunities: Skill development, knowledge transfer, best practices
4. Innovation Opportunities: New approaches, technologies, methodologies
5. Business Opportunities: Value creation, customer impact, competitive advantage

For each opportunity identified, provide:
- Opportunity Type: [Efficiency/Collaboration/Learning/Innovation/Business]
- Opportunity Level: [HIGH/MEDIUM/LOW]
- Opportunity Description: [Specific description of the opportunity]
- Benefits: [Concrete benefits this opportunity provides]
- Action Required: [Specific steps to capitalize on this opportunity]

ANALYSIS GUIDELINES

1. Be Thorough: Review all work items carefully, don't miss potential relationships
2. Be Specific: Provide concrete evidence and reasoning for each relationship
3. Be Practical: Focus on relationships that matter for project execution
4. Be Objective: Base analysis on evidence, not assumptions
5. Consider Context: Understand the broader project and business context
6. Prioritize Impact: Focus on relationships that have the most significant impact

MANDATORY MULTIPLE POINTS REQUIREMENT:
- You MUST generate AT LEAST 2 distinct points for Risk Assessment
- You MUST generate AT LEAST 2 distinct points for Dependencies  
- You MUST generate AT LEAST 2 distinct points for Recommendations
- You MUST generate AT LEAST 2 distinct points for Opportunities
- If you only provide 1 point for any section, your analysis is INCOMPLETE
- Think creatively and deeply about different angles and perspectives
- Consider both obvious and subtle risks, dependencies, recommendations, and opportunities
- Look at technical, business, process, and human factors
- Consider short-term and long-term implications

QUALITY STANDARDS
- Accuracy: Ensure all relationships are genuinely meaningful
- Completeness: Cover all significant relationship types
- Clarity: Make explanations clear and actionable
- Consistency: Use consistent terminology and format
- Actionability: Provide insights that teams can act upon

Please conduct a comprehensive analysis following these guidelines and provide detailed, actionable insights that will help the development team make informed decisions about their work items."""

        # Add user-friendly reasoning instruction
        prompt += """

IMPORTANT: For the "Why This Work Item Is Relevant" section, write 2-4 clear, user-friendly bullet points that explain:
1. The specific connection between the work items
2. How one work item affects or depends on the other
3. Shared context, requirements, or technical elements
4. Business impact or timing considerations

Make the reasoning clear and actionable for project managers and developers.

FINAL REMINDER: You MUST provide AT LEAST 2 points for EACH of the four analysis sections (Risk Assessment, Dependencies, Recommendations, Opportunities). This is a MANDATORY requirement. If you cannot identify 2 distinct points for any section, you must think more deeply and creatively about potential issues and opportunities. Your analysis is incomplete if any section has fewer than 2 points."""

        # Debug: Log prompt length
        print(f"DEBUG: Generated prompt length: {len(prompt)} characters")
        print(f"DEBUG: Prompt preview (first 200 chars): {prompt[:200]}")

        return prompt
    
    @staticmethod
    def _format_selected_work_item(work_item_data):
        """Format the selected work item data for the prompt."""
        # Fix Created By mapping - extract displayName from the field
        created_by = work_item_data['created_by']
        if isinstance(created_by, dict) and 'displayName' in created_by:
            created_by = created_by['displayName']
        elif isinstance(created_by, str) and created_by != 'Unknown':
            # If it's already a string, use it as is
            pass
        else:
            created_by = 'Unknown'
        
        return f"""ID: {work_item_data['id']}
Title: {work_item_data['title']}
Type: {work_item_data['work_item_type']}
State: {work_item_data['state']}
Priority: {work_item_data['priority']}
Severity: {work_item_data['severity']}
Assigned To: {work_item_data['assigned_to']}
Created By: {created_by}
Created Date: {work_item_data['created_date']}
Tags: {work_item_data['tags']}
Area Path: {work_item_data['area_path']}
Iteration Path: {work_item_data['iteration_path']}
Effort: {work_item_data['effort']}
Story Points: {work_item_data['story_points']}

Description:
{work_item_data['description'][:800]}{'...' if len(work_item_data['description']) > 800 else ''}"""
    
    @staticmethod
    def _format_all_work_items(all_items_data):
        """Format all work items data for the prompt."""
        formatted_items = []
        
        for i, item in enumerate(all_items_data, 1):
            # Fix Assigned To - ensure it's not always "Unassigned"
            assigned_to = item['assigned_to']
            if assigned_to == 'Unassigned' or not assigned_to:
                assigned_to = 'Not Assigned'
            
            # Fix tags - ensure proper comma-separated values
            tags = item['tags']
            if not tags or tags.strip() == '':
                tags = 'No tags'
            else:
                # Ensure tags are properly formatted as comma-separated
                if isinstance(tags, str):
                    # Split by semicolon and join with comma if needed
                    if ';' in tags:
                        tags = ', '.join([tag.strip() for tag in tags.split(';') if tag.strip()])
                    else:
                        tags = tags.strip()
            
            # Ensure description is included and properly formatted
            description = item.get('description', 'No description available')
            if not description or description.strip() == '':
                description = 'No description available'
            
            formatted_item = f"""Item {i}:
- ID: {item['id']}
- Title: {item['title']}
- Type: {item['work_item_type']}
- State: {item['state']}
- Priority: {item['priority']}
- Assigned To: {assigned_to}
- Tags: {tags}
- Area Path: {item['area_path']}
- Description: {description[:800]}{'...' if len(description) > 800 else ''}
---"""
            formatted_items.append(formatted_item)
        
        return "\n".join(formatted_items)
    
    @staticmethod
    def _format_optimized_work_items(all_items_data):
        """Format work items data for optimized prompt (concise format)."""
        formatted_items = []
        
        for i, item in enumerate(all_items_data, 1):
            # Get semantic similarity score if available
            similarity_score = item.get('semanticSimilarityScore', 0)
            similarity_text = f" (Similarity: {similarity_score:.2f})" if similarity_score > 0 else ""
            
            # Simplified format for better performance
            formatted_item = f"""Item {i}{similarity_text}:
- ID: {item['id']}
- Title: {item['title'][:100]}{'...' if len(item['title']) > 100 else ''}
- Type: {item['work_item_type']}
- State: {item['state']}
- Priority: {item['priority']}
- Assigned To: {item['assigned_to']}
- Area Path: {item['area_path']}
- Tags: {item['tags'][:50]}{'...' if len(item['tags']) > 50 else ''}
---"""
            formatted_items.append(formatted_item)
        
        return "\n".join(formatted_items)
    
    @staticmethod
    def create_optimized_prompt(selected_work_item_data, all_work_items_data, max_items=10):
        """
        Create an optimized system prompt for AI Deep Dive analysis with many work items.
        This version limits the number of work items and uses a more concise format.
        
        Args:
            selected_work_item_data (dict or WorkItem): Data of the selected work item to analyze
            all_work_items_data (list): List of all available work items data (dicts or WorkItem objects)
            max_items (int): Maximum number of work items to include in the prompt
            
        Returns:
            str: Optimized system prompt for the LLM
        """
        
        # Convert WorkItem objects to dictionaries if needed
        if not isinstance(selected_work_item_data, dict):
            selected_work_item_data = ADOWorkItemAnalysisPrompt.work_item_to_dict(selected_work_item_data)
        
        # Convert all work items to dictionaries and limit the number
        processed_all_work_items = []
        limited_items = all_work_items_data[:max_items]  # Limit to max_items first
        logger.info(f"Optimized prompt: limiting from {len(all_work_items_data)} to {len(limited_items)} work items")
        
        for item in limited_items:
            if not isinstance(item, dict):
                processed_all_work_items.append(ADOWorkItemAnalysisPrompt.work_item_to_dict(item))
            else:
                processed_all_work_items.append(item)
        
        # Sort by semantic similarity score if available (for AI Deep Dive)
        if processed_all_work_items and 'semanticSimilarityScore' in processed_all_work_items[0]:
            processed_all_work_items.sort(key=lambda x: x.get('semanticSimilarityScore', 0), reverse=True)
        
        prompt = f"""You are an expert Azure DevOps work item analyst specializing in AI-powered relationship analysis. Your task is to analyze a selected work item and identify the most relevant relationships from a curated set of semantically similar work items.

## CONTEXT
You are analyzing work items from an Azure DevOps project using AI Deep Dive analysis, which has already identified the most semantically similar work items. Focus on the most meaningful relationships and dependencies.

SELECTED WORK ITEM TO ANALYZE
{ADOWorkItemAnalysisPrompt._format_selected_work_item(selected_work_item_data)}

SEMANTICALLY SIMILAR WORK ITEMS ({len(processed_all_work_items)} items - Top Results)
{ADOWorkItemAnalysisPrompt._format_optimized_work_items(processed_all_work_items)}

ANALYSIS OBJECTIVES
1. Primary Goal: Identify the most relevant work items from the semantically similar set
2. Secondary Goal: Understand the nature and strength of these relationships
3. Tertiary Goal: Provide actionable insights for project planning

RELATIONSHIP TYPES TO CONSIDER
1. FUNCTIONAL DEPENDENCIES - Prerequisites, dependents, blocking relationships
2. BUSINESS LOGIC RELATIONSHIPS - Process flow, feature groups, user journey
3. TECHNICAL DEPENDENCIES - Shared components, data dependencies, infrastructure
4. QUALITY & MAINTENANCE - Bug-fix relationships, technical debt, testing
5. CROSS-FUNCTIONAL RELATIONSHIPS - UI/UX, backend/frontend, integration

ANALYSIS CRITERIA
- HIGH CONFIDENCE: Clear, direct relationship with strong evidence
- MEDIUM CONFIDENCE: Probable relationship with some supporting evidence  
- LOW CONFIDENCE: Possible relationship with limited evidence

OUTPUT REQUIREMENTS
Provide a structured analysis with:

RELATED WORK ITEMS ANALYSIS
- HIGH CONFIDENCE RELATIONSHIPS (with ID, Title, Type, State, Priority, Relationship Type, Description, Evidence, Impact)
- MEDIUM CONFIDENCE RELATIONSHIPS (same format)
- LOW CONFIDENCE RELATIONSHIPS (same format)

RELATIONSHIP PATTERNS ANALYSIS
- Primary Patterns: Most common relationship types
- Dependency Clusters: Groups forming dependency chains
- Cross-Team Dependencies: Relationships spanning teams
- Technical Debt Indicators: Items suggesting refactoring needs

RISK ASSESSMENT
- High-Risk Dependencies: Items significantly impacting the selected work
- Blocking Issues: Items preventing progress
- Resource Conflicts: Potential resource allocation issues

RECOMMENDATIONS
- Immediate Actions: What should be done next
- Planning Considerations: How this affects project planning
- Risk Mitigation: Suggestions for reducing risks
- Optimization Opportunities: Ways to improve efficiency

Focus on the most impactful relationships and provide concise, actionable insights."""

        return prompt

    @staticmethod
    def create_simplified_prompt(selected_work_item_data, all_work_items_data):
        """
        Create a simplified version of the system prompt for faster processing with user-friendly reasoning.
        
        Args:
            selected_work_item_data (dict or WorkItem): Data of the selected work item
            all_work_items_data (list): List of all available work items data (dicts or WorkItem objects)
            
        Returns:
            str: Simplified system prompt with user-friendly reasoning format
        """
        
        # Convert WorkItem objects to dictionaries if needed
        if not isinstance(selected_work_item_data, dict):
            selected_work_item_data = ADOWorkItemAnalysisPrompt.work_item_to_dict(selected_work_item_data)
        
        # Convert all work items to dictionaries if needed
        processed_all_work_items = []
        for item in all_work_items_data:
            if not isinstance(item, dict):
                processed_all_work_items.append(ADOWorkItemAnalysisPrompt.work_item_to_dict(item))
            else:
                processed_all_work_items.append(item)
        
        prompt = f"""You are an Azure DevOps work item analyst. Analyze the selected work item and find related items from the available list.

SELECTED WORK ITEM:
ID: {selected_work_item_data['id']}
Title: {selected_work_item_data['title']}
Type: {selected_work_item_data['work_item_type']}
State: {selected_work_item_data['state']}
Description: {selected_work_item_data['description'][:800]}{'...' if len(selected_work_item_data['description']) > 800 else ''}

AVAILABLE WORK ITEMS ({len(processed_all_work_items)} items):
{ADOWorkItemAnalysisPrompt._format_simplified_work_items(processed_all_work_items)}

TASK: Find work items related to the selected item. Consider:
- Functional dependencies
- Technical relationships  
- Business logic connections
- Shared components or data
- User experience relationships

OUTPUT FORMAT:
RELATED WORK ITEMS

HIGH CONFIDENCE RELATIONSHIPS
For each high-confidence relationship, provide:
- ID: [Work Item ID]
- Title: [Full Title]
- Type: [Work Item Type]
- State: [Current State]
- Priority: [Priority Level]
- Relationship Type: [Specific relationship category]
- Why This Work Item Is Relevant: [2-4 bullet points explaining the relevance in user-friendly language]
  • [First reason - be specific about the connection]
  • [Second reason - explain the impact or dependency]
  • [Third reason - mention shared context or requirements]
  • [Fourth reason - if applicable, explain timing or priority alignment]

IMPORTANT FORMATTING: Each bullet point must be on a separate line. Use proper line breaks between each bullet point.

MEDIUM CONFIDENCE RELATIONSHIPS
[Same format as above with 2-4 bullet points explaining relevance]

LOW CONFIDENCE RELATIONSHIPS
[Same format as above with 2-4 bullet points explaining relevance]

RELATIONSHIP PATTERNS ANALYSIS
- Primary Patterns: [Most common types of relationships found]
- Dependency Clusters: [Groups of items that form dependency chains]
- Cross-Team Dependencies: [Relationships spanning multiple teams]
- Technical Debt Indicators: [Items suggesting technical debt or refactoring needs]

DETAILED ANALYSIS SECTIONS

CRITICAL REQUIREMENT: You MUST provide AT LEAST 2 points for EACH section below. If you cannot identify 2 distinct points for any section, you must think more deeply about potential risks, dependencies, recommendations, and opportunities. Each section is MANDATORY and requires multiple insights.

IMPORTANT FORMATTING REQUIREMENTS:
- Do NOT use markdown formatting (no ##, ###, **, or other markdown symbols)
- Use plain text with clear headings and structure
- Use simple bullet points with dashes (-) for lists
- Use clear section headers without markdown symbols
- Format each point as: "Risk 1", "Risk 2", "Dependency 1", "Dependency 2", etc.

RISK ASSESSMENT (MANDATORY: Minimum 2, Maximum 5 points)
Analyze the selected work item and related work items to identify potential risks. You MUST find at least 2 different types of risks:

1. Technical Risks: Code quality, architecture, integration, performance, security
2. Resource Risks: Team capacity, skill gaps, availability, workload distribution
3. Timeline Risks: Deadlines, dependencies, delays, sprint planning
4. External Risks: Third-party dependencies, external team coordination, business changes
5. Process Risks: Workflow bottlenecks, communication gaps, quality assurance

For each risk identified, provide:
- Risk Category: [Technical/Resource/Timeline/External/Process]
- Risk Level: [HIGH/MEDIUM/LOW]
- Risk Description: [Specific, actionable description of the risk]
- Impact: [Concrete impact on project success]
- Mitigation: [Specific steps to address this risk]

DEPENDENCIES (MANDATORY: Minimum 2, Maximum 5 points)
Analyze dependencies that could affect the selected work item. You MUST identify at least 2 different types of dependencies:

1. Technical Dependencies: Code, APIs, infrastructure, tools, libraries
2. Resource Dependencies: Team members, skills, external teams, vendors
3. Timeline Dependencies: Sprint schedules, milestone dependencies, release cycles
4. Process Dependencies: Workflow steps, approvals, testing, deployment
5. Business Dependencies: Requirements, stakeholders, external factors

For each dependency identified, provide:
- Dependency Type: [Technical/Resource/Timeline/Process/Business]
- Dependency Level: [CRITICAL/HIGH/MEDIUM/LOW]
- Dependency Description: [Specific description of the dependency]
- Impact: [How this affects the selected work item]
- Action Required: [Specific actions needed to manage this dependency]

RECOMMENDATIONS (MANDATORY: Minimum 2, Maximum 5 points)
Provide actionable recommendations based on your analysis. You MUST suggest at least 2 different types of recommendations:

1. Immediate Actions: What should be done right now
2. Planning Actions: How to improve project planning and coordination
3. Process Improvements: Workflow, communication, quality processes
4. Technical Actions: Code quality, architecture, testing improvements
5. Risk Mitigation: Specific steps to reduce identified risks

For each recommendation, provide:
- Recommendation Type: [Immediate Action/Planning/Process/Technical/Risk Mitigation]
- Priority Level: [HIGH/MEDIUM/LOW]
- Recommendation Description: [Specific, actionable recommendation]
- Rationale: [Why this recommendation is critical]
- Implementation: [Step-by-step implementation approach]

OPPORTUNITIES (MANDATORY: Minimum 2, Maximum 5 points)
Identify opportunities for improvement and optimization. You MUST find at least 2 different types of opportunities:

1. Efficiency Opportunities: Process improvements, automation, optimization
2. Collaboration Opportunities: Team coordination, knowledge sharing, cross-functional work
3. Learning Opportunities: Skill development, knowledge transfer, best practices
4. Innovation Opportunities: New approaches, technologies, methodologies
5. Business Opportunities: Value creation, customer impact, competitive advantage

For each opportunity identified, provide:
- Opportunity Type: [Efficiency/Collaboration/Learning/Innovation/Business]
- Opportunity Level: [HIGH/MEDIUM/LOW]
- Opportunity Description: [Specific description of the opportunity]
- Benefits: [Concrete benefits this opportunity provides]
- Action Required: [Specific steps to capitalize on this opportunity]

IMPORTANT: For the "Why This Work Item Is Relevant" section, write 2-4 clear, user-friendly bullet points that explain:
1. The specific connection between the work items
2. How one work item affects or depends on the other
3. Shared context, requirements, or technical elements
4. Business impact or timing considerations

Make the reasoning clear and actionable for project managers and developers.

FINAL REMINDER: You MUST provide AT LEAST 2 points for EACH of the four analysis sections (Risk Assessment, Dependencies, Recommendations, Opportunities). This is a MANDATORY requirement. If you cannot identify 2 distinct points for any section, you must think more deeply and creatively about potential issues and opportunities. Your analysis is incomplete if any section has fewer than 2 points."""

        return prompt
    
    @staticmethod
    def _format_simplified_work_items(all_items_data):
        """Format work items in a simplified format for the simplified prompt."""
        formatted_items = []
        
        for item in all_items_data:
            formatted_item = f"""ID: {item['id']} | {item['title']} | {item['work_item_type']} | {item['state']}"""
            formatted_items.append(formatted_item)
        
        return "\n".join(formatted_items)
    
    @staticmethod
    def modify_system_prompt(selected_work_item_data, all_work_items_data, custom_modifications=None):
        """
        Create a modified system prompt with custom formatting and data fixes.
        
        Args:
            selected_work_item_data (dict or WorkItem): Data of the selected work item to analyze
            all_work_items_data (list): List of all available work items data (dicts or WorkItem objects)
            custom_modifications (dict): Optional custom modifications to apply
            
        Returns:
            str: Modified system prompt for the LLM
        """
        
        # Convert WorkItem objects to dictionaries if needed
        if not isinstance(selected_work_item_data, dict):
            selected_work_item_data = ADOWorkItemAnalysisPrompt.work_item_to_dict(selected_work_item_data)
        
        # Convert all work items to dictionaries if needed
        processed_all_work_items = []
        for item in all_work_items_data:
            if not isinstance(item, dict):
                processed_all_work_items.append(ADOWorkItemAnalysisPrompt.work_item_to_dict(item))
            else:
                processed_all_work_items.append(item)
        
        # Apply data fixes to selected work item
        fixed_selected_data = ADOWorkItemAnalysisPrompt._fix_selected_work_item_data(selected_work_item_data)
        
        # Apply data fixes to all work items
        fixed_all_items_data = []
        for item in processed_all_work_items:
            fixed_item = ADOWorkItemAnalysisPrompt._fix_work_item_data(item)
            fixed_all_items_data.append(fixed_item)
        
        # Create the modified prompt
        prompt = f"""You are an expert Azure DevOps work item analyst with deep knowledge of software development methodologies, project management, and technical architecture. Your task is to analyze a selected work item and a collection of all available work items to identify meaningful relationships and dependencies.

CONTEXT
You are analyzing work items from an Azure DevOps project to help development teams understand dependencies, plan work effectively, and identify potential risks or opportunities for optimization.

SELECTED WORK ITEM TO ANALYZE
{ADOWorkItemAnalysisPrompt._format_selected_work_item(fixed_selected_data)}

ALL AVAILABLE WORK ITEMS ({len(fixed_all_items_data)} items)
{ADOWorkItemAnalysisPrompt._format_all_work_items(fixed_all_items_data)}

ANALYSIS OBJECTIVES
1. Primary Goal: Identify work items that are genuinely related to the selected work item
2. Secondary Goal: Understand the nature and strength of these relationships
3. Tertiary Goal: Provide insights that could help with project planning and risk management

RELATIONSHIP TYPES TO CONSIDER

1. FUNCTIONAL DEPENDENCIES
- Prerequisites: Work items that must be completed before the selected item
- Dependents: Work items that depend on the selected item
- Blocking: Work items that block progress on the selected item

2. BUSINESS LOGIC RELATIONSHIPS
- Process Flow: Items that are part of the same business process
- Feature Groups: Items that implement related features
- User Journey: Items that affect the same user experience

3. TECHNICAL DEPENDENCIES
- Shared Components: Items that use the same libraries, APIs, or services
- Data Dependencies: Items that share data models, databases, or data flows
- Infrastructure: Items that depend on the same infrastructure or deployment

4. HIERARCHICAL RELATIONSHIPS
- Epic-Story: Parent-child relationships in agile planning
- Story-Task: Breakdown relationships
- Feature-Component: High-level to detailed implementation

5. QUALITY & MAINTENANCE
- Bug-Fix: Bugs and their corresponding fixes
- Technical Debt: Items related to code quality improvements
- Testing: Items related to testing the selected work

6. CROSS-FUNCTIONAL RELATIONSHIPS
- UI/UX: Items affecting the same user interface
- Backend/Frontend: Items in different architectural layers
- Integration: Items that need to work together

ANALYSIS CRITERIA

RELATIONSHIP STRENGTH ASSESSMENT
- HIGH CONFIDENCE: Clear, direct relationship with strong evidence
- MEDIUM CONFIDENCE: Probable relationship with some supporting evidence
- LOW CONFIDENCE: Possible relationship with limited evidence

EVIDENCE WEIGHTING
- Title Similarity: Keywords, terminology, and naming conventions
- Description Content: Shared concepts, requirements, or technical details
- Tags & Categories: Common tags, area paths, or iteration paths
- Assigned Teams: Same team or related team assignments
- Timing: Items created or planned in similar timeframes
- Priority/Effort: Similar business importance or complexity

OUTPUT REQUIREMENTS

STRUCTURED ANALYSIS FORMAT

RELATED WORK ITEMS ANALYSIS

HIGH CONFIDENCE RELATIONSHIPS
For each high-confidence relationship, provide:
- ID: [Work Item ID]
- Title: [Full Title]
- Type: [Work Item Type]
- State: [Current State]
- Priority: [Priority Level]
- Relationship Type: [Specific relationship category]
- Why This Work Item Is Relevant: [2-4 bullet points explaining the relevance in user-friendly language]
  • [First reason - be specific about the connection]
  • [Second reason - explain the impact or dependency]
  • [Third reason - mention shared context or requirements]
  • [Fourth reason - if applicable, explain timing or priority alignment]

IMPORTANT FORMATTING: Each bullet point must be on a separate line. Use proper line breaks between each bullet point.

MEDIUM CONFIDENCE RELATIONSHIPS
[Same format as above with 2-4 bullet points explaining relevance]

LOW CONFIDENCE RELATIONSHIPS
[Same format as above with 2-4 bullet points explaining relevance]

RELATIONSHIP PATTERNS ANALYSIS
- Primary Patterns: [Most common types of relationships found]
- Dependency Clusters: [Groups of items that form dependency chains]
- Cross-Team Dependencies: [Relationships spanning multiple teams]
- Technical Debt Indicators: [Items suggesting technical debt or refactoring needs]

DETAILED ANALYSIS SECTIONS

CRITICAL REQUIREMENT: You MUST provide AT LEAST 2 points for EACH section below. If you cannot identify 2 distinct points for any section, you must think more deeply about potential risks, dependencies, recommendations, and opportunities. Each section is MANDATORY and requires multiple insights.

IMPORTANT FORMATTING REQUIREMENTS:
- Do NOT use markdown formatting (no ##, ###, **, or other markdown symbols)
- Use plain text with clear headings and structure
- Use simple bullet points with dashes (-) for lists
- Use clear section headers without markdown symbols
- Format each point as: "Risk 1", "Risk 2", "Dependency 1", "Dependency 2", etc.

RISK ASSESSMENT (MANDATORY: Minimum 2, Maximum 5 points)
Analyze the selected work item and related work items to identify potential risks. You MUST find at least 2 different types of risks:

1. Technical Risks: Code quality, architecture, integration, performance, security
2. Resource Risks: Team capacity, skill gaps, availability, workload distribution
3. Timeline Risks: Deadlines, dependencies, delays, sprint planning
4. External Risks: Third-party dependencies, external team coordination, business changes
5. Process Risks: Workflow bottlenecks, communication gaps, quality assurance

For each risk identified, provide:
- Risk Category: [Technical/Resource/Timeline/External/Process]
- Risk Level: [HIGH/MEDIUM/LOW]
- Risk Description: [Specific, actionable description of the risk]
- Impact: [Concrete impact on project success]
- Mitigation: [Specific steps to address this risk]

DEPENDENCIES (MANDATORY: Minimum 2, Maximum 5 points)
Analyze dependencies that could affect the selected work item. You MUST identify at least 2 different types of dependencies:

1. Technical Dependencies: Code, APIs, infrastructure, tools, libraries
2. Resource Dependencies: Team members, skills, external teams, vendors
3. Timeline Dependencies: Sprint schedules, milestone dependencies, release cycles
4. Process Dependencies: Workflow steps, approvals, testing, deployment
5. Business Dependencies: Requirements, stakeholders, external factors

For each dependency identified, provide:
- Dependency Type: [Technical/Resource/Timeline/Process/Business]
- Dependency Level: [CRITICAL/HIGH/MEDIUM/LOW]
- Dependency Description: [Specific description of the dependency]
- Impact: [How this affects the selected work item]
- Action Required: [Specific actions needed to manage this dependency]

RECOMMENDATIONS (MANDATORY: Minimum 2, Maximum 5 points)
Provide actionable recommendations based on your analysis. You MUST suggest at least 2 different types of recommendations:

1. Immediate Actions: What should be done right now
2. Planning Actions: How to improve project planning and coordination
3. Process Improvements: Workflow, communication, quality processes
4. Technical Actions: Code quality, architecture, testing improvements
5. Risk Mitigation: Specific steps to reduce identified risks

For each recommendation, provide:
- Recommendation Type: [Immediate Action/Planning/Process/Technical/Risk Mitigation]
- Priority Level: [HIGH/MEDIUM/LOW]
- Recommendation Description: [Specific, actionable recommendation]
- Rationale: [Why this recommendation is critical]
- Implementation: [Step-by-step implementation approach]

OPPORTUNITIES (MANDATORY: Minimum 2, Maximum 5 points)
Identify opportunities for improvement and optimization. You MUST find at least 2 different types of opportunities:

1. Efficiency Opportunities: Process improvements, automation, optimization
2. Collaboration Opportunities: Team coordination, knowledge sharing, cross-functional work
3. Learning Opportunities: Skill development, knowledge transfer, best practices
4. Innovation Opportunities: New approaches, technologies, methodologies
5. Business Opportunities: Value creation, customer impact, competitive advantage

For each opportunity identified, provide:
- Opportunity Type: [Efficiency/Collaboration/Learning/Innovation/Business]
- Opportunity Level: [HIGH/MEDIUM/LOW]
- Opportunity Description: [Specific description of the opportunity]
- Benefits: [Concrete benefits this opportunity provides]
- Action Required: [Specific steps to capitalize on this opportunity]

ANALYSIS GUIDELINES

1. Be Thorough: Review all work items carefully, don't miss potential relationships
2. Be Specific: Provide concrete evidence and reasoning for each relationship
3. Be Practical: Focus on relationships that matter for project execution
4. Be Objective: Base analysis on evidence, not assumptions
5. Consider Context: Understand the broader project and business context
6. Prioritize Impact: Focus on relationships that have the most significant impact

MANDATORY MULTIPLE POINTS REQUIREMENT:
- You MUST generate AT LEAST 2 distinct points for Risk Assessment
- You MUST generate AT LEAST 2 distinct points for Dependencies  
- You MUST generate AT LEAST 2 distinct points for Recommendations
- You MUST generate AT LEAST 2 distinct points for Opportunities
- If you only provide 1 point for any section, your analysis is INCOMPLETE
- Think creatively and deeply about different angles and perspectives
- Consider both obvious and subtle risks, dependencies, recommendations, and opportunities
- Look at technical, business, process, and human factors
- Consider short-term and long-term implications

QUALITY STANDARDS
- Accuracy: Ensure all relationships are genuinely meaningful
- Completeness: Cover all significant relationship types
- Clarity: Make explanations clear and actionable
- Consistency: Use consistent terminology and format
- Actionability: Provide insights that teams can act upon

Please conduct a comprehensive analysis following these guidelines and provide detailed, actionable insights that will help the development team make informed decisions about their work items."""
        
        return prompt
    
    @staticmethod
    def _fix_selected_work_item_data(work_item_data):
        """Fix data issues in the selected work item data."""
        fixed_data = work_item_data.copy()
        
        # Fix Created By mapping - extract displayName from the field
        created_by = fixed_data.get('created_by', 'Unknown')
        if isinstance(created_by, dict) and 'displayName' in created_by:
            fixed_data['created_by'] = created_by['displayName']
        elif isinstance(created_by, str) and created_by != 'Unknown':
            # If it's already a string, use it as is
            pass
        else:
            fixed_data['created_by'] = 'Unknown'
        
        # Ensure description is included and properly formatted
        description = fixed_data.get('description', 'No description available')
        if not description or description.strip() == '':
            fixed_data['description'] = 'No description available'
        
        return fixed_data
    
    @staticmethod
    def _fix_work_item_data(work_item_data):
        """Fix data issues in work item data."""
        fixed_data = work_item_data.copy()
        
        # Fix Assigned To - ensure it's not always "Unassigned"
        assigned_to = fixed_data.get('assigned_to', 'Unassigned')
        if assigned_to == 'Unassigned' or not assigned_to:
            fixed_data['assigned_to'] = 'Not Assigned'
        
        # Fix tags - ensure proper comma-separated values
        tags = fixed_data.get('tags', '')
        if not tags or tags.strip() == '':
            fixed_data['tags'] = 'No tags'
        else:
            # Ensure tags are properly formatted as comma-separated
            if isinstance(tags, str):
                # Split by semicolon and join with comma if needed
                if ';' in tags:
                    fixed_data['tags'] = ', '.join([tag.strip() for tag in tags.split(';') if tag.strip()])
                else:
                    fixed_data['tags'] = tags.strip()
        
        # Ensure description is included and properly formatted
        description = fixed_data.get('description', 'No description available')
        if not description or description.strip() == '':
            fixed_data['description'] = 'No description available'
        
        return fixed_data
    
    @staticmethod
    def debug_work_item_data(work_item_data, item_name="Work Item"):
        """Debug method to check work item data fields."""
        print(f"\n=== DEBUG: {item_name} ===")
        print(f"ID: {work_item_data.get('id', 'MISSING')}")
        print(f"Title: {work_item_data.get('title', 'MISSING')}")
        print(f"Description: {work_item_data.get('description', 'MISSING')[:100]}{'...' if len(work_item_data.get('description', '')) > 100 else ''}")
        print(f"Type: {work_item_data.get('work_item_type', 'MISSING')}")
        print(f"State: {work_item_data.get('state', 'MISSING')}")
        print(f"Assigned To: {work_item_data.get('assigned_to', 'MISSING')}")
        print(f"Created By: {work_item_data.get('created_by', 'MISSING')}")
        print(f"Tags: {work_item_data.get('tags', 'MISSING')}")
        print("=" * 50)


# Example usage and testing
if __name__ == "__main__":
    # Sample data for testing
    sample_selected_item = {
        'id': 12345,
        'title': 'Implement User Authentication System',
        'work_item_type': 'User Story',
        'state': 'Active',
        'priority': 'High',
        'severity': 'Not set',
        'assigned_to': 'John Doe',
        'created_by': 'Jane Smith',
        'created_date': '2024-01-15',
        'tags': 'authentication,security,user-management',
        'area_path': 'Project\\Features\\Security',
        'iteration_path': 'Project\\Sprint 1',
        'effort': '8',
        'story_points': '5',
        'description': 'Implement a secure user authentication system including login, logout, password reset, and session management features.'
    }
    
    sample_all_items = [
        {
            'id': 12346,
            'title': 'Design User Database Schema',
            'work_item_type': 'Task',
            'state': 'Active',
            'priority': 'High',
            'assigned_to': 'Database Team',
            'tags': 'database,schema,user-management',
            'area_path': 'Project\\Features\\Security',
            'description': 'Design and implement the database schema for user management including users, roles, and permissions tables.'
        },
        {
            'id': 12347,
            'title': 'Create Login UI Components',
            'work_item_type': 'Task',
            'state': 'New',
            'priority': 'Medium',
            'assigned_to': 'UI Team',
            'tags': 'ui,login,components',
            'area_path': 'Project\\Features\\Security',
            'description': 'Create reusable UI components for login forms, password fields, and authentication dialogs.'
        }
    ]
    
    # Test the prompt generation
    print("=== FULL SYSTEM PROMPT ===")
    print(ADOWorkItemAnalysisPrompt.create_system_prompt(sample_selected_item, sample_all_items))
    
    print("\n" + "="*80 + "\n")
    
    print("=== SIMPLIFIED PROMPT ===")
    print(ADOWorkItemAnalysisPrompt.create_simplified_prompt(sample_selected_item, sample_all_items))
