#!/usr/bin/env python3
"""
Azure DevOps Work Item Refinement Tool

This script takes an ADO work item ID as input and uses OpenArena LLM API
to refine and improve the work item details including title, description,
acceptance criteria, and recommendations.

Prerequisites:
- Python 3.6 or higher
- Azure DevOps account with appropriate permissions
- Personal Access Token (PAT) for authentication
- OpenArena ESSO token configured
- Required Python packages installed

Usage:
    python ado_refinement.py <work_item_id>
    
Example:
    python ado_refinement.py 12345
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ado_access import AzureDevOpsClient
from openarena.websocket_client import OpenArenaWebSocketClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/ado_refinement.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ADOWorkItemRefiner:
    """Class for refining Azure DevOps work items using OpenArena LLM."""
    
    def __init__(self, organization_url, personal_access_token):
        """
        Initialize the ADO Work Item Refiner.
        
        Args:
            organization_url (str): The URL of your Azure DevOps organization.
            personal_access_token (str): Your Personal Access Token for authentication.
        """
        self.ado_client = AzureDevOpsClient(organization_url, personal_access_token)
        self.openarena_client = OpenArenaWebSocketClient()
        logger.info("Initialized ADO Work Item Refiner")
    
    def get_work_item_details(self, work_item_id):
        """
        Get detailed information about a work item.
        
        Args:
            work_item_id (int): The ID of the work item to retrieve.
            
        Returns:
            dict: Dictionary containing work item details.
        """
        try:
            work_item = self.ado_client.get_work_item(work_item_id)
            
            details = {
                'id': work_item.id,
                'title': work_item.fields.get('System.Title', 'N/A'),
                'description': work_item.fields.get('System.Description', 'No description provided'),
                'work_item_type': work_item.fields.get('System.WorkItemType', 'N/A'),
                'state': work_item.fields.get('System.State', 'N/A'),
                'assigned_to': work_item.fields.get('System.AssignedTo', 'Unassigned'),
                'tags': work_item.fields.get('System.Tags', ''),
                'created_by': work_item.fields.get('System.CreatedBy', 'Unknown'),
                'created_date': work_item.fields.get('System.CreatedDate', 'Unknown'),
                'changed_by': work_item.fields.get('System.ChangedBy', 'Unknown'),
                'changed_date': work_item.fields.get('System.ChangedDate', 'Unknown'),
                'priority': work_item.fields.get('Microsoft.VSTS.Common.Priority', 'Not set'),
                'severity': work_item.fields.get('Microsoft.VSTS.Common.Severity', 'Not set'),
                'effort': work_item.fields.get('Microsoft.VSTS.Scheduling.Effort', 'Not set'),
                'story_points': work_item.fields.get('Microsoft.VSTS.Scheduling.StoryPoints', 'Not set')
            }
            
            logger.info(f"Retrieved work item {work_item_id}: {details['title']}")
            return details
            
        except Exception as e:
            logger.error(f"Error retrieving work item {work_item_id}: {str(e)}")
            raise
    
    def print_work_item_details(self, details):
        """
        Print formatted work item details.
        
        Args:
            details (dict): Work item details dictionary.
        """
        print("\n" + "="*60)
        print("ORIGINAL WORK ITEM DETAILS")
        print("="*60)
        print(f"ID: {details['id']}")
        print(f"Title: {details['title']}")
        print(f"Type: {details['work_item_type']}")
        print(f"State: {details['state']}")
        print(f"Priority: {details['priority']}")
        print(f"Severity: {details['severity']}")
        print(f"Effort: {details['effort']}")
        print(f"Story Points: {details['story_points']}")
        print(f"Assigned To: {details['assigned_to']}")
        print(f"Created By: {details['created_by']} on {details['created_date']}")
        print(f"Last Modified By: {details['changed_by']} on {details['changed_date']}")
        
        if details['tags']:
            print(f"Tags: {details['tags']}")
        
        print(f"\nDescription:")
        print("-" * 40)
        print(details['description'])
        print("="*60)
    
    def create_refinement_prompt(self, details):
        """
        Create a comprehensive prompt for LLM refinement.
        
        Args:
            details (dict): Work item details dictionary.
            
        Returns:
            str: Formatted prompt for LLM refinement.
        """
        prompt = f"""
Please help refine and improve this Azure DevOps work item to make it more actionable, clear, and comprehensive.

WORK ITEM INFORMATION:
- ID: {details['id']}
- Type: {details['work_item_type']}
- Current Title: {details['title']}
- Current State: {details['state']}
- Priority: {details['priority']}
- Severity: {details['severity']}
- Effort: {details['effort']}
- Story Points: {details['story_points']}
- Assigned To: {details['assigned_to']}
- Tags: {details['tags']}

CURRENT DESCRIPTION:
{details['description']}

Please provide a comprehensive refinement that includes:

1. **IMPROVED TITLE**
   - Make it clear, concise, and action-oriented
   - Use active voice and specific language
   - Ensure it clearly describes what needs to be accomplished

2. **ENHANCED DESCRIPTION**
   - Expand the current description with more context
   - Add business value and stakeholder impact
   - Include technical context and considerations

3. **ACCEPTANCE CRITERIA**
   - Define clear, testable acceptance criteria
   - Use "Given-When-Then" format where appropriate
   - Ensure criteria are measurable and verifiable

4. **BUSINESS CONTEXT**
   - Explain why this work item is important
   - Describe the business problem it solves
   - Identify stakeholders and their needs

5. **TECHNICAL CONSIDERATIONS**
   - Highlight technical dependencies
   - Identify potential technical challenges
   - Suggest implementation approach

6. **DEPENDENCIES & BLOCKERS**
   - List any dependencies on other work items
   - Identify potential blockers or risks
   - Suggest mitigation strategies

7. **ESTIMATION GUIDANCE**
   - Provide guidance on effort estimation
   - Suggest story point values if applicable
   - Identify factors that might affect estimation

8. **NEXT STEPS**
   - Recommend immediate next actions
   - Suggest who should be involved
   - Identify any research or investigation needed

9. **IMPROVED TAGS**
   - Suggest additional tags for better categorization
   - Include tags for priority, complexity, and domain

10. **RISK ASSESSMENT**
    - Identify potential risks or issues
    - Suggest risk mitigation strategies
    - Flag any high-risk areas

Please format your response in a clear, structured manner with appropriate headings and bullet points. Focus on making this work item more actionable and easier to understand for developers, testers, and stakeholders.
"""
        return prompt
    
    def refine_work_item(self, work_item_id):
        """
        Refine a work item using OpenArena LLM.
        
        Args:
            work_item_id (int): The ID of the work item to refine.
            
        Returns:
            tuple: (refined_content, cost_tracker)
        """
        try:
            logger.info(f"Starting refinement process for work item {work_item_id}")
            
            # Get work item details
            details = self.get_work_item_details(work_item_id)
            
            # Print original details
            self.print_work_item_details(details)
            
            # Create refinement prompt
            prompt = self.create_refinement_prompt(details)
            
            print("\n" + "="*60)
            print("REFINING WITH OPENARENA LLM...")
            print("="*60)
            
            # Send to OpenArena LLM
            refined_content, cost_tracker = self.openarena_client.query_workflow(
                workflow_id='gpt4o',
                query=prompt,
                is_persistence_allowed=False
            )
            
            return refined_content, cost_tracker
            
        except Exception as e:
            logger.error(f"Error during refinement process: {str(e)}")
            raise
    
    def print_refinement_results(self, refined_content, cost_tracker):
        """
        Print the refinement results in a formatted way.
        
        Args:
            refined_content (str): The refined content from LLM.
            cost_tracker (dict): Cost tracking information.
        """
        print("\n" + "="*60)
        print("REFINED WORK ITEM")
        print("="*60)
        
        if refined_content:
            print(refined_content)
        else:
            print("No refinement content received from OpenArena LLM.")
        
        print("\n" + "="*60)
        print("COST INFORMATION")
        print("="*60)
        
        if cost_tracker and 'error' not in cost_tracker:
            print(f"Cost tracking details: {cost_tracker}")
        else:
            print("No cost information available or error occurred.")
        
        print("="*60)
    
    def save_refinement_to_file(self, work_item_id, original_details, refined_content, cost_tracker):
        """
        Save the refinement results to a file.
        
        Args:
            work_item_id (int): Work item ID.
            original_details (dict): Original work item details.
            refined_content (str): Refined content from LLM.
            cost_tracker (dict): Cost tracking information.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"work_item_{work_item_id}_refinement_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("AZURE DEVOPS WORK ITEM REFINEMENT REPORT\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Work Item ID: {work_item_id}\n\n")
                
                f.write("ORIGINAL WORK ITEM DETAILS\n")
                f.write("-" * 30 + "\n")
                for key, value in original_details.items():
                    f.write(f"{key}: {value}\n")
                
                f.write("\nREFINED WORK ITEM\n")
                f.write("-" * 30 + "\n")
                f.write(refined_content if refined_content else "No refinement content received.\n")
                
                f.write("\nCOST INFORMATION\n")
                f.write("-" * 30 + "\n")
                if cost_tracker and 'error' not in cost_tracker:
                    f.write(f"Cost tracking: {cost_tracker}\n")
                else:
                    f.write("No cost information available.\n")
            
            logger.info(f"Refinement results saved to {filename}")
            print(f"\nRefinement results saved to: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving refinement results to file: {str(e)}")
            print(f"Warning: Could not save results to file: {str(e)}")


def main():
    """Main function to run the ADO work item refinement tool."""
    parser = argparse.ArgumentParser(
        description="Refine Azure DevOps work items using OpenArena LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ado_refinement.py 12345
  python ado_refinement.py --org "https://dev.azure.com/myorg" --pat "mytoken" 12345
        """
    )
    
    parser.add_argument(
        'work_item_id',
        type=int,
        help='The ID of the work item to refine'
    )
    
    parser.add_argument(
        '--org',
        '--organization',
        dest='organization_url',
        default='https://dev.azure.com/your-organization',
        help='Azure DevOps organization URL (default: https://dev.azure.com/your-organization)'
    )
    
    parser.add_argument(
        '--pat',
        '--token',
        dest='personal_access_token',
        help='Personal Access Token for Azure DevOps authentication'
    )
    
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save refinement results to a file'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check for PAT
    if not args.personal_access_token:
        print("Personal Access Token (PAT) is required.")
        print("Please provide it using --pat or --token argument.")
        print("You can also set it as an environment variable: ADO_PAT")
        sys.exit(1)
    
    try:
        # Create refiner instance
        refiner = ADOWorkItemRefiner(args.organization_url, args.personal_access_token)
        
        # Get original details for saving
        original_details = refiner.get_work_item_details(args.work_item_id)
        
        # Perform refinement
        refined_content, cost_tracker = refiner.refine_work_item(args.work_item_id)
        
        # Print results
        refiner.print_refinement_results(refined_content, cost_tracker)
        
        # Save to file if requested
        if args.save:
            refiner.save_refinement_to_file(
                args.work_item_id,
                original_details,
                refined_content,
                cost_tracker
            )
        
        print(f"\n✅ Work item {args.work_item_id} refinement completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n❌ Refinement process interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during refinement process: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
