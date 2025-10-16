"""
Azure DevOps AI Studio

This script provides a graphical user interface for interacting with Azure DevOps boards.
It uses Tkinter for the UI and the AzureDevOpsClient class from ado_access.py for ADO operations.

Prerequisites:
- Python 3.6 or higher
- Azure DevOps account with appropriate permissions
- Personal Access Token (PAT) for authentication
"""

import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import io
import sys
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
import json
import subprocess
import time
from websockets.sync.client import connect
import base64
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ado.ado_access import AzureDevOpsClient
from openarena.websocket_client import OpenArenaWebSocketClient
from llm.ado_analysis_prompt import ADOWorkItemAnalysisPrompt

# Import icon helper
try:
    from .icon_helper import set_application_icon
except ImportError:
    try:
        from icon_helper import set_application_icon
    except ImportError:
        def set_application_icon(root):
            print("⚠️ Icon helper not available, using default icon")

class RedirectText:
    """Class to redirect stdout to a tkinter Text widget."""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""

    def write(self, string):
        self.buffer += string
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass

class ADOBoardViewerApp:
    """Main application class for the Azure DevOps AI Studio."""
    
    def __init__(self, root):
        """Initialize the application."""
        # Load environment variables from env_config.py first
        try:
            from openarena.config.env_config import set_environment_variables
            set_environment_variables()
        except Exception as e:
            print(f"Warning: Could not load environment variables: {e}")
        
        self.root = root
        self.root.title("Azure DevOps AI Studio")
        self.root.geometry("1200x700")  # Increased width to accommodate wider columns
        self.root.minsize(1000, 600)   # Increased minimum width
        
        # Set custom application icon
        set_application_icon(self.root)
        
        # Set style
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Use a modern theme
        
        # Create client variable
        self.client = None
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initialize filter variables early to prevent AttributeError
        self.filter_vars = {}
        self.filter_widgets = {}
        self.filter_data = {}
        self.enhanced_filter_manager = None
        self.current_work_items = []
        
        # Add caching for related work items to prevent repeated API calls
        self.related_items_cache = {}
        
        # Add cache management methods
        self.cache_max_size = 50  # Limit cache size to prevent memory issues
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create tabs
        self.create_connection_tab()
        self.create_openarena_test_tab()
        self.create_team_selection_tab()
        self.create_model_selection_tab()
        self.create_work_items_tab()
        self.create_ado_operations_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        # Load saved settings if available
        self.load_settings()
        
        # Set default maximum ADO limit to prevent VS402337 errors
        self.max_ado_work_item_limit = 19000
    
    def create_connection_tab(self):
        """Create the connection tab."""
        connection_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(connection_frame, text="Create ADO Connection")
        
        # Connection settings
        settings_frame = ttk.LabelFrame(connection_frame, text="Azure DevOps Connection Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # Organization URL
        ttk.Label(settings_frame, text="Organization URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.org_url_var = tk.StringVar(value=os.getenv('AZURE_DEVOPS_ORG_URL', 'https://dev.azure.com/your-organization'))
        ttk.Entry(settings_frame, textvariable=self.org_url_var, width=50).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Personal Access Token
        ttk.Label(settings_frame, text="Personal Access Token:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.pat_var = tk.StringVar(value=os.getenv('AZURE_DEVOPS_PAT', 'your_azure_devops_pat_here'))
        pat_entry = ttk.Entry(settings_frame, textvariable=self.pat_var, width=50, show="*")
        pat_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Project
        ttk.Label(settings_frame, text="Project:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.project_var = tk.StringVar(value=os.getenv('AZURE_DEVOPS_PROJECT', 'Your Project Name'))
        ttk.Entry(settings_frame, textvariable=self.project_var, width=50).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Team
        ttk.Label(settings_frame, text="Team:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.team_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.team_var, width=50).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Connect button
        connect_button = ttk.Button(settings_frame, text="Connect", command=self.connect_to_ado)
        connect_button.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Save settings checkbox
        self.save_settings_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Save settings", variable=self.save_settings_var).grid(row=5, column=0, sticky=tk.W)
        
        # Auto Connect checkbox
        self.auto_connect_var = tk.BooleanVar(value=False)
        auto_connect_checkbox = ttk.Checkbutton(settings_frame, text="Auto Connect to ADO", variable=self.auto_connect_var, command=self.on_auto_connect_changed)
        auto_connect_checkbox.grid(row=5, column=1, sticky=tk.W, padx=(10, 0))
        
        # Output area
        output_frame = ttk.LabelFrame(connection_frame, text="Output", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        self.connection_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=10)
        self.connection_output.pack(fill=tk.BOTH, expand=True)
        self.connection_output.configure(state="disabled")
    
    def create_team_selection_tab(self):
        """Create the team selection tab."""
        team_selection_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(team_selection_frame, text="ADO Team Selection")
        
        # Description frame
        desc_frame = ttk.LabelFrame(team_selection_frame, text="About Team Selection", padding="10")
        desc_frame.pack(fill=tk.X, pady=(0, 10))
        
        desc_text = """This tab allows you to select from available teams in your project. 
        The selected team will be used in other tabs for Azure DevOps operations. 
        You can also copy team URLs or open them directly in your browser."""
        
        desc_label = ttk.Label(desc_frame, text=desc_text, wraplength=600, justify=tk.LEFT)
        desc_label.pack(anchor=tk.W)
        
        # Input frame
        input_frame = ttk.LabelFrame(team_selection_frame, text="Select Team", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Project
        ttk.Label(input_frame, text="Project:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.team_project_var = tk.StringVar(value=os.getenv('AZURE_DEVOPS_PROJECT', 'Your Project Name'))
        ttk.Entry(input_frame, textvariable=self.team_project_var, width=50).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Team selection dropdown
        ttk.Label(input_frame, text="Select Team:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.team_selection_var = tk.StringVar()
        
        # Create a searchable combobox
        self.team_combo = ttk.Combobox(input_frame, textvariable=self.team_selection_var, 
                                      values=[], state="normal", width=50)
        self.team_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Bind events for searchable combobox
        self.team_combo.bind('<KeyRelease>', self.filter_teams)
        self.team_combo.bind('<<ComboboxSelected>>', self.on_team_selected)
        
        # Create a container frame for the 3 main action buttons
        action_buttons_frame = ttk.Frame(input_frame)
        action_buttons_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        # Configure the frame to center the buttons
        action_buttons_frame.columnconfigure(0, weight=1)
        action_buttons_frame.columnconfigure(1, weight=1)
        action_buttons_frame.columnconfigure(2, weight=1)
        
        # Get All Teams button
        get_teams_button = ttk.Button(action_buttons_frame, text="Get All Teams", command=self.get_teams)
        get_teams_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        # Get Practical Law and Westlaw teams button
        get_pl_wl_teams_button = ttk.Button(action_buttons_frame, text="Get Practical Law and Westlaw team(s)", command=self.get_practical_law_westlaw_teams)
        get_pl_wl_teams_button.grid(row=0, column=1, padx=5, sticky="ew")
        
        # Get Work Items for Selected Team button - moved to Related Work Items tab
        
        # Create a container frame for the additional action buttons
        additional_buttons_frame = ttk.Frame(input_frame)
        additional_buttons_frame.grid(row=3, column=0, columnspan=2, pady=5)
        
        # Configure the frame to center the buttons
        additional_buttons_frame.columnconfigure(0, weight=1)
        additional_buttons_frame.columnconfigure(1, weight=1)
        additional_buttons_frame.columnconfigure(2, weight=1)
        
        # Test Team Context button
        test_team_context_button = ttk.Button(additional_buttons_frame, text="🔍 Test Team Context", command=self.test_team_context)
        test_team_context_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        # Explain Team Query Strategy button
        explain_strategy_button = ttk.Button(additional_buttons_frame, text="📚 Explain Team Query Strategy", command=self.explain_team_query_strategy)
        explain_strategy_button.grid(row=0, column=1, padx=5, sticky="ew")
        
        # Discover Area Paths button
        discover_area_paths_button = ttk.Button(additional_buttons_frame, text="🔍 Discover Area Paths", command=self.discover_area_paths)
        discover_area_paths_button.grid(row=0, column=2, padx=(5, 0), sticky="ew")
        
        # Enhanced Team Filtering Info button
        enhanced_filtering_button = ttk.Button(additional_buttons_frame, text="🚀 Enhanced Team Filtering", command=self.show_enhanced_filtering_info)
        enhanced_filtering_button.grid(row=0, column=3, padx=5, sticky="ew")
        
        # Configure Area Path Mappings button
        configure_mappings_button = ttk.Button(additional_buttons_frame, text="⚙️ Configure Mappings", command=self.configure_area_path_mappings)
        configure_mappings_button.grid(row=0, column=4, padx=5, sticky="ew")
        
        # Work item filters frame - moved to Related Work Items tab
        
        # Create notebook for sub-tabs
        self.team_sub_notebook = ttk.Notebook(team_selection_frame)
        self.team_sub_notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Available Teams sub-tab
        available_teams_frame = ttk.Frame(self.team_sub_notebook, padding="10")
        self.team_sub_notebook.add(available_teams_frame, text="Available Teams")
        
        # Configure the frame to expand properly
        available_teams_frame.columnconfigure(0, weight=1)
        available_teams_frame.rowconfigure(1, weight=1)
        
        # Team information display
        info_frame = ttk.Frame(available_teams_frame)
        info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(info_frame, text="Team Information:", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W)
        
        # Create a scrollable frame for team details that expands to fill available space
        team_details_container = ttk.Frame(available_teams_frame)
        team_details_container.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        
        # Configure the container to expand
        team_details_container.columnconfigure(0, weight=1)
        team_details_container.rowconfigure(0, weight=1)
        
        # Create canvas and scrollbar for team details
        team_details_canvas = tk.Canvas(team_details_container)
        team_details_scrollbar = ttk.Scrollbar(team_details_container, orient="vertical", command=team_details_canvas.yview)
        self.team_details_frame = ttk.Frame(team_details_canvas)
        
        # Configure canvas scrolling
        team_details_canvas.configure(yscrollcommand=team_details_scrollbar.set)
        
        # Pack scrollbar and canvas - make canvas expand to fill space
        team_details_scrollbar.pack(side="right", fill="y")
        team_details_canvas.pack(side="left", fill="both", expand=True)
        
        # Create window in canvas for the frame
        team_details_canvas.create_window((0, 0), window=self.team_details_frame, anchor="nw")
        
        # Configure scrolling and canvas expansion
        def configure_scroll_region(event):
            team_details_canvas.configure(scrollregion=team_details_canvas.bbox("all"))
        
        def on_canvas_configure(event):
            # Update the inner frame's width to match the canvas width
            canvas_width = event.width
            team_details_canvas.itemconfig(team_details_canvas.find_withtag("all")[0], width=canvas_width)
        
        self.team_details_frame.bind("<Configure>", configure_scroll_region)
        team_details_canvas.bind("<Configure>", on_canvas_configure)
        
        # Raw Output sub-tab
        raw_output_frame = ttk.Frame(self.team_sub_notebook, padding="10")
        self.team_sub_notebook.add(raw_output_frame, text="Raw Output")
        
        # Teams output area (moved to raw output sub-tab)
        self.teams_output = scrolledtext.ScrolledText(raw_output_frame, wrap=tk.WORD, height=8)
        self.teams_output.pack(fill=tk.BOTH, expand=True)
        self.teams_output.configure(state="disabled")
    

    def create_work_items_tab(self):
        """Create the work items display tab."""
        work_items_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(work_items_frame, text="Related Work Items")
        

        
        # Create a horizontal frame to hold both filters and controls side by side
        filters_controls_frame = ttk.Frame(work_items_frame)
        filters_controls_frame.pack(fill=tk.X, pady=5)
        
        # Work item filters frame - left half
        selected_team = self.team_selection_var.get() if hasattr(self, 'team_selection_var') and self.team_selection_var.get() else "No Team Selected"
        filters_frame = ttk.LabelFrame(filters_controls_frame, text=f"Source Work Item Filters for {selected_team}", padding="10")
        filters_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Work Items Controls frame - right half
        controls_frame = ttk.LabelFrame(filters_controls_frame, text="Work Items Controls", padding="10")
        controls_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Refresh button
        refresh_button = ttk.Button(controls_frame, text="🔄 Refresh Work Items", command=self.refresh_work_items)
        refresh_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Clear button
        clear_button = ttk.Button(controls_frame, text="🗑️ Clear Display", command=self.clear_work_items_display)
        clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Export button
        export_button = ttk.Button(controls_frame, text="📤 Export to File", command=self.export_work_items)
        export_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Verify Team-Specific button
        verify_button = ttk.Button(controls_frame, text="🔍 Verify Team-Specific", command=self.verify_team_specific_items)
        verify_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Performance Settings button (moved from filters section)
        perf_settings_button = ttk.Button(controls_frame, text="⚙️ Performance Settings", 
                                         command=self.show_performance_settings)
        perf_settings_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Hierarchy loading toggle checkbox
        self.load_hierarchy_var = tk.BooleanVar(value=False)  # Default to False for performance
        hierarchy_checkbox = ttk.Checkbutton(controls_frame, text="📊 Load Hierarchy for All Items", 
                                           variable=self.load_hierarchy_var,
                                           command=self.on_hierarchy_toggle_changed)
        hierarchy_checkbox.pack(side=tk.LEFT, padx=(0, 10))
        
        # Status label
        self.work_items_status_var = tk.StringVar(value="No work items loaded. Use the 'Get Work Items for Selected Team' button above to retrieve work items.")
        status_label = ttk.Label(controls_frame, textvariable=self.work_items_status_var, font=("TkDefaultFont", 9))
        status_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Create enhanced filters frame
        self.create_enhanced_filters(filters_frame)
        
        # Note: Enhanced filter buttons are now in the create_enhanced_filters method
        
        # Refresh Filters button (hidden)
        # refresh_filters_button = ttk.Button(filters_frame, text="🔄 Refresh Filters", command=self.populate_filters_dynamically)
        # refresh_filters_button.grid(row=0, column=6, padx=(10, 0), sticky=tk.W, pady=2)
        
        # Help button (hidden)
        # help_button = ttk.Button(filters_frame, text="❓ Help", command=self.show_team_help)
        # help_button.grid(row=0, column=7, padx=(10, 0), sticky=tk.W, pady=2)
        
        # Work items display frame
        display_frame = ttk.LabelFrame(work_items_frame, text="Work Items Display", padding="10")
        display_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create a notebook for different views
        self.work_items_notebook = ttk.Notebook(display_frame)
        self.work_items_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Summary view tab (hidden)
        summary_frame = ttk.Frame(self.work_items_notebook, padding="10")
        self.work_items_notebook.add(summary_frame, text="Summary View")
        
        # Summary text widget
        self.work_items_summary = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, height=15)
        self.work_items_summary.pack(fill=tk.BOTH, expand=True)
        self.work_items_summary.configure(state="disabled")
        
        # Detailed view tab (hidden)
        detailed_frame = ttk.Frame(self.work_items_notebook, padding="10")
        self.work_items_notebook.add(detailed_frame, text="Detailed View")
        
        # Detailed text widget
        self.work_items_detailed = scrolledtext.ScrolledText(detailed_frame, wrap=tk.WORD, height=15)
        self.work_items_detailed.pack(fill=tk.BOTH, expand=True)
        self.work_items_detailed.configure(state="disabled")
        
        # Table view tab (renamed to ADO Work Items)
        table_frame = ttk.Frame(self.work_items_notebook, padding="10")
        self.work_items_notebook.add(table_frame, text="ADO Work Items")
        
        # Create filter interface above the table
        self.create_filter_interface(table_frame)
        
        # Refine Related Work Items sub-tab
        self.refine_related_frame = ttk.Frame(self.work_items_notebook, padding="10")
        self.work_items_notebook.add(self.refine_related_frame, text="Refine Related Work Items")
        
        # Initialize variables for this sub-tab
        self.current_source_work_item = None
        self.current_related_items = []
        
        # Header frame (simple frame without label)
        header_frame = ttk.Frame(self.refine_related_frame, padding="10")
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Left side: Source work item info
        source_frame = ttk.Frame(header_frame)
        source_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.source_info_label = ttk.Label(source_frame, text="No work item selected", 
                                         font=("TkDefaultFont", 10, "bold"))
        self.source_info_label.pack(anchor=tk.W)
        
        self.related_count_label = ttk.Label(source_frame, text="")
        self.related_count_label.pack(anchor=tk.W)
        
        # Right side: Analysis with LLM button
        self.llm_analysis_button = ttk.Button(
            header_frame, 
            text="🤖 Analysis with LLM", 
            command=self.analyze_with_llm,
            width=20
        )
        self.llm_analysis_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Create filter interface for refine related work items tab
        self.create_refine_filter_interface(self.refine_related_frame)
        
        # Create treeview for related items
        columns = ('ID', 'Type', 'State', 'Title', 'Assigned To', 'Created Date')
        self.refine_related_tree = ttk.Treeview(self.refine_related_frame, columns=columns, show='headings', height=15)
        
        # Configure columns with appropriate widths
        column_widths = {
            'ID': 80,
            'Type': 100,
            'State': 100,
            'Title': 400,
            'Assigned To': 150,
            'Created Date': 120
        }
        
        for col in columns:
            self.refine_related_tree.heading(col, text=col)
            if col in column_widths:
                self.refine_related_tree.column(col, width=column_widths[col], minwidth=column_widths[col]//2)
            else:
                self.refine_related_tree.column(col, width=120, minwidth=80)
        
        # Add scrollbars
        tree_scroll_y = ttk.Scrollbar(self.refine_related_frame, orient=tk.VERTICAL, command=self.refine_related_tree.yview)
        tree_scroll_x = ttk.Scrollbar(self.refine_related_frame, orient=tk.HORIZONTAL, command=self.refine_related_tree.xview)
        self.refine_related_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        # Pack the treeview and scrollbars
        self.refine_related_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Add initial message
        self.refine_related_tree.insert('', 'end', values=(
            "", "", "", "Click 'Show Related Work Items' in the ADO Work Items tab to see related items here", 
            "", ""
        ))
        
        # LLM Analysis Results tab
        self.llm_analysis_frame = ttk.Frame(self.work_items_notebook, padding="10")
        self.work_items_notebook.add(self.llm_analysis_frame, text="LLM Analysis Results")
        
        # Style the frame with a subtle background
        style = ttk.Style()
        style.configure("LLMAnalysis.TFrame", background="#F8FAFC")
        self.llm_analysis_frame.configure(style="LLMAnalysis.TFrame")
        
        # Create sub-notebook for LLM Analysis Results
        self.llm_analysis_notebook = ttk.Notebook(self.llm_analysis_frame)
        self.llm_analysis_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Analysis Results sub-tab
        self.llm_results_frame = ttk.Frame(self.llm_analysis_notebook, padding="10")
        self.llm_analysis_notebook.add(self.llm_results_frame, text="Analysis Results")
        
        # LLM Analysis text widget with enhanced styling
        self.llm_analysis_text = scrolledtext.ScrolledText(
            self.llm_results_frame, 
            wrap=tk.WORD, 
            height=15,
            font=("Arial", 9),
            bg="#FAFAFA",
            fg="#1F2937",
            insertbackground="#3B82F6",
            selectbackground="#3B82F6",
            selectforeground="white",
            relief="solid",
            borderwidth=2,
            padx=15,
            pady=15
        )
        self.llm_analysis_text.pack(fill=tk.BOTH, expand=True)
        
        # All Work Items sub-tab
        self.all_work_items_frame = ttk.Frame(self.llm_analysis_notebook, padding="10")
        self.llm_analysis_notebook.add(self.all_work_items_frame, text="All Work Items")
        
        # All Work Items text widget with enhanced styling
        self.all_work_items_text = scrolledtext.ScrolledText(
            self.all_work_items_frame, 
            wrap=tk.WORD, 
            height=15,
            font=("Consolas", 8),  # Monospace font for better data display
            bg="#F8F9FA",
            fg="#2D3748",
            insertbackground="#3B82F6",
            selectbackground="#3B82F6",
            selectforeground="white",
            relief="solid",
            borderwidth=2,
            padx=15,
            pady=15
        )
        self.all_work_items_text.pack(fill=tk.BOTH, expand=True)
        
        # Add initial message to All Work Items tab
        self.all_work_items_text.insert(tk.END, "📊 All Work Items Data\n\n")
        self.all_work_items_text.insert(tk.END, "This tab will display all work items data retrieved from Azure DevOps when you perform an LLM analysis.\n\n")
        self.all_work_items_text.insert(tk.END, "The data includes:\n")
        self.all_work_items_text.insert(tk.END, "• Work item IDs and titles\n")
        self.all_work_items_text.insert(tk.END, "• Work item types and states\n")
        self.all_work_items_text.insert(tk.END, "• Assigned users and area paths\n")
        self.all_work_items_text.insert(tk.END, "• Descriptions and other relevant fields\n")
        self.all_work_items_text.configure(state="disabled")
        
        # System Prompt sub-tab
        self.system_prompt_frame = ttk.Frame(self.llm_analysis_notebook, padding="10")
        self.llm_analysis_notebook.add(self.system_prompt_frame, text="System Prompt")
        
        # System Prompt text widget
        self.system_prompt_text = scrolledtext.ScrolledText(
            self.system_prompt_frame,
            wrap=tk.WORD,
            height=15,
            font=("Consolas", 9),  # Monospace font for better readability
            bg="#F8F9FA",
            fg="#2D3748",
            insertbackground="#3B82F6",
            selectbackground="#3B82F6",
            selectforeground="white",
            relief="solid",
            borderwidth=2,
            padx=15,
            pady=15
        )
        self.system_prompt_text.pack(fill=tk.BOTH, expand=True)
        
        # Add initial message to System Prompt tab
        self.system_prompt_text.insert(tk.END, "🔧 System Prompt\n\n")
        self.system_prompt_text.insert(tk.END, "This tab will display the exact system prompt sent to the LLM when you perform an analysis.\n\n")
        self.system_prompt_text.insert(tk.END, "The system prompt contains:\n")
        self.system_prompt_text.insert(tk.END, "• Instructions for the LLM\n")
        self.system_prompt_text.insert(tk.END, "• Selected work item details\n")
        self.system_prompt_text.insert(tk.END, "• All available work items data\n")
        self.system_prompt_text.insert(tk.END, "• Analysis objectives and criteria\n")
        self.system_prompt_text.configure(state="disabled")
        
        # Add initial welcome message with formatting
        welcome_message = """🤖 LLM Analysis Results

This tab will display the results of LLM analysis when you click the "🤖 Analyze with LLM" button in the ADO Work Items tab.

To get started:
1. Go to the "ADO Work Items" tab
2. Click "🤖 Analyze with LLM" on any work item row
3. Wait for the analysis to complete
4. Results will appear here automatically

The analysis will provide insights about:
• Related work items
• Technical dependencies
• Business relationships
• Impact analysis
• Recommendations"""
        
        # Configure initial styling for welcome message
        self._configure_llm_text_styling()
        
        # Insert welcome message with formatting
        self.llm_analysis_text.insert(tk.END, "🤖 LLM Analysis Results\n\n", "header")
        self.llm_analysis_text.insert(tk.END, "This tab will display the results of LLM analysis when you click the \"🤖 Analyze with LLM\" button in the ADO Work Items tab.\n\n", "work_item_details")
        self.llm_analysis_text.insert(tk.END, "To get started:\n", "subsection_header")
        self.llm_analysis_text.insert(tk.END, "1. Go to the \"ADO Work Items\" tab\n", "work_item_details")
        self.llm_analysis_text.insert(tk.END, "2. Click \"🤖 Analyze with LLM\" on any work item row\n", "work_item_details")
        self.llm_analysis_text.insert(tk.END, "3. Wait for the analysis to complete\n", "work_item_details")
        self.llm_analysis_text.insert(tk.END, "4. Results will appear here automatically\n\n", "work_item_details")
        self.llm_analysis_text.insert(tk.END, "The analysis will provide insights about:\n", "subsection_header")
        self.llm_analysis_text.insert(tk.END, "• Related work items\n", "evidence")
        self.llm_analysis_text.insert(tk.END, "• Technical dependencies\n", "evidence")
        self.llm_analysis_text.insert(tk.END, "• Business relationships\n", "evidence")
        self.llm_analysis_text.insert(tk.END, "• Impact analysis\n", "evidence")
        self.llm_analysis_text.insert(tk.END, "• Recommendations", "evidence")
        
        self.llm_analysis_text.configure(state="disabled")
        
        # Hide the first two tabs (Summary View and Detailed View)
        self.work_items_notebook.hide(0)  # Hide Summary View
        self.work_items_notebook.hide(1)  # Hide Detailed View
        
        # Create treeview for table display
        columns = ('ID', 'Type', 'State', 'Title', 'Assigned To', 'Created Date', 'Show Related Work Items', 'Analyze with LLM', 'Open in Azure DevOps')
        self.work_items_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Initialize sorting state
        self.sort_column = None
        self.sort_reverse = False
        
        # Configure columns with appropriate widths (optimized to fit without horizontal scroll)
        column_widths = {
            'ID': 35,        # Further reduced
            'Type': 45,      # Further reduced
            'State': 45,     # Further reduced
            'Title': 80,     # Even more aggressively reduced to make maximum room
            'Assigned To': 140,  # Further increased to prevent name truncation
            'Created Date': 90,  # Increased to prevent date truncation
            'Show Related Work Items': 160,  # Keep same
            'Analyze with LLM': 130,         # Keep same
            'Open in Azure DevOps': 150      # Increased to prevent truncation
        }
        
        for col in columns:
            # Format column headers for better readability - use shorter, single-line headers
            if col == 'Show Related Work Items':
                header_text = "Related"
            elif col == 'Analyze with LLM':
                header_text = "Analyze"
            elif col == 'Open in Azure DevOps':
                header_text = "Open ADO"
            else:
                header_text = col
            
            # Make headers clickable for sorting (except action columns)
            if col not in ['Show Related Work Items', 'Analyze with LLM', 'Open in Azure DevOps']:
                self.work_items_tree.heading(col, text=header_text, command=lambda c=col: self.sort_treeview(c))
            else:
                self.work_items_tree.heading(col, text=header_text)
                
            if col in column_widths:
                if col == 'Title':
                    # Make Title column stretchable to use available space, but with very small minimum
                    self.work_items_tree.column(col, width=column_widths[col], minwidth=60, stretch=True)
                else:
                    self.work_items_tree.column(col, width=column_widths[col], minwidth=column_widths[col]//2, stretch=False)
            else:
                self.work_items_tree.column(col, width=100, minwidth=50, stretch=False)
        
        # Add only vertical scrollbar (remove horizontal scrollbar)
        tree_scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.work_items_tree.yview)
        self.work_items_tree.configure(yscrollcommand=tree_scroll_y.set)
        
        # Use pack layout for proper alignment of treeview and scrollbar
        self.work_items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind click events for the action columns
        self.work_items_tree.bind('<Button-1>', self.on_tree_click)
        
        # Style the action columns to look more clickable
        self.style_action_columns()
        
        # Add tooltip support for better text visibility
        self.tooltip = None
        self.work_items_tree.bind('<Motion>', self.on_tree_motion)
        self.work_items_tree.bind('<Leave>', self.on_tree_leave)
    
    def style_action_columns(self):
        """Apply styling to make action columns look more clickable."""
        # Create a custom style for action columns
        style = ttk.Style()
        
        # Configure the action columns to have a different appearance
        # Note: Treeview styling is limited, but we can use tags for row styling
        pass  # Placeholder for future styling enhancements
        
        # Store current work items
        self.current_work_items = []
    
    def create_enhanced_filters(self, parent_frame):
        """Create enhanced filtering interface."""
        # Import enhanced filter manager
        try:
            from ado.enhanced_filters import EnhancedFilterManager
            if self.client:
                self.enhanced_filter_manager = EnhancedFilterManager(self.client)
        except ImportError as e:
            logger.error(f"Could not import EnhancedFilterManager: {e}")
            return
        
        # Create main filters frame
        main_filters_frame = ttk.Frame(parent_frame)
        main_filters_frame.grid(row=0, column=0, columnspan=6, sticky=tk.W+tk.E, pady=5)
        
        # Row 0: Basic filters
        row = 0
        
        # Work Item Type filter
        ttk.Label(main_filters_frame, text="Work Item Type:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.work_item_type_filter = tk.StringVar(value="All")
        self.work_item_type_combo = ttk.Combobox(main_filters_frame, textvariable=self.work_item_type_filter, 
                                                values=["All"], state="readonly", width=15)
        self.work_item_type_combo.grid(row=row, column=1, sticky=tk.W, padx=(5, 10), pady=2)
        self.work_item_type_combo.bind('<<ComboboxSelected>>', self.on_work_item_type_changed)
        
        # State filter
        ttk.Label(main_filters_frame, text="State:").grid(row=row, column=2, sticky=tk.W, pady=2)
        self.state_filter = tk.StringVar(value="All")
        self.state_combo = ttk.Combobox(main_filters_frame, textvariable=self.state_filter, 
                                       values=["All"], state="readonly", width=15)
        self.state_combo.grid(row=row, column=3, sticky=tk.W, padx=(5, 10), pady=2)
        
        # Sub-State filter
        ttk.Label(main_filters_frame, text="Sub-State:").grid(row=row, column=4, sticky=tk.W, pady=2)
        self.sub_state_filter = tk.StringVar(value="All")
        self.sub_state_combo = ttk.Combobox(main_filters_frame, textvariable=self.sub_state_filter, 
                                           values=["All"], state="readonly", width=15)
        self.sub_state_combo.grid(row=row, column=5, sticky=tk.W, padx=(5, 0), pady=2)
        
        # Row 1: Date filters and Get Work Items button
        row = 1
        
        # Date Range filter with calendar functionality
        ttk.Label(main_filters_frame, text="Date Range:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.date_range_filter = tk.StringVar(value="All")
        self.date_range_combo = ttk.Combobox(main_filters_frame, textvariable=self.date_range_filter, 
                                            values=["All", "Last 7 days", "Last 30 days", "Last 3 months", 
                                                   "Last 6 months", "Last year", "This quarter", "Last quarter",
                                                   "This year", "Last year", "Custom range..."], 
                                            state="readonly", width=15)
        self.date_range_combo.bind('<<ComboboxSelected>>', lambda e: self.on_main_date_filter_change())
        self.date_range_combo.grid(row=row, column=1, sticky=tk.W, padx=(5, 10), pady=2)
        
        # Get Work Items button - moved to row 1 to save space
        get_work_items_button = ttk.Button(main_filters_frame, text="📋 Get Work Items", 
                                          command=self.get_team_work_items_from_related_tab)
        get_work_items_button.grid(row=row, column=2, padx=(0, 10), sticky=tk.W, pady=2)
        
        # Custom date range entry (hidden by default)
        self.main_custom_date_frame = ttk.Frame(main_filters_frame)
        self.main_custom_date_frame.grid(row=row, column=3, columnspan=2, sticky=tk.W, padx=(5, 10), pady=2)
        
        ttk.Label(self.main_custom_date_frame, text="From:").pack(side=tk.LEFT)
        self.main_date_from_var = tk.StringVar()
        self.main_date_from_entry = ttk.Entry(self.main_custom_date_frame, textvariable=self.main_date_from_var, width=12)
        self.main_date_from_entry.pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Label(self.main_custom_date_frame, text="To:").pack(side=tk.LEFT)
        self.main_date_to_var = tk.StringVar()
        self.main_date_to_entry = ttk.Entry(self.main_custom_date_frame, textvariable=self.main_date_to_var, width=12)
        self.main_date_to_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Calendar buttons
        self.main_cal_from_btn = ttk.Button(self.main_custom_date_frame, text="📅", width=3, 
                                          command=lambda: self.show_calendar(self.main_date_from_var))
        self.main_cal_from_btn.pack(side=tk.LEFT, padx=(5, 2))
        
        self.main_cal_to_btn = ttk.Button(self.main_custom_date_frame, text="📅", width=3, 
                                        command=lambda: self.show_calendar(self.main_date_to_var))
        self.main_cal_to_btn.pack(side=tk.LEFT, padx=(2, 0))
        
        # Initially hide custom date frame
        self.main_custom_date_frame.grid_remove()
        
        # Performance Settings button moved to Work Items Controls section
    
    def populate_enhanced_filters(self):
        """Populate filter options using multi-threaded API calls."""
        if not self.client:
            messagebox.showerror("Error", "Please connect to Azure DevOps first.")
            return
        
        project = self.project_var.get()
        team = self.team_selection_var.get() if hasattr(self, 'team_selection_var') else None
        
        if not project:
            messagebox.showerror("Error", "Please specify a project.")
            return
        
        # Show progress dialog
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Populating Filters")
        progress_window.geometry("400x150")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        progress_label = ttk.Label(progress_window, text="Populating filter options...")
        progress_label.pack(pady=20)
        
        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
        progress_bar.pack(pady=10, padx=20, fill=tk.X)
        progress_bar.start()
        
        status_label = ttk.Label(progress_window, text="This may take a few moments...")
        status_label.pack(pady=10)
        
        def populate_filters_async():
            try:
                print(f"🔄 Starting filter population for project: {project}, team: {team}")
                
                # Initialize enhanced filter manager if not already done
                if not self.enhanced_filter_manager:
                    print("📦 Initializing EnhancedFilterManager...")
                    from ado.enhanced_filters import EnhancedFilterManager
                    self.enhanced_filter_manager = EnhancedFilterManager(self.client)
                    print("✅ EnhancedFilterManager initialized")
                
                # Populate filters
                print("🔍 Populating filters...")
                self.filter_data = self.enhanced_filter_manager.prepopulate_filters_async(project, team)
                print(f"✅ Filter population completed. Got {len(self.filter_data)} filter categories")
                
                # Update UI in main thread
                print("🔄 Updating UI...")
                self.root.after(0, lambda: self._update_filter_combos())
                self.root.after(0, progress_window.destroy)
                print("✅ UI update completed")
                
            except Exception as e:
                error_msg = f"Error populating filters: {e}"
                print(f"❌ {error_msg}")
                logger.error(error_msg)
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to populate filters: {e}"))
                self.root.after(0, progress_window.destroy)
        
        # Start async operation
        threading.Thread(target=populate_filters_async, daemon=True).start()
    
    def auto_populate_enhanced_filters(self):
        """Auto-populate filter options using multi-threaded API calls without showing progress dialog."""
        if not self.client:
            print("⚠️ No ADO connection available for auto-populating filters.")
            return
        
        project = self.project_var.get()
        team = self.team_selection_var.get() if hasattr(self, 'team_selection_var') else None
        
        if not project:
            print("⚠️ No project specified for auto-populating filters.")
            return
        
        def populate_filters_async():
            try:
                print(f"🔄 Starting auto filter population for project: {project}, team: {team}")
                
                # Initialize enhanced filter manager if not already done
                if not self.enhanced_filter_manager:
                    print("📦 Initializing EnhancedFilterManager...")
                    from ado.enhanced_filters import EnhancedFilterManager
                    self.enhanced_filter_manager = EnhancedFilterManager(self.client)
                    print("✅ EnhancedFilterManager initialized")
                
                # Populate filters
                print("🔍 Auto-populating filters...")
                self.filter_data = self.enhanced_filter_manager.prepopulate_filters_async(project, team)
                print(f"✅ Auto filter population completed. Got {len(self.filter_data)} filter categories")
                
                # Update UI in main thread
                print("🔄 Updating UI...")
                self.root.after(0, lambda: self._update_filter_combos())
                print("✅ UI update completed")
                
            except Exception as e:
                error_msg = f"Error auto-populating filters: {e}"
                print(f"❌ {error_msg}")
                logger.error(error_msg)
                import traceback
                traceback.print_exc()
        
        # Start async operation in background thread
        threading.Thread(target=populate_filters_async, daemon=True).start()
    
    def _update_filter_combos(self):
        """Update filter combo boxes with populated data."""
        try:
            print(f"🔄 Updating filter combos with {len(self.filter_data)} filter categories")
            print(f"   Available filter data keys: {list(self.filter_data.keys())}")
            
            if not self.filter_data:
                print("⚠️ No filter data available to update combos")
                return
            
            # Update work item types
            if 'work_item_types' in self.filter_data and hasattr(self, 'work_item_type_combo'):
                types = ["All"] + self.filter_data['work_item_types']
                self.work_item_type_combo['values'] = types
                print(f"✅ Updated work item types: {len(types)-1} types")
            else:
                if 'work_item_types' not in self.filter_data:
                    print("⚠️ No work_item_types in filter data")
                if not hasattr(self, 'work_item_type_combo'):
                    print("⚠️ work_item_type_combo widget not found")
            
            # Update states
            if 'work_item_states' in self.filter_data and hasattr(self, 'state_combo'):
                states = ["All"] + self.filter_data['work_item_states']
                self.state_combo['values'] = states
                print(f"✅ Updated states: {len(states)-1} states")
            
            # Update sub-states
            if 'sub_states' in self.filter_data and hasattr(self, 'sub_state_combo'):
                sub_states = ["All"] + self.filter_data['sub_states']
                self.sub_state_combo['values'] = sub_states
                print(f"✅ Updated sub-states: {len(sub_states)-1} sub-states")
            
            # Update assigned users
            if 'assigned_users' in self.filter_data and hasattr(self, 'assigned_to_combo'):
                users = ["All"] + self.filter_data['assigned_users']
                self.assigned_to_combo['values'] = users
                print(f"✅ Updated assigned users: {len(users)-1} users")
            
            # Update iteration paths
            if 'iteration_paths' in self.filter_data and hasattr(self, 'iteration_path_combo'):
                iterations = ["All"] + self.filter_data['iteration_paths']
                self.iteration_path_combo['values'] = iterations
                print(f"✅ Updated iteration paths: {len(iterations)-1} iterations")
            
            # Update area paths
            if 'area_paths' in self.filter_data and hasattr(self, 'area_path_combo'):
                areas = ["All"] + self.filter_data['area_paths']
                self.area_path_combo['values'] = areas
                print(f"✅ Updated area paths: {len(areas)-1} areas")
            
            # Update tags
            if 'tags' in self.filter_data and hasattr(self, 'tags_combo'):
                tags = ["All"] + self.filter_data['tags']
                self.tags_combo['values'] = tags
                print(f"✅ Updated tags: {len(tags)-1} tags")
            
            # Update priorities
            if 'priorities' in self.filter_data and hasattr(self, 'priority_combo'):
                priorities = ["All"] + self.filter_data['priorities']
                self.priority_combo['values'] = priorities
                print(f"✅ Updated priorities: {len(priorities)-1} priorities")
            
            # Update created by users
            if 'created_by_users' in self.filter_data and hasattr(self, 'created_by_combo'):
                users = ["All"] + self.filter_data['created_by_users']
                self.created_by_combo['values'] = users
                print(f"✅ Updated created by users: {len(users)-1} users")
            
            # Update changed by users
            if 'changed_by_users' in self.filter_data and hasattr(self, 'changed_by_combo'):
                users = ["All"] + self.filter_data['changed_by_users']
                self.changed_by_combo['values'] = users
                print(f"✅ Updated changed by users: {len(users)-1} users")
            
            # Update date ranges
            if 'date_ranges' in self.filter_data and hasattr(self, 'date_range_combo'):
                date_ranges = ["All"] + self.filter_data['date_ranges']
                self.date_range_combo['values'] = date_ranges
                print(f"✅ Updated date ranges: {len(date_ranges)-1} ranges")
            
            self.work_items_status_var.set("Filters populated successfully")
            print("🎉 All enhanced filters populated successfully!")
            
        except Exception as e:
            logger.error(f"Error updating filter combos: {e}")
            print(f"❌ Error updating filter combos: {e}")
            messagebox.showerror("Error", f"Failed to update filter options: {e}")
    
    def apply_enhanced_filters(self):
        """Apply enhanced filters to current work items."""
        if not self.current_work_items:
            messagebox.showwarning("Warning", "No work items loaded. Please get work items first.")
            return
        
        if not self.enhanced_filter_manager:
            messagebox.showerror("Error", "Enhanced filter manager not initialized.")
            return
        
        # Collect current filter values
        filters = {
            'work_item_type': self.work_item_type_filter.get(),
            'state': self.state_filter.get(),
            'sub_state': self.sub_state_filter.get(),
            'date_range': self.date_range_filter.get()
        }
        
        # Remove "All" values
        filters = {k: v for k, v in filters.items() if v != "All"}
        
        # Apply filters
        filtered_items = self.enhanced_filter_manager.apply_filters_to_work_items(
            self.current_work_items, filters
        )
        
        # Update display
        self.display_work_items(filtered_items)
        self.work_items_status_var.set(f"Applied filters: {len(self.current_work_items)} -> {len(filtered_items)} items")
    
    def clear_enhanced_filters(self):
        """Clear all enhanced filters."""
        self.work_item_type_filter.set("All")
        self.state_filter.set("All")
        self.sub_state_filter.set("All")
        self.date_range_filter.set("All")
        
        # Refresh display with original work items
        if self.current_work_items:
            self.display_work_items(self.current_work_items)
            self.work_items_status_var.set(f"Cleared filters: showing {len(self.current_work_items)} items")
    
    def refresh_work_items(self):
        """Refresh the work items display."""
        if self.current_work_items:
            self.display_work_items(self.current_work_items)
            self.work_items_status_var.set(f"Refreshed {len(self.current_work_items)} work items")
        else:
            self.work_items_status_var.set("No work items to refresh")
    
    def clear_work_items_display(self):
        """Clear the work items display."""
        # Clear summary view
        self.work_items_summary.configure(state="normal")
        self.work_items_summary.delete(1.0, tk.END)
        self.work_items_summary.configure(state="disabled")
        
        # Clear detailed view
        self.work_items_detailed.configure(state="normal")
        self.work_items_detailed.delete(1.0, tk.END)
        self.work_items_detailed.configure(state="disabled")
        
        # Clear table view
        for item in self.work_items_tree.get_children():
            self.work_items_tree.delete(item)
        
        # Clear current work items
        self.current_work_items = []
        self.work_items_status_var.set("Work items display cleared")
    
    def export_work_items(self):
        """Export work items to a text file."""
        if not self.current_work_items:
            messagebox.showwarning("No Data", "No work items to export.")
            return
        
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Export Work Items"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("Azure DevOps Work Items Export\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Project: {self.team_project_var.get().strip()}\n")
                    f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total Items: {len(self.current_work_items)}\n\n")
                    
                    for i, item in enumerate(self.current_work_items, 1):
                        f.write(f"{i}. Work Item ID: {item.id}\n")
                        f.write(f"   Title: {item.fields.get('System.Title', 'No Title')}\n")
                        f.write(f"   Type: {item.fields.get('System.WorkItemType', 'Unknown')}\n")
                        f.write(f"   State: {item.fields.get('System.State', 'Unknown')}\n")
                        f.write(f"   Created By: {item.fields.get('System.CreatedBy', 'Unknown')}\n")
                        assigned_to_raw = item.fields.get('System.AssignedTo', 'Unassigned')
                        assigned_to = self.get_assigned_to_display_name(assigned_to_raw)
                        f.write(f"   Assigned To: {assigned_to}\n")
                        
                        if 'System.Description' in item.fields and item.fields['System.Description']:
                            desc = item.fields['System.Description']
                            if '<' in desc and '>' in desc:
                                import re
                                desc = re.sub('<[^<]+?>', '', desc)
                                desc = re.sub('\s+', ' ', desc).strip()
                            f.write(f"   Description: {desc}\n")
                        
                        if 'System.Tags' in item.fields and item.fields['System.Tags']:
                            f.write(f"   Tags: {item.fields['System.Tags']}\n")
                        
                        f.write("\n")
                
                messagebox.showinfo("Export Successful", f"Work items exported to {filename}")
                self.work_items_status_var.set(f"Exported {len(self.current_work_items)} work items to {filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export work items: {str(e)}")
            self.work_items_status_var.set("Export failed")
    
    def display_work_items(self, work_items):
        """Display work items in all three views."""
        self.current_work_items = work_items
        
        # Update status
        self.work_items_status_var.set(f"Displaying {len(work_items)} work items")
        
        # Update filter count (showing all items initially)
        self.update_filter_count(len(work_items), len(work_items))
        
        # Auto-populate filters in background
        self.populate_table_filters()
        
        # Display in summary view
        self.display_summary_view(work_items)
        
        # Display in detailed view
        self.display_detailed_view(work_items)
        
        # Display in table view
        self.display_table_view(work_items)
    
    def display_summary_view(self, work_items):
        """Display work items in summary view."""
        self.work_items_summary.configure(state="normal")
        self.work_items_summary.delete(1.0, tk.END)
        
        if not work_items:
            self.work_items_summary.insert(tk.END, "No work items to display.")
            self.work_items_summary.configure(state="disabled")
            return
        
        # Display summary
        self.work_items_summary.insert(tk.END, f"Work Items Summary ({len(work_items)} items)\n")
        self.work_items_summary.insert(tk.END, "=" * 60 + "\n\n")
        
        # Summary table
        self.work_items_summary.insert(tk.END, f"{'ID':<8} {'Type':<15} {'State':<12} {'Title':<50} {'Area Path'}\n")
        self.work_items_summary.insert(tk.END, "-" * 120 + "\n")
        
        for item in work_items:
            item_id = item.id
            item_type = item.fields.get('System.WorkItemType', 'Unknown')
            item_state = item.fields.get('System.State', 'Unknown')
            item_title = item.fields.get('System.Title', 'No Title')
            area_path = item.fields.get('System.AreaPath', 'Unknown')
            
            # Keep title full length for better readability
            
            self.work_items_summary.insert(tk.END, f"{item_id:<8} {item_type:<15} {item_state:<12} {item_title:<80} {area_path}\n")
        
        self.work_items_summary.configure(state="disabled")
    
    def display_detailed_view(self, work_items):
        """Display work items in detailed view."""
        self.work_items_detailed.configure(state="normal")
        self.work_items_detailed.delete(1.0, tk.END)
        
        if not work_items:
            self.work_items_detailed.insert(tk.END, "No work items to display.")
            self.work_items_detailed.configure(state="disabled")
            return
        
        # Display detailed information
        for i, item in enumerate(work_items, 1):
            self.work_items_detailed.insert(tk.END, f"{i}. Work Item ID: {item.id}\n")
            self.work_items_detailed.insert(tk.END, f"   Title: {item.fields.get('System.Title', 'No Title')}\n")
            self.work_items_detailed.insert(tk.END, f"   Type: {item.fields.get('System.WorkItemType', 'Unknown')}\n")
            self.work_items_detailed.insert(tk.END, f"   State: {item.fields.get('System.State', 'Unknown')}\n")
            self.work_items_detailed.insert(tk.END, f"   Created By: {item.fields.get('System.CreatedBy', 'Unknown')}\n")
            assigned_to_raw = item.fields.get('System.AssignedTo', 'Unassigned')
            assigned_to = self.get_assigned_to_display_name(assigned_to_raw)
            self.work_items_detailed.insert(tk.END, f"   Assigned To: {assigned_to}\n")
            
            if 'System.Description' in item.fields and item.fields['System.Description']:
                desc = item.fields['System.Description']
                if '<' in desc and '>' in desc:
                    import re
                    desc = re.sub('<[^<]+?>', '', desc)
                    desc = re.sub('\s+', ' ', desc).strip()
                self.work_items_detailed.insert(tk.END, f"   Description: {desc[:200]}{'...' if len(desc) > 200 else ''}\n")
            
            if 'System.Tags' in item.fields and item.fields['System.Tags']:
                self.work_items_detailed.insert(tk.END, f"   Tags: {item.fields['System.Tags']}\n")
            
            if 'System.CreatedDate' in item.fields:
                created_date = item.fields['System.CreatedDate']
                if hasattr(created_date, 'strftime'):
                    self.work_items_detailed.insert(tk.END, f"   Created: {created_date.strftime('%Y-%m-%d %H:%M:%S')}\n")
                else:
                    self.work_items_detailed.insert(tk.END, f"   Created: {created_date}\n")
            
            self.work_items_detailed.insert(tk.END, "\n")
        
        self.work_items_detailed.configure(state="disabled")
    
    def get_assigned_to_display_name(self, assigned_to_field):
        """Extract the display name from the assigned_to field."""
        if not assigned_to_field or assigned_to_field == 'Unassigned':
            return 'Unassigned'
        
        # If it's a dictionary with displayName, extract it
        if isinstance(assigned_to_field, dict):
            if 'displayName' in assigned_to_field:
                return assigned_to_field['displayName']
            elif 'uniqueName' in assigned_to_field:
                return assigned_to_field['uniqueName']
            elif 'name' in assigned_to_field:
                return assigned_to_field['name']
            else:
                # Fallback: prioritize email-like fields, then other string values
                email_value = None
                other_string_values = []
                
                # First pass: collect all string values
                for key, value in assigned_to_field.items():
                    if isinstance(value, str):
                        if 'email' in key.lower() or 'mail' in key.lower():
                            email_value = value
                        else:
                            other_string_values.append(value)
                
                # Return email if found, otherwise first other string value
                if email_value:
                    return email_value
                elif other_string_values:
                    # For the test case, we want to prioritize non-id fields
                    for value in other_string_values:
                        if not value.isdigit():  # Skip pure numeric IDs
                            return value
                    # If all are numeric, return the first one
                    return other_string_values[0]
                else:
                    # If no string values found, return a summary
                    return f"User ({len(assigned_to_field)} fields)"
        
        # If it's already a string, return as is
        return str(assigned_to_field)

    def sort_treeview(self, col):
        """Sort treeview by column."""
        try:
            # Determine if we're sorting the same column
            if self.sort_column == col:
                self.sort_reverse = not self.sort_reverse
            else:
                self.sort_reverse = False
                self.sort_column = col
            
            # Get all items from the treeview
            items = [(self.work_items_tree.set(child, col), child) for child in self.work_items_tree.get_children('')]
            
            # Sort based on column type
            if col == 'ID':
                # Sort numerically
                items.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=self.sort_reverse)
            elif col == 'Created Date':
                # Sort by date
                items.sort(key=lambda x: x[0], reverse=self.sort_reverse)
            else:
                # Sort alphabetically
                items.sort(key=lambda x: x[0].lower(), reverse=self.sort_reverse)
            
            # Rearrange items in treeview
            for index, (val, child) in enumerate(items):
                self.work_items_tree.move(child, '', index)
            
            # Update header to show sort direction
            self.update_sort_header(col)
            
        except Exception as e:
            print(f"Error sorting treeview: {e}")
    
    def update_sort_header(self, col):
        """Update column header to show sort direction."""
        try:
            # Get current header text
            current_text = self.work_items_tree.heading(col, 'text')
            
            # Remove existing sort indicators
            if current_text.endswith(' ↑') or current_text.endswith(' ↓'):
                current_text = current_text[:-2]
            
            # Add sort indicator
            if self.sort_column == col:
                if self.sort_reverse:
                    current_text += ' ↓'
                else:
                    current_text += ' ↑'
            
            # Update header
            self.work_items_tree.heading(col, text=current_text)
            
        except Exception as e:
            print(f"Error updating sort header: {e}")
    
    def create_filter_interface(self, parent_frame):
        """Create enhanced filter interface above the table."""
        # Create main filter frame
        self.filter_frame = ttk.LabelFrame(parent_frame, text="Filters", padding="5")
        self.filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Create header frame with toggle button
        header_frame = ttk.Frame(self.filter_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Toggle button to expand/collapse filters
        self.filter_toggle_var = tk.BooleanVar(value=False)  # Start minimized
        self.filter_toggle_btn = ttk.Button(
            header_frame, 
            text="🔽 Show Filters", 
            command=self.toggle_filters,
            width=15
        )
        self.filter_toggle_btn.pack(side=tk.LEFT)
        
        # Quick filter summary label
        self.filter_summary_label = ttk.Label(header_frame, text="No filters applied", foreground="gray")
        self.filter_summary_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Filter count display label
        self.filter_count_label = ttk.Label(header_frame, text="", foreground="blue", font=("TkDefaultFont", 9, "bold"))
        self.filter_count_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Create main filter controls frame (initially hidden)
        self.main_filters_frame = ttk.Frame(self.filter_frame)
        # Don't pack initially - will be shown/hidden by toggle
        
        # Create the enhanced filter interface
        self.create_enhanced_table_filters(self.main_filters_frame)
        
        # Initially hide the filters
        self.main_filters_frame.pack_forget()
    
    def toggle_filters(self):
        """Toggle the visibility of the filter section."""
        if self.filter_toggle_var.get():
            # Hide filters
            self.main_filters_frame.pack_forget()
            self.filter_toggle_btn.configure(text="🔽 Show Filters")
            self.filter_toggle_var.set(False)
        else:
            # Show filters
            self.main_filters_frame.pack(fill=tk.X, pady=(5, 0))
            self.filter_toggle_btn.configure(text="🔼 Hide Filters")
            self.filter_toggle_var.set(True)
    
    def update_filter_summary(self):
        """Update the filter summary label to show active filters."""
        active_filters = []
        
        # Check each filter for non-default values
        if self.title_filter.get().strip():
            active_filters.append(f"Title: '{self.title_filter.get()[:20]}...'")
        
        if self.assigned_to_filter.get() != "All":
            active_filters.append(f"Assigned: {self.assigned_to_filter.get()}")
        
        if self.priority_filter.get() != "All":
            active_filters.append(f"Priority: {self.priority_filter.get()}")
        
        if self.created_date_filter.get() != "All":
            active_filters.append(f"Date: {self.created_date_filter.get()}")
        
        if self.tags_filter.get() != "All":
            active_filters.append(f"Tags: {self.tags_filter.get()}")
        
        if self.area_path_filter.get() != "All":
            active_filters.append(f"Area: {self.area_path_filter.get()}")
        
        if self.iteration_path_filter.get() != "All":
            active_filters.append(f"Iteration: {self.iteration_path_filter.get()}")
        
        if self.created_by_filter.get() != "All":
            active_filters.append(f"Created By: {self.created_by_filter.get()}")
        
        if active_filters:
            summary_text = " | ".join(active_filters[:3])  # Show max 3 filters
            if len(active_filters) > 3:
                summary_text += f" (+{len(active_filters) - 3} more)"
            self.filter_summary_label.configure(text=summary_text, foreground="blue")
        else:
            self.filter_summary_label.configure(text="No filters applied", foreground="gray")
    
    def update_filter_count(self, filtered_count=None, total_count=None):
        """Update the filter count display showing filtered vs total items."""
        try:
            # Get counts if not provided
            if filtered_count is None:
                if hasattr(self, 'work_items_tree') and self.work_items_tree:
                    filtered_count = len(self.work_items_tree.get_children())
                else:
                    filtered_count = 0
            
            if total_count is None:
                if hasattr(self, 'current_work_items') and self.current_work_items:
                    total_count = len(self.current_work_items)
                else:
                    total_count = 0
            
            # Update the count display
            if total_count > 0:
                if filtered_count == total_count:
                    # No filters applied or all items match
                    count_text = f"Showing {filtered_count:,} of {total_count:,} items"
                    self.filter_count_label.configure(text=count_text, foreground="green")
                else:
                    # Some items filtered out
                    count_text = f"Showing {filtered_count:,} of {total_count:,} items"
                    self.filter_count_label.configure(text=count_text, foreground="blue")
            else:
                # No items available
                self.filter_count_label.configure(text="No items available", foreground="gray")
                
        except Exception as e:
            print(f"Error updating filter count: {e}")
            self.filter_count_label.configure(text="Count unavailable", foreground="red")
    
    def create_enhanced_table_filters(self, parent_frame):
        """Create enhanced filter interface with better organized layout."""
        # Configure grid weights for better distribution
        for i in range(6):  # 6 columns for better distribution
            parent_frame.columnconfigure(i, weight=1)
        
        # Row 0: Title/Description and Assigned To
        row = 0
        
        # Title/Description filter
        ttk.Label(parent_frame, text="Title/Description:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.title_filter = tk.StringVar()
        self.title_entry = ttk.Entry(parent_frame, textvariable=self.title_filter, width=30)
        self.title_entry.bind('<KeyRelease>', lambda e: self.apply_filters())
        self.title_entry.grid(row=row, column=1, columnspan=2, sticky=tk.W+tk.E, padx=(5, 10), pady=2)
        
        # Assigned To filter
        ttk.Label(parent_frame, text="Assigned To:").grid(row=row, column=3, sticky=tk.W, pady=2)
        self.assigned_to_filter = tk.StringVar(value="All")
        self.assigned_to_combo = ttk.Combobox(parent_frame, textvariable=self.assigned_to_filter, 
                                             values=["All"], state="readonly", width=20)
        self.assigned_to_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.assigned_to_combo.grid(row=row, column=4, columnspan=2, sticky=tk.W+tk.E, padx=(5, 0), pady=2)
        
        # Row 1: Created Date and Priority
        row = 1
        
        # Created Date filter
        ttk.Label(parent_frame, text="Created Date:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.created_date_filter = tk.StringVar(value="All")
        self.created_date_combo = ttk.Combobox(parent_frame, textvariable=self.created_date_filter, 
                                              values=["All", "Last 7 days", "Last 30 days", "Last 3 months", 
                                                     "Last 6 months", "Last year", "This quarter", "Last quarter",
                                                     "This year", "Last year", "Custom range..."], 
                                              state="readonly", width=18)
        self.created_date_combo.bind('<<ComboboxSelected>>', lambda e: self.on_date_filter_change())
        self.created_date_combo.grid(row=row, column=1, sticky=tk.W+tk.E, padx=(5, 10), pady=2)
        
        # Custom date range entry (hidden by default)
        self.custom_date_frame = ttk.Frame(parent_frame)
        self.custom_date_frame.grid(row=row, column=2, columnspan=2, sticky=tk.W, padx=(5, 10), pady=2)
        
        ttk.Label(self.custom_date_frame, text="From:").pack(side=tk.LEFT)
        self.date_from_var = tk.StringVar()
        self.date_from_entry = ttk.Entry(self.custom_date_frame, textvariable=self.date_from_var, width=12)
        self.date_from_entry.pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Label(self.custom_date_frame, text="To:").pack(side=tk.LEFT)
        self.date_to_var = tk.StringVar()
        self.date_to_entry = ttk.Entry(self.custom_date_frame, textvariable=self.date_to_var, width=12)
        self.date_to_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Calendar buttons
        self.cal_from_btn = ttk.Button(self.custom_date_frame, text="📅", width=3, 
                                      command=lambda: self.show_calendar(self.date_from_var))
        self.cal_from_btn.pack(side=tk.LEFT, padx=(5, 2))
        
        self.cal_to_btn = ttk.Button(self.custom_date_frame, text="📅", width=3, 
                                    command=lambda: self.show_calendar(self.date_to_var))
        self.cal_to_btn.pack(side=tk.LEFT, padx=(2, 0))
        
        # Initially hide custom date frame
        self.custom_date_frame.grid_remove()
        
        # Priority filter
        ttk.Label(parent_frame, text="Priority:").grid(row=row, column=4, sticky=tk.W, pady=2)
        self.priority_filter = tk.StringVar(value="All")
        self.priority_combo = ttk.Combobox(parent_frame, textvariable=self.priority_filter, 
                                          values=["All"], state="readonly", width=15)
        self.priority_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.priority_combo.grid(row=row, column=5, sticky=tk.W+tk.E, padx=(5, 0), pady=2)
        
        # Row 2: Area Path and Created By
        row = 2
        
        # Area Path filter
        ttk.Label(parent_frame, text="Area Path:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.area_path_filter = tk.StringVar(value="All")
        self.area_path_combo = ttk.Combobox(parent_frame, textvariable=self.area_path_filter, 
                                           values=["All"], state="readonly", width=20)
        self.area_path_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.area_path_combo.grid(row=row, column=1, columnspan=2, sticky=tk.W+tk.E, padx=(5, 10), pady=2)
        
        # Created By filter
        ttk.Label(parent_frame, text="Created By:").grid(row=row, column=3, sticky=tk.W, pady=2)
        self.created_by_filter = tk.StringVar(value="All")
        self.created_by_combo = ttk.Combobox(parent_frame, textvariable=self.created_by_filter, 
                                            values=["All"], state="readonly", width=20)
        self.created_by_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.created_by_combo.grid(row=row, column=4, columnspan=2, sticky=tk.W+tk.E, padx=(5, 0), pady=2)
        
        # Row 3: Tags and Iteration Path
        row = 3
        
        # Tags filter
        ttk.Label(parent_frame, text="Tags:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.tags_filter = tk.StringVar(value="All")
        self.tags_combo = ttk.Combobox(parent_frame, textvariable=self.tags_filter, 
                                      values=["All"], state="readonly", width=20)
        self.tags_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.tags_combo.grid(row=row, column=1, columnspan=2, sticky=tk.W+tk.E, padx=(5, 10), pady=2)
        
        # Iteration Path filter
        ttk.Label(parent_frame, text="Iteration Path:").grid(row=row, column=3, sticky=tk.W, pady=2)
        self.iteration_path_filter = tk.StringVar(value="All")
        self.iteration_path_combo = ttk.Combobox(parent_frame, textvariable=self.iteration_path_filter, 
                                                values=["All"], state="readonly", width=20)
        self.iteration_path_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_filters())
        self.iteration_path_combo.grid(row=row, column=4, columnspan=2, sticky=tk.W+tk.E, padx=(5, 0), pady=2)
        
        # Row 4: Action buttons
        row = 4
        
        # Clear filters button
        clear_button = ttk.Button(parent_frame, text="🗑️ Clear Filters", command=self.clear_filters)
        clear_button.grid(row=row, column=0, padx=(0, 10), sticky=tk.W, pady=5)
        

        
        # Initialize filter variables dictionary for backward compatibility
        self.filter_vars = {
            'Title': self.title_filter,
            'Assigned To': self.assigned_to_filter,
            'Priority': self.priority_filter,
            'Created Date': self.created_date_filter,
            'Tags': self.tags_filter,
            'Area Path': self.area_path_filter,
            'Iteration Path': self.iteration_path_filter,
            'Created By': self.created_by_filter
        }
        
        # Initialize filter widgets dictionary
        self.filter_widgets = {
            'Title': self.title_entry,
            'Assigned To': self.assigned_to_combo,
            'Priority': self.priority_combo,
            'Created Date': self.created_date_combo,
            'Tags': self.tags_combo,
            'Area Path': self.area_path_combo,
            'Iteration Path': self.iteration_path_combo,
            'Created By': self.created_by_combo
        }
    
    def create_refine_filter_interface(self, parent_frame):
        """Create enhanced filter interface for the refine related work items tab."""
        # Create main filter frame
        self.refine_filter_frame = ttk.LabelFrame(parent_frame, text="Filters", padding="5")
        self.refine_filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Create header frame with toggle button
        refine_header_frame = ttk.Frame(self.refine_filter_frame)
        refine_header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Toggle button to expand/collapse filters
        self.refine_filter_toggle_var = tk.BooleanVar(value=False)  # Start minimized
        self.refine_filter_toggle_btn = ttk.Button(
            refine_header_frame, 
            text="🔽 Show Filters", 
            command=self.toggle_refine_filters,
            width=15
        )
        self.refine_filter_toggle_btn.pack(side=tk.LEFT)
        
        # Quick filter summary label
        self.refine_filter_summary_label = ttk.Label(refine_header_frame, text="No filters applied", foreground="gray")
        self.refine_filter_summary_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Filter count display label
        self.refine_filter_count_label = ttk.Label(refine_header_frame, text="", foreground="blue", font=("TkDefaultFont", 9, "bold"))
        self.refine_filter_count_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Create main filter controls frame (initially hidden)
        self.refine_main_filters_frame = ttk.Frame(self.refine_filter_frame)
        # Don't pack initially - will be shown/hidden by toggle
        
        # Create the enhanced filter interface for refine tab
        self.create_enhanced_refine_table_filters(self.refine_main_filters_frame)
        
        # Initially hide the filters
        self.refine_main_filters_frame.pack_forget()
    
    def create_enhanced_refine_table_filters(self, parent_frame):
        """Create enhanced filter interface for refine related work items with better organized layout."""
        # Configure grid weights for better distribution
        for i in range(6):  # 6 columns for better distribution
            parent_frame.columnconfigure(i, weight=1)
        
        # Row 0: Title/Description and Assigned To
        row = 0
        
        # Title/Description filter
        ttk.Label(parent_frame, text="Title/Description:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.refine_title_filter = tk.StringVar()
        self.refine_title_entry = ttk.Entry(parent_frame, textvariable=self.refine_title_filter, width=30)
        self.refine_title_entry.bind('<KeyRelease>', lambda e: self.apply_refine_filters())
        self.refine_title_entry.grid(row=row, column=1, columnspan=2, sticky=tk.W+tk.E, padx=(5, 10), pady=2)
        
        # Assigned To filter
        ttk.Label(parent_frame, text="Assigned To:").grid(row=row, column=3, sticky=tk.W, pady=2)
        self.refine_assigned_to_filter = tk.StringVar(value="All")
        self.refine_assigned_to_combo = ttk.Combobox(parent_frame, textvariable=self.refine_assigned_to_filter, 
                                             values=["All"], state="readonly", width=20)
        self.refine_assigned_to_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_refine_filters())
        self.refine_assigned_to_combo.grid(row=row, column=4, columnspan=2, sticky=tk.W+tk.E, padx=(5, 0), pady=2)
        
        # Row 1: Created Date and Priority
        row = 1
        
        # Created Date filter
        ttk.Label(parent_frame, text="Created Date:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.refine_created_date_filter = tk.StringVar(value="All")
        self.refine_created_date_combo = ttk.Combobox(parent_frame, textvariable=self.refine_created_date_filter, 
                                              values=["All", "Last 7 days", "Last 30 days", "Last 3 months", 
                                                     "Last 6 months", "Last year", "This quarter", "Last quarter",
                                                     "This year", "Last year", "Custom range..."], 
                                              state="readonly", width=18)
        self.refine_created_date_combo.bind('<<ComboboxSelected>>', lambda e: self.on_refine_date_filter_change())
        self.refine_created_date_combo.grid(row=row, column=1, sticky=tk.W+tk.E, padx=(5, 10), pady=2)
        
        # Custom date range entry (hidden by default)
        self.refine_custom_date_frame = ttk.Frame(parent_frame)
        self.refine_custom_date_frame.grid(row=row, column=2, columnspan=2, sticky=tk.W, padx=(5, 10), pady=2)
        
        ttk.Label(self.refine_custom_date_frame, text="From:").pack(side=tk.LEFT)
        self.refine_date_from_var = tk.StringVar()
        self.refine_date_from_entry = ttk.Entry(self.refine_custom_date_frame, textvariable=self.refine_date_from_var, width=12)
        self.refine_date_from_entry.pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Label(self.refine_custom_date_frame, text="To:").pack(side=tk.LEFT)
        self.refine_date_to_var = tk.StringVar()
        self.refine_date_to_entry = ttk.Entry(self.refine_custom_date_frame, textvariable=self.refine_date_to_var, width=12)
        self.refine_date_to_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Calendar buttons
        self.refine_cal_from_btn = ttk.Button(self.refine_custom_date_frame, text="📅", width=3, 
                                      command=lambda: self.show_calendar(self.refine_date_from_var))
        self.refine_cal_from_btn.pack(side=tk.LEFT, padx=(5, 2))
        
        self.refine_cal_to_btn = ttk.Button(self.refine_custom_date_frame, text="📅", width=3, 
                                    command=lambda: self.show_calendar(self.refine_date_to_var))
        self.refine_cal_to_btn.pack(side=tk.LEFT, padx=(2, 0))
        
        # Initially hide custom date frame
        self.refine_custom_date_frame.grid_remove()
        
        # Priority filter
        ttk.Label(parent_frame, text="Priority:").grid(row=row, column=4, sticky=tk.W, pady=2)
        self.refine_priority_filter = tk.StringVar(value="All")
        self.refine_priority_combo = ttk.Combobox(parent_frame, textvariable=self.refine_priority_filter, 
                                          values=["All"], state="readonly", width=15)
        self.refine_priority_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_refine_filters())
        self.refine_priority_combo.grid(row=row, column=5, sticky=tk.W+tk.E, padx=(5, 0), pady=2)
        
        # Row 2: Area Path and Created By
        row = 2
        
        # Area Path filter
        ttk.Label(parent_frame, text="Area Path:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.refine_area_path_filter = tk.StringVar(value="All")
        self.refine_area_path_combo = ttk.Combobox(parent_frame, textvariable=self.refine_area_path_filter, 
                                           values=["All"], state="readonly", width=20)
        self.refine_area_path_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_refine_filters())
        self.refine_area_path_combo.grid(row=row, column=1, columnspan=2, sticky=tk.W+tk.E, padx=(5, 10), pady=2)
        
        # Created By filter
        ttk.Label(parent_frame, text="Created By:").grid(row=row, column=3, sticky=tk.W, pady=2)
        self.refine_created_by_filter = tk.StringVar(value="All")
        self.refine_created_by_combo = ttk.Combobox(parent_frame, textvariable=self.refine_created_by_filter, 
                                            values=["All"], state="readonly", width=20)
        self.refine_created_by_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_refine_filters())
        self.refine_created_by_combo.grid(row=row, column=4, columnspan=2, sticky=tk.W+tk.E, padx=(5, 0), pady=2)
        
        # Row 3: Tags and Iteration Path
        row = 3
        
        # Tags filter
        ttk.Label(parent_frame, text="Tags:").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.refine_tags_filter = tk.StringVar(value="All")
        self.refine_tags_combo = ttk.Combobox(parent_frame, textvariable=self.refine_tags_filter, 
                                      values=["All"], state="readonly", width=20)
        self.refine_tags_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_refine_filters())
        self.refine_tags_combo.grid(row=row, column=1, columnspan=2, sticky=tk.W+tk.E, padx=(5, 10), pady=2)
        
        # Iteration Path filter
        ttk.Label(parent_frame, text="Iteration Path:").grid(row=row, column=3, sticky=tk.W, pady=2)
        self.refine_iteration_path_filter = tk.StringVar(value="All")
        self.refine_iteration_path_combo = ttk.Combobox(parent_frame, textvariable=self.refine_iteration_path_filter, 
                                                values=["All"], state="readonly", width=20)
        self.refine_iteration_path_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_refine_filters())
        self.refine_iteration_path_combo.grid(row=row, column=4, columnspan=2, sticky=tk.W+tk.E, padx=(5, 0), pady=2)
        
        # Row 4: Action buttons
        row = 4
        
        # Clear filters button
        clear_button = ttk.Button(parent_frame, text="🗑️ Clear Filters", command=self.clear_refine_filters)
        clear_button.grid(row=row, column=0, padx=(0, 10), sticky=tk.W, pady=5)
        
        # Initialize refine filter variables dictionary
        self.refine_filter_vars = {
            'Title': self.refine_title_filter,
            'Assigned To': self.refine_assigned_to_filter,
            'Priority': self.refine_priority_filter,
            'Created Date': self.refine_created_date_filter,
            'Tags': self.refine_tags_filter,
            'Area Path': self.refine_area_path_filter,
            'Iteration Path': self.refine_iteration_path_filter,
            'Created By': self.refine_created_by_filter
        }
        
        # Initialize refine filter widgets dictionary
        self.refine_filter_widgets = {
            'Title': self.refine_title_entry,
            'Assigned To': self.refine_assigned_to_combo,
            'Priority': self.refine_priority_combo,
            'Created Date': self.refine_created_date_combo,
            'Tags': self.refine_tags_combo,
            'Area Path': self.refine_area_path_combo,
            'Iteration Path': self.refine_iteration_path_combo,
            'Created By': self.refine_created_by_combo
        }
    
    def toggle_refine_filters(self):
        """Toggle the visibility of the refine filter section."""
        if self.refine_filter_toggle_var.get():
            # Hide filters
            self.refine_main_filters_frame.pack_forget()
            self.refine_filter_toggle_btn.configure(text="🔽 Show Filters")
            self.refine_filter_toggle_var.set(False)
        else:
            # Show filters
            self.refine_main_filters_frame.pack(fill=tk.X, pady=(5, 0))
            self.refine_filter_toggle_btn.configure(text="🔼 Hide Filters")
            self.refine_filter_toggle_var.set(True)
    
    def apply_refine_filters(self):
        """Apply filters to the refine related work items table view."""
        try:
            if not hasattr(self, 'current_related_items') or not self.current_related_items:
                return
            
            # Filter the related items based on current filter values
            filtered_items = []
            for item in self.current_related_items:
                if self.refine_item_matches_filters(item):
                    filtered_items.append(item)
            
            # Update the tree view with filtered items
            self.display_refine_filtered_items(filtered_items)
            
            # Update filter count
            self.update_refine_filter_count(len(filtered_items), len(self.current_related_items))
            
            # Update filter summary
            self.update_refine_filter_summary()
            
        except Exception as e:
            print(f"Error applying refine filters: {e}")
    
    def refine_item_matches_filters(self, item):
        """Check if a refine work item matches the current filters."""
        try:
            # Check title filter
            title_text = self.refine_title_filter.get().strip().lower()
            if title_text and title_text not in item.get('title', '').lower():
                return False
            
            # Check assigned to filter
            assigned_to = self.refine_assigned_to_filter.get()
            if assigned_to != "All" and assigned_to != item.get('assigned_to', ''):
                return False
            
            # Check priority filter
            priority = self.refine_priority_filter.get()
            if priority != "All" and priority != item.get('priority', ''):
                return False
            
            # Check created date filter
            if not self.refine_matches_date_filter(item, self.refine_created_date_filter.get()):
                return False
            
            # Check area path filter
            area_path = self.refine_area_path_filter.get()
            if area_path != "All" and area_path != item.get('area_path', ''):
                return False
            
            # Check created by filter
            created_by = self.refine_created_by_filter.get()
            if created_by != "All" and created_by != item.get('created_by', ''):
                return False
            
            # Check tags filter
            tags = self.refine_tags_filter.get()
            if tags != "All" and tags not in item.get('tags', ''):
                return False
            
            # Check iteration path filter
            iteration_path = self.refine_iteration_path_filter.get()
            if iteration_path != "All" and iteration_path != item.get('iteration_path', ''):
                return False
            
            return True
            
        except Exception as e:
            print(f"Error checking refine item filters: {e}")
            return True
    
    def refine_matches_date_filter(self, item, filter_value):
        """Check if refine item matches date filter criteria."""
        try:
            if not filter_value or filter_value == "All":
                return True
            
            if filter_value == "Custom range...":
                # Check custom date range
                from_date = self.refine_date_from_var.get().strip()
                to_date = self.refine_date_to_var.get().strip()
                
                if not from_date and not to_date:
                    return True
                
                item_date = item.get('created_date', '')
                if not item_date:
                    return True
                
                # Parse dates and compare
                from datetime import datetime
                try:
                    item_dt = datetime.strptime(item_date, '%Y-%m-%d')
                    
                    if from_date:
                        from_dt = datetime.strptime(from_date, '%Y-%m-%d')
                        if item_dt < from_dt:
                            return False
                    
                    if to_date:
                        to_dt = datetime.strptime(to_date, '%Y-%m-%d')
                        if item_dt > to_dt:
                            return False
                    
                    return True
                except ValueError:
                    return True
            
            # Handle predefined date ranges
            from datetime import datetime, timedelta
            item_date = item.get('created_date', '')
            if not item_date:
                return True
            
            try:
                item_dt = datetime.strptime(item_date, '%Y-%m-%d')
                now = datetime.now()
                
                if filter_value == "Last 7 days":
                    return item_dt >= (now - timedelta(days=7))
                elif filter_value == "Last 30 days":
                    return item_dt >= (now - timedelta(days=30))
                elif filter_value == "Last 3 months":
                    return item_dt >= (now - timedelta(days=90))
                elif filter_value == "Last 6 months":
                    return item_dt >= (now - timedelta(days=180))
                elif filter_value == "Last year":
                    return item_dt >= (now - timedelta(days=365))
                elif filter_value == "This year":
                    return item_dt.year == now.year
                elif filter_value == "Last year":
                    return item_dt.year == (now.year - 1)
                elif filter_value == "This quarter":
                    quarter_start = datetime(now.year, ((now.month - 1) // 3) * 3 + 1, 1)
                    return item_dt >= quarter_start
                elif filter_value == "Last quarter":
                    current_quarter = (now.month - 1) // 3
                    if current_quarter == 0:
                        quarter_start = datetime(now.year - 1, 10, 1)
                    else:
                        quarter_start = datetime(now.year, (current_quarter - 1) * 3 + 1, 1)
                    quarter_end = datetime(now.year, current_quarter * 3 + 1, 1) - timedelta(days=1)
                    return quarter_start <= item_dt <= quarter_end
                
                return True
            except ValueError:
                return True
            
        except Exception as e:
            print(f"Error checking refine date filter: {e}")
            return True
    
    def display_refine_filtered_items(self, work_items):
        """Display filtered refine work items in table view."""
        try:
            # Clear existing items
            for item in self.refine_related_tree.get_children():
                self.refine_related_tree.delete(item)
            
            # Check if hierarchy loading is enabled
            load_hierarchy = getattr(self, 'load_hierarchy_var', None) and self.load_hierarchy_var.get()
            
            # Add filtered work items to treeview
            for item in work_items:
                item_id = item.get('id', '')
                item_type = item.get('type', '')
                item_state = item.get('state', '')
                item_title = item.get('title', '')
                assigned_to = item.get('assigned_to', '')
                created_date = item.get('created_date', '')
                
                # Only get hierarchy information if enabled
                if load_hierarchy:
                    try:
                        hierarchy = self.client.get_work_item_hierarchy(item_id)
                        if hierarchy and hierarchy.get('hierarchy_path'):
                            # Add hierarchy info to the title
                            hierarchy_info = self._get_hierarchy_summary(hierarchy)
                            item_title_with_hierarchy = f"{item_title} {hierarchy_info}"
                        else:
                            item_title_with_hierarchy = item_title
                    except Exception as e:
                        logger.warning(f"Could not get hierarchy for work item {item_id}: {e}")
                        item_title_with_hierarchy = item_title
                else:
                    # Skip hierarchy loading for better performance
                    item_title_with_hierarchy = item_title
                
                self.refine_related_tree.insert('', 'end', values=(
                    item_id, item_type, item_state, item_title_with_hierarchy, assigned_to, created_date
                ))
            
        except Exception as e:
            print(f"Error displaying refine filtered items: {e}")

    def _get_hierarchy_summary(self, hierarchy):
        """Get a brief summary of the hierarchy for display in the refine tab."""
        if not hierarchy or not hierarchy.get('hierarchy_path'):
            return ""
        
        hierarchy_path = hierarchy['hierarchy_path']
        if len(hierarchy_path) <= 1:
            return ""
        
        # Get the top-level item (Epic, Feature, etc.)
        top_item = hierarchy_path[0]
        top_type = top_item.fields.get('System.WorkItemType', '').lower()
        top_id = top_item.id
        
        # Create a brief hierarchy summary
        if top_type == 'epic':
            return f"[Epic #{top_id}]"
        elif top_type == 'feature':
            return f"[Feature #{top_id}]"
        elif top_type in ['user story', 'story']:
            return f"[Story #{top_id}]"
        else:
            return f"[{top_type.title()} #{top_id}]"
    
    def clear_refine_filters(self):
        """Clear all refine filters."""
        try:
            # Clear all filter variables
            self.refine_title_filter.set("")
            self.refine_assigned_to_filter.set("All")
            self.refine_priority_filter.set("All")
            self.refine_created_date_filter.set("All")
            self.refine_area_path_filter.set("All")
            self.refine_created_by_filter.set("All")
            self.refine_tags_filter.set("All")
            self.refine_iteration_path_filter.set("All")
            
            # Clear custom date fields
            self.refine_date_from_var.set("")
            self.refine_date_to_var.set("")
            self.refine_custom_date_frame.grid_remove()
            
            # Reapply filters (which will show all items since filters are cleared)
            self.apply_refine_filters()
            
        except Exception as e:
            print(f"Error clearing refine filters: {e}")
    
    def on_refine_date_filter_change(self):
        """Handle refine date filter selection change."""
        selected = self.refine_created_date_filter.get()
        if selected == "Custom range...":
            # Show custom date range controls
            self.refine_custom_date_frame.grid()
        else:
            # Hide custom date range controls
            self.refine_custom_date_frame.grid_remove()
            # Clear custom date fields
            self.refine_date_from_var.set("")
            self.refine_date_to_var.set("")
            # Apply filters immediately for predefined ranges
            self.apply_refine_filters()
    
    def update_refine_filter_summary(self):
        """Update the refine filter summary label to show active filters."""
        active_filters = []
        
        # Check each filter for non-default values
        if self.refine_title_filter.get().strip():
            active_filters.append(f"Title: '{self.refine_title_filter.get()[:20]}...'")
        
        if self.refine_assigned_to_filter.get() != "All":
            active_filters.append(f"Assigned: {self.refine_assigned_to_filter.get()}")
        
        if self.refine_priority_filter.get() != "All":
            active_filters.append(f"Priority: {self.refine_priority_filter.get()}")
        
        if self.refine_created_date_filter.get() != "All":
            active_filters.append(f"Date: {self.refine_created_date_filter.get()}")
        
        if self.refine_tags_filter.get() != "All":
            active_filters.append(f"Tags: {self.refine_tags_filter.get()}")
        
        if self.refine_area_path_filter.get() != "All":
            active_filters.append(f"Area: {self.refine_area_path_filter.get()}")
        
        if self.refine_iteration_path_filter.get() != "All":
            active_filters.append(f"Iteration: {self.refine_iteration_path_filter.get()}")
        
        if self.refine_created_by_filter.get() != "All":
            active_filters.append(f"Created By: {self.refine_created_by_filter.get()}")
        
        if active_filters:
            summary_text = " | ".join(active_filters[:3])  # Show max 3 filters
            if len(active_filters) > 3:
                summary_text += f" (+{len(active_filters) - 3} more)"
            self.refine_filter_summary_label.configure(text=summary_text, foreground="blue")
        else:
            self.refine_filter_summary_label.configure(text="No filters applied", foreground="gray")
    
    def update_refine_filter_count(self, filtered_count=None, total_count=None):
        """Update the refine filter count display showing filtered vs total items."""
        try:
            # Get counts if not provided
            if filtered_count is None:
                if hasattr(self, 'refine_related_tree') and self.refine_related_tree:
                    filtered_count = len(self.refine_related_tree.get_children())
                else:
                    filtered_count = 0
            
            if total_count is None:
                if hasattr(self, 'current_related_items') and self.current_related_items:
                    total_count = len(self.current_related_items)
                else:
                    total_count = 0
            
            # Update the count label
            if filtered_count == total_count:
                self.refine_filter_count_label.configure(text=f"Showing {filtered_count} of {total_count} items", foreground="green")
            else:
                self.refine_filter_count_label.configure(text=f"Showing {filtered_count} of {total_count} items", foreground="orange")
                
        except Exception as e:
            print(f"Error updating refine filter count: {e}")
            self.refine_filter_count_label.configure(text="Count unavailable", foreground="red")
    
    def populate_refine_filter_dropdowns(self):
        """Populate refine filter dropdown options from current related items."""
        try:
            if not hasattr(self, 'current_related_items') or not self.current_related_items:
                return
            
            # Collect unique values for each filter
            filter_data = {
                'assigned_to': set(),
                'priority': set(),
                'area_path': set(),
                'created_by': set(),
                'tags': set(),
                'iteration_path': set()
            }
            
            for item in self.current_related_items:
                # Collect assigned to values
                if item.get('assigned_to') and item.get('assigned_to') != 'Unassigned':
                    filter_data['assigned_to'].add(item.get('assigned_to'))
                
                # Collect priority values
                if item.get('priority'):
                    filter_data['priority'].add(str(item.get('priority')))
                
                # Collect area path values
                if item.get('area_path'):
                    filter_data['area_path'].add(item.get('area_path'))
                
                # Collect created by values
                if item.get('created_by'):
                    filter_data['created_by'].add(item.get('created_by'))
                
                # Collect tags (split by semicolon and add individual tags)
                if item.get('tags'):
                    tags = item.get('tags').split(';')
                    for tag in tags:
                        tag = tag.strip()
                        if tag:
                            filter_data['tags'].add(tag)
                
                # Collect iteration path values
                if item.get('iteration_path'):
                    filter_data['iteration_path'].add(item.get('iteration_path'))
            
            # Update filter combo boxes
            self.refine_assigned_to_combo['values'] = ["All"] + sorted(list(filter_data['assigned_to']))
            self.refine_priority_combo['values'] = ["All"] + sorted(list(filter_data['priority']))
            self.refine_area_path_combo['values'] = ["All"] + sorted(list(filter_data['area_path']))
            self.refine_created_by_combo['values'] = ["All"] + sorted(list(filter_data['created_by']))
            self.refine_tags_combo['values'] = ["All"] + sorted(list(filter_data['tags']))
            self.refine_iteration_path_combo['values'] = ["All"] + sorted(list(filter_data['iteration_path']))
            
            print(f"✅ Populated refine filter dropdowns with {len(self.current_related_items)} related items")
            
        except Exception as e:
            print(f"Error populating refine filter dropdowns: {e}")
    
    def analyze_with_llm(self):
        """Analyze the current source work item and related items with LLM using the same logic as the first tab."""
        try:
            if not hasattr(self, 'current_source_work_item') or not self.current_source_work_item:
                messagebox.showwarning("No Work Item", "Please select a work item first to analyze.")
                return
            
            if not hasattr(self, 'current_related_items') or not self.current_related_items:
                messagebox.showwarning("No Related Items", "No related work items found to analyze.")
                return
            
            print(f"🤖 Starting LLM analysis for work item {self.current_source_work_item.id} using related items...")
            
            # Convert related items back to work item objects for compatibility with existing LLM analysis
            all_work_items = []
            for item_data in self.current_related_items:
                # Create a mock work item object with the necessary fields
                class MockWorkItem:
                    def __init__(self, data):
                        self.id = data.get('id', '')
                        self.fields = {
                            'System.Title': data.get('title', ''),
                            'System.WorkItemType': data.get('type', ''),
                            'System.State': data.get('state', ''),
                            'System.AssignedTo': data.get('assigned_to', ''),
                            'System.CreatedDate': data.get('created_date', ''),
                            'System.AreaPath': data.get('area_path', ''),
                            'System.CreatedBy': data.get('created_by', ''),
                            'System.Tags': data.get('tags', ''),
                            'System.IterationPath': data.get('iteration_path', ''),
                            'Microsoft.VSTS.Common.Priority': data.get('priority', ''),
                            'System.Description': data.get('description', 'No description available')
                        }
                
                mock_item = MockWorkItem(item_data)
                all_work_items.append(mock_item)
            
            print(f"📊 Using {len(all_work_items)} related work items for LLM analysis")
            
            # Use the same LLM analysis logic as the first tab
            import threading
            threading.Thread(target=self._perform_llm_analysis, 
                           args=(self.current_source_work_item, all_work_items)).start()
            
        except Exception as e:
            print(f"Error starting LLM analysis: {e}")
            messagebox.showerror("Error", f"Failed to start LLM analysis: {e}")
    

    
    def update_filter_frame_title(self, selected_team):
        """Update the filter frame title with the selected team name."""
        try:
            # Find the filter frame and update its text
            for widget in self.root.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.LabelFrame) and "Source Work Item Filters" in str(child.cget('text')):
                            child.configure(text=f"Source Work Item Filters for {selected_team}")
                            break
                # Also check for nested frames (like in notebooks)
                if hasattr(widget, 'winfo_children'):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Frame):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, ttk.LabelFrame) and "Source Work Item Filters" in str(grandchild.cget('text')):
                                    grandchild.configure(text=f"Source Work Item Filters for {selected_team}")
                                    break
        except Exception as e:
            print(f"Error updating filter frame title: {e}")
    
    def on_main_date_filter_change(self):
        """Handle main date filter selection change."""
        selected = self.date_range_filter.get()
        if selected == "Custom range...":
            # Show custom date range frame
            self.main_custom_date_frame.grid()
        else:
            # Hide custom date range frame
            self.main_custom_date_frame.grid_remove()
            # Apply filters immediately for predefined ranges
            self.apply_enhanced_filters()
    
    def on_date_filter_change(self):
        """Handle date filter selection change."""
        selected = self.created_date_filter.get()
        if selected == "Custom range...":
            # Show custom date range frame
            self.custom_date_frame.grid()
        else:
            # Hide custom date range frame
            self.custom_date_frame.grid_remove()
            # Apply filters immediately for predefined ranges
            self.apply_filters()
    
    def show_calendar(self, date_var):
        """Show calendar widget for date selection."""
        try:
            from tkcalendar import Calendar
        except ImportError:
            messagebox.showerror("Error", "tkcalendar module not found. Please install it with: pip install tkcalendar")
            return
        
        # Create calendar window
        cal_window = tk.Toplevel(self.root)
        cal_window.title("Select Date")
        cal_window.geometry("300x300")
        cal_window.transient(self.root)
        cal_window.grab_set()
        
        # Create calendar widget
        cal = Calendar(cal_window, selectmode='day', date_pattern='yyyy-mm-dd')
        cal.pack(pady=20)
        
        def on_date_select():
            selected_date = cal.get_date()
            date_var.set(selected_date)
            cal_window.destroy()
            self.apply_filters()
        
        # Add OK button
        ok_button = ttk.Button(cal_window, text="OK", command=on_date_select)
        ok_button.pack(pady=10)
        
        # Center the window
        cal_window.update_idletasks()
        x = (cal_window.winfo_screenwidth() // 2) - (cal_window.winfo_width() // 2)
        y = (cal_window.winfo_screenheight() // 2) - (cal_window.winfo_height() // 2)
        cal_window.geometry(f"+{x}+{y}")
    
    def get_date_range_from_filter(self, filter_value):
        """Convert date filter selection to date range."""
        from datetime import datetime, timedelta
        import calendar
        
        if filter_value == "All":
            return None, None
        
        today = datetime.now().date()
        
        if filter_value == "Last 7 days":
            return today - timedelta(days=7), today
        elif filter_value == "Last 30 days":
            return today - timedelta(days=30), today
        elif filter_value == "Last 3 months":
            return today - timedelta(days=90), today
        elif filter_value == "Last 6 months":
            return today - timedelta(days=180), today
        elif filter_value == "Last year":
            return today - timedelta(days=365), today
        elif filter_value == "This quarter":
            current_month = today.month
            quarter_start_month = ((current_month - 1) // 3) * 3 + 1
            quarter_start = today.replace(month=quarter_start_month, day=1)
            return quarter_start, today
        elif filter_value == "Last quarter":
            current_month = today.month
            last_quarter_month = ((current_month - 1) // 3) * 3 - 2
            if last_quarter_month <= 0:
                last_quarter_month += 12
                year = today.year - 1
            else:
                year = today.year
            quarter_start = today.replace(year=year, month=last_quarter_month, day=1)
            quarter_end = today.replace(month=quarter_start_month, day=1) - timedelta(days=1)
            return quarter_start, quarter_end
        elif filter_value == "This year":
            year_start = today.replace(month=1, day=1)
            return year_start, today
        elif filter_value == "Last year":
            last_year = today.year - 1
            year_start = today.replace(year=last_year, month=1, day=1)
            year_end = today.replace(year=last_year, month=12, day=31)
            return year_start, year_end
        elif filter_value == "Custom range...":
            # Get custom date range
            from_date_str = self.date_from_var.get()
            to_date_str = self.date_to_var.get()
            
            if from_date_str and to_date_str:
                try:
                    from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
                    to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
                    return from_date, to_date
                except ValueError:
                    messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD format.")
                    return None, None
        
        return None, None
    
    def populate_table_filters(self):
        """Populate filter options from current work items in background thread."""
        if not self.current_work_items:
            return
        
        # Run in background thread to avoid UI blocking
        import threading
        thread = threading.Thread(target=self._populate_filters_background)
        thread.daemon = True
        thread.start()
    
    def _populate_filters_background(self):
        """Background method to populate filter options."""
        try:
            # Collect unique values for each filter
            assigned_to = set()
            priorities = set()
            tags = set()
            area_paths = set()
            iteration_paths = set()
            created_by = set()
            
            for item in self.current_work_items:
                # Assigned to
                if 'System.AssignedTo' in item.fields and item.fields['System.AssignedTo']:
                    assigned_to.add(self.get_assigned_to_display_name(item.fields['System.AssignedTo']))
                
                # Priority
                if 'Microsoft.VSTS.Common.Priority' in item.fields:
                    priorities.add(str(item.fields['Microsoft.VSTS.Common.Priority']))
                
                # Tags
                if 'System.Tags' in item.fields and item.fields['System.Tags']:
                    tag_list = item.fields['System.Tags'].split(';')
                    for tag in tag_list:
                        if tag.strip():
                            tags.add(tag.strip())
                
                # Area Path
                if 'System.AreaPath' in item.fields:
                    area_paths.add(item.fields['System.AreaPath'])
                
                # Iteration Path
                if 'System.IterationPath' in item.fields:
                    iteration_paths.add(item.fields['System.IterationPath'])
                
                # Created By
                if 'System.CreatedBy' in item.fields and item.fields['System.CreatedBy']:
                    created_by.add(self.get_assigned_to_display_name(item.fields['System.CreatedBy']))
            
            # Update combo boxes in main thread
            self.root.after(0, self._update_table_filter_combos, {
                'assigned_to': assigned_to,
                'priorities': priorities,
                'tags': tags,
                'area_paths': area_paths,
                'iteration_paths': iteration_paths,
                'created_by': created_by
            })
            
        except Exception as e:
            print(f"Error populating filters in background: {e}")
    
    def _update_table_filter_combos(self, filter_data):
        """Update filter combo boxes with collected data."""
        try:
            self.assigned_to_combo['values'] = ["All"] + sorted(list(filter_data['assigned_to']))
            self.priority_combo['values'] = ["All"] + sorted(list(filter_data['priorities']))
            self.tags_combo['values'] = ["All"] + sorted(list(filter_data['tags']))
            self.area_path_combo['values'] = ["All"] + sorted(list(filter_data['area_paths']))
            self.iteration_path_combo['values'] = ["All"] + sorted(list(filter_data['iteration_paths']))
            self.created_by_combo['values'] = ["All"] + sorted(list(filter_data['created_by']))
        except Exception as e:
            print(f"Error updating filter combos: {e}")
    
    def get_available_values_for_column(self, col):
        """Get available values for a column from current work items."""
        try:
            values = set()
            for item in self.current_work_items:
                if col == 'Type':
                    value = item.fields.get('System.WorkItemType', 'Unknown')
                elif col == 'State':
                    value = item.fields.get('System.State', 'Unknown')
                elif col == 'Assigned To':
                    value = self.get_assigned_to_display_name(item.fields.get('System.AssignedTo', 'Unassigned'))
                else:
                    continue
                
                if value and value != 'Unknown' and value != 'Unassigned':
                    values.add(str(value))
            
            return sorted(list(values))
        except Exception as e:
            print(f"Error getting available values for {col}: {e}")
            return []
    
    def apply_filters(self):
        """Apply filters to the table view."""
        try:
            # Check if work_items_tree is initialized
            if not hasattr(self, 'work_items_tree') or self.work_items_tree is None:
                return
                
            # Clear existing items
            for item in self.work_items_tree.get_children():
                self.work_items_tree.delete(item)
            
            if not self.current_work_items:
                return
            
            # Filter work items based on current filter values
            filtered_items = []
            for item in self.current_work_items:
                if self.item_matches_filters(item):
                    filtered_items.append(item)
            
            # Display filtered items
            self.display_filtered_items(filtered_items)
            
            # Update filter summary
            self.update_filter_summary()
            
            # Update filter count
            self.update_filter_count(len(filtered_items), len(self.current_work_items))
            
        except Exception as e:
            print(f"Error applying filters: {e}")
    
    def item_matches_filters(self, item):
        """Check if a work item matches the current filters."""
        try:
            # Check basic filters first
            if hasattr(self, 'filter_vars') and self.filter_vars:
                for col, filter_var in self.filter_vars.items():
                    filter_value = filter_var.get().strip()
                    
                    if not filter_value or filter_value == "All":
                        continue
                    
                    # Get item value for this column
                    if col == 'Title':
                        # Search in both title and description
                        title_value = item.fields.get('System.Title', 'No Title')
                        description_value = item.fields.get('System.Description', '')
                        combined_text = f"{title_value} {description_value}".lower()
                        if filter_value.lower() not in combined_text:
                            return False
                            
                    elif col == 'Assigned To':
                        item_value = self.get_assigned_to_display_name(item.fields.get('System.AssignedTo', 'Unassigned'))
                        if filter_value != str(item_value):
                            return False
                            
                    elif col == 'Priority':
                        item_priority = str(item.fields.get('Microsoft.VSTS.Common.Priority', ''))
                        if filter_value != item_priority:
                            return False
                            
                    elif col == 'Created Date':
                        if not self.matches_date_filter(item, filter_value):
                            return False
                            
                    elif col == 'Tags':
                        item_tags = item.fields.get('System.Tags', '')
                        if filter_value not in str(item_tags):
                            return False
                            
                    elif col == 'Area Path':
                        item_area_path = item.fields.get('System.AreaPath', '')
                        if filter_value != str(item_area_path):
                            return False
                            
                    elif col == 'Iteration Path':
                        item_iteration_path = item.fields.get('System.IterationPath', '')
                        if filter_value != str(item_iteration_path):
                            return False
                            
                    elif col == 'Created By':
                        item_created_by = self.get_assigned_to_display_name(item.fields.get('System.CreatedBy', ''))
                        if filter_value != str(item_created_by):
                            return False
            
            return True
            
        except Exception as e:
            print(f"Error checking item filters: {e}")
            return True
    
    def matches_date_filter(self, item, filter_value):
        """Check if item matches date filter criteria."""
        try:
            if not filter_value or filter_value == "All":
                return True
            
            # Get item created date
            if 'System.CreatedDate' not in item.fields:
                return False
            
            item_date = item.fields['System.CreatedDate']
            if not item_date:
                return False
            
            # Convert to date object
            from datetime import datetime
            if hasattr(item_date, 'date'):
                item_date = item_date.date()
            elif hasattr(item_date, 'strftime'):
                item_date = datetime.strptime(item_date.strftime('%Y-%m-%d'), '%Y-%m-%d').date()
            else:
                item_date = datetime.strptime(str(item_date)[:10], '%Y-%m-%d').date()
            
            # Get date range from filter
            from_date, to_date = self.get_date_range_from_filter(filter_value)
            
            if from_date is None and to_date is None:
                return True  # No date filter
            
            # Check if item date is within range
            if from_date and item_date < from_date:
                return False
            if to_date and item_date > to_date:
                return False
            
            return True
            
        except Exception as e:
            print(f"Error checking date filter: {e}")
            return True
    
    def display_filtered_items(self, work_items):
        """Display filtered work items in table view."""
        try:
            # Add work items to treeview
            for item in work_items:
                item_id = item.id
                item_type = item.fields.get('System.WorkItemType', 'Unknown')
                item_state = item.fields.get('System.State', 'Unknown')
                item_title = item.fields.get('System.Title', 'No Title')
                assigned_to_raw = item.fields.get('System.AssignedTo', 'Unassigned')
                assigned_to = self.get_assigned_to_display_name(assigned_to_raw)
                area_path = item.fields.get('System.AreaPath', 'Unknown')
                
                # Get created date
                created_date = "Unknown"
                if 'System.CreatedDate' in item.fields:
                    date_obj = item.fields['System.CreatedDate']
                    if hasattr(date_obj, 'strftime'):
                        created_date = date_obj.strftime('%d %b %Y')
                    else:
                        created_date = str(date_obj)[:10] if str(date_obj) != 'None' else 'Unknown'
                
                # Truncate assigned_to if too long (keep title full length)
                if len(str(assigned_to)) > 20:
                    assigned_to = str(assigned_to)[:17] + "..."
                
                # Insert with separate action columns
                tree_item = self.work_items_tree.insert('', 'end', values=(
                    item_id, item_type, item_state, item_title, assigned_to, created_date, "🔗 Show Related Work Items", "🤖 Analyze with LLM", "🌐 Open in Azure DevOps"
                ))
            
            # After populating, add buttons to each row
            self.add_action_buttons_to_tree()
            
        except Exception as e:
            print(f"Error displaying filtered items: {e}")
    
    def clear_filters(self):
        """Clear all filters."""
        try:
            # Clear basic filters
            if hasattr(self, 'filter_vars') and self.filter_vars:
                for filter_var in self.filter_vars.values():
                    if hasattr(filter_var, 'set'):
                        filter_var.set("")
            
            # Clear additional filters
            if hasattr(self, 'title_filter'):
                self.title_filter.set("")
            if hasattr(self, 'assigned_to_filter'):
                self.assigned_to_filter.set("All")
            if hasattr(self, 'created_date_filter'):
                self.created_date_filter.set("All")
            if hasattr(self, 'priority_filter'):
                self.priority_filter.set("All")
            if hasattr(self, 'tags_filter'):
                self.tags_filter.set("All")
            if hasattr(self, 'area_path_filter'):
                self.area_path_filter.set("All")
            if hasattr(self, 'iteration_path_filter'):
                self.iteration_path_filter.set("All")
            if hasattr(self, 'created_by_filter'):
                self.created_by_filter.set("All")
            
            # Clear custom date range
            if hasattr(self, 'date_from_var'):
                self.date_from_var.set("")
            if hasattr(self, 'date_to_var'):
                self.date_to_var.set("")
            
            # Hide custom date frame
            if hasattr(self, 'custom_date_frame'):
                self.custom_date_frame.grid_remove()
            
            # Refresh the table with all items
            self.apply_filters()
            
        except Exception as e:
            print(f"Error clearing filters: {e}")

    def display_table_view(self, work_items):
        """Display work items in table view."""
        # Store work items for filtering
        self.current_work_items = work_items
        
        # Clear existing items
        for item in self.work_items_tree.get_children():
            self.work_items_tree.delete(item)
        
        if not work_items:
            return
        
        # Update filter dropdowns with available values
        self.update_filter_dropdowns()
        
        # Display all items (filtering will be applied if filters are set)
        self.display_filtered_items(work_items)
    
    def update_filter_dropdowns(self):
        """Update filter dropdown values based on current work items."""
        try:
            for col in ['Type', 'State', 'Assigned To']:
                if col in self.filter_widgets:
                    available_values = self.get_available_values_for_column(col)
                    current_values = ["All"] + available_values
                    self.filter_widgets[col]['values'] = current_values
        except Exception as e:
            print(f"Error updating filter dropdowns: {e}")
    
    def add_action_buttons_to_tree(self):
        """Add action buttons to the treeview rows."""
        # Get all items in the tree
        for item in self.work_items_tree.get_children():
            # Get the work item ID from the first column
            item_values = self.work_items_tree.item(item, 'values')
            if item_values:
                work_item_id = item_values[0]
                
                # Find the corresponding work item object
                work_item = None
                for wi in self.current_work_items:
                    if str(wi.id) == str(work_item_id):
                        work_item = wi
                        break
                
                if work_item:
                    # Set the three separate action columns with icons and text
                    # Make them look more clickable with better formatting
                    self.work_items_tree.set(item, 'Show Related Work Items', "🔗 Show Related Work Items")
                    self.work_items_tree.set(item, 'Analyze with LLM', "🤖 Analyze with LLM")
                    self.work_items_tree.set(item, 'Open in Azure DevOps', "🌐 Open in Azure DevOps")
    
    def on_tree_click(self, event):
        """Handle clicks on the treeview for the three separate action columns."""
        # Get the clicked item and column
        item = self.work_items_tree.identify_row(event.y)
        column = self.work_items_tree.identify_column(event.x)
        
        if item and column:
            # Get the work item ID from the first column
            item_values = self.work_items_tree.item(item, 'values')
            if item_values:
                work_item_id = item_values[0]
                
                # Find the corresponding work item object
                work_item = None
                for wi in self.current_work_items:
                    if str(wi.id) == str(work_item_id):
                        work_item = wi
                        break
                
                if work_item:
                    # Handle clicks on specific action columns
                    if column == '#7':  # Related column (7th column, 0-indexed)
                        self.show_related_work_items(work_item)
                    elif column == '#8':  # Analyze column (8th column, 0-indexed)
                        self.analyze_work_item_with_llm(work_item)
                    elif column == '#9':  # Open column (9th column, 0-indexed)
                        if hasattr(work_item, 'url') and work_item.url:
                            self.open_url(work_item.url)
                        else:
                            messagebox.showinfo("No URL", "This work item doesn't have a URL to open.")
    
    # Removed show_actions_popup method - no longer needed
    
    def on_work_item_select(self, event):
        """Handle work item selection in the treeview."""
        # Selection is now handled by the action buttons in each row
        # No popup needed - actions are directly accessible
        pass
    
    # Removed display_selected_work_item_details method - no longer needed
    # Action buttons are now directly in the table rows
    
    def show_related_work_items(self, work_item):
        """Show related work items for the selected work item using optimized search strategy with caching."""
        try:
            print(f"🔍 Searching for related work items for work item {work_item.id}...")
            
            # Get the project name
            project_name = self.team_project_var.get().strip()
            if not project_name:
                messagebox.showwarning("No Project", "Please select a project first.")
                return
            
            # Check cache first to avoid repeated API calls
            cache_key = f"{project_name}_{work_item.id}"
            if cache_key in self.related_items_cache:
                print(f"📋 Using cached results for work item {work_item.id}")
                related_items = self.related_items_cache[cache_key]
                if related_items:
                    print(f"✅ Found {len(related_items)} cached related work items, displaying in Refine Related Work Items tab...")
                    self.display_related_work_items_in_refine_tab(work_item, related_items)
                else:
                    print("❌ Cached result shows no related work items found")
                    messagebox.showinfo("No Related Items", f"No related work items found for work item {work_item.id}")
                return
            
            # Check if we have a meaningful title for keyword search
            title = work_item.fields.get('System.Title', '')
            has_meaningful_title = len(title.strip()) > 10 and not title.lower().startswith(('bug', 'task', 'user story'))
            
            related_items = []
            
            if has_meaningful_title:
                print(f"🔍 Using title-based keyword search (title: '{title[:50]}...')")
                # Try title-based keyword search first for work items with meaningful titles
                related_items = self.client.query_related_work_items_by_title_keywords(project_name, work_item)
                
                # Only fall back if title-based search completely fails (not just returns few results)
                if not related_items:
                    print(f"🔍 Title-based search failed, trying relationship-based search...")
                    related_items = self.client.query_related_work_items(project_name, work_item.id)
            else:
                print(f"🔍 Using relationship-based search (title too short or generic: '{title}')")
                # For work items with short/generic titles, go straight to relationship-based search
                related_items = self.client.query_related_work_items(project_name, work_item.id)
            
            # Cache the results to prevent repeated API calls
            self._add_to_cache(cache_key, related_items)
            print(f"💾 Cached results for work item {work_item.id}")
            
            if related_items:
                print(f"✅ Found {len(related_items)} related work items, displaying in Refine Related Work Items tab...")
                self.display_related_work_items_in_refine_tab(work_item, related_items)
            else:
                print("❌ No related work items found by any method")
                messagebox.showinfo("No Related Items", f"No related work items found for work item {work_item.id}")
                
        except Exception as e:
            error_msg = f"Error retrieving related work items: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", error_msg)
    
    def analyze_work_item_with_llm(self, selected_work_item):
        """Analyze the selected work item and all work items using OpenArena LLM to find related items."""
        try:
            print(f"🤖 Starting LLM analysis for work item {selected_work_item.id}...")
            
            # Get the project name
            project_name = self.team_project_var.get().strip()
            if not project_name:
                messagebox.showwarning("No Project", "Please select a project first.")
                return
            
            # Get work items for the project with better filtering and limiting
            # Use more restrictive filters to avoid hitting the 20,000 limit
            
            # Get configuration values
            work_item_limit = getattr(self, 'llm_work_item_limit_var', tk.IntVar(value=500)).get()
            analysis_strategy = getattr(self, 'llm_strategy_var', tk.StringVar(value="area_path")).get()
            
            print(f"⚙️ Using LLM analysis configuration:")
            print(f"   - Work item limit: {work_item_limit}")
            print(f"   - Strategy: {analysis_strategy}")
            print(f"   - Selected work item area path: {selected_work_item.fields.get('System.AreaPath', 'No Area Path')}")
            
            # First, try to get work items based on the selected strategy
            selected_area_path = selected_work_item.fields.get('System.AreaPath', '')
            
            if analysis_strategy == "area_path" and selected_area_path:
                print(f"🎯 Strategy: Area Path Focus - {selected_area_path}")
                try:
                    # Try to get work items from the same area path first
                    # Use the state filter from the UI instead of hardcoded "Active"
                    state_filter = self.state_filter.get()
                    state = None if state_filter == "All" else state_filter
                    all_work_items = self.client.query_work_items(
                        project=project_name, 
                        work_item_type=None,
                        state=state,
                        limit=work_item_limit + 10  # Get a few extra for filtering
                    )
                    
                    # Filter by area path if we got items - use broader matching
                    if all_work_items:
                        # First try exact area path match
                        exact_area_filtered_items = [
                            item for item in all_work_items 
                            if item.fields.get('System.AreaPath', '') == selected_area_path
                        ]
                        
                        if exact_area_filtered_items and len(exact_area_filtered_items) >= 10:
                            # If we have enough items in exact area path, use them
                            all_work_items = exact_area_filtered_items[:work_item_limit]
                            print(f"✅ Found {len(all_work_items)} work items in exact area path: {selected_area_path}")
                        else:
                            # Try broader area path matching (parent area paths)
                            print(f"⚠️ Only {len(exact_area_filtered_items)} work items in exact area path, trying broader matching...")
                            
                            # Extract parent area paths (e.g., "Your Project\Team" from "Your Project\Team - Subteam")
                            area_path_parts = selected_area_path.split('\\')
                            broader_matches = []
                            
                            # Try progressively broader area paths
                            for i in range(len(area_path_parts) - 1, 0, -1):
                                parent_area_path = '\\'.join(area_path_parts[:i])
                                parent_matches = [
                                    item for item in all_work_items 
                                    if item.fields.get('System.AreaPath', '').startswith(parent_area_path)
                                ]
                                if parent_matches and len(parent_matches) >= 20:  # Need at least 20 items
                                    broader_matches = parent_matches[:work_item_limit]
                                    print(f"✅ Found {len(broader_matches)} work items in broader area path: {parent_area_path}")
                                    break
                            
                            if broader_matches:
                                all_work_items = broader_matches
                            else:
                                # If still not enough, use all work items but prioritize by area path similarity
                                print("⚠️ Not enough work items in related area paths, using all work items with prioritization")
                                # Sort by area path similarity (items with similar area paths first)
                                def area_path_similarity(item):
                                    item_area = item.fields.get('System.AreaPath', '')
                                    if item_area == selected_area_path:
                                        return 3  # Exact match
                                    elif item_area.startswith(area_path_parts[0] if area_path_parts else ''):
                                        return 2  # Same root area
                                    elif any(part in item_area for part in area_path_parts):
                                        return 1  # Some overlap
                                    else:
                                        return 0  # No similarity
                                
                                all_work_items = sorted(all_work_items, key=area_path_similarity, reverse=True)[:work_item_limit]
                                print(f"✅ Using {len(all_work_items)} work items with area path prioritization")
                    else:
                        print("⚠️ No work items returned, using general query")
                        all_work_items = self.client.query_work_items(
                            project=project_name,
                            work_item_type=None,
                            state=state,
                            limit=work_item_limit
                        )
                        
                except Exception as e:
                    print(f"⚠️ Error getting area-specific work items: {e}")
                    print("🔄 Falling back to general query")
                    all_work_items = self.client.query_work_items(
                        project=project_name,
                        work_item_type=None,
                        state=state,
                        limit=work_item_limit
                    )
                    
            elif analysis_strategy == "broader":
                print("🌍 Strategy: Broader Area Analysis")
                try:
                    # Get state filter for broader strategy
                    state_filter = self.state_filter.get()
                    state = None if state_filter == "All" else state_filter
                    # Get work items from broader area paths
                    all_work_items = self.client.query_work_items(
                        project=project_name,
                        work_item_type=None,
                        state=state,
                        limit=work_item_limit
                    )
                    
                    # Apply broader area path filtering
                    if all_work_items and selected_area_path:
                        area_path_parts = selected_area_path.split('\\')
                        if len(area_path_parts) > 1:
                            # Use parent area path (e.g., "Your Project\Team" from "Your Project\Team - Subteam")
                            parent_area_path = '\\'.join(area_path_parts[:-1])
                            broader_items = [
                                item for item in all_work_items 
                                if item.fields.get('System.AreaPath', '').startswith(parent_area_path)
                            ]
                            if broader_items:
                                all_work_items = broader_items[:work_item_limit]
                                print(f"✅ Found {len(all_work_items)} work items in broader area: {parent_area_path}")
                            else:
                                print(f"⚠️ No work items in broader area {parent_area_path}, using all work items")
                        else:
                            print("⚠️ Cannot determine parent area path, using all work items")
                    else:
                        print("⚠️ No area path available, using all work items")
                        
                except Exception as e:
                    print(f"⚠️ Error getting broader area work items: {e}")
                    print("🔄 Falling back to general query")
                    all_work_items = self.client.query_work_items(
                        project=project_name,
                        work_item_type=None,
                        state=state,
                        limit=work_item_limit
                    )
                    
            elif analysis_strategy == "recent":
                print("🕒 Strategy: Recent Work Items Focus")
                try:
                    # Get state filter for recent strategy
                    state_filter = self.state_filter.get()
                    state = None if state_filter == "All" else state_filter
                    # Try to get recent work items
                    all_work_items = self.client.query_work_items(
                        project=project_name,
                        work_item_type=None,
                        state=state,
                        limit=work_item_limit
                    )
                except Exception as e:
                    print(f"⚠️ Error getting recent work items: {e}")
                    print("🔄 Falling back to general query")
                    all_work_items = self.client.query_work_items(
                        project=project_name,
                        work_item_type=None,
                        state=state,
                        limit=work_item_limit
                    )
            else:
                # General strategy or fallback
                print("🌐 Strategy: General Project Analysis")
                # Get state filter for general strategy
                state_filter = self.state_filter.get()
                state = None if state_filter == "All" else state_filter
                all_work_items = self.client.query_work_items(
                    project=project_name,
                    work_item_type=None,
                    state=state,
                    limit=work_item_limit
                )
            
            print(f"📊 Retrieved {len(all_work_items)} work items for LLM analysis")
            
            if not all_work_items:
                messagebox.showinfo("No Work Items", f"No work items found in project '{project_name}'")
                return
            
            # Check if we need to reduce work items for WebSocket size limits
            all_work_items = self._optimize_work_items_for_llm(all_work_items, work_item_limit)
            
            # Start LLM analysis in a separate thread
            threading.Thread(target=self._perform_llm_analysis, 
                           args=(selected_work_item, all_work_items)).start()
                
        except Exception as e:
            error_msg = str(e)
            
            # Handle specific Azure DevOps size limit errors
            if "VS402337" in error_msg or "size limit" in error_msg.lower():
                print(f"❌ Size limit error detected: {error_msg}")
                
                # Try to use pagination method as fallback
                try:
                    print("🔄 Attempting to use pagination method to retrieve work items...")
                    all_work_items = self.client.query_work_items_paginated(
                        project=project_name,
                        team=None,  # No team context in this analysis method
                        work_item_type=None,
                        state=state,
                        page_size=500,  # Smaller page size to avoid VS402337
                        max_pages=40   # More pages to compensate for smaller page size
                    )
                    
                    if all_work_items:
                        print(f"✅ Successfully retrieved {len(all_work_items)} work items using pagination")
                        # Limit to the configured work item limit for LLM analysis
                        all_work_items = all_work_items[:work_item_limit]
                        print(f"📊 Using {len(all_work_items)} work items for LLM analysis")
                        
                        # Start LLM analysis with paginated results
                        threading.Thread(target=self._perform_llm_analysis, 
                                       args=(selected_work_item, all_work_items)).start()
                        return
                    else:
                        raise Exception("No work items returned from pagination method")
                        
                except Exception as pagination_error:
                    print(f"❌ Pagination method also failed: {pagination_error}")
                    error_msg = f"Error starting LLM analysis: {error_msg}\n\n💡 Solution: The project contains too many work items. Try:\n1. Select a more specific team or area\n2. Use work item type filters\n3. Reduce the work item limit in settings\n4. Contact your administrator to increase limits"
                    messagebox.showerror("Work Item Size Limit Error", error_msg)
            else:
                error_msg = f"Error starting LLM analysis: {error_msg}"
                print(f"❌ {error_msg}")
                messagebox.showerror("Error", error_msg)
    
    def _perform_llm_analysis(self, selected_work_item, all_work_items):
        """Perform the actual LLM analysis in a separate thread."""
        try:
            # Create transparent robot icon for the progress window
            try:
                from PIL import Image, ImageDraw, ImageTk
                
                # Create a 32x32 transparent icon
                size = 32
                img = Image.new('RGBA', (size, size), (0, 0, 0, 0))  # Transparent background
                draw = ImageDraw.Draw(img)
                
                # Robot design with transparency
                black = (0, 0, 0, 255)      # Solid black
                white = (255, 255, 255, 255) # Solid white
                transparent = (0, 0, 0, 0)   # Fully transparent
                
                # Robot head (black rectangle with white border, transparent background)
                draw.rectangle([6, 6, size-6, size-6], fill=black, outline=white, width=1)
                
                # Robot eyes (white circles on black)
                left_eye_x, right_eye_x = size//3, 2*size//3
                eye_y = size//3
                eye_size = 3
                
                draw.ellipse([left_eye_x-eye_size, eye_y-eye_size, left_eye_x+eye_size, eye_y+eye_size], 
                            fill=white, outline=black)
                draw.ellipse([right_eye_x-eye_size, eye_y-eye_size, right_eye_x+eye_size, eye_y+eye_size], 
                            fill=white, outline=black)
                
                # Robot mouth (white line)
                mouth_y = 2*size//3
                draw.line([size//4, mouth_y, 3*size//4, mouth_y], fill=white, width=2)
                
                # Robot antenna (white line)
                draw.line([size//2, 6, size//2, 2], fill=white, width=2)
                
                # Convert to PhotoImage
                robot_icon = ImageTk.PhotoImage(img)
                print("✅ Transparent robot icon created successfully!")
                
            except Exception as e:
                print(f"Could not create transparent robot icon: {e}")
                robot_icon = None
            
            # Create a progress window
            progress_window = tk.Toplevel(self.root)
            progress_window.title("🤖 LLM Analysis in Progress")
            progress_window.geometry("700x500")
            progress_window.minsize(600, 400)  # Set minimum size
            progress_window.resizable(True, True)
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            # Set the transparent robot icon on the progress window
            if robot_icon:
                try:
                    # Store reference to prevent garbage collection
                    progress_window._robot_icon = robot_icon
                    
                    # Set the transparent robot icon
                    progress_window.iconphoto(False, robot_icon)
                    print("✅ Transparent robot icon set on progress window!")
                except Exception as e:
                    print(f"Could not set transparent robot icon on progress window: {e}")
            else:
                print("⚠️ No transparent robot icon available, using default")
            
            # Progress content
            progress_frame = ttk.Frame(progress_window, padding="20")
            progress_frame.pack(fill=tk.BOTH, expand=True)
            
            # Header with model and workflow information
            header_frame = ttk.Frame(progress_frame)
            header_frame.pack(fill=tk.X, pady=(0, 15))
            
            ttk.Label(header_frame, text="🤖 OpenArena LLM Analysis", 
                     font=("TkDefaultFont", 14, "bold")).pack()
            
            # Import configuration at the beginning to ensure variables are available
            try:
                from openarena.config.env_config import (
                    OPENARENA_CLAUDE41OPUS_WORKFLOW_ID,
                    OPENARENA_GPT5_WORKFLOW_ID,
                    OPENARENA_GEMINI25PRO_WORKFLOW_ID,
                    OPENARENA_LLAMA3_70B_WORKFLOW_ID
                )
            except ImportError:
                # Fallback values if import fails
                OPENARENA_CLAUDE41OPUS_WORKFLOW_ID = "claude41opus_workflow"
                OPENARENA_GPT5_WORKFLOW_ID = "gpt5_workflow"
                OPENARENA_GEMINI25PRO_WORKFLOW_ID = "gemini25pro_workflow"
                OPENARENA_LLAMA3_70B_WORKFLOW_ID = "llama3_70b_workflow"
            
            # Get selected model and workflow ID for display
            selected_model = getattr(self, 'current_model_var', None)
            if selected_model:
                model_name = selected_model.get()
            else:
                model_name = 'gemini25pro'  # fallback
            
            # Map model names to display names
            model_display_names = {
                'claude41opus': 'Claude 4.1 Opus',
                'gpt5': 'GPT-5',
                'gemini25pro': 'Gemini 2.5 Pro',
                'llama3_70b': 'Llama 3 70b'
            }
            
            # Map model names to workflow IDs
            workflow_ids = {
                'claude41opus': OPENARENA_CLAUDE41OPUS_WORKFLOW_ID,
                'gpt5': OPENARENA_GPT5_WORKFLOW_ID,
                'gemini25pro': OPENARENA_GEMINI25PRO_WORKFLOW_ID,
                'llama3_70b': OPENARENA_LLAMA3_70B_WORKFLOW_ID
            }
            
            workflow_id = workflow_ids.get(model_name, OPENARENA_GEMINI25PRO_WORKFLOW_ID)
            display_name = model_display_names.get(model_name, model_name.title())
            
            # Model and workflow info in a labeled frame
            model_info_frame = ttk.LabelFrame(progress_frame, text="AI Configuration", padding="10")
            model_info_frame.pack(fill=tk.X, pady=(0, 15))
            
            # Create a grid layout for better organization
            ttk.Label(model_info_frame, text="AI Model:", 
                     font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            ttk.Label(model_info_frame, text=display_name, 
                     font=("TkDefaultFont", 10, "bold"), foreground="blue").grid(row=0, column=1, sticky=tk.W)
            
            # Get workflow name for display
            workflow_names = {
                OPENARENA_CLAUDE4OPUS_WORKFLOW_ID: "Claude 4 Opus Analysis Workflow",
                OPENARENA_GPT5_WORKFLOW_ID: "GPT-5 Analysis Workflow", 
                OPENARENA_GEMINI2PRO_WORKFLOW_ID: "Gemini 2 Pro Analysis Workflow",
                OPENARENA_AZUREDEVOPSAGENT_WORKFLOW_ID: "Azure DevOps Agent Analysis Workflow"
            }
            workflow_name = workflow_names.get(workflow_id, "Unknown Workflow")
            
            ttk.Label(model_info_frame, text="Workflow:", 
                     font=("TkDefaultFont", 9, "bold")).grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
            ttk.Label(model_info_frame, text=workflow_name, 
                     font=("TkDefaultFont", 9), foreground="green").grid(row=1, column=1, sticky=tk.W)
            
            ttk.Label(model_info_frame, text="Workflow ID:", 
                     font=("TkDefaultFont", 9, "bold")).grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
            ttk.Label(model_info_frame, text=f"{workflow_id[:8]}...", 
                     font=("TkDefaultFont", 9), foreground="gray").grid(row=2, column=1, sticky=tk.W)
            
            # Progress status
            progress_label = ttk.Label(progress_frame, text="Initializing analysis...", 
                                     font=("TkDefaultFont", 10))
            progress_label.pack(pady=(0, 10))
            
            # Function to update both progress label and status
            def update_progress_and_status(label_text, status_message):
                progress_label.config(text=label_text)
                update_status(status_message)
                progress_window.update()
            
            # Progress bar with better styling
            progress_frame_bar = ttk.Frame(progress_frame)
            progress_frame_bar.pack(fill=tk.X, pady=(0, 15))
            
            ttk.Label(progress_frame_bar, text="Progress:", 
                     font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
            
            progress_bar = ttk.Progressbar(progress_frame_bar, mode='indeterminate', length=300)
            progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
            progress_bar.start()
            
            # Real-time status updates
            status_frame = ttk.LabelFrame(progress_frame, text="Progress Updates", padding="10")
            status_frame.pack(fill=tk.BOTH, expand=True)
            
            # Add a label to show current status
            current_status_label = ttk.Label(status_frame, text="Ready to start analysis...", 
                                           font=("TkDefaultFont", 9, "bold"), foreground="blue")
            current_status_label.pack(anchor=tk.W, pady=(0, 5))
            
            status_text = scrolledtext.ScrolledText(status_frame, wrap=tk.WORD, height=15, 
                                                 font=("Consolas", 10), background="#f8f8f8")
            status_text.pack(fill=tk.BOTH, expand=True)
            
            # Function to update status
            def update_status(message, is_error=False):
                timestamp = datetime.now().strftime("%H:%M:%S")
                color = "red" if is_error else "black"
                status_text.insert(tk.END, f"[{timestamp}] {message}\n")
                status_text.see(tk.END)
                
                # Update current status label
                current_status_label.config(text=message)
                if is_error:
                    current_status_label.config(foreground="red")
                else:
                    current_status_label.config(foreground="blue")
                
                progress_window.update()
            
            # Add a close button at the bottom
            close_button_frame = ttk.Frame(progress_frame)
            close_button_frame.pack(fill=tk.X, pady=(10, 0))
            
            close_button = ttk.Button(close_button_frame, text="❌ Close Progress Window", 
                                    command=progress_window.destroy)
            close_button.pack(side=tk.RIGHT)
            
            # Initial status
            update_progress_and_status("Starting LLM analysis...", "🚀 Starting LLM analysis...")
            
            # Extract work item data
            update_progress_and_status("Extracting work item data...", "📊 Extracting work item data...")
            selected_item_data = self._extract_work_item_data(selected_work_item)
            all_items_data = [self._extract_work_item_data(item) for item in all_work_items]
            update_progress_and_status("Data extraction complete", f"📊 Extracted data from {len(all_items_data)} work items")
            
            # Create system prompt for LLM using the modified prompt generator
            update_progress_and_status("Creating system prompt...", "🤖 Creating system prompt for LLM...")
            system_prompt = ADOWorkItemAnalysisPrompt.modify_system_prompt(selected_item_data, all_items_data)
            # Store the system prompt for display in the System Prompt tab
            self.current_system_prompt = system_prompt
            update_progress_and_status("System prompt ready", "✅ System prompt created successfully")
            
            # Update progress
            update_progress_and_status("Sending to OpenArena LLM...", "🚀 Sending to OpenArena LLM...")
            
                        # Send to OpenArena LLM using direct WebSocket approach (same as working test)
            try:
                update_progress_and_status("Connecting to OpenArena...", "Connecting to OpenArena WebSocket...")
                print("Connecting to OpenArena WebSocket directly...")
                
                # Import required modules
                import json
                import time
                from websockets.sync.client import connect
                
                # Get configuration
                from openarena.config.env_config import (
                    OPENARENA_ESSO_TOKEN,
                    OPENARENA_WEBSOCKET_URL
                )
                
                # Get selected model and workflow ID
                selected_model = getattr(self, 'current_model_var', None)
                if selected_model:
                    model_name = selected_model.get()
                else:
                    model_name = 'gemini2pro'  # fallback
                
                # Update status with model and workflow info
                update_status(f"Using AI Model: {model_display_names.get(model_name, model_name.title())}")
                update_status(f"Workflow: {workflow_name}")
                update_status(f"Workflow ID: {workflow_id[:8]}...")
                
                # Build WebSocket URL with authorization (same as working test)
                esso_token = OPENARENA_ESSO_TOKEN
                if esso_token.startswith('bearer '):
                    esso_token = esso_token[7:]  # Remove 'bearer ' prefix
                
                ws_url = f"{OPENARENA_WEBSOCKET_URL}/?Authorization={esso_token}"
                update_status(f"Establishing WebSocket connection...")
                print(f"Connecting to: {ws_url}")
                
                # Establish connection (same as working test)
                connection_start = time.time()
                ws = connect(ws_url)
                connection_time = time.time() - connection_start
                update_progress_and_status("Connected to OpenArena", f"✅ Connected successfully in {connection_time:.2f}s")
                print(f"✅ Connected successfully in {connection_time:.2f}s")
                
                # Prepare and send message (same as working test)
                message = {
                    "action": "SendMessage",
                    "workflow_id": workflow_id,
                    "query": system_prompt,
                    "is_persistence_allowed": False
                }
                
                msg_json = json.dumps(message)
                update_progress_and_status(f"Sending to {model_name}...", f"📤 Sending message to {model_name}...")
                print(f"📤 Sending message to {model_name}...")
                
                send_start = time.time()
                ws.send(msg_json)
                send_time = time.time() - send_start
                update_progress_and_status("Message sent, waiting for response...", f"📨 Message sent in {send_time:.2f}s")
                print(f"📨 Message sent in {send_time:.2f}s")
                
                # Receive response (same as working test)
                update_progress_and_status("Receiving LLM response...", "📥 Receiving response from LLM...")
                print("📥 Receiving response...")
                answer = ""
                cost_tracker = {}
                eof = False
                message_count = 0
                start_time = time.time()
                
                while not eof:
                    try:
                        message = ws.recv()
                        message_count += 1
                        update_status(f"📨 Received message #{message_count}")
                        print(f"📨 Received message #{message_count}")
                        
                        message_data = json.loads(message)
                        
                        for model, value in message_data.items():
                            if "answer" in value:
                                answer += value["answer"]
                                update_status(f"📝 Processing response chunk #{message_count}")
                            elif "cost_track" in value:
                                cost_tracker = value['cost_track']
                                update_progress_and_status("Finalizing analysis...", "💰 Cost tracking received, completing analysis...")
                                eof = True
                                
                    except json.JSONDecodeError as e:
                        error_msg = f"⚠️ JSON decode error: {e}"
                        update_status(error_msg, is_error=True)
                        print(error_msg)
                        continue
                    except Exception as e:
                        error_msg = f"⚠️ Error receiving message: {e}"
                        update_status(error_msg, is_error=True)
                        print(error_msg)
                        break
                
                # Calculate total response time
                total_time = time.time() - start_time
                update_progress_and_status("Response received", f"✅ Response received in {total_time:.2f}s")
                print(f"✅ Response received in {total_time:.2f}s")
                update_status(f"📊 Total messages processed: {message_count}")
                print(f"📊 Total messages: {message_count}")
                
                # Close WebSocket connection
                update_progress_and_status("Closing connection...", "🔌 Closing WebSocket connection...")
                ws.close()
                update_status("🔌 WebSocket connection closed")
                print("🔌 WebSocket connection closed")
                
                if not answer:
                    update_status("❌ No response received from OpenArena", is_error=True)
                    raise Exception("No response received from OpenArena")
                
                update_progress_and_status("Analysis completed!", "✅ LLM analysis completed successfully!")
                print("✅ LLM analysis completed successfully")
                
                # Final status update
                update_status("🎉 Analysis complete! Closing progress window...")
                
                # Show final summary
                summary_frame = ttk.LabelFrame(progress_frame, text="Analysis Summary", padding="15")
                summary_frame.pack(fill=tk.X, pady=(10, 0))
                
                # Create a more detailed summary with better formatting
                summary_text = f"""✅ LLM Analysis Completed Successfully!

🤖 AI Model: {model_display_names.get(model_name, model_name.title())}
🔧 Workflow: {workflow_name}
📊 Work Items Analyzed: {len(all_items_data)}
📝 Response Length: {len(answer)} characters
💰 Cost: ${cost_tracker.get('cost', 0):.4f} ({cost_tracker.get('tokens_used', 0)} tokens)
⏱️ Total Time: {total_time:.2f} seconds
📨 Messages Processed: {message_count}
🔌 Connection Time: {connection_time:.2f}s
📤 Send Time: {send_time:.2f}s
📥 Response Time: {total_time:.2f}s"""
                
                # Use a text widget for better formatting
                summary_text_widget = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, height=8, 
                                                             font=("Consolas", 10), background="#f0f8ff")
                summary_text_widget.pack(fill=tk.X, expand=True)
                summary_text_widget.insert(tk.END, summary_text)
                summary_text_widget.configure(state="disabled")
                
                progress_window.after(3000, progress_window.destroy)  # Close after 3 seconds to show summary
                
                # Display results
                self._display_llm_analysis_results(selected_work_item, answer, cost_tracker, all_work_items)
                
            except Exception as e:
                error_msg = f"OpenArena connection failed: {e}"
                update_status(f"❌ {error_msg}", is_error=True)
                print(f"OpenArena connection failed: {e}")
                
                # Close progress window
                progress_window.destroy()
                
                # Show detailed error message to user
                error_details = f"""OpenArena LLM Analysis Failed

The system was unable to connect to OpenArena for LLM analysis.

Error Details:
{str(e)}

Possible Causes:
• Authentication failure (ESSO token expired or invalid)
• Network connectivity issues
• OpenArena service unavailable
• Incorrect WebSocket URL configuration

To resolve this issue:
1. Check your OpenArena ESSO token in src/openarena/config/env_config.py
2. Verify the WebSocket URL is correct
3. Ensure you have network access to OpenArena
4. Contact your OpenArena administrator if the issue persists

Note: The system will not fall back to mock responses to ensure you're aware of the connection issue."""
                
                # Create error dialog
                error_window = tk.Toplevel(self.root)
                error_window.title("LLM Analysis Failed")
                error_window.geometry("600x500")
                error_window.resizable(True, True)
                error_window.transient(self.root)
                error_window.grab_set()
                
                # Error content
                error_frame = ttk.Frame(error_window, padding="20")
                error_frame.pack(fill=tk.BOTH, expand=True)
                
                # Error icon and title
                ttk.Label(error_frame, text="❌ LLM Analysis Failed", 
                         font=("TkDefaultFont", 14, "bold"), 
                         foreground="red").pack(pady=(0, 20))
                
                # Error details in scrollable text
                error_text = scrolledtext.ScrolledText(error_frame, wrap=tk.WORD, height=20)
                error_text.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
                error_text.insert(tk.END, error_details)
                error_text.configure(state="disabled")
                
                # Buttons
                button_frame = ttk.Frame(error_frame)
                button_frame.pack(fill=tk.X)
                
                # Retry button
                retry_button = ttk.Button(button_frame, text="🔄 Retry Analysis", 
                                        command=lambda: self._retry_llm_analysis(selected_work_item, all_work_items, error_window))
                retry_button.pack(side=tk.LEFT, padx=(0, 10))
                
                # Close button
                close_button = ttk.Button(button_frame, text="Close", 
                                        command=error_window.destroy)
                close_button.pack(side=tk.LEFT)
                
        except Exception as e:
            print(f"Error in LLM analysis: {e}")
            # Close progress window
            progress_window.destroy()
            messagebox.showerror("Error", f"LLM analysis failed: {str(e)}")
    
    def _retry_llm_analysis(self, selected_work_item, all_work_items, error_window):
        """Retry LLM analysis after a connection failure."""
        # Close the error window
        error_window.destroy()
        
        # Wait a moment for the window to close
        self.root.after(100, lambda: self._perform_llm_analysis(selected_work_item, all_work_items))
    
    def _extract_work_item_data(self, work_item):
        """Extract relevant data from a work item for LLM analysis."""
        # Get and clean description
        description = work_item.fields.get('System.Description', '')
        if description:
            # Remove HTML tags if present
            if '<' in description and '>' in description:
                import re
                description = re.sub('<[^<]+?>', '', description)
                description = re.sub('\s+', ' ', description).strip()
            description = description.strip()
        
        if not description:
            description = 'No description available'
            print(f"⚠️ Work item {work_item.id} has no description field")
        else:
            print(f"✅ Work item {work_item.id} has description: {description[:50]}{'...' if len(description) > 50 else ''}")
        
        return {
            'id': work_item.id,
            'title': work_item.fields.get('System.Title', 'No Title'),
            'description': description,
            'work_item_type': work_item.fields.get('System.WorkItemType', 'Unknown'),
            'state': work_item.fields.get('System.State', 'Unknown'),
            'assigned_to': self.get_assigned_to_display_name(work_item.fields.get('System.AssignedTo', 'Unassigned')),
            'tags': work_item.fields.get('System.Tags', ''),
            'created_by': work_item.fields.get('System.CreatedBy', 'Unknown'),
            'created_date': work_item.fields.get('System.CreatedDate', 'Unknown'),
            'priority': work_item.fields.get('Microsoft.VSTS.Common.Priority', 'Not set'),
            'severity': work_item.fields.get('Microsoft.VSTS.Common.Severity', 'Not set'),
            'effort': work_item.fields.get('Microsoft.VSTS.Scheduling.Effort', 'Not set'),
            'story_points': work_item.fields.get('Microsoft.VSTS.Scheduling.StoryPoints', 'Not set'),
            'area_path': work_item.fields.get('System.AreaPath', ''),
            'iteration_path': work_item.fields.get('System.IterationPath', '')
        }
    
    # Note: LLM system prompt generation is now handled by ADOWorkItemAnalysisPrompt class
    
    # Note: Work item formatting is now handled by ADOWorkItemAnalysisPrompt class
    
    def _display_llm_analysis_results(self, selected_work_item, llm_response, cost_tracker, all_work_items):
        """Display the LLM analysis results in the LLM Analysis Results tab."""
        # Switch to the LLM Analysis Results tab
        self.work_items_notebook.select(4)  # Index 4 is the LLM Analysis Results tab (after Refine Related Work Items sub-tab)
        
        # Clear previous content
        self.llm_analysis_text.configure(state="normal")
        self.llm_analysis_text.delete(1.0, tk.END)
        
        # Configure text widget with better styling
        self._configure_llm_text_styling()
        
        # Create header with work item information
        header_text = f"🤖 LLM Analysis Results for Work Item {selected_work_item.id}\n"
        header_text += f"📋 Title: {selected_work_item.fields.get('System.Title', 'No Title')}\n"
        header_text += "=" * 80 + "\n\n"
        
        # Add cost information if available
        if cost_tracker and 'cost' in cost_tracker:
            cost_info = f"💰 Analysis Cost: ${cost_tracker.get('cost', 0):.4f} ({cost_tracker.get('tokens_used', 0)} tokens)\n"
            header_text += cost_info + "=" * 80 + "\n\n"
        
        # Insert header
        self.llm_analysis_text.insert(tk.END, header_text, "header")
        
        # Add hierarchy information for the selected work item
        try:
            hierarchy = self.client.get_work_item_hierarchy(selected_work_item.id)
            if hierarchy:
                hierarchy_text = self.client.get_work_item_hierarchy_display_text(hierarchy)
                self.llm_analysis_text.insert(tk.END, "📊 SELECTED WORK ITEM HIERARCHY\n", "subheader")
                self.llm_analysis_text.insert(tk.END, "=" * 50 + "\n\n", "subheader")
                self.llm_analysis_text.insert(tk.END, hierarchy_text)
                self.llm_analysis_text.insert(tk.END, "\n" + "=" * 80 + "\n\n")
        except Exception as e:
            logger.warning(f"Could not get hierarchy for selected work item: {e}")
            self.llm_analysis_text.insert(tk.END, "📊 SELECTED WORK ITEM HIERARCHY\n", "subheader")
            self.llm_analysis_text.insert(tk.END, "=" * 50 + "\n\n", "subheader")
            self.llm_analysis_text.insert(tk.END, "❌ Could not retrieve hierarchy information.\n\n")
            self.llm_analysis_text.insert(tk.END, "=" * 80 + "\n\n")
        
        # Format and insert the LLM response with rich formatting
        self._insert_formatted_llm_response(llm_response)
        
        # Add hierarchy information for related work items mentioned in the LLM response
        self._add_related_work_items_hierarchy(llm_response, all_work_items)
        
        # Add action buttons at the bottom
        button_frame = ttk.Frame(self.llm_results_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Store reference to button frame for later removal
        self.llm_analysis_button_frame = button_frame
        
        # Display the system prompt in the System Prompt tab
        self._display_system_prompt()
        
        # Display all work items in the All Work Items tab
        self._display_all_work_items(all_work_items)
        
        # Copy to clipboard button
        copy_button = ttk.Button(button_frame, text="📋 Copy to Clipboard", 
                               command=lambda: self._copy_to_clipboard(llm_response))
        copy_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Export to file button
        export_button = ttk.Button(button_frame, text="💾 Export to File", 
                                 command=lambda: self._export_analysis_to_file(selected_work_item, llm_response))
        export_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Launch Modern UI button
        modern_ui_button = ttk.Button(button_frame, text="🎨 Launch Modern UI", 
                                    command=lambda: self._launch_modern_ui_with_analysis(selected_work_item, llm_response, all_work_items))
        modern_ui_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Clear button
        clear_button = ttk.Button(button_frame, text="🗑️ Clear Results", 
                                command=self._clear_llm_analysis_results)
        clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Configure text widget as read-only
        self.llm_analysis_text.configure(state="disabled")
        
        # Show success message
        messagebox.showinfo("Success", f"LLM analysis completed for Work Item {selected_work_item.id}!\nResults displayed in the 'LLM Analysis Results' tab.")
    
    def _launch_modern_ui_with_analysis(self, selected_work_item, llm_response, all_work_items):
        """Launch the modern UI with the current analysis results."""
        try:
            print(f"🎨 Launching Modern UI for Work Item {selected_work_item.id}...")
            
            # Create a temporary data file with the analysis results
            analysis_data = self._prepare_analysis_data_for_modern_ui(selected_work_item, llm_response, all_work_items)
            
            # Save analysis data to a temporary file
            import tempfile
            import json
            import os
            
            temp_dir = tempfile.gettempdir()
            analysis_file = os.path.join(temp_dir, f"ado_analysis_{selected_work_item.id}.json")
            
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            
            print(f"📁 Analysis data saved to: {analysis_file}")
            
            # Launch the modern UI with the work item ID
            self._start_modern_ui_backend(selected_work_item.id)
            
            # Show info message
            messagebox.showinfo("Modern UI Launched", 
                              f"Modern UI launched for Work Item {selected_work_item.id}!\n"
                              f"🌐 The application should open in your browser at http://localhost:5000\n"
                              f"📊 Analysis data has been prepared and will be displayed in the modern interface.")
            
        except Exception as e:
            print(f"❌ Error launching Modern UI: {e}")
            messagebox.showerror("Error", f"Failed to launch Modern UI: {str(e)}")
    
    def _prepare_analysis_data_for_modern_ui(self, selected_work_item, llm_response, all_work_items):
        """Prepare analysis data in the format expected by the modern UI."""
        try:
            # Get hierarchy information
            hierarchy = []
            try:
                hierarchy = self.client.get_work_item_hierarchy(selected_work_item.id)
            except Exception as e:
                print(f"Warning: Could not get hierarchy: {e}")
            
            # Parse LLM response to extract related work items with confidence scores
            related_work_items = self._parse_llm_response_for_modern_ui(llm_response, all_work_items)
            
            # Format selected work item
            selected_work_item_data = {
                'id': selected_work_item.id,
                'title': selected_work_item.fields.get('System.Title', 'No Title'),
                'type': selected_work_item.fields.get('System.WorkItemType', 'Unknown'),
                'state': selected_work_item.fields.get('System.State', 'Unknown'),
                'assignedTo': selected_work_item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned') if isinstance(selected_work_item.fields.get('System.AssignedTo'), dict) else str(selected_work_item.fields.get('System.AssignedTo', 'Unassigned')),
                'areaPath': selected_work_item.fields.get('System.AreaPath', ''),
                'iterationPath': selected_work_item.fields.get('System.IterationPath', ''),
                'description': selected_work_item.fields.get('System.Description', ''),
                'reason': selected_work_item.fields.get('System.Reason', '')
            }
            
            # Format hierarchy
            hierarchy_data = []
            if hierarchy and isinstance(hierarchy, dict):
                # Process hierarchy_path which contains the actual work items
                hierarchy_path = hierarchy.get('hierarchy_path', [])
                print(f"🔍 Debug: Processing hierarchy_path with {len(hierarchy_path)} items")
                
                for item in hierarchy_path:
                    try:
                        # Debug: Check item type
                        print(f"🔍 Debug: Processing hierarchy item type: {type(item)}")
                        if hasattr(item, 'id'):
                            hierarchy_data.append({
                                'id': item.id,
                                'title': item.fields.get('System.Title', 'No Title'),
                                'type': item.fields.get('System.WorkItemType', 'Unknown'),
                                'state': item.fields.get('System.State', 'Unknown'),
                                'assignedTo': item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned') if isinstance(item.fields.get('System.AssignedTo'), dict) else str(item.fields.get('System.AssignedTo', 'Unassigned')),
                                'areaPath': item.fields.get('System.AreaPath', ''),
                                'iterationPath': item.fields.get('System.IterationPath', ''),
                                'description': item.fields.get('System.Description', ''),
                                'reason': item.fields.get('System.Reason', '')
                            })
                        else:
                            print(f"⚠️ Warning: Hierarchy item {item} does not have 'id' attribute, skipping")
                    except Exception as e:
                        print(f"⚠️ Error processing hierarchy item {item}: {e}")
                        continue
            else:
                print(f"🔍 Debug: Hierarchy is not a dict or is empty: {type(hierarchy)}")
            
            # Generate analysis insights
            insights = self._generate_analysis_insights_for_modern_ui(related_work_items, selected_work_item_data, llm_response)
            
            return {
                'selectedWorkItem': selected_work_item_data,
                'hierarchy': hierarchy_data,
                'relatedWorkItems': related_work_items,
                'analysisInsights': insights,
                'llmResponse': llm_response,
                'costInfo': {
                    'cost': 0.0234,  # Mock cost - you can get this from cost_tracker if available
                    'tokens': 1250,  # Mock tokens
                    'model': 'gpt-4',
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            print(f"Error preparing analysis data: {e}")
            import traceback
            traceback.print_exc()
            # Return a minimal structure instead of empty dict
            return {
                'selectedWorkItem': {
                    'id': selected_work_item.id,
                    'title': selected_work_item.fields.get('System.Title', 'No Title'),
                    'type': selected_work_item.fields.get('System.WorkItemType', 'Unknown'),
                    'state': selected_work_item.fields.get('System.State', 'Unknown'),
                    'assignedTo': 'Unknown',
                    'areaPath': '',
                    'iterationPath': '',
                    'description': '',
                    'reason': ''
                },
                'hierarchy': [],
                'relatedWorkItems': [],
                'analysisInsights': {
                    'risks': [],
                    'opportunities': [],
                    'dependencies': [],
                    'recommendations': [],
                    'summary': {
                        'totalRelatedItems': 0,
                        'highConfidenceItems': 0,
                        'mediumConfidenceItems': 0,
                        'lowConfidenceItems': 0,
                        'risksIdentified': 0,
                        'opportunitiesFound': 0,
                        'dependenciesFound': 0,
                        'recommendationsGenerated': 0
                    }
                },
                'llmResponse': llm_response,
                'costInfo': {
                    'cost': 0.0234,
                    'tokens': 1250,
                    'model': 'gpt-4',
                    'timestamp': datetime.now().isoformat()
                }
            }
    
    def _parse_llm_response_for_modern_ui(self, llm_response, all_work_items):
        """Parse LLM response to extract related work items with confidence scores."""
        related_work_items = []
        
        try:
            # Debug: Check what all_work_items contains
            print(f"🔍 Debug: all_work_items type: {type(all_work_items)}")
            print(f"🔍 Debug: all_work_items length: {len(all_work_items) if hasattr(all_work_items, '__len__') else 'N/A'}")
            if all_work_items and len(all_work_items) > 0:
                print(f"🔍 Debug: First item type: {type(all_work_items[0])}")
                if hasattr(all_work_items[0], 'id'):
                    print(f"🔍 Debug: First item ID: {all_work_items[0].id}")
                else:
                    print(f"🔍 Debug: First item content: {str(all_work_items[0])[:100]}...")
            
            # This is a simplified parser - you can enhance this based on your LLM response format
            lines = llm_response.split('\n')
            
            print(f"🔍 Debug: Parsing LLM response with {len(lines)} lines")
            print(f"🔍 Debug: First few lines of LLM response:")
            for i, line in enumerate(lines[:10]):
                print(f"  {i}: {line}")
            
            # First pass: collect all work item IDs with their confidence levels
            work_item_confidence_map = {}
            current_confidence = 'low'  # Default confidence
            
            for line in lines:
                line = line.strip()
                
                # Check for confidence section headers
                if '## HIGH CONFIDENCE RELATIONSHIPS' in line.upper():
                    current_confidence = 'high'
                    print(f"🔍 Debug: Found HIGH CONFIDENCE section")
                    continue
                elif '## MEDIUM CONFIDENCE RELATIONSHIPS' in line.upper():
                    current_confidence = 'medium'
                    print(f"🔍 Debug: Found MEDIUM CONFIDENCE section")
                    continue
                elif '## LOW CONFIDENCE RELATIONSHIPS' in line.upper():
                    current_confidence = 'low'
                    print(f"🔍 Debug: Found LOW CONFIDENCE section")
                    continue
                elif line.startswith('##') and 'RELATIONSHIPS' in line.upper():
                    # Other relationship sections - default to low
                    current_confidence = 'low'
                    print(f"🔍 Debug: Found other relationship section: {line}")
                    continue
                
                # Debug: Show lines that contain work item IDs
                if any(char.isdigit() for char in line) and ('ID:' in line or '#' in line):
                    print(f"🔍 Debug: Line with potential work item ID: '{line}'")
                
                # Look for work item references in the response - handle both formats
                work_item_ids = []
                
                # Format 1: - **ID:** 12345 (from the images)
                if '- **ID:' in line and any(char.isdigit() for char in line):
                    import re
                    work_item_ids = re.findall(r'- \*\*ID:\s*(\d+)', line)
                    if not work_item_ids:
                        # Try alternative pattern with different spacing
                        work_item_ids = re.findall(r'- \*\*ID:\s*(\d+)', line)
                    print(f"🔍 Debug: Found Format 1 work item IDs: {work_item_ids} in line: {line}")
                
                # Format 1c: ### 1. ID: 12345 (new LLM format)
                elif '###' in line and 'ID:' in line and any(char.isdigit() for char in line):
                    import re
                    work_item_ids = re.findall(r'### \d+\. ID:\s*(\d+)', line)
                    print(f"🔍 Debug: Found Format 1c work item IDs: {work_item_ids} in line: {line}")
                
                # Format 1b: - **IDs:** 12345, 67890 (multiple IDs)
                elif '- **IDs:' in line and any(char.isdigit() for char in line):
                    import re
                    work_item_ids = re.findall(r'- \*\*IDs:\s*([\d,\s]+)', line)
                    if work_item_ids:
                        # Split by comma and extract individual IDs
                        id_string = work_item_ids[0]
                        work_item_ids = re.findall(r'(\d+)', id_string)
                    print(f"🔍 Debug: Found Format 1b work item IDs: {work_item_ids} in line: {line}")
                
                # Format 2: #12345 (legacy format)
                elif '#' in line and any(char.isdigit() for char in line):
                    import re
                    work_item_ids = re.findall(r'#(\d+)', line)
                    print(f"🔍 Debug: Found Format 2 work item IDs: {work_item_ids} in line: {line}")
                
                # Format 3: Just numbers that look like work item IDs (6+ digits)
                elif any(char.isdigit() for char in line) and not line.startswith('##'):
                    import re
                    # Look for 6+ digit numbers that could be work item IDs
                    potential_ids = re.findall(r'\b(\d{6,})\b', line)
                    work_item_ids = potential_ids
                    if work_item_ids:
                        print(f"🔍 Debug: Found Format 3 work item IDs: {work_item_ids} in line: {line}")
                
                # Store work item IDs with their confidence level
                for work_item_id in work_item_ids:
                    work_item_id = int(work_item_id)
                    # Only store if we haven't seen this ID before, or if current confidence is higher
                    if work_item_id not in work_item_confidence_map:
                        work_item_confidence_map[work_item_id] = current_confidence
                        print(f"🔍 Debug: Mapped work item {work_item_id} to confidence: {current_confidence} (from line: '{line}')")
                    else:
                        print(f"🔍 Debug: Work item {work_item_id} already mapped to {work_item_confidence_map[work_item_id]}, skipping")
            
            # Second pass: create related work items with stored confidence levels
            for work_item_id, confidence in work_item_confidence_map.items():
                # Find the work item in all_work_items
                related_item = next((item for item in all_work_items if hasattr(item, 'id') and item.id == work_item_id), None)
                
                if related_item:
                    # Determine relationship type
                    relationship_type = self._determine_relationship_type("", related_item)
                    
                    # Extract reasoning
                    reasoning = self._extract_reasoning("", related_item)
                    
                    print(f"🔍 Debug: Adding work item {work_item_id} with confidence: {confidence}")
                    
                    related_work_items.append({
                        'id': related_item.id,
                        'title': related_item.fields.get('System.Title', 'No Title'),
                        'type': related_item.fields.get('System.WorkItemType', 'Unknown'),
                        'state': related_item.fields.get('System.State', 'Unknown'),
                        'assignedTo': related_item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned') if isinstance(related_item.fields.get('System.AssignedTo'), dict) else str(related_item.fields.get('System.AssignedTo', 'Unassigned')),
                        'areaPath': related_item.fields.get('System.AreaPath', ''),
                        'iterationPath': related_item.fields.get('System.IterationPath', ''),
                        'description': related_item.fields.get('System.Description', ''),
                        'confidence': confidence,
                        'relationshipType': relationship_type,
                        'reasoning': reasoning,
                        'lastUpdated': 'Recently'
                    })
            
            # Remove duplicates
            seen_ids = set()
            unique_related_items = []
            for item in related_work_items:
                if item['id'] not in seen_ids:
                    unique_related_items.append(item)
                    seen_ids.add(item['id'])
            
            # Sort by confidence
            unique_related_items.sort(key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x['confidence'], 0), reverse=True)
            
            print(f"🔍 Debug: Final parsed related work items count: {len(unique_related_items)}")
            for item in unique_related_items:
                print(f"  - ID: {item['id']}, Title: {item['title'][:50]}..., Confidence: {item['confidence']}")
            
            return unique_related_items
            
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return []
    
    def _determine_confidence_score(self, line, related_item):
        """Determine confidence score based on context analysis."""
        line_lower = line.lower()
        
        # High confidence indicators
        high_indicators = ['directly related', 'strong relationship', 'dependency', 'prerequisite', 'blocking']
        if any(indicator in line_lower for indicator in high_indicators):
            return 'high'
        
        # Medium confidence indicators
        medium_indicators = ['related', 'similar', 'associated', 'part of', 'related to']
        if any(indicator in line_lower for indicator in medium_indicators):
            return 'medium'
        
        # Default to low confidence
        return 'low'
    
    def _determine_relationship_type(self, line, related_item):
        """Determine relationship type based on context analysis."""
        line_lower = line.lower()
        
        if 'dependency' in line_lower or 'prerequisite' in line_lower:
            return 'dependency'
        elif 'feature' in line_lower or 'enhancement' in line_lower:
            return 'feature'
        elif 'bug' in line_lower or 'fix' in line_lower:
            return 'bug'
        elif 'blocking' in line_lower:
            return 'blocking'
        else:
            return 'related'
    
    def _extract_reasoning(self, line, related_item):
        """Extract reasoning from the LLM response line."""
        return f"AI identified relationship based on analysis of work item content and context. {line[:200]}..."
    
    def _generate_analysis_insights_for_modern_ui(self, related_work_items, selected_work_item, llm_response=None):
        """Generate analysis insights based on related work items and LLM response."""
        
        # Count confidence levels
        confidence_counts = {}
        for item in related_work_items:
            confidence = item['confidence']
            confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
        
        # Parse LLM response for detailed analysis if available
        relationship_patterns = []
        risk_assessment = []
        recommendations = []
        
        if llm_response:
            lines = llm_response.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                
                # Check for analysis section headers
                if '## RELATIONSHIP PATTERNS ANALYSIS' in line.upper():
                    current_section = 'patterns'
                    continue
                elif '## RISK ASSESSMENT' in line.upper():
                    current_section = 'risk'
                    continue
                elif '## RECOMMENDATIONS' in line.upper():
                    current_section = 'recommendations'
                    continue
                elif line.startswith('##') and not 'RELATIONSHIPS' in line.upper():
                    current_section = None
                    continue
                
                # Process content based on current section
                if current_section == 'patterns' and line and not line.startswith('#'):
                    relationship_patterns.append(line)
                elif current_section == 'risk' and line and not line.startswith('#'):
                    risk_assessment.append(line)
                elif current_section == 'recommendations' and line and not line.startswith('#'):
                    recommendations.append(line)
                
                # Also look for specific risk and recommendation patterns in any section
                if line and not line.startswith('#'):
                    # Look for risk indicators
                    if any(keyword in line.lower() for keyword in ['risk', 'blocking', 'conflict', 'dependency', 'issue', 'problem']):
                        if current_section != 'risk':  # Don't duplicate if already in risk section
                            risk_assessment.append(line)
                    
                    # Look for recommendation indicators
                    if any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'action', 'consider', 'should', 'must', 'coordinate', 'review', 'audit']):
                        if current_section != 'recommendations':  # Don't duplicate if already in recommendations section
                            recommendations.append(line)
        
        # Generate risks from extracted risk assessment or fallback to generated ones
        risks = []
        if risk_assessment:
            # Process extracted risk assessment content - be more selective
            for line in risk_assessment:
                if line.strip() and not line.startswith('#'):
                    # Look for risk indicators in the line
                    if any(keyword in line.lower() for keyword in ['risk', 'blocking', 'conflict', 'dependency', 'issue', 'problem']):
                        # Skip very short or generic lines
                        if len(line.strip()) < 20:
                            continue
                        
                        # Skip lines that are just titles or headers
                        if line.strip().endswith(':') or line.strip().startswith('**') and line.strip().endswith('**'):
                            continue
                        
                        # Extract title and description from the line
                        title = 'AI Identified Risk'
                        description = line.strip()
                        
                        # Try to extract a more specific title
                        if ':' in line:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                potential_title = parts[0].strip()
                                if len(potential_title) < 50 and len(potential_title) > 5:  # Reasonable title length
                                    title = potential_title
                                    description = parts[1].strip()
                        
                        # Determine severity based on keywords
                        severity = 'low'
                        if any(word in line.lower() for word in ['high', 'critical', 'urgent', 'blocking', 'failing']):
                            severity = 'high'
                        elif any(word in line.lower() for word in ['medium', 'significant', 'important']):
                            severity = 'medium'
                        
                        # Only add if we have meaningful content
                        if len(description) > 10:
                            risks.append({
                                'title': title,
                                'description': description,
                                'severity': severity
                            })
        else:
            # Fallback to generated risks
            if confidence_counts.get('low', 0) > 2:
                risks.append({
                    'title': 'Multiple Low Confidence Items',
                    'description': f"Found {confidence_counts['low']} items with low confidence relationships. Review these carefully.",
                    'severity': 'medium'
                })
        
        # Generate opportunities
        opportunities = []
        
        # Add opportunities based on confidence levels
        if confidence_counts.get('high', 0) > 3:
            opportunities.append({
                'title': 'Strong Relationship Network',
                'description': f"Found {confidence_counts['high']} high-confidence relationships. Consider coordinating these work items.",
                'type': 'optimization'
            })
        
        # Add opportunities based on relationship patterns
        if relationship_patterns:
            for line in relationship_patterns:
                if line.strip() and not line.startswith('#'):
                    # Look for opportunity indicators
                    if any(keyword in line.lower() for keyword in ['opportunity', 'optimization', 'enhancement', 'improvement', 'coordinate', 'leverage', 'shared']):
                        opportunities.append({
                            'title': 'Pattern-Based Opportunity',
                            'description': line.strip(),
                            'type': 'enhancement'
                        })
        
        # Add opportunities based on cross-team dependencies
        if any('cross-team' in line.lower() or 'team' in line.lower() for line in relationship_patterns):
            opportunities.append({
                'title': 'Cross-Team Coordination',
                'description': "Multiple teams are involved in related work items. Consider establishing cross-team coordination.",
                'type': 'coordination'
            })
        
        # Generate recommendations from extracted content or fallback to generated ones
        recommendations_list = []
        if recommendations:
            # Process extracted recommendations content - be more selective
            for line in recommendations:
                if line.strip() and not line.startswith('#'):
                    # Look for recommendation indicators in the line
                    if any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'action', 'consider', 'should', 'must', 'coordinate', 'review', 'audit']):
                        # Skip very short or generic lines
                        if len(line.strip()) < 20:
                            continue
                        
                        # Skip lines that are just titles or headers
                        if line.strip().endswith(':') or line.strip().startswith('**') and line.strip().endswith('**'):
                            continue
                        
                        # Extract title and description from the line
                        title = 'AI Recommendation'
                        description = line.strip()
                        
                        # Try to extract a more specific title
                        if ':' in line:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                potential_title = parts[0].strip()
                                if len(potential_title) < 50 and len(potential_title) > 5:  # Reasonable title length
                                    title = potential_title
                                    description = parts[1].strip()
                        elif line.startswith('- '):
                            # Handle bullet point format
                            title = line[2:].strip()
                            description = line[2:].strip()
                        
                        # Determine priority based on keywords
                        priority = 'medium'
                        if any(word in line.lower() for word in ['critical', 'urgent', 'immediate', 'high', 'priority']):
                            priority = 'high'
                        elif any(word in line.lower() for word in ['low', 'optional', 'consider']):
                            priority = 'low'
                        
                        # Only add if we have meaningful content and avoid duplicates
                        if len(description) > 10 and not any(existing['title'] == title for existing in recommendations_list):
                            recommendations_list.append({
                                'title': title,
                                'description': description,
                                'priority': priority
                            })
        else:
            # Fallback to generated recommendations
            if confidence_counts.get('high', 0) > 0:
                recommendations_list.append({
                    'title': 'Prioritize High Confidence Items',
                    'description': "Focus on work items with high confidence relationships first.",
                    'priority': 'high'
                })
        
        return {
            'risks': risks,
            'opportunities': opportunities,
            'dependencies': [],
            'recommendations': recommendations_list,
            'summary': {
                'totalRelatedItems': len(related_work_items),
                'highConfidenceItems': confidence_counts.get('high', 0),
                'mediumConfidenceItems': confidence_counts.get('medium', 0),
                'lowConfidenceItems': confidence_counts.get('low', 0),
                'risksIdentified': len(risks),
                'opportunitiesFound': len(opportunities),
                'dependenciesFound': 0,
                'recommendationsGenerated': len(recommendations_list)
            }
        }
    
    def _start_modern_ui_backend(self, work_item_id):
        """Open the modern UI in browser (backend should already be running)."""
        try:
            import webbrowser
            import requests
            
            # Check if the backend is already running
            try:
                response = requests.get('http://localhost:5000', timeout=2)
                if response.status_code == 200:
                    print("✅ Modern UI backend is already running")
                else:
                    print("⚠️ Modern UI backend responded with unexpected status")
            except requests.exceptions.RequestException:
                print("❌ Modern UI backend is not running")
                print("💡 Please start the application with: python app/main/launch_azure_devops_ai_studio.py --mode gui")
                messagebox.showerror("Modern UI Not Available", 
                                   "The modern UI backend is not running.\n"
                                   "Please restart the application with the GUI mode to start all services.")
                return
            
            # Open browser to the modern UI
            webbrowser.open(f'http://localhost:5000/analysis/{work_item_id}')
            
        except Exception as e:
            print(f"Error opening modern UI: {e}")
            messagebox.showerror("Error", f"Failed to open modern UI: {str(e)}")
    
    def _display_all_work_items(self, all_work_items):
        """Display all work items data in the All Work Items tab."""
        # Clear previous content
        self.all_work_items_text.configure(state="normal")
        self.all_work_items_text.delete(1.0, tk.END)
        
        # Create header
        header_text = f"📊 All Work Items Data ({len(all_work_items)} items)\n"
        header_text += "=" * 80 + "\n\n"
        
        # Insert header
        self.all_work_items_text.insert(tk.END, header_text)
        
        # Format and insert all work items
        for i, work_item in enumerate(all_work_items, 1):
            work_item_text = self._format_work_item_for_display(work_item, i)
            self.all_work_items_text.insert(tk.END, work_item_text)
            self.all_work_items_text.insert(tk.END, "\n" + "-" * 60 + "\n\n")
        
        # Configure as read-only
        self.all_work_items_text.configure(state="disabled")
    
    def _format_work_item_for_display(self, work_item, index):
        """Format a single work item for display in the All Work Items tab."""
        # Extract key fields
        work_item_id = work_item.id
        title = work_item.fields.get('System.Title', 'No Title')
        work_item_type = work_item.fields.get('System.WorkItemType', 'Unknown')
        state = work_item.fields.get('System.State', 'Unknown')
        assigned_to = self.get_assigned_to_display_name(work_item.fields.get('System.AssignedTo', 'Unassigned'))
        area_path = work_item.fields.get('System.AreaPath', 'No Area Path')
        iteration_path = work_item.fields.get('System.IterationPath', 'No Iteration')
        description = work_item.fields.get('System.Description', 'No description')
        created_date = work_item.fields.get('System.CreatedDate', 'Unknown')
        changed_date = work_item.fields.get('System.ChangedDate', 'Unknown')
        
        # Format the work item data
        formatted_text = f"Work Item #{index}: {work_item_id}\n"
        formatted_text += f"Title: {title}\n"
        formatted_text += f"Type: {work_item_type}\n"
        formatted_text += f"State: {state}\n"
        formatted_text += f"Assigned To: {assigned_to}\n"
        formatted_text += f"Area Path: {area_path}\n"
        formatted_text += f"Iteration Path: {iteration_path}\n"
        formatted_text += f"Created: {created_date}\n"
        formatted_text += f"Changed: {changed_date}\n"
        
        # Add description (truncated if too long)
        if description and description != 'No description':
            # Clean up HTML tags and truncate if necessary
            import re
            clean_description = re.sub(r'<[^>]+>', '', description)
            if len(clean_description) > 200:
                clean_description = clean_description[:200] + "..."
            formatted_text += f"Description: {clean_description}\n"
        
        # Add any additional relevant fields
        additional_fields = []
        for field_name, field_value in work_item.fields.items():
            if field_name not in ['System.Title', 'System.WorkItemType', 'System.State', 
                                'System.AssignedTo', 'System.AreaPath', 'System.IterationPath',
                                'System.Description', 'System.CreatedDate', 'System.ChangedDate']:
                if field_value and str(field_value).strip():
                    additional_fields.append(f"{field_name}: {field_value}")
        
        if additional_fields:
            formatted_text += f"Additional Fields: {', '.join(additional_fields[:3])}\n"  # Limit to first 3 additional fields
        
        return formatted_text

    def _add_related_work_items_hierarchy(self, llm_response, all_work_items):
        """Add hierarchy information for related work items mentioned in the LLM response."""
        try:
            # Extract work item IDs from the LLM response
            import re
            work_item_ids = self._extract_work_item_ids_from_text(llm_response)
            
            if not work_item_ids:
                return
            
            # Get unique work item IDs that are not the selected work item
            unique_ids = list(set(work_item_ids))
            
            # Limit to first 5 related work items to avoid overwhelming the display
            if len(unique_ids) > 5:
                unique_ids = unique_ids[:5]
            
            self.llm_analysis_text.insert(tk.END, "\n" + "=" * 80 + "\n\n")
            self.llm_analysis_text.insert(tk.END, "📊 RELATED WORK ITEMS HIERARCHY\n", "subheader")
            self.llm_analysis_text.insert(tk.END, "=" * 50 + "\n\n", "subheader")
            
            for i, work_item_id in enumerate(unique_ids, 1):
                try:
                    # Get hierarchy for this related work item
                    hierarchy = self.client.get_work_item_hierarchy(work_item_id)
                    if hierarchy:
                        hierarchy_text = self.client.get_work_item_hierarchy_display_text(hierarchy)
                        self.llm_analysis_text.insert(tk.END, f"--- Related Work Item #{i} ---\n", "section_header")
                        self.llm_analysis_text.insert(tk.END, hierarchy_text)
                        self.llm_analysis_text.insert(tk.END, "\n" + "-" * 60 + "\n\n")
                    else:
                        self.llm_analysis_text.insert(tk.END, f"--- Related Work Item #{i} ---\n", "section_header")
                        self.llm_analysis_text.insert(tk.END, f"❌ Could not retrieve hierarchy for Work Item {work_item_id}\n\n")
                        self.llm_analysis_text.insert(tk.END, "-" * 60 + "\n\n")
                        
                except Exception as e:
                    logger.warning(f"Could not get hierarchy for related work item {work_item_id}: {e}")
                    self.llm_analysis_text.insert(tk.END, f"--- Related Work Item #{i} ---\n", "section_header")
                    self.llm_analysis_text.insert(tk.END, f"❌ Error retrieving hierarchy for Work Item {work_item_id}: {str(e)}\n\n")
                    self.llm_analysis_text.insert(tk.END, "-" * 60 + "\n\n")
                    
        except Exception as e:
            logger.warning(f"Error adding related work items hierarchy: {e}")
            self.llm_analysis_text.insert(tk.END, "\n" + "=" * 80 + "\n\n")
            self.llm_analysis_text.insert(tk.END, "📊 RELATED WORK ITEMS HIERARCHY\n", "subheader")
            self.llm_analysis_text.insert(tk.END, "=" * 50 + "\n\n", "subheader")
            self.llm_analysis_text.insert(tk.END, f"❌ Error retrieving related work items hierarchy: {str(e)}\n\n")

    def _extract_work_item_ids_from_text(self, text):
        """Extract work item IDs from text using regex patterns."""
        import re
        
        # Pattern to match work item IDs in various formats
        patterns = [
            r'Work Item (\d+)',  # "Work Item 12345"
            r'#(\d+)',          # "#12345"
            r'ID: (\d+)',       # "ID: 12345"
            r'Item (\d+)',      # "Item 12345"
            r'(\d{4,})',        # Any 4+ digit number (likely work item ID)
        ]
        
        work_item_ids = []
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    work_item_id = int(match)
                    if 1000 <= work_item_id <= 999999:  # Reasonable range for work item IDs
                        work_item_ids.append(work_item_id)
                except ValueError:
                    continue
        
        return work_item_ids
    
    def _optimize_work_items_for_llm(self, all_work_items, work_item_limit):
        """Optimize work items for LLM analysis by reducing size if needed for WebSocket limits."""
        try:
            # Create a test system prompt to estimate size
            from src.llm.ado_analysis_prompt import ADOWorkItemAnalysisPrompt
            
            # Test with a subset to estimate size
            test_size = min(100, len(all_work_items))
            test_items = all_work_items[:test_size]
            
            # Create test system prompt
            test_prompt = ADOWorkItemAnalysisPrompt.create_system_prompt(
                self._extract_work_item_data(all_work_items[0]),  # Use first item as selected
                [self._extract_work_item_data(item) for item in test_items]
            )
            
            # Estimate full size
            estimated_size_per_item = len(test_prompt) / test_size
            estimated_full_size = estimated_size_per_item * len(all_work_items)
            
            # Use consistent WebSocket size limits from environment configuration
            import os
            max_safe_size = int(os.getenv('OPENARENA_SAFE_MESSAGE_SIZE', '500000'))  # Use safe size from config
            max_items_for_websocket = int(max_safe_size / estimated_size_per_item) if estimated_size_per_item > 0 else 100
            
            print(f"📏 Size estimation:")
            print(f"   - Estimated size per work item: {estimated_size_per_item:.0f} bytes")
            print(f"   - Estimated full size: {estimated_full_size:.0f} bytes")
            print(f"   - Max safe size: {max_safe_size} bytes")
            print(f"   - Max items for WebSocket: {max_items_for_websocket}")
            
            if len(all_work_items) > max_items_for_websocket:
                print(f"⚠️ Work item count ({len(all_work_items)}) exceeds WebSocket limit ({max_items_for_websocket})")
                print(f"🔄 Reducing to {max_items_for_websocket} work items for WebSocket compatibility")
                
                # Prioritize work items by relevance
                optimized_items = self._prioritize_work_items_for_llm(all_work_items, max_items_for_websocket)
                return optimized_items
            else:
                print(f"✅ Work item count ({len(all_work_items)}) is within WebSocket limits")
                return all_work_items
                
        except Exception as e:
            print(f"⚠️ Error optimizing work items: {e}")
            # Fallback: just limit to a safe number
            safe_limit = min(100, len(all_work_items))
            print(f"🔄 Using fallback limit of {safe_limit} work items")
            return all_work_items[:safe_limit]
    
    def _prioritize_work_items_for_llm(self, all_work_items, max_count):
        """Prioritize work items for LLM analysis based on relevance."""
        if len(all_work_items) <= max_count:
            return all_work_items
        
        # Get the first work item as reference for prioritization
        reference_item = all_work_items[0]
        reference_area_path = reference_item.fields.get('System.AreaPath', '')
        reference_work_item_type = reference_item.fields.get('System.WorkItemType', '')
        
        # Create priority scoring
        def calculate_priority(item):
            score = 0
            
            # Same area path gets highest priority
            if item.fields.get('System.AreaPath', '') == reference_area_path:
                score += 100
            
            # Same work item type gets high priority
            if item.fields.get('System.WorkItemType', '') == reference_work_item_type:
                score += 50
            
            # Recent items get higher priority
            created_date = item.fields.get('System.CreatedDate', '')
            if created_date:
                try:
                    from datetime import datetime
                    # Simple date comparison - more recent = higher score
                    if '2025' in created_date:
                        score += 30
                    elif '2024' in created_date:
                        score += 20
                    elif '2023' in created_date:
                        score += 10
                except:
                    pass
            
            # Active/New items get higher priority than closed
            state = item.fields.get('System.State', '').lower()
            if state in ['active', 'new', 'in progress']:
                score += 25
            elif state in ['resolved', 'completed']:
                score += 15
            elif state == 'closed':
                score += 5
            
            return score
        
        # Sort by priority and take top items
        prioritized_items = sorted(all_work_items, key=calculate_priority, reverse=True)
        return prioritized_items[:max_count]
    
    def _display_system_prompt(self):
        """Display the system prompt in the System Prompt tab."""
        if hasattr(self, 'current_system_prompt') and self.current_system_prompt:
            # Clear previous content
            self.system_prompt_text.configure(state="normal")
            self.system_prompt_text.delete(1.0, tk.END)
            
            # Insert the system prompt
            self.system_prompt_text.insert(tk.END, "🔧 System Prompt Sent to LLM\n")
            self.system_prompt_text.insert(tk.END, "=" * 80 + "\n\n")
            self.system_prompt_text.insert(tk.END, self.current_system_prompt)
            
            # Configure as read-only
            self.system_prompt_text.configure(state="disabled")
        else:
            # Show default message if no system prompt available
            self.system_prompt_text.configure(state="normal")
            self.system_prompt_text.delete(1.0, tk.END)
            self.system_prompt_text.insert(tk.END, "🔧 System Prompt\n\n")
            self.system_prompt_text.insert(tk.END, "No system prompt available. Perform an LLM analysis to see the system prompt here.\n\n")
            self.system_prompt_text.insert(tk.END, "The system prompt contains:\n")
            self.system_prompt_text.insert(tk.END, "• Instructions for the LLM\n")
            self.system_prompt_text.insert(tk.END, "• Selected work item details\n")
            self.system_prompt_text.insert(tk.END, "• All available work items data\n")
            self.system_prompt_text.insert(tk.END, "• Analysis objectives and criteria\n")
            self.system_prompt_text.configure(state="disabled")
    
    def _configure_llm_text_styling(self):
        """Configure text widget with rich styling for better readability."""
        # Configure tags for different text styles with enhanced color scheme
        self.llm_analysis_text.tag_configure("header", 
                                           font=("Arial", 12, "bold"), 
                                           foreground="#1A5F7A",
                                           spacing1=10, spacing3=10)
        
        self.llm_analysis_text.tag_configure("section_header", 
                                           font=("Arial", 11, "bold"), 
                                           foreground="#8B2F97",
                                           spacing1=8, spacing3=5)
        
        self.llm_analysis_text.tag_configure("subsection_header", 
                                           font=("Arial", 10, "bold"), 
                                           foreground="#D97706",
                                           spacing1=5, spacing3=3)
        
        self.llm_analysis_text.tag_configure("work_item_id", 
                                           font=("Consolas", 9, "bold"), 
                                           foreground="#DC2626",
                                           background="#FEF2F2")
        
        self.llm_analysis_text.tag_configure("work_item_title", 
                                           font=("Arial", 9, "bold"), 
                                           foreground="#1E40AF",
                                           spacing1=2)
        
        self.llm_analysis_text.tag_configure("work_item_details", 
                                           font=("Arial", 9), 
                                           foreground="#374151",
                                           spacing1=1)
        
        self.llm_analysis_text.tag_configure("relationship_type", 
                                           font=("Arial", 9, "bold"), 
                                           foreground="#7C3AED",
                                           background="#F3F4F6")
        
        self.llm_analysis_text.tag_configure("evidence", 
                                           font=("Arial", 9), 
                                           foreground="#6B7280",
                                           spacing1=1)
        
        self.llm_analysis_text.tag_configure("impact", 
                                           font=("Arial", 9), 
                                           foreground="#059669",
                                           background="#F0FDF4")
        
        self.llm_analysis_text.tag_configure("separator", 
                                           font=("Arial", 9), 
                                           foreground="#9CA3AF",
                                           spacing1=5, spacing3=5)
        
        # Add new tags for better visual hierarchy
        self.llm_analysis_text.tag_configure("highlight", 
                                           font=("Arial", 9, "bold"), 
                                           foreground="#1F2937",
                                           background="#FEF3C7")
        
        self.llm_analysis_text.tag_configure("note", 
                                           font=("Arial", 9, "italic"), 
                                           foreground="#7C2D12",
                                           background="#FEF3C7")
        
        # Add tags for specific section types
        self.llm_analysis_text.tag_configure("patterns", 
                                           font=("Arial", 9, "bold"), 
                                           foreground="#7C2D12",
                                           background="#FEF3C7")
        
        self.llm_analysis_text.tag_configure("risk", 
                                           font=("Arial", 9, "bold"), 
                                           foreground="#DC2626",
                                           background="#FEF2F2")
        
        self.llm_analysis_text.tag_configure("recommendations", 
                                           font=("Arial", 9, "bold"), 
                                           foreground="#059669",
                                           background="#F0FDF4")
        
        # Add tags for enhanced formatting
        self.llm_analysis_text.tag_configure("bold_text", 
                                           font=("Arial", 9, "bold"), 
                                           foreground="#1F2937")
        
        self.llm_analysis_text.tag_configure("underline_bold", 
                                           font=("Arial", 9, "bold underline"), 
                                           foreground="#DC2626",
                                           background="#FEF2F2")
        
        # Set default font for the text widget
        self.llm_analysis_text.configure(font=("Arial", 9))
    
    def _insert_formatted_llm_response(self, llm_response):
        """Insert the LLM response with rich formatting."""
        if not llm_response:
            self.llm_analysis_text.insert(tk.END, "No analysis results available.", "section_header")
            return
        
        # Split the response into lines for processing
        lines = llm_response.split('\n')
        current_section = None
        current_subsection = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect section headers
            if line.startswith('### ') and line.endswith('RELATIONSHIPS'):
                current_section = line[4:]  # Remove '### '
                self.llm_analysis_text.insert(tk.END, f"\n{line}\n", "section_header")
                continue
            elif line.startswith('### ') and 'RELATIONSHIP PATTERNS ANALYSIS' in line:
                current_section = "patterns"
                self.llm_analysis_text.insert(tk.END, f"\n{line}\n", "section_header")
                continue
            elif line.startswith('### ') and 'RISK ASSESSMENT' in line:
                current_section = "risk"
                self.llm_analysis_text.insert(tk.END, f"\n{line}\n", "section_header")
                continue
            elif line.startswith('### ') and 'RECOMMENDATIONS' in line:
                current_section = "recommendations"
                self.llm_analysis_text.insert(tk.END, f"\n{line}\n", "section_header")
                continue
            # Detect #### **ID**: 12345 pattern for underline & bold
            elif line.startswith('#### ') and '**' in line and ':' in line:
                # Extract the #### part and the **key**: value part
                parts = line.split('**', 1)
                if len(parts) == 2:
                    header_part = parts[0].strip()  # #### part
                    key_value_part = parts[1]  # key**: value part
                    
                    if ':' in key_value_part:
                        key, value = key_value_part.split(':', 1)
                        key = key.strip('*')
                        value = value.strip()
                        
                        self.llm_analysis_text.insert(tk.END, f"\n{header_part}", "section_header")
                        self.llm_analysis_text.insert(tk.END, f" {key}: ", "underline_bold")
                        self.llm_analysis_text.insert(tk.END, f"{value}\n", "work_item_id")
                    else:
                        self.llm_analysis_text.insert(tk.END, f"\n{line}\n", "section_header")
                else:
                    self.llm_analysis_text.insert(tk.END, f"\n{line}\n", "section_header")
                continue
            # Detect regular #### headers
            elif line.startswith('#### '):
                self.llm_analysis_text.insert(tk.END, f"\n{line}\n", "section_header")
                continue
            
            # Detect subsection headers
            elif line.startswith('**') and line.endswith('**'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip('*')
                    value = value.strip()
                    
                    if key.lower() in ['id', 'work item id']:
                        self.llm_analysis_text.insert(tk.END, f"\n{key}: ", "subsection_header")
                        self.llm_analysis_text.insert(tk.END, value, "work_item_id")
                    elif key.lower() in ['title']:
                        self.llm_analysis_text.insert(tk.END, f"\n{key}: ", "subsection_header")
                        self.llm_analysis_text.insert(tk.END, value, "work_item_title")
                    elif key.lower() in ['relationship type']:
                        self.llm_analysis_text.insert(tk.END, f"\n{key}: ", "subsection_header")
                        self.llm_analysis_text.insert(tk.END, value, "relationship_type")
                    elif key.lower() in ['impact']:
                        self.llm_analysis_text.insert(tk.END, f"\n{key}: ", "subsection_header")
                        self.llm_analysis_text.insert(tk.END, value, "impact")
                    # Handle patterns, risk, and recommendations subsections
                    elif key.lower() in ['primary patterns', 'dependency clusters', 'cross-team dependencies', 'technical debt indicators']:
                        self.llm_analysis_text.insert(tk.END, f"\n{key}: ", "subsection_header")
                        self.llm_analysis_text.insert(tk.END, value, "highlight")
                    elif key.lower() in ['high-risk dependencies', 'blocking issues', 'resource conflicts']:
                        self.llm_analysis_text.insert(tk.END, f"\n{key}: ", "subsection_header")
                        self.llm_analysis_text.insert(tk.END, value, "highlight")
                    elif key.lower() in ['immediate actions', 'planning considerations', 'risk mitigation', 'optimization opportunities']:
                        self.llm_analysis_text.insert(tk.END, f"\n{key}: ", "subsection_header")
                        self.llm_analysis_text.insert(tk.END, value, "highlight")
                    else:
                        self.llm_analysis_text.insert(tk.END, f"\n{line}", "subsection_header")
                else:
                    # Handle bold text without colons (like **ABC**)
                    bold_text = line.strip('*')
                    self.llm_analysis_text.insert(tk.END, f"\n{bold_text}", "bold_text")
                continue
            
            # Detect evidence and impact sections
            elif line.startswith('**Evidence:**'):
                self.llm_analysis_text.insert(tk.END, f"\n{line}", "subsection_header")
                continue
            elif line.startswith('**Impact:**'):
                self.llm_analysis_text.insert(tk.END, f"\n{line}", "subsection_header")
                continue
            
            # Handle bullet points and evidence items
            elif line.startswith('•') or line.startswith('-'):
                self.llm_analysis_text.insert(tk.END, f"  {line}\n", "evidence")
                continue
            # Handle numbered lists (common in recommendations and actions)
            elif line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                # Extract the number and content
                parts = line.strip().split('.', 1)
                if len(parts) == 2:
                    number = parts[0].strip()
                    content = parts[1].strip()
                    self.llm_analysis_text.insert(tk.END, f"  {number}. ", "highlight")
                    self.llm_analysis_text.insert(tk.END, f"{content}\n", "work_item_details")
                else:
                    self.llm_analysis_text.insert(tk.END, f"  {line}\n", "work_item_details")
                continue
            
            # Handle separators
            elif line.startswith('---'):
                self.llm_analysis_text.insert(tk.END, f"{line}\n", "separator")
                continue
            
            # Handle regular content
            else:
                # Check if this is a work item detail line
                if ':' in line and any(keyword in line.lower() for keyword in ['type:', 'state:', 'priority:', 'assigned to:', 'created by:', 'tags:', 'area path:']):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        self.llm_analysis_text.insert(tk.END, f"{key}: ", "subsection_header")
                        self.llm_analysis_text.insert(tk.END, f"{value}\n", "work_item_details")
                else:
                    # Regular text content - apply section-specific styling
                    if current_section == "patterns" and any(keyword in line.lower() for keyword in ['ui', 'styling', 'accessibility', 'practical law']):
                        self.llm_analysis_text.insert(tk.END, f"{line}\n", "patterns")
                    elif current_section == "risk" and any(keyword in line.lower() for keyword in ['risk', 'blocking', 'conflict', 'dependency']):
                        self.llm_analysis_text.insert(tk.END, f"{line}\n", "risk")
                    elif current_section == "recommendations" and any(keyword in line.lower() for keyword in ['action', 'consideration', 'mitigation', 'opportunity']):
                        self.llm_analysis_text.insert(tk.END, f"{line}\n", "recommendations")
                    else:
                        # Regular text content
                        self.llm_analysis_text.insert(tk.END, f"{line}\n")
        
        # Add a final separator
        self.llm_analysis_text.insert(tk.END, "\n" + "=" * 80 + "\n", "separator")
        
        # Add some spacing after each major section for better readability
        self.llm_analysis_text.insert(tk.END, "\n", "separator")
    
    def _clear_llm_analysis_results(self):
        """Clear the LLM analysis results tab and restore welcome message."""
        self.llm_analysis_text.configure(state="normal")
        self.llm_analysis_text.delete(1.0, tk.END)
        
        # Restore welcome message with formatting
        self._configure_llm_text_styling()
        self.llm_analysis_text.insert(tk.END, "🤖 LLM Analysis Results\n\n", "header")
        self.llm_analysis_text.insert(tk.END, "This tab will display the results of LLM analysis when you click the \"🤖 Analyze with LLM\" button in the ADO Work Items tab.\n\n", "work_item_details")
        self.llm_analysis_text.insert(tk.END, "To get started:\n", "subsection_header")
        self.llm_analysis_text.insert(tk.END, "1. Go to the \"ADO Work Items\" tab\n", "work_item_details")
        self.llm_analysis_text.insert(tk.END, "2. Click \"🤖 Analyze with LLM\" on any work item row\n", "work_item_details")
        self.llm_analysis_text.insert(tk.END, "3. Wait for the analysis to complete\n", "work_item_details")
        self.llm_analysis_text.insert(tk.END, "4. Results will appear here automatically\n\n", "work_item_details")
        self.llm_analysis_text.insert(tk.END, "The analysis will provide insights about:\n", "subsection_header")
        self.llm_analysis_text.insert(tk.END, "• Related work items\n", "evidence")
        self.llm_analysis_text.insert(tk.END, "• Technical dependencies\n", "evidence")
        self.llm_analysis_text.insert(tk.END, "• Business relationships\n", "evidence")
        self.llm_analysis_text.insert(tk.END, "• Impact analysis\n", "evidence")
        self.llm_analysis_text.insert(tk.END, "• Recommendations", "evidence")
        
        self.llm_analysis_text.configure(state="disabled")
        
        # Remove the button frame if it exists
        if hasattr(self, 'llm_analysis_button_frame') and self.llm_analysis_button_frame:
            self.llm_analysis_button_frame.destroy()
            self.llm_analysis_button_frame = None
        
        # Clear the system prompt
        self.current_system_prompt = None
        self._display_system_prompt()
    
    def _copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            messagebox.showinfo("Success", "Analysis results copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy to clipboard: {str(e)}")
    
    def _export_analysis_to_file(self, work_item, analysis_text):
        """Export analysis results to a text file."""
        try:
            from tkinter import filedialog
            import os
            from datetime import datetime
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"LLM_Analysis_WI{work_item.id}_{timestamp}.txt"
            
            # Get save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialname=filename
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"LLM Analysis Results for Work Item {work_item.id}\n")
                    f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(analysis_text)
                
                messagebox.showinfo("Success", f"Analysis exported to: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export analysis: {str(e)}")
    
    def display_related_work_items(self, source_work_item, related_items):
        """Display related work items in a new window."""
        # Create a popup window to show related work items
        related_window = tk.Toplevel(self.root)
        related_window.title(f"Related Work Items for {source_work_item.id}")
        related_window.geometry("1200x700")  # Increased width to accommodate wider columns
        related_window.resizable(True, True)
        
        # Make the window modal
        related_window.transient(self.root)
        related_window.grab_set()
        
        # Create main frame
        main_frame = ttk.Frame(related_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.LabelFrame(main_frame, text=f"Related Work Items for Work Item {source_work_item.id}", padding="10")
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text=f"Title: {source_work_item.fields.get('System.Title', 'No Title')}", 
                 font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(header_frame, text=f"Found {len(related_items)} related work items").pack(anchor=tk.W)
        
        # Create treeview for related items
        columns = ('ID', 'Type', 'State', 'Title', 'Relationship', 'Assigned To')
        related_tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=20)
        
        # Configure columns with appropriate widths
        column_widths = {
            'ID': 80,
            'Type': 100,
            'State': 100,
            'Title': 300,  # Increased width for title
            'Relationship': 120,
            'Assigned To': 150
        }
        
        for col in columns:
            related_tree.heading(col, text=col)
            if col in column_widths:
                related_tree.column(col, width=column_widths[col], minwidth=column_widths[col]//2)
            else:
                related_tree.column(col, width=120, minwidth=80)
        
        # Add scrollbars
        tree_scroll_y = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=related_tree.yview)
        tree_scroll_x = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=related_tree.xview)
        related_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        # Pack the treeview and scrollbars
        related_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Populate the treeview
        for item in related_items:
            item_id = item.id
            item_type = item.fields.get('System.WorkItemType', 'Unknown')
            item_state = item.fields.get('System.State', 'Unknown')
            item_title = item.fields.get('System.Title', 'No Title')
            relationship = item.fields.get('System.RelatedLinks', 'Unknown')
            assigned_to_raw = item.fields.get('System.AssignedTo', 'Unassigned')
            assigned_to = self.get_assigned_to_display_name(assigned_to_raw)
            
            # Keep title full length for better readability
            
            related_tree.insert('', 'end', values=(
                item_id, item_type, item_state, item_title, relationship, assigned_to
            ))
        
        # Close button
        close_button = ttk.Button(main_frame, text="❌ Close", 
                                command=related_window.destroy)
        close_button.pack(pady=10)
    
    def display_related_work_items_in_subtab(self, source_work_item, related_items):
        """Display related work items in a new sub-tab within the Related Work Items tab.
        
        DEPRECATED: This method is no longer used. Related work items are now displayed
        in the main "Refine Related Work Items" tab instead of creating sub-tabs.
        """
        try:
            # Create a new sub-tab for this specific work item's related items
            tab_name = f"Related to #{source_work_item.id}"
            
            # Check if tab already exists and remove it
            for i in range(self.notebook.index("end")):
                if self.notebook.tab(i, "text") == tab_name:
                    self.notebook.forget(i)
                    break
            
            # Create new frame for the sub-tab
            related_frame = ttk.Frame(self.notebook, padding="10")
            self.notebook.add(related_frame, text=tab_name)
            
            # Switch to the new tab
            self.notebook.select(related_frame)
            
            # Header frame
            header_frame = ttk.LabelFrame(related_frame, text=f"Related Work Items for Work Item #{source_work_item.id}", padding="10")
            header_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Source work item info
            source_title = source_work_item.fields.get('System.Title', 'No Title')
            ttk.Label(header_frame, text=f"Source: {source_title}", 
                     font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W)
            ttk.Label(header_frame, text=f"Found {len(related_items)} related work items").pack(anchor=tk.W)
            
            # Create treeview for related items
            columns = ('ID', 'Type', 'State', 'Title', 'Assigned To', 'Created Date', 'Actions')
            related_tree = ttk.Treeview(related_frame, columns=columns, show='headings', height=15)
            
            # Configure columns with appropriate widths
            column_widths = {
                'ID': 80,
                'Type': 100,
                'State': 100,
                'Title': 300,
                'Assigned To': 150,
                'Created Date': 120,
                'Actions': 200
            }
            
            for col in columns:
                related_tree.heading(col, text=col)
                if col in column_widths:
                    related_tree.column(col, width=column_widths[col], minwidth=column_widths[col]//2)
                else:
                    related_tree.column(col, width=120, minwidth=80)
            
            # Add scrollbars
            tree_scroll_y = ttk.Scrollbar(related_frame, orient=tk.VERTICAL, command=related_tree.yview)
            tree_scroll_x = ttk.Scrollbar(related_frame, orient=tk.HORIZONTAL, command=related_tree.xview)
            related_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
            
            # Pack the treeview and scrollbars
            related_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
            tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
            
            # Populate the treeview
            for item in related_items:
                item_id = item.id
                item_type = item.fields.get('System.WorkItemType', 'Unknown')
                item_state = item.fields.get('System.State', 'Unknown')
                item_title = item.fields.get('System.Title', 'No Title')
                assigned_to_raw = item.fields.get('System.AssignedTo', 'Unassigned')
                assigned_to = self.get_assigned_to_display_name(assigned_to_raw)
                created_date = item.fields.get('System.CreatedDate', 'Unknown')
                
                # Format created date
                if created_date != 'Unknown' and hasattr(created_date, 'strftime'):
                    created_date = created_date.strftime('%Y-%m-%d')
                elif isinstance(created_date, str) and created_date != 'Unknown':
                    try:
                        from datetime import datetime
                        created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    except:
                        pass
                
                related_tree.insert('', 'end', values=(
                    item_id, item_type, item_state, item_title, assigned_to, created_date, "🔗 Show Related | 🤖 Analyze | 🌐 Open"
                ))
            
            # Bind double-click event to show work item details
            related_tree.bind('<Double-1>', lambda event: self.on_related_item_double_click(event, related_tree))
            
            # Add close button for this sub-tab
            close_frame = ttk.Frame(related_frame)
            close_frame.pack(fill=tk.X, pady=10)
            
            close_button = ttk.Button(close_frame, text="❌ Close This Tab", 
                                    command=lambda: self.close_subtab(tab_name))
            close_button.pack(side=tk.RIGHT)
            
            print(f"✅ Created sub-tab '{tab_name}' with {len(related_items)} related work items")
            
        except Exception as e:
            error_msg = f"Error creating related work items sub-tab: {str(e)}"
            print(f"❌ {error_msg}")
            messagebox.showerror("Error", error_msg)
    
    def close_subtab(self, tab_name):
        """Close a specific sub-tab."""
        try:
            for i in range(self.notebook.index("end")):
                if self.notebook.tab(i, "text") == tab_name:
                    self.notebook.forget(i)
                    break
        except Exception as e:
            print(f"❌ Error closing sub-tab: {str(e)}")
    
    def on_related_item_double_click(self, event, tree):
        """Handle double-click on related work item."""
        try:
            item = tree.selection()[0]
            values = tree.item(item, 'values')
            if values:
                work_item_id = values[0]
                print(f"🔍 Double-clicked on work item {work_item_id}")
                # You can add more functionality here, like showing details or opening in ADO
        except Exception as e:
            print(f"❌ Error handling double-click: {str(e)}")
    

    
    def display_related_work_items_in_refine_tab(self, source_work_item, related_items):
        """Display related work items in the Refine Related Work Items sub-tab."""
        try:
            # Store the current source work item and related items
            self.current_source_work_item = source_work_item
            self.current_related_items = related_items
            
            # Switch to the Refine Related Work Items sub-tab
            # Find the sub-tab index for "Refine Related Work Items" within the work items notebook
            refine_tab_index = None
            for i in range(self.work_items_notebook.index("end")):
                if self.work_items_notebook.tab(i, "text") == "Refine Related Work Items":
                    refine_tab_index = i
                    break
            
            if refine_tab_index is not None:
                self.work_items_notebook.select(refine_tab_index)
            
            # Update header information
            source_title = source_work_item.fields.get('System.Title', 'No Title')
            self.source_info_label.config(text=f"Source: {source_title}")
            self.related_count_label.config(text=f"Found {len(related_items)} related work items")
            
            # Clear existing items in the treeview
            for item in self.refine_related_tree.get_children():
                self.refine_related_tree.delete(item)
            
            # Convert related items to dictionary format for filtering
            self.current_related_items = []
            for item in related_items:
                item_id = item.id
                item_type = item.fields.get('System.WorkItemType', 'Unknown')
                item_state = item.fields.get('System.State', 'Unknown')
                item_title = item.fields.get('System.Title', 'No Title')
                assigned_to_raw = item.fields.get('System.AssignedTo', 'Unassigned')
                assigned_to = self.get_assigned_to_display_name(assigned_to_raw)
                created_date = item.fields.get('System.CreatedDate', 'Unknown')
                
                # Format created date
                if created_date != 'Unknown' and hasattr(created_date, 'strftime'):
                    created_date = created_date.strftime('%Y-%m-%d')
                elif isinstance(created_date, str) and created_date != 'Unknown':
                    try:
                        from datetime import datetime
                        created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    except:
                        pass
                
                # Get and clean description
                description = item.fields.get('System.Description', '')
                if description:
                    # Remove HTML tags if present
                    if '<' in description and '>' in description:
                        import re
                        description = re.sub('<[^<]+?>', '', description)
                        description = re.sub('\s+', ' ', description).strip()
                    description = description.strip()
                
                if not description:
                    description = 'No description available'
                
                # Store item data for filtering
                item_data = {
                    'id': item_id,
                    'type': item_type,
                    'state': item_state,
                    'title': item_title,
                    'assigned_to': assigned_to,
                    'created_date': created_date,
                    'area_path': item.fields.get('System.AreaPath', ''),
                    'created_by': self.get_assigned_to_display_name(item.fields.get('System.CreatedBy', '')),
                    'tags': item.fields.get('System.Tags', ''),
                    'iteration_path': item.fields.get('System.IterationPath', ''),
                    'priority': item.fields.get('Microsoft.VSTS.Common.Priority', ''),
                    'description': description
                }
                self.current_related_items.append(item_data)
            
            # Populate filter dropdowns with data from related items
            self.populate_refine_filter_dropdowns()
            
            # Apply initial filters (show all items)
            self.apply_refine_filters()
            
            print(f"✅ Displayed {len(related_items)} related work items in Refine Related Work Items sub-tab")
            
        except Exception as e:
            error_msg = f"Error displaying related work items in refine sub-tab: {str(e)}"
            print(f"❌ {error_msg}")
            messagebox.showerror("Error", error_msg)
    
    def create_get_item_tab(self):
        """Create the get item tab."""
        get_item_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(get_item_frame, text="Get Work Item")
        
        # Input frame
        input_frame = ttk.LabelFrame(get_item_frame, text="Get Work Item by ID", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Work Item ID
        ttk.Label(input_frame, text="Work Item ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.get_item_id_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.get_item_id_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Get button
        get_button = ttk.Button(input_frame, text="Get Work Item", command=self.get_work_item)
        get_button.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Output area
        output_frame = ttk.LabelFrame(get_item_frame, text="Work Item Details", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.get_item_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.get_item_output.pack(fill=tk.BOTH, expand=True)
        self.get_item_output.configure(state="disabled")
    
    def create_query_items_tab(self):
        """Create the query items tab."""
        query_items_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(query_items_frame, text="Query Work Items")
        
        # Input frame
        input_frame = ttk.LabelFrame(query_items_frame, text="Query Work Items", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Work Item Type
        ttk.Label(input_frame, text="Work Item Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.query_type_var = tk.StringVar(value="User Story")
        ttk.Entry(input_frame, textvariable=self.query_type_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # State
        ttk.Label(input_frame, text="State:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.query_state_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.query_state_var, width=20).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Limit
        ttk.Label(input_frame, text="Limit:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.query_limit_var = tk.StringVar(value="10")
        ttk.Entry(input_frame, textvariable=self.query_limit_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Query button
        query_button = ttk.Button(input_frame, text="Query Work Items", command=self.query_work_items)
        query_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Output area
        output_frame = ttk.LabelFrame(query_items_frame, text="Query Results", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.query_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.query_output.pack(fill=tk.BOTH, expand=True)
        self.query_output.configure(state="disabled")
    
    def create_board_columns_tab(self):
        """Create the board columns tab."""
        board_columns_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(board_columns_frame, text="Board Columns")
        
        # Input frame
        input_frame = ttk.LabelFrame(board_columns_frame, text="Get Board Columns", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Board Name
        ttk.Label(input_frame, text="Board Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.board_name_var = tk.StringVar(value="Stories")
        ttk.Entry(input_frame, textvariable=self.board_name_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Get button
        get_button = ttk.Button(input_frame, text="Get Board Columns", command=self.get_board_columns)
        get_button.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Output area
        output_frame = ttk.LabelFrame(board_columns_frame, text="Board Columns", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.board_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.board_output.pack(fill=tk.BOTH, expand=True)
        self.board_output.configure(state="disabled")
    
    def create_create_item_tab(self):
        """Create the create item tab."""
        create_item_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(create_item_frame, text="Create Work Item")
        
        # Input frame
        input_frame = ttk.LabelFrame(create_item_frame, text="Create New Work Item", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Work Item Type
        ttk.Label(input_frame, text="Work Item Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.create_type_var = tk.StringVar(value="User Story")
        ttk.Entry(input_frame, textvariable=self.create_type_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Title
        ttk.Label(input_frame, text="Title:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.create_title_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.create_title_var, width=50).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Description
        ttk.Label(input_frame, text="Description:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.create_desc_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.create_desc_var, width=50).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Assigned To
        ttk.Label(input_frame, text="Assigned To:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.create_assigned_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.create_assigned_var, width=30).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Tags
        ttk.Label(input_frame, text="Tags (semicolon-separated):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.create_tags_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.create_tags_var, width=50).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Create button
        create_button = ttk.Button(input_frame, text="Create Work Item", command=self.create_work_item)
        create_button.grid(row=5, column=0, columnspan=2, pady=10)
        
        # Output area
        output_frame = ttk.LabelFrame(create_item_frame, text="Result", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.create_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.create_output.pack(fill=tk.BOTH, expand=True)
        self.create_output.configure(state="disabled")
    
    def create_update_item_tab(self):
        """Create the update item tab."""
        update_item_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(update_item_frame, text="Update Work Item")
        
        # Input frame
        input_frame = ttk.LabelFrame(update_item_frame, text="Update Existing Work Item", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Work Item ID
        ttk.Label(input_frame, text="Work Item ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.update_id_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.update_id_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Title
        ttk.Label(input_frame, text="New Title:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.update_title_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.update_title_var, width=50).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Description
        ttk.Label(input_frame, text="New Description:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.update_desc_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.update_desc_var, width=50).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # State
        ttk.Label(input_frame, text="New State:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.update_state_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.update_state_var, width=20).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Assigned To
        ttk.Label(input_frame, text="New Assigned To:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.update_assigned_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.update_assigned_var, width=30).grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Tags
        ttk.Label(input_frame, text="New Tags (semicolon-separated):").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.update_tags_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.update_tags_var, width=50).grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Update button
        update_button = ttk.Button(input_frame, text="Update Work Item", command=self.update_work_item)
        update_button.grid(row=6, column=0, columnspan=2, pady=10)
        
        # Output area
        output_frame = ttk.LabelFrame(update_item_frame, text="Result", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.update_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.update_output.pack(fill=tk.BOTH, expand=True)
        self.update_output.configure(state="disabled")
    
    def create_refine_item_tab(self):
        """Create the refine work item tab."""
        refine_item_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(refine_item_frame, text="Refine Work Item")
        
        # Input frame
        input_frame = ttk.LabelFrame(refine_item_frame, text="Refine Work Item", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Work Item ID
        ttk.Label(input_frame, text="Work Item ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.refine_id_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.refine_id_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Refine button
        refine_button = ttk.Button(input_frame, text="Refine Work Item", command=self.refine_work_item)
        refine_button.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Output area with tabs for formatted and raw output
        output_notebook = ttk.Notebook(refine_item_frame)
        output_notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Formatted output tab
        formatted_frame = ttk.Frame(output_notebook, padding="10")
        output_notebook.add(formatted_frame, text="Formatted Output")
        
        self.refine_output = scrolledtext.ScrolledText(formatted_frame, wrap=tk.WORD)
        self.refine_output.pack(fill=tk.BOTH, expand=True)
        self.refine_output.configure(state="disabled")
        
        # Raw output tab
        raw_frame = ttk.Frame(output_notebook, padding="10")
        output_notebook.add(raw_frame, text="Raw LLM Output")
        
        # Raw output controls
        raw_controls_frame = ttk.Frame(raw_frame)
        raw_controls_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(raw_controls_frame, text="Raw response from OpenArena LLM:").pack(side=tk.LEFT)
        
        # Copy raw output button
        copy_raw_button = ttk.Button(raw_controls_frame, text="Copy Raw Output", 
                                   command=lambda: self.copy_to_clipboard(self.raw_output))
        copy_raw_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Clear raw output button
        clear_raw_button = ttk.Button(raw_controls_frame, text="Clear Raw Output", 
                                    command=lambda: self.clear_raw_output())
        clear_raw_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.raw_output = scrolledtext.ScrolledText(raw_frame, wrap=tk.WORD, font=("Consolas", 9), 
                                                  background="#f8f8f8", foreground="#333333")
        self.raw_output.pack(fill=tk.BOTH, expand=True)
        self.raw_output.configure(state="disabled")
    
    def create_model_selection_tab(self):
        """Create the AI model selection tab."""
        model_selection_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(model_selection_frame, text="Open Arena - AI Model Selection")
        
        # Model selection frame
        selection_frame = ttk.LabelFrame(model_selection_frame, text="Select AI Model for OpenArena", padding="10")
        selection_frame.pack(fill=tk.X, pady=5)
        
        # Current model display
        current_model_frame = ttk.Frame(selection_frame)
        current_model_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(current_model_frame, text="Current Model:", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W)
        
        self.current_model_var = tk.StringVar(value="claude4opus")
        self.current_model_label = ttk.Label(current_model_frame, textvariable=self.current_model_var, 
                                           font=("TkDefaultFont", 12), foreground="blue")
        self.current_model_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Model selection dropdown
        model_frame = ttk.Frame(selection_frame)
        model_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(model_frame, text="Select AI Model:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.model_selection_var = tk.StringVar(value="claude4opus")
        model_combo = ttk.Combobox(model_frame, textvariable=self.model_selection_var, 
                                  values=["claude4opus", "gpt5", "gemini2pro", "azuredevopsagent"], 
                                  state="readonly", width=25)
        model_combo.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Model descriptions
        model_info_frame = ttk.Frame(selection_frame)
        model_info_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(model_info_frame, text="Model Information:", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W)
        
        model_descriptions = {
            "claude4opus": "Claude 4 Opus - Advanced reasoning and analysis capabilities. Excellent for complex problem-solving and detailed analysis.",
            "gpt5": "GPT-5 - Latest OpenAI model with enhanced language understanding. Great for natural language processing and creative tasks.", 
            "gemini2pro": "Gemini 2 Pro - Google's advanced multimodal AI model. Excellent for understanding context and generating structured responses.",
            "azuredevopsagent": "Azure DevOps Agent - Specialized AI model for Azure DevOps workflows and project management tasks. Optimized for development team collaboration and backlog refinement."
        }
        
        self.model_info_label = ttk.Label(model_info_frame, text=model_descriptions["claude4opus"], 
                                         wraplength=500, justify=tk.LEFT)
        self.model_info_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Update model info when selection changes
        def update_model_info(*args):
            selected_model = self.model_selection_var.get()
            self.model_info_label.config(text=model_descriptions.get(selected_model, ""))
        
        self.model_selection_var.trace('w', update_model_info)
        
        # Buttons frame
        buttons_frame = ttk.Frame(selection_frame)
        buttons_frame.pack(fill=tk.X, pady=15)
        
        # Switch model button
        switch_button = ttk.Button(buttons_frame, text="Switch to Selected Model", 
                                 command=self.switch_ai_model, style="Accent.TButton")
        switch_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Test connection button
        test_button = ttk.Button(buttons_frame, text="Test Model Connection", 
                               command=self.test_model_connection)
        test_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Show configuration button
        config_button = ttk.Button(buttons_frame, text="Show Configuration", 
                                 command=self.show_model_configuration)
        config_button.pack(side=tk.LEFT)
        
        # LLM Analysis Configuration frame
        llm_config_frame = ttk.LabelFrame(model_selection_frame, text="LLM Analysis Configuration", padding="10")
        llm_config_frame.pack(fill=tk.X, pady=5)
        
        # Work item limit configuration
        limit_frame = ttk.Frame(llm_config_frame)
        limit_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(limit_frame, text="Max Work Items for LLM Analysis:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.llm_work_item_limit_var = tk.IntVar(value=500)
        limit_spinbox = ttk.Spinbox(limit_frame, from_=10, to=1000, width=10, 
                                   textvariable=self.llm_work_item_limit_var)
        limit_spinbox.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        ttk.Label(limit_frame, text="(10-1000, default: 500)").grid(row=0, column=2, sticky=tk.W, pady=5)
        
        # Analysis strategy configuration
        strategy_frame = ttk.Frame(llm_config_frame)
        strategy_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(strategy_frame, text="Analysis Strategy:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.llm_strategy_var = tk.StringVar(value="area_path")
        strategy_combo = ttk.Combobox(strategy_frame, textvariable=self.llm_strategy_var,
                                     values=["area_path", "broader", "general", "recent"], 
                                     state="readonly", width=15)
        strategy_combo.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        strategy_descriptions = {
            "area_path": "Focus on same area path (most relevant)",
            "broader": "Include related area paths (more context)",
            "general": "General project-wide analysis",
            "recent": "Focus on recent work items"
        }
        
        self.strategy_info_label = ttk.Label(strategy_frame, 
                                           text=strategy_descriptions["area_path"], 
                                           wraplength=400, justify=tk.LEFT)
        self.strategy_info_label.grid(row=0, column=2, sticky=tk.W, padx=10, pady=5)
        
        # Update strategy info when selection changes
        def update_strategy_info(*args):
            selected_strategy = self.llm_strategy_var.get()
            self.strategy_info_label.config(text=strategy_descriptions.get(selected_strategy, ""))
        
        self.llm_strategy_var.trace('w', update_strategy_info)
        
        # Save LLM configuration button
        save_llm_config_button = ttk.Button(llm_config_frame, text="💾 Save LLM Configuration", 
                                          command=self.save_settings)
        save_llm_config_button.pack(pady=10)
        
        # Configuration display frame
        config_frame = ttk.LabelFrame(model_selection_frame, text="Model Configuration", padding="10")
        config_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.config_output = scrolledtext.ScrolledText(config_frame, wrap=tk.WORD, height=8)
        self.config_output.pack(fill=tk.BOTH, expand=True)
        self.config_output.configure(state="disabled")
        
        # Status frame
        status_frame = ttk.Frame(model_selection_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.model_status_var = tk.StringVar(value="Ready to select model")
        self.model_status_label = ttk.Label(status_frame, textvariable=self.model_status_var, 
                                          relief=tk.SUNKEN, anchor=tk.W)
        self.model_status_label.pack(fill=tk.X)
    
    def connect_to_ado(self):
        """Connect to Azure DevOps."""
        # Get connection details
        org_url = self.org_url_var.get().strip()
        pat = self.pat_var.get().strip()
        project = self.project_var.get().strip()
        team = self.team_var.get().strip()
        
        # Validate inputs
        if not org_url or not pat or not project:
            messagebox.showerror("Error", "Organization URL, PAT, and Project are required.")
            return
        
        # Update status
        self.status_var.set("Connecting to Azure DevOps...")
        
        # Clear output
        self.connection_output.configure(state="normal")
        self.connection_output.delete(1.0, tk.END)
        self.connection_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.connection_output)
        
        # Connect in a separate thread to avoid freezing the UI
        def connect_thread():
            try:
                # Create client
                with redirect_stdout(redirect):
                    print(f"Connecting to {org_url}...")
                    self.client = AzureDevOpsClient(org_url, pat)
                    print(f"Connected successfully to {org_url}")
                    print(f"Project: {project}")
                    if team:
                        print(f"Team: {team}")
                    print("\nConnection successful!")
                
                # Save settings if requested
                if self.save_settings_var.get():
                    self.save_settings()
                
                # Update status
                self.status_var.set("Connected to Azure DevOps")
                
                # Enable other tabs
                self.notebook.tab(1, state="normal")  # Test Open Arena - AI Models tab
                self.notebook.tab(2, state="normal")  # ADO Team Selection tab
                self.notebook.tab(3, state="normal")  # Open Arena - AI Model Selection tab
                self.notebook.tab(4, state="normal")  # Related Work Items tab
                self.notebook.tab(5, state="normal")  # ADO Operations tab
                
                # Automatically load teams after successful connection
                self.root.after(1000, self.auto_load_teams)  # Delay by 1 second to ensure UI is ready
                
            except Exception as e:
                # Show error
                with redirect_stdout(redirect):
                    print(f"Error connecting to Azure DevOps: {str(e)}")
                
                # Update status
                self.status_var.set("Connection failed")
                
                # Disable other tabs
                self.notebook.tab(1, state="disabled")  # Test Open Arena - AI Models tab
                self.notebook.tab(2, state="disabled")  # ADO Team Selection tab
                self.notebook.tab(3, state="disabled")  # Open Arena - AI Model Selection tab
                self.notebook.tab(4, state="disabled")  # Related Work Items tab
                self.notebook.tab(5, state="disabled")  # ADO Operations tab
        
        # Start connection thread
        threading.Thread(target=connect_thread).start()
    
    def on_auto_connect_changed(self):
        """Handle auto-connect checkbox state change."""
        if self.auto_connect_var.get():
            # Auto-connect is enabled, check if we have valid settings and connect
            org_url = self.org_url_var.get().strip()
            pat = self.pat_var.get().strip()
            project = self.project_var.get().strip()
            
            if org_url and pat and project:
                # We have valid settings, trigger auto-connect
                self.auto_connect_to_ado()
            else:
                # Missing required settings, show message
                messagebox.showinfo("Auto Connect", "Please fill in Organization URL, PAT, and Project before enabling auto-connect.")
                self.auto_connect_var.set(False)
    
    def auto_connect_to_ado(self):
        """Automatically connect to ADO when auto-connect is enabled."""
        # Only auto-connect if we're not already connected
        if not hasattr(self, 'client') or self.client is None:
            self.connect_to_ado()
    
    def auto_load_teams(self):
        """Automatically load teams after successful connection."""
        try:
            # Get project
            project = self.team_project_var.get().strip()
            
            # Update status
            self.status_var.set(f"Auto-loading teams for project '{project}'...")
            
            # Get teams from Azure DevOps
            teams_response = self.client.get_teams(project)
            
            if teams_response:
                available_teams = [team.name for team in teams_response]
                print(f"✅ Auto-loaded {len(available_teams)} teams from Azure DevOps")
                
                # Update the team selection dropdown with default selection
                self.update_team_dropdown(available_teams)
                
                # Update status
                self.status_var.set(f"Auto-loaded {len(available_teams)} teams. First team set as default.")
            else:
                print("ℹ️ No teams available for auto-loading")
                self.status_var.set("No teams available for auto-loading")
                
        except Exception as e:
            print(f"Error auto-loading teams: {str(e)}")
            self.status_var.set("Failed to auto-load teams")
    
    def get_teams(self):
        """Get and display available teams for the selected project."""
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Get project
        project = self.team_project_var.get().strip()
        
        # Update status
        self.status_var.set(f"Getting teams for project '{project}'...")
        
        # Clear output
        self.teams_output.configure(state="normal")
        self.teams_output.delete(1.0, tk.END)
        self.teams_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.teams_output)
        
        # Get teams in a separate thread
        def get_teams_thread():
            try:
                # Get teams from Azure DevOps
                with redirect_stdout(redirect):
                    print(f"Getting teams for project '{project}'...")
                    print("Making API call to Azure DevOps...")
                    
                    # Make actual API call to get teams
                    teams_response = self.client.get_teams(project)
                    
                    if teams_response:
                        available_teams = [team.name for team in teams_response]
                        print(f"✅ Successfully retrieved {len(available_teams)} teams from Azure DevOps")
                        print(f"🔍 Teams response type: {type(teams_response)}")
                        print(f"🔍 Teams response length: {len(teams_response)}")
                        
                        # Print detailed team information
                        self.client.print_teams(teams_response)
                        
                        # Show raw output (limit to first 20 for readability, but show total count)
                        print("\n" + "="*60)
                        print(f"RAW TEAM DATA OUTPUT (Showing first 20 of {len(teams_response)} teams)")
                        print("="*60)
                        
                        # Show first 20 teams in detail
                        for i, team in enumerate(teams_response[:20], 1):
                            print(f"\nTeam {i} Raw Data:")
                            print(f"  Name: {team.name}")
                            print(f"  ID: {team.id}")
                            print(f"  Description: {team.description}")
                            print(f"  URL: {team.url}")
                            print(f"  Identity URL: {team.identity_url}")
                            print(f"  All attributes: {dir(team)}")
                            print(f"  Raw object: {team}")
                        
                        if len(teams_response) > 20:
                            print(f"\n... and {len(teams_response) - 20} more teams (truncated for display)")
                        
                        print("="*60)
                    else:
                        print("❌ No teams returned from Azure DevOps")
                        available_teams = []
                    
                    print("\nAvailable teams from your project:")
                    print("=" * 50)
                    
                    # Display teams
                    for i, team in enumerate(available_teams, 1):
                        print(f"{i}. {team}")
                    
                    print()
                    
                    # Update the team selection dropdown
                    self.root.after(0, lambda: self.update_team_dropdown(available_teams))
                    
                    # Update team details display
                    self.root.after(0, lambda: self.update_team_details(available_teams))
                    
                    print("✅ Teams loaded successfully!")
                    print("💡 Teams are automatically sorted alphabetically and the first team is set as default.")
                    print("💡 You can type to filter teams in the dropdown, and selection happens automatically.")
                
                # Update status
                self.status_var.set(f"Retrieved {len(available_teams)} teams for project '{project}'")
                
            except Exception as e:
                # Show error
                with redirect_stdout(redirect):
                    print(f"❌ Error retrieving teams: {str(e)}")
                    print("🔄 Please check your connection and try again.")
                    
                    available_teams = []
                
                    print("No teams available due to error.")
                    print("Please ensure you are connected to Azure DevOps and have access to the project.")
                
                # Update status
                self.status_var.set("Failed to retrieve teams")
        
        # Start thread
        threading.Thread(target=get_teams_thread).start()
    
    def get_team_work_items_from_related_tab(self):
        """Get all work items for the selected team from the Related Work Items tab."""
        print("🔍 DEBUG: ==========================================")
        print("🔍 DEBUG: get_team_work_items_from_related_tab() called")
        print("🔍 DEBUG: ==========================================")
        
        # Validate that we're on the correct tab
        current_tab = self.notebook.select()
        current_tab_name = self.notebook.tab(current_tab, 'text')
        
        print(f"🔍 DEBUG: Current tab index: {current_tab}")
        print(f"🔍 DEBUG: Current tab name: '{current_tab_name}'")
        print(f"🔍 DEBUG: Expected tab name: 'Related Work Items'")
        
        if current_tab_name != "Related Work Items":
            print(f"⚠️ WARNING: Called from wrong tab: '{current_tab_name}' instead of 'Related Work Items'")
            # Don't switch tabs, just show a warning
            messagebox.showwarning("Wrong Tab", f"This function should be called from the 'Related Work Items' tab, not from '{current_tab_name}'.")
            return
        
        print("🔍 DEBUG: Tab validation passed - continuing execution")
        
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Check if a team is selected
        selected_team = self.team_selection_var.get()
        if not selected_team or selected_team == "No teams available":
            # Provide more helpful error message
            result = messagebox.askyesno(
                "No Team Selected", 
                "No team is currently selected. Would you like to load available teams now?\n\n"
                "This will automatically set the first team as default."
            )
            if result:
                self.get_teams()
            return
        
        # Get project
        project = self.team_project_var.get().strip()
        
        # Ensure filters are populated with actual values from the project
        if self.client:
            self.auto_populate_enhanced_filters()
        
        # Update status
        self.status_var.set(f"Getting work items for team '{selected_team}'...")
        
        # Clear output
        self.teams_output.configure(state="normal")
        self.teams_output.delete(1.0, tk.END)
        self.teams_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.teams_output)
        
        # Get work items in a separate thread
        def get_work_items_thread():
            try:
                with redirect_stdout(redirect):
                    print(f"Getting work items for team '{selected_team}' in project '{project}'...")
                    print("=" * 60)
                    
                    # Get filter values with proper validation
                    work_item_type_filter = self.work_item_type_filter.get()
                    state_filter = self.state_filter.get()
                    sub_state_filter = self.sub_state_filter.get()
                    date_range_filter = self.date_range_filter.get()
                    
                    # Validate and transform filters
                    work_item_type, state = self._validate_and_transform_filters(
                        project, work_item_type_filter, state_filter
                    )
                    
                    print(f"Filters applied:")
                    print(f"  Work Item Type: {work_item_type_filter} → {work_item_type}")
                    print(f"  State: {state_filter} → {state}")
                    print(f"  Sub-State: {sub_state_filter}")
                    print(f"  Date Range: {date_range_filter}")
                    print(f"  Team: {selected_team}")
                    print(f"  Project: {project}")
                    print()
                    
                    print(f"[DEBUG] Making ADO API call with team context: '{selected_team}'")
                    print(f"   - Project: {project}")
                    print(f"   - Work Item Type Filter: {work_item_type}")
                    print(f"   - State Filter: {state}")
                    print(f"   - Limit: Intelligent (up to 5000 with enhanced filters)")
                    print()
                    print("📋 Query Strategy:")
                    print("The system will attempt to get team-specific work items in this order:")
                    print("1️⃣ Team Backlog Context (Most Specific)")
                    print("2️⃣ Team Area Path (Fallback)")
                    print("3️⃣ Manual Area Path Mapping (Fallback)")
                    print("4️⃣ Project-Wide Query (Last Resort)")
                    print()
                    
                    # Get work items for the team with enhanced filtering
                    # Collect enhanced filter values
                    enhanced_filters = {}
                    if hasattr(self, 'work_item_type_filter') and self.work_item_type_filter.get() != "All":
                        enhanced_filters['work_item_type'] = self.work_item_type_filter.get()
                    if hasattr(self, 'state_filter') and self.state_filter.get() != "All":
                        enhanced_filters['state'] = self.state_filter.get()
                    if hasattr(self, 'sub_state_filter') and self.sub_state_filter.get() != "All":
                        enhanced_filters['sub_state'] = self.sub_state_filter.get()
                    # Removed assigned_to filter as requested
                    if hasattr(self, 'iteration_path_filter') and self.iteration_path_filter.get() != "All":
                        enhanced_filters['iteration_path'] = self.iteration_path_filter.get()
                    if hasattr(self, 'area_path_filter') and self.area_path_filter.get() != "All":
                        enhanced_filters['area_path'] = self.area_path_filter.get()
                    if hasattr(self, 'tags_filter') and self.tags_filter.get() != "All":
                        enhanced_filters['tags'] = self.tags_filter.get()
                    if hasattr(self, 'priority_filter') and self.priority_filter.get() != "All":
                        enhanced_filters['priority'] = self.priority_filter.get()
                    if hasattr(self, 'created_by_filter') and self.created_by_filter.get() != "All":
                        enhanced_filters['created_by'] = self.created_by_filter.get()
                    if hasattr(self, 'date_range_filter') and self.date_range_filter.get() != "All":
                        enhanced_filters['date_range'] = self.date_range_filter.get()
                    
                    # Use intelligent limit based on filters
                    limit = None  # Let the system determine intelligent limits
                    if enhanced_filters:
                        limit = 5000  # Higher limit when using enhanced filters
                        print(f"Using enhanced filters with limit: {limit}")
                        print(f"Enhanced filters: {enhanced_filters}")
                    
                    work_items = self.client.query_work_items(
                        project=project,
                        team=selected_team,  # Pass the selected team
                        work_item_type=work_item_type,
                        state=state,
                        limit=limit,  # Intelligent limit instead of hard 100
                        enhanced_filters=enhanced_filters
                    )
                    
                    if work_items:
                        print(f"[SUCCESS] Retrieved {len(work_items)} work items for team '{selected_team}'")
                        print()
                        
                        # Debug: Show states of retrieved work items
                        if state:
                            print(f"[DEBUG] Checking states of retrieved work items (filtered by '{state}'):")
                            item_states = {}
                            for item in work_items:
                                item_state = item.fields.get("System.State", "Unknown")
                                item_states[item_state] = item_states.get(item_state, 0) + 1
                            print(f"   States found in results: {item_states}")
                            if state not in item_states:
                                print(f"[WARNING] No work items found with state '{state}'!")
                                print(f"   This suggests the state filter is not working correctly.")
                        print()
                        
                        # Analyze the results to determine how team-specific they are
                        print("[DEBUG] Analyzing Results:")
                        area_paths = {}
                        for item in work_items:
                            area_path = item.fields.get("System.AreaPath", "Unknown")
                            area_paths[area_path] = area_paths.get(area_path, 0) + 1
                        
                        # Get team area path for comparison
                        team_area_path = None
                        try:
                            team_info = self.client.get_team_info(project, selected_team)
                            team_area_path = team_info.get('default_area_path') if team_info else None
                        except:
                            pass
                        
                        # Calculate team-specific percentage
                        team_specific_count = 0
                        if team_area_path:
                            for path, count in area_paths.items():
                                if path.startswith(team_area_path):
                                    team_specific_count += count
                            
                            team_specific_percentage = (team_specific_count / len(work_items) * 100)
                            
                            if team_specific_percentage >= 80:
                                print(f"✅ EXCELLENT: {team_specific_percentage:.1f}% of items are team-specific")
                            elif team_specific_percentage >= 50:
                                print(f"⚠️ GOOD: {team_specific_percentage:.1f}% of items are team-specific")
                            else:
                                print(f"❌ POOR: {team_specific_percentage:.1f}% of items are team-specific")
                                print("   This suggests the query fell back to project-wide search")
                        else:
                            print("⚠️ Could not determine team area path for analysis")
                        
                        print()
                        print("Work items have been retrieved successfully!")
                        print("Switch to the 'Work Items' tab to view them in different formats:")
                        print("  - Summary View: Compact table format")
                        print("  - Detailed View: Full information for each item")
                        print("  - Table View: Interactive table with sorting")
                        print()
                        print("You can also:")
                        print("  - Refresh the display")
                        print("  - Clear the display")
                        print("  - Export to a text file")
                        print("  - Use '🔍 Verify Team-Specific' to analyze results in detail")
                        
                        # Display work items in the new tab
                        self.root.after(0, lambda: self.display_work_items(work_items))
                        
                        # Stay on the current tab (Related Work Items)
                        # Don't switch tabs - let the user stay where they are
                        
                    else:
                        print(f"ℹ️ No work items found for team '{selected_team}'")
                        print("This could mean:")
                        print("  - The team has no work items assigned")
                        print("  - The work items are not properly associated with the team")
                        print("  - You may need to check team context or area path settings")
                        print()
                        print("💡 Troubleshooting:")
                        print("  - Use '🧪 Test Team Context' to diagnose team configuration")
                        print("  - Use '📚 Explain Team Query Strategy' to understand how queries work")
                        print("  - Check if the team has an area path configured in Azure DevOps")
                
                # Update status
                self.status_var.set(f"Retrieved {len(work_items) if work_items else 0} work items for team '{selected_team}'")
                
            except Exception as e:
                with redirect_stdout(redirect):
                    print(f"❌ Error retrieving work items for team '{selected_team}': {str(e)}")
                    print("Please check:")
                    print("  - Your connection to Azure DevOps")
                    print("  - Team permissions and access")
                    print("  - Project and team configuration")
                
                # Update status
                self.status_var.set("Failed to retrieve work items")
        
        # Start thread
        threading.Thread(target=get_work_items_thread).start()
    
    def _validate_and_transform_filters(self, project, work_item_type_filter, state_filter):
        """
        Validate and transform filter values to ensure they are valid for the project.
        
        Args:
            project (str): The project name
            work_item_type_filter (str): The selected work item type filter
            state_filter (str): The selected state filter
            
        Returns:
            tuple: (validated_work_item_type, validated_state)
        """
        try:
            # Initialize validated filters
            validated_work_item_type = None
            validated_state = None
            
            # Get available work item types and states for validation
            available_work_item_types = []
            available_states = []
            
            try:
                available_work_item_types = self.client.get_work_item_types(project)
                available_states = self.client.get_work_item_states(project)
                print(f"[DEBUG] Available work item types: {available_work_item_types}")
                print(f"[DEBUG] Available states: {available_states}")
            except Exception as e:
                print(f"[WARNING] Could not retrieve available types/states: {e}")
                # Continue with validation using empty lists
            
            # Validate and transform work item type filter
            if work_item_type_filter and work_item_type_filter.strip() and work_item_type_filter != "All":
                work_item_type = work_item_type_filter.strip()
                if available_work_item_types and work_item_type not in available_work_item_types:
                    print(f"[WARNING] Work item type '{work_item_type}' not found in available types!")
                    print(f"   Available types: {available_work_item_types}")
                    print(f"   This might cause the filter to not work properly.")
                    # Try to find a close match
                    close_match = self._find_close_match(work_item_type, available_work_item_types)
                    if close_match:
                        print(f"   Using close match: '{close_match}'")
                        validated_work_item_type = close_match
                    else:
                        print(f"   No close match found, using original value")
                        validated_work_item_type = work_item_type
                else:
                    validated_work_item_type = work_item_type
            
            # Validate and transform state filter
            if state_filter and state_filter.strip() and state_filter != "All":
                state = state_filter.strip()
                if available_states and state not in available_states:
                    print(f"[WARNING] State '{state}' not found in available states!")
                    print(f"   Available states: {available_states}")
                    print(f"   This might cause the filter to not work properly.")
                    # Try to find a close match
                    close_match = self._find_close_match(state, available_states)
                    if close_match:
                        print(f"   Using close match: '{close_match}'")
                        validated_state = close_match
                    else:
                        print(f"   No close match found, using original value")
                        validated_state = state
                else:
                    validated_state = state
            
            print(f"[DEBUG] Filter validation complete:")
            print(f"   Work Item Type: '{work_item_type_filter}' → '{validated_work_item_type}'")
            print(f"   State: '{state_filter}' → '{validated_state}'")
            
            return validated_work_item_type, validated_state
            
        except Exception as e:
            print(f"[ERROR] Error validating filters: {e}")
            # Return original values as fallback
            work_item_type = None if work_item_type_filter in ["All", ""] else work_item_type_filter
            state = None if state_filter in ["All", ""] else state_filter
            return work_item_type, state
    
    def _find_close_match(self, target, options):
        """
        Find a close match for a target string in a list of options.
        
        Args:
            target (str): The target string to match
            options (list): List of available options
            
        Returns:
            str or None: The closest match or None if no close match found
        """
        if not target or not options:
            return None
        
        target_lower = target.lower()
        
        # Exact match (case insensitive)
        for option in options:
            if option.lower() == target_lower:
                return option
        
        # Partial match
        for option in options:
            if target_lower in option.lower() or option.lower() in target_lower:
                return option
        
        # Fuzzy match (simple character similarity)
        best_match = None
        best_score = 0
        
        for option in options:
            score = self._calculate_similarity(target_lower, option.lower())
            if score > best_score and score > 0.6:  # 60% similarity threshold
                best_score = score
                best_match = option
        
        return best_match
    
    def _calculate_similarity(self, str1, str2):
        """
        Calculate similarity between two strings using simple character matching.
        
        Args:
            str1 (str): First string
            str2 (str): Second string
            
        Returns:
            float: Similarity score between 0 and 1
        """
        if not str1 or not str2:
            return 0.0
        
        # Simple character-based similarity
        common_chars = set(str1) & set(str2)
        total_chars = set(str1) | set(str2)
        
        if not total_chars:
            return 0.0
        
        return len(common_chars) / len(total_chars)
    
    def show_performance_settings(self):
        """Show performance settings dialog for work item retrieval."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Performance Settings")
        settings_window.geometry("600x400")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Center the window
        settings_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 100, self.root.winfo_rooty() + 100))
        
        # Main frame
        main_frame = ttk.Frame(settings_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="⚙️ Performance Settings", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Work Item Retrieval Settings", padding="15")
        settings_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Default limit setting
        limit_frame = ttk.Frame(settings_frame)
        limit_frame.pack(fill=tk.X, pady=(0, 10))
        
        limit_label = ttk.Label(limit_frame, text="Default Work Item Limit:")
        limit_label.pack(side=tk.LEFT)
        
        limit_var = tk.StringVar(value="50")
        limit_entry = ttk.Entry(limit_frame, textvariable=limit_var, width=10)
        limit_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        limit_help = ttk.Label(limit_frame, text="(1-1000, lower = faster)", font=("Arial", 8))
        limit_help.pack(side=tk.LEFT, padx=(10, 0))
        
        # Timeout settings
        timeout_frame = ttk.Frame(settings_frame)
        timeout_frame.pack(fill=tk.X, pady=(0, 10))
        
        timeout_label = ttk.Label(timeout_frame, text="Connection Timeout (seconds):")
        timeout_label.pack(side=tk.LEFT)
        
        timeout_var = tk.StringVar(value="30")
        timeout_entry = ttk.Entry(timeout_frame, textvariable=timeout_var, width=10)
        timeout_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Query strategy settings
        strategy_frame = ttk.Frame(settings_frame)
        strategy_frame.pack(fill=tk.X, pady=(0, 10))
        
        strategy_label = ttk.Label(strategy_frame, text="Query Strategy:")
        strategy_label.pack(side=tk.LEFT)
        
        strategy_var = tk.StringVar(value="optimized")
        strategy_combo = ttk.Combobox(strategy_frame, textvariable=strategy_var, 
                                     values=["optimized", "comprehensive", "fast"], 
                                     state="readonly", width=15)
        strategy_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Performance tips
        tips_frame = ttk.LabelFrame(main_frame, text="💡 Performance Tips", padding="15")
        tips_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        tips_text = tk.Text(tips_frame, height=8, wrap=tk.WORD, font=("Arial", 9))
        tips_text.pack(fill=tk.BOTH, expand=True)
        
        tips_content = """• Lower work item limits (10-50) provide faster results
• Use specific work item types and states to reduce query time
• The 'optimized' strategy tries the fastest methods first
• Connection timeouts prevent hanging on slow networks
• Batch processing is used automatically for large result sets
• Progress indicators show real-time status during retrieval"""
        
        tips_text.insert(tk.END, tips_content)
        tips_text.config(state=tk.DISABLED)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        save_button = ttk.Button(button_frame, text="Save Settings", 
                                command=lambda: self.save_performance_settings(limit_var.get(), timeout_var.get(), strategy_var.get(), settings_window))
        save_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        cancel_button = ttk.Button(button_frame, text="Cancel", 
                                  command=settings_window.destroy)
        cancel_button.pack(side=tk.RIGHT)
        
        reset_button = ttk.Button(button_frame, text="Reset to Defaults", 
                                 command=lambda: self.reset_performance_settings(limit_var, timeout_var, strategy_var))
        reset_button.pack(side=tk.LEFT)
    
    def save_performance_settings(self, limit, timeout, strategy, window):
        """Save performance settings."""
        try:
            # Validate inputs
            limit_int = int(limit)
            if limit_int < 1 or limit_int > 1000:
                messagebox.showerror("Invalid Input", "Work item limit must be between 1 and 1000")
                return
            
            timeout_int = int(timeout)
            if timeout_int < 5 or timeout_int > 300:
                messagebox.showerror("Invalid Input", "Timeout must be between 5 and 300 seconds")
                return
            
            # Save settings (you can implement persistent storage here)
            self.performance_settings = {
                'default_limit': limit_int,
                'connection_timeout': timeout_int,
                'query_strategy': strategy
            }
            
            messagebox.showinfo("Success", "Performance settings saved successfully!")
            window.destroy()
            
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for limit and timeout")
    
    def reset_performance_settings(self, limit_var, timeout_var, strategy_var):
        """Reset performance settings to defaults."""
        limit_var.set("50")
        timeout_var.set("30")
        strategy_var.set("optimized")
    
    def show_team_help(self):
        """Show help information for team work item retrieval."""
        help_window = tk.Toplevel(self.root)
        help_window.title("Team Work Item Retrieval Help")
        help_window.geometry("700x500")
        help_window.transient(self.root)
        help_window.grab_set()
        
        # Center the window
        help_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # Main frame
        main_frame = ttk.Frame(help_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="❓ Team Work Item Retrieval Help", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Help text
        help_text = tk.Text(main_frame, wrap=tk.WORD, font=("Arial", 10))
        help_text.pack(fill=tk.BOTH, expand=True)
        
        help_content = """🔍 How to Get Work Items for a Selected Team

1. SELECT A TEAM:
   • Choose a team from the dropdown list
   • If no teams are available, click "Get Teams" first
   • The system will remember your last selection

2. APPLY FILTERS (Optional):
   • Work Item Type: Filter by specific types (Bug, User Story, etc.)
   • State: Filter by work item state (Active, Closed, etc.)
   • Leave as "All" for no filtering

3. CLICK "Get Work Items for Selected Team":
   • The system will query Azure DevOps using optimized strategies
   • Progress indicators show real-time status
   • Results are displayed in the "Related Work Items" tab

📋 Query Strategy (Automatic):
   • Strategy 1: Team Backlog Context (Fastest, most reliable)
   • Strategy 2: Team Area Path (Fast, if configured)
   • Strategy 3: Project-wide Query (Slower, fallback)

⚡ Performance Tips:
   • Use specific filters to reduce query time
   • Lower work item limits for faster results
   • Check "Performance Settings" for optimization options
   • The system automatically uses batch processing for large results

🔧 Troubleshooting:
   • If queries are slow, check your network connection
   • Verify team permissions in Azure DevOps
   • Use "Test Team Context" to diagnose issues
   • Check "Performance Settings" for timeout configurations

💡 Best Practices:
   • Start with smaller limits (10-50) for testing
   • Use specific work item types when possible
   • Monitor the progress indicators during retrieval
   • Check the performance metrics in the output"""
        
        help_text.insert(tk.END, help_content)
        help_text.config(state=tk.DISABLED)
        
        # Close button
        close_button = ttk.Button(main_frame, text="Close", command=help_window.destroy)
        close_button.pack(pady=(20, 0))
    
    def get_practical_law_westlaw_teams(self):
        """Get and display teams related to Practical Law and Westlaw."""
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Get project
        project = self.team_project_var.get().strip()
        
        # Update status
        self.status_var.set(f"Getting Practical Law and Westlaw teams for project '{project}'...")
        
        # Clear output
        self.teams_output.configure(state="normal")
        self.teams_output.delete(1.0, tk.END)
        self.teams_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.teams_output)
        
        # Get teams in a separate thread
        def get_pl_wl_teams_thread():
            try:
                # Get teams from Azure DevOps
                with redirect_stdout(redirect):
                    print(f"Getting Practical Law and Westlaw teams for project '{project}'...")
                    print("Making API call to Azure DevOps...")
                    print("=" * 60)
                    
                    # Make actual API call to get teams
                    all_teams_response = self.client.get_teams(project)
                    
                    if all_teams_response:
                        print(f"✅ Successfully retrieved {len(all_teams_response)} total teams from Azure DevOps")
                        
                        # Filter teams for Practical Law and Westlaw
                        pl_wl_teams = []
                        for team in all_teams_response:
                            team_name = team.name.lower()
                            if any(keyword in team_name for keyword in ['practical law', 'westlaw', 'pl', 'wl']):
                                pl_wl_teams.append(team)
                        
                        print(f"🔍 Found {len(pl_wl_teams)} teams related to Practical Law and Westlaw:")
                        print("=" * 60)
                        
                        if pl_wl_teams:
                            # Display filtered teams
                            for i, team in enumerate(pl_wl_teams, 1):
                                print(f"\n{i}. {team.name}")
                                print(f"   ID: {team.id}")
                                print(f"   Description: {team.description}")
                                print(f"   URL: {team.url}")
                                print(f"   Identity URL: {team.identity_url}")
                                print("-" * 40)
                            
                            # Update the team selection dropdown with filtered teams
                            filtered_team_names = [team.name for team in pl_wl_teams]
                            self.root.after(0, lambda: self.update_team_dropdown(filtered_team_names))
                            
                            # Update team details display
                            self.root.after(0, lambda: self.update_team_details(filtered_team_names))
                            
                            print(f"\n✅ Successfully filtered and displayed {len(pl_wl_teams)} Practical Law and Westlaw teams")
                            print("💡 These teams are now available in the dropdown above.")
                            print("💡 Teams are automatically sorted and the first team is set as default.")
                        else:
                            print("ℹ️ No teams found matching Practical Law or Westlaw criteria")
                            print("This could mean:")
                            print("  - Teams don't have these keywords in their names")
                            print("  - Teams might be named differently")
                            print("  - You may need to check the full team list for variations")
                            
                            # Show all team names for reference
                            print("\nAll available team names for reference:")
                            print("-" * 40)
                            for i, team in enumerate(all_teams_response, 1):
                                print(f"{i}. {team.name}")
                        
                        print("=" * 60)
                    else:
                        print("❌ No teams returned from Azure DevOps")
                        print("Please check your connection and project access.")
                
                # Update status
                if 'pl_wl_teams' in locals() and pl_wl_teams:
                    self.status_var.set(f"Retrieved {len(pl_wl_teams)} Practical Law and Westlaw teams for project '{project}'")
                else:
                    self.status_var.set("No Practical Law and Westlaw teams found")
                
            except Exception as e:
                # Show error
                with redirect_stdout(redirect):
                    print(f"❌ Error retrieving Practical Law and Westlaw teams: {str(e)}")
                    print("🔄 Please check your connection and try again.")
                    print("Please ensure you are connected to Azure DevOps and have access to the project.")
                
                # Update status
                self.status_var.set("Failed to retrieve Practical Law and Westlaw teams")
        
        # Start thread
        threading.Thread(target=get_pl_wl_teams_thread).start()
    
    def test_team_context(self):
        """Test team context and show detailed information about the selected team."""
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Check if a team is selected
        selected_team = self.team_selection_var.get()
        if not selected_team or selected_team == "No teams available":
            # Provide more helpful error message
            result = messagebox.askyesno(
                "No Team Selected", 
                "No team is currently selected. Would you like to load available teams now?\n\n"
                "This will automatically set the first team as default."
            )
            if result:
                self.get_teams()
            return
        
        # Get project
        project = self.team_project_var.get().strip()
        
        # Update status
        self.status_var.set(f"Testing team context for team '{selected_team}'...")
        
        # Clear output
        self.teams_output.configure(state="normal")
        self.teams_output.delete(1.0, tk.END)
        self.teams_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.teams_output)
        
        # Test team context in a separate thread
        def test_team_context_thread():
            try:
                with redirect_stdout(redirect):
                    print(f"🔍 Testing Team Context for '{selected_team}'")
                    print("=" * 60)
                    
                    print(f"Project: {project}")
                    print(f"Selected Team: {selected_team}")
                    print()
                    
                    # Use the new backend method to test team context
                    print("🧪 Running comprehensive team context tests...")
                    success = self.client.test_team_context(project, selected_team)
                    
                    if success:
                        print("✅ Team context testing completed successfully")
                        print("Check the logs for detailed information about each test")
                    else:
                        print("❌ Team context testing failed")
                        print("Check the logs for error details")
                    
                    print()
                    print("=" * 60)
                    print("🎯 Team Context Test Summary:")
                    print(f"   Team: '{selected_team}' in project '{project}'")
                    print(f"   Status: {'✅ Success' if success else '❌ Failed'}")
                    print(f"   💡 Use 'Get Work Items for Selected Team' to retrieve team-specific work items")
                    print(f"   💡 Use '📚 Explain Team Query Strategy' to understand how queries work")
                    print(f"   💡 Use '🔍 Verify Team-Specific' to check query results")
                
                # Update status
                self.status_var.set(f"Team context test completed for '{selected_team}'")
                
            except Exception as e:
                with redirect_stdout(redirect):
                    print(f"❌ Error during team context test: {str(e)}")
                    print("Please check your connection and team selection.")
                
                # Update status
                self.status_var.set("Team context test failed")
        
        # Start thread
        threading.Thread(target=test_team_context_thread).start()
    
    def filter_teams(self, event):
        """Filter teams based on user input in the combobox."""
        try:
            # Get the current input value
            current_value = self.team_selection_var.get().lower()
            
            # Get all available teams
            all_teams = self.team_combo['values']
            
            if not current_value:
                # If no input, show all teams
                self.team_combo['values'] = all_teams
                return
            
            # Filter teams that contain the input value
            filtered_teams = [team for team in all_teams if current_value in team.lower()]
            
            # Update the dropdown values
            self.team_combo['values'] = filtered_teams
            
            # If there's only one match, select it
            if len(filtered_teams) == 1:
                self.team_combo.set(filtered_teams[0])
                self.team_selection_var.set(filtered_teams[0])
                self.on_team_selected(None)
            
        except Exception as e:
            print(f"Error filtering teams: {str(e)}")
    
    def on_team_selected(self, event):
        """Handle team selection from dropdown."""
        try:
            selected_team = self.team_selection_var.get()
            
            if selected_team and selected_team != "No teams available":
                # Update the team variable in the connection tab
                self.team_var.set(selected_team)
                
                # Update status
                self.status_var.set(f"Team automatically set to: {selected_team}")
                
                # Update filter frame title with selected team
                self.update_filter_frame_title(selected_team)
                
                # Show confirmation in status bar (not popup to avoid interruption)
                print(f"✅ Team '{selected_team}' has been automatically set!")
                print(f"💡 You can now use this team in other tabs.")
                
                # Auto-populate enhanced filters in background thread
                if self.client:
                    print(f"🔄 Auto-populating enhanced filters for team '{selected_team}'...")
                    self.auto_populate_enhanced_filters()
                else:
                    print("⚠️ No ADO connection available. Filters will be populated when connection is established.")
                
        except Exception as e:
            print(f"Error handling team selection: {str(e)}")
    
    def populate_filters_dynamically(self):
        """Dynamically populate the work item type and state filters with actual values from the project."""
        try:
            if not self.client:
                return
            
            project = self.team_project_var.get().strip()
            if not project:
                return
            
            # Get work item types and states in a separate thread to avoid blocking the UI
            def populate_filters_thread():
                try:
                    # Get available work item types
                    work_item_types = self.client.get_work_item_types(project)
                    if work_item_types:
                        # Update the work item type filter dropdown
                        self.root.after(0, lambda: self.update_work_item_type_filter(work_item_types))
                        
                        # After updating work item types, trigger state filter update based on current selection
                        self.root.after(100, self.on_work_item_type_changed)
                    else:
                        # Fallback: get available states for all work item types
                        states = self.client.get_work_item_states(project)
                        if states:
                            # Update the state filter dropdown
                            self.root.after(0, lambda: self.update_state_filter(states))
                        
                except Exception as e:
                    print(f"Warning: Could not populate filters dynamically: {e}")
                    print("Using default filter values instead.")
            
            # Start the thread
            threading.Thread(target=populate_filters_thread, daemon=True).start()
            
        except Exception as e:
            print(f"Error setting up dynamic filter population: {e}")
    
    def update_work_item_type_filter(self, work_item_types):
        """Update the work item type filter dropdown with actual values."""
        try:
            # Add "All" at the beginning
            all_types = ["All"] + sorted(work_item_types)
            
            # Update the combobox values
            for widget in self.root.winfo_children():
                if hasattr(widget, 'winfo_children'):
                    for child in widget.winfo_children():
                        if hasattr(child, 'winfo_children'):
                            for grandchild in child.winfo_children():
                                if hasattr(grandchild, 'winfo_children'):
                                    for great_grandchild in grandchild.winfo_children():
                                        if hasattr(great_grandchild, 'winfo_children'):
                                            for filters_frame in great_grandchild.winfo_children():
                                                if hasattr(filters_frame, 'grid_slaves'):
                                                    # Find the work item type combobox
                                                    for widget in filters_frame.grid_slaves():
                                                        if hasattr(widget, 'cget') and widget.cget('textvariable') == str(self.work_item_type_filter):
                                                            widget['values'] = all_types
                                                            print(f"✅ Updated work item type filter with {len(work_item_types)} types")
                                                            return
            
            # Fallback: try to find the combobox by searching through the notebook
            for tab_id in range(self.notebook.index('end')):
                tab_widget = self.notebook.nametowidget(tab_id)
                self._find_and_update_combobox(tab_widget, 'work_item_type', all_types)
                
        except Exception as e:
            print(f"Error updating work item type filter: {e}")
    
    def update_state_filter(self, states):
        """Update the state filter dropdown with actual values."""
        try:
            # Add "All" at the beginning
            all_states = ["All"] + sorted(states)
            
            # Find and update the state filter combobox
            for tab_id in range(self.notebook.index('end')):
                tab_widget = self.notebook.nametowidget(tab_id)
                self._find_and_update_combobox(tab_widget, 'state', all_states)
                
        except Exception as e:
            print(f"Error updating state filter: {e}")
    
    def _find_and_update_combobox(self, parent_widget, filter_type, values):
        """Recursively find and update a combobox widget."""
        try:
            for widget in parent_widget.winfo_children():
                # Check if this is a combobox widget
                if isinstance(widget, ttk.Combobox):
                    try:
                        # Get the textvariable safely
                        textvar = widget.cget('textvariable')
                        if textvar:
                            if filter_type == 'work_item_type' and textvar == str(self.work_item_type_filter):
                                widget['values'] = values
                                print(f"✅ Updated {filter_type} filter with {len(values)-1} values")
                                return True
                            elif filter_type == 'state' and textvar == str(self.state_filter):
                                widget['values'] = values
                                print(f"✅ Updated {filter_type} filter with {len(values)-1} values")
                                return True
                    except Exception as e:
                        # Skip this widget if we can't get textvariable
                        continue
                
                # Recursively search children
                if hasattr(widget, 'winfo_children'):
                    if self._find_and_update_combobox(widget, filter_type, values):
                        return True
            
            return False
            
        except Exception as e:
            print(f"Error in _find_and_update_combobox: {e}")
            return False

    def on_work_item_type_changed(self, event=None):
        """Handle work item type selection change to update state filter."""
        try:
            if not self.client:
                print("⚠️ No ADO client available for work item type change")
                return
            
            project = self.team_project_var.get().strip()
            if not project:
                print("⚠️ No project selected for work item type change")
                return
            
            selected_work_item_type = self.work_item_type_filter.get()
            print(f"🔄 Work item type changed to: '{selected_work_item_type}'")
            
            # Get states based on selected work item type
            def update_states_thread():
                try:
                    if selected_work_item_type == "All":
                        # Get all unique states from all work item types
                        all_states = self.client.get_work_item_states(project)
                        print(f"📋 Getting all states for 'All' work item types: {len(all_states)} states")
                    else:
                        # Get states for specific work item type
                        all_states = self.client.get_work_item_states_for_type(project, selected_work_item_type)
                        print(f"📋 Getting states for '{selected_work_item_type}': {len(all_states)} states")
                    
                    if all_states:
                        # Add "All" at the beginning
                        states_with_all = ["All"] + sorted(all_states)
                        
                        # Update the state filter dropdown in the main thread
                        self.root.after(0, lambda: self.update_state_filter_for_work_item_type(states_with_all, selected_work_item_type))
                    else:
                        print(f"⚠️ No states found for work item type '{selected_work_item_type}'")
                        
                except Exception as e:
                    print(f"❌ Error getting states for work item type '{selected_work_item_type}': {e}")
                    # Fallback to default states
                    default_states = ["All", "Active", "Closed", "Resolved", "New", "In Progress", "Removed"]
                    self.root.after(0, lambda: self.update_state_filter_for_work_item_type(default_states, selected_work_item_type))
            
            # Start the thread to avoid blocking the UI
            threading.Thread(target=update_states_thread, daemon=True).start()
            
        except Exception as e:
            print(f"❌ Error handling work item type change: {e}")

    def update_state_filter_for_work_item_type(self, states, work_item_type):
        """Update the state filter dropdown with states relevant to the selected work item type."""
        try:
            # Find and update the state filter combobox
            for tab_id in range(self.notebook.index('end')):
                tab_widget = self.notebook.nametowidget(tab_id)
                if self._find_and_update_combobox(tab_widget, 'state', states):
                    print(f"✅ Updated state filter for '{work_item_type}' with {len(states)-1} states")
                    
                    # Reset state filter to "All" when work item type changes
                    current_state = self.state_filter.get()
                    if current_state not in states:
                        self.state_filter.set("All")
                        print(f"🔄 Reset state filter to 'All' (previous state '{current_state}' not available for '{work_item_type}')")
                    else:
                        print(f"✅ State filter '{current_state}' is still valid for '{work_item_type}'")
                    return
            
            print(f"⚠️ Could not find state filter combobox to update for '{work_item_type}'")
            
        except Exception as e:
            print(f"❌ Error updating state filter for work item type '{work_item_type}': {e}")
    
    def update_team_dropdown(self, teams):
        """Update the team selection dropdown with available teams."""
        try:
            # Sort teams alphabetically
            sorted_teams = sorted(teams, key=str.lower)
            
            # Store all teams for filtering
            self.all_teams = sorted_teams
            
            self.team_combo['values'] = sorted_teams
            if sorted_teams:
                # Use the first team as default
                selected_team = sorted_teams[0]
                print(f"✅ Setting default team to: {selected_team}")
                
                self.team_combo.set(selected_team)
                # Automatically set the selected team
                self.team_selection_var.set(selected_team)
                self.on_team_selected(None)
            else:
                self.team_combo.set("No teams available")
                self.team_selection_var.set("")
        except Exception as e:
            print(f"Error updating team dropdown: {str(e)}")
    
    def update_team_details(self, teams):
        """Update the team details display with team information and URLs."""
        try:
            # Clear existing team details
            for widget in self.team_details_frame.winfo_children():
                widget.destroy()
            
            # Add summary header
            summary_frame = ttk.Frame(self.team_details_frame)
            summary_frame.pack(fill=tk.X, pady=(0, 10))
            
            summary_label = ttk.Label(summary_frame, 
                                    text=f"Total Teams: {len(teams)}", 
                                    font=("TkDefaultFont", 12, "bold"),
                                    foreground="green")
            summary_label.pack(anchor=tk.W)
            
            # Add separator
            separator = ttk.Separator(summary_frame, orient='horizontal')
            separator.pack(fill=tk.X, pady=5)
            
            # Create team information display
            for i, team in enumerate(teams):
                team_frame = ttk.Frame(self.team_details_frame)
                team_frame.pack(fill=tk.X, pady=2)
                
                # Team name with number
                team_label = ttk.Label(team_frame, text=f"{i+1}. {team}", font=("TkDefaultFont", 9, "bold"))
                team_label.pack(anchor=tk.W)
                
                # Generate team URL dynamically
                project = self.team_project_var.get().strip()
                org_url = getattr(self.client, 'organization_url', 'https://dev.azure.com/your-organization') if self.client else 'https://dev.azure.com/your-organization'
                
                # Create the team backlog URL
                team_name_encoded = team.replace(' ', '%20').replace('-', '%20')
                url = f"{org_url}/{project}/_backlogs/backlog/{team_name_encoded}/Epics"
                
                url_frame = ttk.Frame(team_frame)
                url_frame.pack(fill=tk.X, padx=(20, 30))
                
                # Configure the URL frame to expand
                url_frame.columnconfigure(0, weight=1)
                url_frame.columnconfigure(1, weight=0)
                
                url_label = ttk.Label(url_frame, text=f"   URL: {url}", font=("TkDefaultFont", 8), foreground="blue", cursor="hand2")
                url_label.grid(row=0, column=0, sticky="w")
                
                # Copy URL button
                copy_button = ttk.Button(url_frame, text="📋 Copy", command=lambda u=url: self.copy_url_to_clipboard(u), width=8)
                copy_button.grid(row=0, column=1, sticky="e", padx=(10, 0))
                
                # Make URL clickable (bind click event)
                url_label.bind("<Button-1>", lambda e, u=url: self.open_url(u))
                url_label.bind("<Enter>", lambda e: url_label.configure(foreground="purple"))
                url_label.bind("<Leave>", lambda e: url_label.configure(foreground="blue"))
                
                # Add separator
                if i < len(teams) - 1:
                    separator = ttk.Separator(team_frame, orient='horizontal')
                    separator.pack(fill=tk.X, pady=2)
                    
        except Exception as e:
            print(f"Error updating team details: {str(e)}")
    
    def copy_url_to_clipboard(self, url):
        """Copy the team URL to clipboard."""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.status_var.set(f"URL copied to clipboard: {url[:50]}...")
        except Exception as e:
            self.status_var.set(f"Failed to copy URL: {str(e)}")
    
    def open_url(self, url):
        """Open the team URL in the default browser."""
        try:
            import webbrowser
            webbrowser.open(url)
            self.status_var.set(f"Opening URL: {url[:50]}...")
        except Exception as e:
            self.status_var.set(f"Failed to open URL: {str(e)}")
    
    def set_selected_team(self):
        """Set the selected team in the connection tab."""
        selected_team = self.team_selection_var.get()
        
        if not selected_team:
            # Provide more helpful error message
            result = messagebox.askyesno(
                "No Team Selected", 
                "No team is currently selected. Would you like to load available teams now?\n\n"
                "This will automatically set the first team as default."
            )
            if result:
                self.get_teams()
            return
        
        # Update the team variable in the connection tab
        self.team_var.set(selected_team)
        
        # Update status
        self.status_var.set(f"Team set to: {selected_team}")
        
        # Show confirmation
        messagebox.showinfo("Success", f"Team '{selected_team}' has been set successfully!\n\nYou can now use this team in other tabs.")
        
        # Switch to connection tab to show the updated team
        self.notebook.select(0)
    
    def get_work_item(self):
        """Get a work item by ID."""
        print("🔍 DEBUG: ==========================================")
        print("🔍 DEBUG: get_work_item() called")
        print("🔍 DEBUG: ==========================================")
        
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Get work item ID
        try:
            work_item_id = int(self.get_item_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Work Item ID must be a number.")
            return
        
        # Update status
        self.status_var.set(f"Getting work item {work_item_id}...")
        
        # Clear output
        self.get_item_output.configure(state="normal")
        self.get_item_output.delete(1.0, tk.END)
        self.get_item_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.get_item_output)
        
        # Get work item in a separate thread
        def get_item_thread():
            try:
                # Get work item
                with redirect_stdout(redirect):
                    work_item = self.client.get_work_item(work_item_id)
                    self.client.print_work_item_details(work_item)
                
                # Update status
                self.status_var.set(f"Retrieved work item {work_item_id}")
                
            except Exception as e:
                # Show error
                with redirect_stdout(redirect):
                    print(f"Error retrieving work item: {str(e)}")
                
                # Update status
                self.status_var.set("Failed to retrieve work item")
        
        # Start thread
        threading.Thread(target=get_item_thread).start()
    
    def query_work_items(self):
        """Query work items."""
        print("🔍 DEBUG: ==========================================")
        print("🔍 DEBUG: query_work_items() called")
        print("🔍 DEBUG: ==========================================")
        
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Get query parameters
        work_item_type = self.query_type_var.get().strip()
        state = self.query_state_var.get().strip()
        
        try:
            limit = int(self.query_limit_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Limit must be a number.")
            return
        
        # Get project
        project = self.project_var.get().strip()
        
        # Update status
        self.status_var.set(f"Querying work items...")
        
        # Clear output
        self.query_output.configure(state="normal")
        self.query_output.delete(1.0, tk.END)
        self.query_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.query_output)
        
        # Query work items in a separate thread
        def query_thread():
            try:
                # Query work items
                with redirect_stdout(redirect):
                    print(f"Querying work items in project '{project}'")
                    if work_item_type:
                        print(f"Work Item Type: {work_item_type}")
                    if state:
                        print(f"State: {state}")
                    print(f"Limit: {limit}")
                    print()
                    
                    work_items = self.client.query_work_items(
                        project=project,
                        work_item_type=work_item_type if work_item_type else None,
                        state=state if state else None,
                        limit=limit
                    )
                    
                    self.client.print_work_items_summary(work_items)
                
                # Update status
                self.status_var.set(f"Query completed")
                
            except Exception as e:
                error_msg = str(e)
                
                # Handle specific Azure DevOps size limit errors
                if "VS402337" in error_msg or "size limit" in error_msg.lower():
                    with redirect_stdout(redirect):
                        print(f"❌ ADO Size Limit Error: {error_msg}")
                        print("💡 Solutions:")
                        print("1. Reduce the limit value")
                        print("2. Add more specific filters (team, work item type, state)")
                        print("3. Use team-specific queries to narrow results")
                        print("4. Contact your administrator to increase limits")
                        
                        # Try to suggest a reasonable limit
                        try:
                            current_limit = int(self.query_limit_var.get().strip())
                            suggested_limit = min(current_limit // 2, 1000)
                            print(f"💡 Suggested limit: {suggested_limit}")
                        except:
                            print("💡 Suggested limit: 1000")
                else:
                    # Show general error
                    with redirect_stdout(redirect):
                        print(f"Error querying work items: {error_msg}")
                
                # Update status
                self.status_var.set("Query failed")
        
        # Start thread
        threading.Thread(target=query_thread).start()
    
    def get_board_columns(self):
        """Get board columns."""
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Get parameters
        board_name = self.board_name_var.get().strip()
        if not board_name:
            board_name = "Stories"
        
        # Get project and team
        project = self.project_var.get().strip()
        team = self.team_var.get().strip()
        
        if not team:
            messagebox.showerror("Error", "Team name is required. Please set it in the Connection tab.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Update status
        self.status_var.set(f"Getting board columns...")
        
        # Clear output
        self.board_output.configure(state="normal")
        self.board_output.delete(1.0, tk.END)
        self.board_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.board_output)
        
        # Get board columns in a separate thread
        def board_thread():
            try:
                # Get board columns
                with redirect_stdout(redirect):
                    print(f"Getting columns for board '{board_name}'")
                    print(f"Project: {project}")
                    print(f"Team: {team}")
                    print()
                    
                    columns = self.client.get_board_columns(project, team, board_name)
                    self.client.print_board_columns(columns)
                
                # Update status
                self.status_var.set(f"Retrieved board columns")
                
            except Exception as e:
                # Show error
                with redirect_stdout(redirect):
                    print(f"Error retrieving board columns: {str(e)}")
                
                # Update status
                self.status_var.set("Failed to retrieve board columns")
        
        # Start thread
        threading.Thread(target=board_thread).start()
    
    def create_work_item(self):
        """Create a new work item."""
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Get parameters
        work_item_type = self.create_type_var.get().strip()
        title = self.create_title_var.get().strip()
        description = self.create_desc_var.get().strip()
        assigned_to = self.create_assigned_var.get().strip()
        tags = self.create_tags_var.get().strip()
        
        # Validate inputs
        if not title:
            messagebox.showerror("Error", "Title is required.")
            return
        
        # Get project
        project = self.project_var.get().strip()
        
        # Update status
        self.status_var.set(f"Creating work item...")
        
        # Clear output
        self.create_output.configure(state="normal")
        self.create_output.delete(1.0, tk.END)
        self.create_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.create_output)
        
        # Create work item in a separate thread
        def create_thread():
            try:
                # Create work item
                with redirect_stdout(redirect):
                    print(f"Creating new {work_item_type} in project '{project}'")
                    print(f"Title: {title}")
                    if description:
                        print(f"Description: {description}")
                    if assigned_to:
                        print(f"Assigned To: {assigned_to}")
                    if tags:
                        print(f"Tags: {tags}")
                    print()
                    
                    work_item = self.client.create_work_item(
                        project=project,
                        work_item_type=work_item_type,
                        title=title,
                        description=description if description else None,
                        assigned_to=assigned_to if assigned_to else None,
                        tags=tags if tags else None
                    )
                    
                    print(f"Created work item {work_item.id}: {title}")
                    self.client.print_work_item_details(work_item)
                
                # Update status
                self.status_var.set(f"Created work item")
                
            except Exception as e:
                # Show error
                with redirect_stdout(redirect):
                    print(f"Error creating work item: {str(e)}")
                
                # Update status
                self.status_var.set("Failed to create work item")
        
        # Start thread
        threading.Thread(target=create_thread).start()
    
    def update_work_item(self):
        """Update an existing work item."""
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Get parameters
        try:
            work_item_id = int(self.update_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Work Item ID must be a number.")
            return
        
        title = self.update_title_var.get().strip()
        description = self.update_desc_var.get().strip()
        state = self.update_state_var.get().strip()
        assigned_to = self.update_assigned_var.get().strip()
        tags = self.update_tags_var.get().strip()
        
        # Validate inputs
        if not work_item_id:
            messagebox.showerror("Error", "Work Item ID is required.")
            return
        
        # Update status
        self.status_var.set(f"Updating work item {work_item_id}...")
        
        # Clear output
        self.update_output.configure(state="normal")
        self.update_output.delete(1.0, tk.END)
        self.update_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.update_output)
        
        # Update work item in a separate thread
        def update_thread():
            try:
                # Update work item
                with redirect_stdout(redirect):
                    print(f"Updating work item {work_item_id}")
                    if title:
                        print(f"New Title: {title}")
                    if description:
                        print(f"New Description: {description}")
                    if state:
                        print(f"New State: {state}")
                    if assigned_to:
                        print(f"New Assigned To: {assigned_to}")
                    if tags:
                        print(f"New Tags: {tags}")
                    print()
                    
                    work_item = self.client.update_work_item(
                        work_item_id=work_item_id,
                        title=title if title else None,
                        description=description if description else None,
                        state=state if state else None,
                        assigned_to=assigned_to if assigned_to else None,
                        tags=tags if tags else None
                    )
                    
                    print(f"Updated work item {work_item_id}")
                    self.client.print_work_item_details(work_item)
                
                # Update status
                self.status_var.set(f"Updated work item {work_item_id}")
                
            except Exception as e:
                # Show error
                with redirect_stdout(redirect):
                    print(f"Error updating work item: {str(e)}")
                
                # Update status
                self.status_var.set("Failed to update work item")
        
        # Start thread
        threading.Thread(target=update_thread).start()
    
    def refine_work_item(self):
        """Refine a work item using OpenArena LLM."""
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Get work item ID
        try:
            work_item_id = int(self.refine_id_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Work Item ID must be a number.")
            return
        
        # Update status
        self.status_var.set(f"Refining work item {work_item_id}...")
        
        # Clear both output tabs
        self.refine_output.configure(state="normal")
        self.refine_output.delete(1.0, tk.END)
        self.refine_output.configure(state="disabled")
        
        self.raw_output.configure(state="normal")
        self.raw_output.delete(1.0, tk.END)
        self.raw_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.refine_output)
        
        # Refine work item in a separate thread
        def refine_thread():
            try:
                # Get the work item details first
                with redirect_stdout(redirect):
                    print(f"Retrieving work item {work_item_id} details...")
                    work_item = self.client.get_work_item(work_item_id)
                    
                    # Extract work item information
                    title = work_item.fields.get("System.Title", "N/A")
                    description = work_item.fields.get("System.Description", "N/A")
                    work_item_type = work_item.fields.get("System.WorkItemType", "N/A")
                    state = work_item.fields.get("System.State", "N/A")
                    assigned_to_raw = work_item.fields.get("System.AssignedTo", "Unassigned")
                    assigned_to = self.get_assigned_to_display_name(assigned_to_raw)
                    tags = work_item.fields.get("System.Tags", "")
                    
                    print(f"\n=== Original Work Item Details ===")
                    print(f"ID: {work_item_id}")
                    print(f"Title: {title}")
                    print(f"Type: {work_item_type}")
                    print(f"State: {state}")
                    print(f"Assigned To: {assigned_to}")
                    if tags:
                        print(f"Tags: {tags}")
                    if description:
                        print(f"\nDescription: {description}")
                    
                    print(f"\n=== Refining with OpenArena LLM ===")
                    
                    # Try to create OpenArena client, fall back to mock if it fails
                    use_mock = False
                    try:
                        openarena_client = OpenArenaWebSocketClient()
                        print("Connected to OpenArena WebSocket")
                        
                        # Test the connection with a simple query first
                        selected_model = getattr(self, 'current_model_var', None)
                        if selected_model:
                            workflow_id = selected_model.get()
                        else:
                            workflow_id = 'gemini2pro'  # fallback
                        
                        test_answer, test_cost = openarena_client.query_workflow(
                            workflow_id=workflow_id,
                            query="Hello, test connection",
                            is_persistence_allowed=False
                        )
                        
                        if not test_answer or 'error' in test_cost:
                            raise Exception(f"OpenArena test query failed: {test_cost}")
                        
                        print("OpenArena connection validated successfully")
                        
                    except Exception as e:
                        print(f"OpenArena connection/validation failed: {e}")
                        print("OpenArena connection failed - cannot proceed with refinement")
                        use_mock = False
                    
                    # Prepare the refinement prompt
                    refinement_prompt = f"""
Please help refine this Azure DevOps work item:

Work Item Type: {work_item_type}
Title: {title}
Current State: {state}
Assigned To: {assigned_to}
Tags: {tags}

Description:
{description if description else 'No description provided'}

Please provide:
1. A refined and improved title that is clear and actionable
2. A comprehensive description that includes:
   - Clear acceptance criteria
   - Business value and context
   - Technical considerations
   - Dependencies and blockers
3. Suggested tags for better categorization
4. Recommendations for next steps
5. Any potential risks or issues to consider

Format your response in a clear, structured manner.
"""
                    
                    if use_mock:
                        print("Sending refinement request to OpenArena LLM...")
                        
                        # Use selected model workflow for refinement
                        selected_model = getattr(self, 'current_model_var', None)
                        if selected_model:
                            workflow_id = selected_model.get()
                        else:
                            workflow_id = 'gemini2pro'  # fallback
                        
                        refined_content, cost_tracker = openarena_client.query_workflow(
                            workflow_id=workflow_id,
                            query=refinement_prompt,
                            is_persistence_allowed=False
                        )
                    else:
                        # Show error message when OpenArena connection fails
                        error_msg = f"""OpenArena Connection Failed

The system was unable to connect to OpenArena for work item refinement.

Error Details:
{str(e)}

To resolve this issue:
1. Check your OpenArena ESSO token in src/openarena/config/env_config.py
2. Verify the WebSocket URL is correct
3. Ensure you have network access to OpenArena
4. Contact your OpenArena administrator if the issue persists

Work item refinement cannot proceed without a valid OpenArena connection."""
                        
                        print(error_msg)
                        messagebox.showerror("OpenArena Connection Failed", error_msg)
                        return
                    
                    if refined_content and use_mock:
                        # Display formatted output in the main output tab
                        print("\n=== Refined Work Item ===")
                        print(refined_content)
                        
                        # Display raw output in the raw output tab
                        self.raw_output.configure(state="normal")
                        self.raw_output.delete(1.0, tk.END)
                        self.raw_output.insert(tk.END, f"=== Raw LLM Response (Received at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n\n")
                        self.raw_output.insert(tk.END, str(refined_content))
                        
                        # Add metadata about the response
                        self.raw_output.insert(tk.END, "\n\n=== Response Metadata ===\n")
                        self.raw_output.insert(tk.END, f"Response Type: {type(refined_content).__name__}\n")
                        self.raw_output.insert(tk.END, f"Response Length: {len(str(refined_content))} characters\n")
                        self.raw_output.insert(tk.END, f"Model Used: {workflow_id}\n")
                        self.raw_output.insert(tk.END, f"Status: Connected to OpenArena\n")
                        
                        # Add the prompt that was sent to the LLM
                        self.raw_output.insert(tk.END, "\n\n=== Prompt Sent to LLM ===\n")
                        self.raw_output.insert(tk.END, refinement_prompt)
                        
                        if cost_tracker and 'error' not in cost_tracker:
                            self.raw_output.insert(tk.END, "\n\n=== Cost Information ===\n")
                            self.raw_output.insert(tk.END, str(cost_tracker))
                        
                        self.raw_output.configure(state="disabled")
                        
                        if cost_tracker and 'error' not in cost_tracker:
                            print(f"\n=== Cost Information ===")
                            print(f"Cost tracking: {cost_tracker}")
                        
                        print("\n✅ Work item refinement completed successfully using OpenArena LLM.")
                    else:
                        print("Failed to get refinement from OpenArena LLM")
                        
                        # Show error in raw output tab as well
                        self.raw_output.configure(state="normal")
                        self.raw_output.delete(1.0, tk.END)
                        self.raw_output.insert(tk.END, f"=== Error: No Response Received (at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===\n\n")
                        self.raw_output.insert(tk.END, "The OpenArena LLM did not return any content.\n")
                        self.raw_output.insert(tk.END, f"Model Used: {workflow_id}\n")
                        self.raw_output.insert(tk.END, f"Mock Mode: {use_mock}\n")
                        self.raw_output.configure(state="disabled")
                
                # Update status
                self.status_var.set(f"Refined work item {work_item_id}")
                
            except Exception as e:
                # Show error
                with redirect_stdout(redirect):
                    print(f"Error refining work item: {str(e)}")
                    import traceback
                    traceback.print_exc()
                
                # Update status
                self.status_var.set("Failed to refine work item")
        
        # Start thread
        threading.Thread(target=refine_thread).start()
    
    def switch_ai_model(self):
        """Switch to the selected AI model."""
        selected_model = self.model_selection_var.get()
        
        # Update current model display
        self.current_model_var.set(selected_model)
        
        # Update status
        self.model_status_var.set(f"Switched to {selected_model}")
        
        # Show configuration for the selected model
        self.show_model_configuration()
        
        # Update main status
        self.status_var.set(f"AI Model switched to {selected_model}")
    
    def test_model_connection(self):
        """Test connection to the selected AI model."""
        selected_model = self.model_selection_var.get()
        
        # Update status
        self.model_status_var.set(f"Testing connection to {selected_model}...")
        
        # Clear output
        self.config_output.configure(state="normal")
        self.config_output.delete(1.0, tk.END)
        self.config_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.config_output)
        
        # Test connection in a separate thread
        def test_thread():
            try:
                with redirect_stdout(redirect):
                    print(f"🧪 Testing connection to {selected_model}...")
                    
                    # Try to create OpenArena client
                    try:
                        from openarena.websocket_client import OpenArenaWebSocketClient
                        openarena_client = OpenArenaWebSocketClient()
                        print("✅ OpenArena client created successfully")
                        
                        # Get workflow ID for the selected model
                        workflow_id = openarena_client.workflow_ids.get(selected_model)
                        if workflow_id:
                            print(f"🔑 Using workflow ID: {workflow_id}")
                            
                            # Test with a simple query
                            print("🔄 Testing connection...")
                            test_answer, test_cost = openarena_client.query_workflow(
                                workflow_id=workflow_id,
                                query="Hello, this is a connection test",
                                is_persistence_allowed=False
                            )
                            
                            if test_answer and 'error' not in test_cost:
                                print("✅ Connection successful!")
                                print(f"📝 Response length: {len(test_answer)} characters")
                                if 'cost' in test_cost:
                                    print(f"💰 Cost: ${test_cost.get('cost', 'N/A')}")
                            else:
                                print("❌ Connection failed!")
                                print(f"Error: {test_cost.get('error', 'Unknown error')}")
                        else:
                            print(f"❌ Model '{selected_model}' not found in configuration")
                            
                    except Exception as e:
                        print(f"❌ OpenArena connection failed: {e}")
                        print("❌ Cannot proceed with mock client - connection issue must be resolved")
                        
                        # Show error message to user
                        error_msg = f"""OpenArena Connection Test Failed

The system was unable to connect to OpenArena for model testing.

Error Details:
{str(e)}

To resolve this issue:
1. Check your OpenArena ESSO token in src/openarena/config/env_config.py
2. Verify the WebSocket URL is correct
3. Ensure you have network access to OpenArena
4. Contact your OpenArena administrator if the issue persists

Model testing cannot proceed without a valid OpenArena connection."""
                        
                        print(error_msg)
                        messagebox.showerror("OpenArena Connection Failed", error_msg)
                
                # Update status
                self.model_status_var.set(f"Connection test completed for {selected_model}")
                
            except Exception as e:
                with redirect_stdout(redirect):
                    print(f"❌ Error testing connection: {str(e)}")
                    import traceback
                    traceback.print_exc()
                
                self.model_status_var.set("Connection test failed")
        
        # Start test thread
        threading.Thread(target=test_thread).start()
    
    def show_model_configuration(self):
        """Show the configuration for the selected AI model."""
        selected_model = self.model_selection_var.get()
        
        # Update status
        self.model_status_var.set(f"Loading configuration for {selected_model}...")
        
        # Clear output
        self.config_output.configure(state="normal")
        self.config_output.delete(1.0, tk.END)
        self.config_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.config_output)
        
        # Show configuration in a separate thread
        def config_thread():
            try:
                with redirect_stdout(redirect):
                    print(f"🔧 Configuration for {selected_model}")
                    print("=" * 50)
                    
                    # Load configuration
                    try:
                        from openarena.config.settings import get_config
                        config = get_config()
                        
                        print(f"🌐 WebSocket URL: {config.websocket_base_url}")
                        print(f"⏱️ Timeout: {config.timeout} seconds")
                        print(f"🔄 Max Retries: {config.max_retries}")
                        print(f"📏 Max Message Size: {config.max_message_size}")
                        print()
                        
                        # Show workflow IDs
                        print("🤖 Available Models:")
                        print("-" * 30)
                        for model, workflow_id in config.workflow_ids.items():
                            if model == selected_model:
                                print(f"  {model:15} : {workflow_id} ← SELECTED")
                            else:
                                print(f"  {model:15} : {workflow_id}")
                        
                        print()
                        print("💡 Model Descriptions:")
                        print("-" * 30)
                        model_info = {
                            "claude4opus": "Claude 4 Opus - Advanced reasoning and analysis capabilities",
                            "gpt5": "GPT-5 - Latest OpenAI model with enhanced language understanding",
                            "gemini2pro": "Gemini 2 Pro - Google's advanced multimodal AI model"
                        }
                        
                        for model, description in model_info.items():
                            if model == selected_model:
                                print(f"  {model:15} : {description} ← SELECTED")
                            else:
                                print(f"  {model:15} : {description}")
                        
                        print()
                        print(f"✅ Configuration loaded successfully for {selected_model}")
                        
                    except Exception as e:
                        print(f"❌ Error loading configuration: {e}")
                        print("🔄 Trying to load from environment...")
                        
                        # Try to get basic info from environment
                        import os
                        env_vars = {
                            "OPENARENA_WEBSOCKET_URL": os.getenv("OPENARENA_WEBSOCKET_URL", "Not set"),
                            "OPENARENA_TIMEOUT": os.getenv("OPENARENA_TIMEOUT", "Not set"),
                            "OPENARENA_MAX_RETRIES": os.getenv("OPENARENA_MAX_RETRIES", "Not set")
                        }
                        
                        print("🌐 Environment Variables:")
                        for key, value in env_vars.items():
                            print(f"  {key}: {value}")
                
                # Update status
                self.model_status_var.set(f"Configuration displayed for {selected_model}")
                
            except Exception as e:
                with redirect_stdout(redirect):
                    print(f"❌ Error showing configuration: {str(e)}")
                    import traceback
                    traceback.print_exc()
                
                self.model_status_var.set("Failed to load configuration")
        
        # Start config thread
        threading.Thread(target=config_thread).start()
    
    def copy_to_clipboard(self, text_widget):
        """Copy the content of a text widget to clipboard."""
        try:
            content = text_widget.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_var.set("Content copied to clipboard")
        except Exception as e:
            self.status_var.set(f"Failed to copy to clipboard: {str(e)}")
    
    def clear_raw_output(self):
        """Clear the raw output text widget."""
        try:
            self.raw_output.configure(state="normal")
            self.raw_output.delete(1.0, tk.END)
            self.raw_output.configure(state="disabled")
            self.status_var.set("Raw output cleared")
        except Exception as e:
            self.status_var.set(f"Failed to clear raw output: {str(e)}")
    
    def load_settings(self):
        """Load saved settings."""
        try:
            # Check if settings file exists
            settings_file = Path("config/ado_settings.txt")
            if settings_file.exists():
                with open(settings_file, "r") as f:
                    settings = {}
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            settings[key] = value
                    
                    # Apply settings
                    if "organization_url" in settings:
                        self.org_url_var.set(settings["organization_url"])
                    if "project" in settings:
                        self.project_var.set(settings["project"])
                    if "team" in settings:
                        self.team_var.set(settings["team"])
                    if "pat" in settings:
                        self.pat_var.set(settings["pat"])
                    
                    # Apply LLM configuration settings
                    if "llm_work_item_limit" in settings:
                        try:
                            limit_value = int(settings["llm_work_item_limit"])
                            if hasattr(self, 'llm_work_item_limit_var'):
                                self.llm_work_item_limit_var.set(limit_value)
                        except ValueError:
                            pass
                    
                    # Load maximum ADO work item limit
                    if "max_ado_work_item_limit" in settings:
                        try:
                            max_limit_value = int(settings["max_ado_work_item_limit"])
                            self.max_ado_work_item_limit = max_limit_value
                            print(f"Loaded max ADO work item limit: {max_limit_value}")
                        except ValueError:
                            print(f"Invalid max_ado_work_item_limit value: {settings['max_ado_work_item_limit']}")
                            self.max_ado_work_item_limit = 19000  # Default fallback
                    
                    if "llm_strategy" in settings:
                        if hasattr(self, 'llm_strategy_var'):
                            self.llm_strategy_var.set(settings["llm_strategy"])
                    
                    # Load auto-connect setting
                    if "auto_connect" in settings:
                        auto_connect_value = settings["auto_connect"].lower() == "true"
                        if hasattr(self, 'auto_connect_var'):
                            self.auto_connect_var.set(auto_connect_value)
                    
                    # Disable other tabs until connected
                    self.notebook.tab(1, state="disabled")  # Test Open Arena - AI Models tab
                    self.notebook.tab(2, state="disabled")  # ADO Team Selection tab
                    self.notebook.tab(3, state="disabled")  # Open Arena - AI Model Selection tab
                    self.notebook.tab(4, state="disabled")  # Related Work Items tab
                    self.notebook.tab(5, state="disabled")  # ADO Operations tab
                    # Note: Test Open Arena - AI Models tab (tab 1) is always enabled as it doesn't require ADO connection
                    
                    # Check if auto-connect is enabled and we have valid settings
                    if hasattr(self, 'auto_connect_var') and self.auto_connect_var.get():
                        org_url = self.org_url_var.get().strip()
                        pat = self.pat_var.get().strip()
                        project = self.project_var.get().strip()
                        
                        if org_url and pat and project:
                            # Auto-connect after a short delay to ensure UI is ready
                            self.root.after(1000, self.auto_connect_to_ado)
        except Exception as e:
            print(f"Error loading settings: {str(e)}")
    
    def save_settings(self):
        """Save settings."""
        try:
            # Ensure config directory exists
            config_dir = Path("config")
            config_dir.mkdir(exist_ok=True)
            
            settings_file = config_dir / "ado_settings.txt"
            with open(settings_file, "w") as f:
                f.write(f"organization_url={self.org_url_var.get().strip()}\n")
                f.write(f"project={self.project_var.get().strip()}\n")
                f.write(f"team={self.team_var.get().strip()}\n")
                f.write(f"pat={self.pat_var.get().strip()}\n")
                
                # Save LLM configuration settings
                if hasattr(self, 'llm_work_item_limit_var'):
                    f.write(f"llm_work_item_limit={self.llm_work_item_limit_var.get()}\n")
                if hasattr(self, 'llm_strategy_var'):
                    f.write(f"llm_strategy={self.llm_strategy_var.get()}\n")
                
                # Save maximum ADO work item limit
                f.write(f"max_ado_work_item_limit={self.max_ado_work_item_limit}\n")
                
                # Save auto-connect setting
                if hasattr(self, 'auto_connect_var'):
                    f.write(f"auto_connect={self.auto_connect_var.get()}\n")
                    
        except Exception as e:
            print(f"Error saving settings: {str(e)}")
    
    def create_openarena_test_tab(self):
        """Create the Open Arena connectivity test tab."""
        openarena_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(openarena_frame, text="Test Open Arena - AI Models")
        
        # Description frame
        desc_frame = ttk.LabelFrame(openarena_frame, text="Open Arena WebSocket Connectivity Testing", padding="10")
        desc_frame.pack(fill=tk.X, pady=(0, 10))
        
        desc_text = """This tab allows you to test connectivity to Open Arena LLM services via WebSocket connections. 
        Test individual models or run comprehensive tests across all available models. Monitor connection performance, 
        response times, and cost tracking in real-time."""
        
        desc_label = ttk.Label(desc_frame, text=desc_text, wraplength=600, justify=tk.LEFT)
        desc_label.pack(anchor=tk.W)
        
        # Test controls frame
        controls_frame = ttk.LabelFrame(openarena_frame, text="Test Controls", padding="10")
        controls_frame.pack(fill=tk.X, pady=5)
        
        # Model selection
        ttk.Label(controls_frame, text="Select Model:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.test_model_var = tk.StringVar(value="claude4opus")
        model_combo = ttk.Combobox(controls_frame, textvariable=self.test_model_var, 
                                  values=["claude4opus", "gpt5", "gemini2pro", "azuredevopsagent"], 
                                  state="readonly", width=20)
        model_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 10), pady=5)
        
        # Custom query input
        ttk.Label(controls_frame, text="Custom Query:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.custom_query_var = tk.StringVar(value="Hello! Can you tell me a short joke?")
        query_entry = ttk.Entry(controls_frame, textvariable=self.custom_query_var, width=50)
        query_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Generate AI Query button
        generate_query_button = ttk.Button(controls_frame, text="🎲 Generate AI Query", command=self.generate_ai_query)
        generate_query_button.grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Persistence checkbox
        self.persistence_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls_frame, text="Allow Persistence", variable=self.persistence_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Test buttons frame
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Single model test button
        single_test_button = ttk.Button(buttons_frame, text="Test Single Model", command=self.test_single_model)
        single_test_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Comprehensive test button
        comprehensive_test_button = ttk.Button(buttons_frame, text="Run Comprehensive Test", command=self.run_comprehensive_test)
        comprehensive_test_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Clear output button
        clear_button = ttk.Button(buttons_frame, text="Clear Output", command=self.clear_openarena_output)
        clear_button.pack(side=tk.LEFT)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(openarena_frame, text="Test Progress", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        
        # Progress bar
        self.test_progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.test_progress.pack(fill=tk.X, pady=5)
        
        # Status label
        self.test_status_var = tk.StringVar(value="Ready to test")
        status_label = ttk.Label(progress_frame, textvariable=self.test_status_var)
        status_label.pack(pady=5)
        
        # Output area
        output_frame = ttk.LabelFrame(openarena_frame, text="Test Output", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create notebook for different output views
        output_notebook = ttk.Notebook(output_frame)
        output_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Real-time output tab
        realtime_frame = ttk.Frame(output_notebook, padding="5")
        output_notebook.add(realtime_frame, text="Real-time Output")
        
        # Add button frame for real-time output actions
        realtime_buttons_frame = ttk.Frame(realtime_frame)
        realtime_buttons_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Copy real-time output button
        copy_realtime_button = ttk.Button(realtime_buttons_frame, text="📋 Copy Output", command=lambda: self.copy_to_clipboard(self.openarena_output))
        copy_realtime_button.pack(side=tk.LEFT)
        
        self.openarena_output = scrolledtext.ScrolledText(realtime_frame, wrap=tk.WORD, height=15)
        self.openarena_output.pack(fill=tk.BOTH, expand=True)
        self.openarena_output.configure(state="disabled")
        
        # Results summary tab
        summary_frame = ttk.Frame(output_notebook, padding="5")
        output_notebook.add(summary_frame, text="Results Summary")
        
        # Add button frame for summary actions
        summary_buttons_frame = ttk.Frame(summary_frame)
        summary_buttons_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Show full response button
        self.show_full_response_button = ttk.Button(summary_buttons_frame, text="📖 Show Full Response", command=self.show_full_response)
        self.show_full_response_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Copy summary button
        copy_summary_button = ttk.Button(summary_buttons_frame, text="📋 Copy Summary", command=lambda: self.copy_to_clipboard(self.results_summary))
        copy_summary_button.pack(side=tk.LEFT)
        
        self.results_summary = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, height=15)
        self.results_summary.pack(fill=tk.BOTH, expand=True)
        self.results_summary.configure(state="disabled")
        
        # Cost analysis tab
        cost_frame = ttk.Frame(output_notebook, padding="5")
        output_notebook.add(cost_frame, text="Cost Analysis")
        
        # Add button frame for cost analysis actions
        cost_buttons_frame = ttk.Frame(cost_frame)
        cost_buttons_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Copy cost analysis button
        copy_cost_button = ttk.Button(cost_buttons_frame, text="📋 Copy Cost Analysis", command=lambda: self.copy_to_clipboard(self.cost_analysis))
        copy_cost_button.pack(side=tk.LEFT)
        
        self.cost_analysis = scrolledtext.ScrolledText(cost_frame, wrap=tk.WORD, height=15)
        self.cost_frame = cost_frame
        self.cost_analysis.pack(fill=tk.BOTH, expand=True)
        self.cost_analysis.configure(state="disabled")
    
    def generate_ai_query(self):
        """Generate a dynamic AI-related query"""
        import random
        
        # Collection of AI-related queries
        ai_queries = [
            "Explain how machine learning can improve software development workflows",
            "What are the best practices for implementing AI in enterprise applications?",
            "How can natural language processing help with code documentation?",
            "What are the ethical considerations when deploying AI systems?",
            "Explain the difference between supervised and unsupervised learning",
            "How can AI assist in identifying related work items in project management?",
            "What are the challenges of implementing AI in legacy systems?",
            "How can AI improve code quality and reduce technical debt?",
            "Explain the concept of transfer learning in machine learning",
            "What are the security implications of AI-powered applications?",
            "How can AI help with automated testing and quality assurance?",
            "What are the key metrics for measuring AI system performance?",
            "Explain the concept of explainable AI and its importance",
            "How can AI assist in project estimation and planning?",
            "What are the best practices for AI model versioning and deployment?",
            "How can AI help identify patterns in user behavior and requirements?",
            "Explain the concept of reinforcement learning in AI",
            "What are the considerations for AI model bias and fairness?",
            "How can AI improve collaboration in distributed teams?",
            "What are the emerging trends in AI for software development?"
        ]
        
        # Generate a random query
        new_query = random.choice(ai_queries)
        self.custom_query_var.set(new_query)
        
        # Update status
        self.status_var.set(f"Generated new AI query: {new_query[:50]}...")
        
        # Also update the Open Arena output to show the new query
        self.update_openarena_output(f"🎲 Generated new AI query: {new_query}\n")
    
    def show_full_response(self):
        """Show the full response in a new window"""
        try:
            # Get the current content of results summary
            content = self.results_summary.get(1.0, tk.END)
            
            if not content.strip():
                messagebox.showinfo("No Content", "No results summary available to display.")
                return
            
            # Create a new window
            response_window = tk.Toplevel(self.root)
            response_window.title("Full Response Details")
            response_window.geometry("800x600")
            response_window.minsize(600, 400)
            
            # Add a frame with padding
            frame = ttk.Frame(response_window, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Add title
            title_label = ttk.Label(frame, text="📖 Full Response Details", font=("Arial", 14, "bold"))
            title_label.pack(pady=(0, 10))
            
            # Add scrollable text area
            text_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=25)
            text_area.pack(fill=tk.BOTH, expand=True)
            
            # Insert the content
            text_area.insert(tk.END, content)
            text_area.configure(state="disabled")
            
            # Add copy button
            copy_button = ttk.Button(frame, text="📋 Copy to Clipboard", 
                                   command=lambda: self.copy_to_clipboard(text_area))
            copy_button.pack(pady=10)
            
            # Add close button
            close_button = ttk.Button(frame, text="Close", 
                                    command=response_window.destroy)
            close_button.pack(pady=(0, 10))
            
            # Focus on the new window
            response_window.focus_set()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show full response: {str(e)}")
    
    def test_single_model(self):
        """Test a single Open Arena model."""
        try:
            self.test_status_var.set("Testing single model...")
            self.test_progress.start()
            
            # Get test parameters
            model_name = self.test_model_var.get()
            query = self.custom_query_var.get()
            persistence = self.persistence_var.get()
            
            # Update status
            self.update_openarena_output(f"🧪 Testing {model_name.upper()} Model\n")
            self.update_openarena_output(f"Query: {query}\n")
            self.update_openarena_output(f"Persistence: {persistence}\n")
            self.update_openarena_output("-" * 60 + "\n")
            
            # Run test in background thread
            threading.Thread(target=self._run_single_test, args=(model_name, query, persistence), daemon=True).start()
            
        except Exception as e:
            self.test_status_var.set(f"Error: {str(e)}")
            self.test_progress.stop()
            self.update_openarena_output(f"❌ Error starting test: {str(e)}\n")
    
    def run_comprehensive_test(self):
        """Run comprehensive test across all models."""
        try:
            self.test_status_var.set("Running comprehensive test...")
            self.test_progress.start()
            
            self.update_openarena_output("🚀 Starting Open Arena WebSocket Connectivity Test\n")
            self.update_openarena_output("=" * 80 + "\n")
            
            # Run test in background thread
            threading.Thread(target=self._run_comprehensive_test, daemon=True).start()
            
        except Exception as e:
            self.test_status_var.set(f"Error: {str(e)}")
            self.test_progress.stop()
            self.update_openarena_output(f"❌ Error starting comprehensive test: {str(e)}\n")
    
    def _run_single_test(self, model_name, query, persistence):
        """Run single model test in background thread."""
        try:
            # Import the tester
            from openarena.test_websocket_connectivity import OpenArenaWebSocketTester
            
            tester = OpenArenaWebSocketTester()
            
            # Get workflow ID for selected model
            workflow_id = tester.config['workflow_ids'][model_name]
            
            # Run the test
            result = tester.test_connection(model_name, workflow_id, query, persistence)
            
            # Update GUI in main thread
            self.root.after(0, lambda: self._handle_single_test_result(result))
            
        except Exception as e:
            error_msg = f"Single test error: {str(e)}"
            self.root.after(0, lambda: self._handle_test_error(error_msg))
    
    def _run_comprehensive_test(self):
        """Run comprehensive test in background thread."""
        try:
            # Import the tester
            from openarena.test_websocket_connectivity import OpenArenaWebSocketTester
            
            tester = OpenArenaWebSocketTester()
            
            # Capture output by redirecting stdout
            import io
            import sys
            from contextlib import redirect_stdout
            
            output_buffer = io.StringIO()
            
            with redirect_stdout(output_buffer):
                tester.run_comprehensive_test()
            
            # Get captured output
            captured_output = output_buffer.getvalue()
            
            # Update GUI in main thread
            self.root.after(0, lambda: self._handle_comprehensive_test_result(captured_output))
            
        except Exception as e:
            error_msg = f"Comprehensive test error: {str(e)}"
            self.root.after(0, lambda: self._handle_test_error(error_msg))
    
    def _handle_single_test_result(self, result):
        """Handle single test result in main thread."""
        try:
            self.test_progress.stop()
            self.test_status_var.set("Single test completed")
            
            if result['success']:
                self.update_openarena_output(f"✅ Test completed successfully!\n")
                self.update_openarena_output(f"Response time: {result['response_time']:.2f}s\n")
                self.update_openarena_output(f"Messages received: {result['connection_details']['message_count']}\n")
                
                # Update results summary
                self.update_results_summary(f"📋 SINGLE TEST RESULT: {result['model'].upper()}\n")
                self.update_results_summary("=" * 60 + "\n")
                self.update_results_summary(f"✅ Status: SUCCESS\n")
                self.update_results_summary(f"⏱️  Response Time: {result['response_time']:.2f}s\n")
                self.update_results_summary(f"🔗 Connection Time: {result['connection_details']['connection_time']:.2f}s\n")
                self.update_results_summary(f"📤 Send Time: {result['connection_details']['send_time']:.2f}s\n")
                self.update_results_summary(f"📨 Messages: {result['connection_details']['message_count']}\n")
                self.update_results_summary(f"🤖 Query: {result['query']}\n")
                self.update_results_summary(f"📝 Response: {result['answer']}\n")
                
                # Update cost analysis
                if result['cost_tracker']:
                    self.update_cost_analysis(f"💰 COST ANALYSIS: {result['model'].upper()}\n")
                    self.update_cost_analysis("=" * 60 + "\n")
                    self.update_cost_analysis(f"Input Tokens: {result['cost_tracker'].get('input_token_count', 0):,}\n")
                    self.update_cost_analysis(f"Output Tokens: {result['cost_tracker'].get('output_token_count', 0):,}\n")
                    self.update_cost_analysis(f"Input Cost: ${result['cost_tracker'].get('input_token_cost', 0):.6f}\n")
                    self.update_cost_analysis(f"Output Cost: ${result['cost_tracker'].get('output_token_cost', 0):.6f}\n")
                    self.update_cost_analysis(f"Total Cost: ${result['cost_tracker'].get('total_cost', 0):.6f}\n")
                    self.update_cost_analysis(f"Cost per Token: ${result['cost_tracker'].get('total_cost', 0) / (result['cost_tracker'].get('input_token_count', 0) + result['cost_tracker'].get('output_token_count', 0)):.8f}\n")
            else:
                self.update_openarena_output(f"❌ Test failed: {result['error']}\n")
                self.update_results_summary(f"❌ Test failed: {result['error']}\n")
            
            self.update_openarena_output("\n" + "=" * 60 + "\n\n")
            
        except Exception as e:
            self._handle_test_error(f"Error handling single test result: {str(e)}")
    
    def _handle_comprehensive_test_result(self, captured_output):
        """Handle comprehensive test result in main thread."""
        try:
            self.test_progress.stop()
            self.test_status_var.set("Comprehensive test completed")
            
            # Update real-time output
            self.update_openarena_output(captured_output)
            
            # Parse results for summary (simplified parsing)
            lines = captured_output.split('\n')
            summary_lines = []
            cost_lines = []
            
            for line in lines:
                if 'TEST RESULT:' in line or 'Status:' in line or 'Response Time:' in line:
                    summary_lines.append(line)
                elif 'Cost Tracking:' in line or 'input_token_count' in line or 'total_cost' in line:
                    cost_lines.append(line)
            
            # Update summary tabs
            if summary_lines:
                self.update_results_summary("📊 COMPREHENSIVE TEST SUMMARY\n")
                self.update_results_summary("=" * 60 + "\n")
                self.update_results_summary('\n'.join(summary_lines))
            
            if cost_lines:
                self.update_cost_analysis("💰 COMPREHENSIVE COST ANALYSIS\n")
                self.update_cost_analysis("=" * 60 + "\n")
                self.update_cost_analysis('\n'.join(cost_lines))
            
        except Exception as e:
            self._handle_test_error(f"Error handling comprehensive test result: {str(e)}")
    
    def _handle_test_error(self, error_message):
        """Handle test errors in main thread."""
        self.test_progress.stop()
        self.test_status_var.set("Test failed")
        self.update_openarena_output(f"❌ {error_message}\n")
    
    def update_openarena_output(self, text):
        """Update the Open Arena output text widget."""
        try:
            self.openarena_output.configure(state="normal")
            self.openarena_output.insert(tk.END, text)
            self.openarena_output.see(tk.END)
            self.openarena_output.configure(state="disabled")
        except Exception as e:
            print(f"Error updating Open Arena output: {str(e)}")
    
    def update_results_summary(self, text):
        """Update the results summary text widget."""
        try:
            self.results_summary.configure(state="normal")
            self.results_summary.insert(tk.END, text)
            self.results_summary.see(tk.END)
            self.results_summary.configure(state="disabled")
        except Exception as e:
            print(f"Error updating results summary: {str(e)}")
    
    def update_cost_analysis(self, text):
        """Update the cost analysis text widget."""
        try:
            self.cost_analysis.configure(state="normal")
            self.cost_analysis.insert(tk.END, text)
            self.cost_analysis.see(tk.END)
            self.cost_analysis.configure(state="disabled")
        except Exception as e:
            print(f"Error updating cost analysis: {str(e)}")
    
    def clear_openarena_output(self):
        """Clear all Open Arena output text widgets."""
        try:
            # Clear real-time output
            self.openarena_output.configure(state="normal")
            self.openarena_output.delete(1.0, tk.END)
            self.openarena_output.configure(state="disabled")
            
            # Clear results summary
            self.results_summary.configure(state="normal")
            self.results_summary.delete(1.0, tk.END)
            self.results_summary.configure(state="disabled")
            
            # Clear cost analysis
            self.cost_analysis.configure(state="normal")
            self.cost_analysis.delete(1.0, tk.END)
            self.cost_analysis.configure(state="disabled")
            
            # Reset status
            self.test_status_var.set("Ready to test")
            
            self.status_var.set("Open Arena output cleared")
        except Exception as e:
            self.status_var.set(f"Failed to clear output: {str(e)}")
    
    def explain_team_query_strategy(self):
        """Explain how team-specific queries work and potential issues."""
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Check if a team is selected
        selected_team = self.team_selection_var.get()
        if not selected_team or selected_team == "No teams available":
            # Provide more helpful error message
            result = messagebox.askyesno(
                "No Team Selected", 
                "No team is currently selected. Would you like to load available teams now?\n\n"
                "This will automatically set the first team as default."
            )
            if result:
                self.get_teams()
            return
        
        # Get project
        project = self.team_project_var.get().strip()
        
        # Update status
        self.status_var.set(f"Explaining team query strategy for team '{selected_team}'...")
        
        # Clear output
        self.teams_output.configure(state="normal")
        self.teams_output.delete(1.0, tk.END)
        self.teams_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.teams_output)
        
        # Explain team query strategy in a separate thread
        def explain_strategy_thread():
            try:
                with redirect_stdout(redirect):
                    print(f"🔍 Team Query Strategy Explanation for '{selected_team}'")
                    print("=" * 60)
                    print()
                    
                    print("📋 How Team-Specific Queries Work:")
                    print("The system attempts to get team-specific work items in this order:")
                    print()
                    print("1️⃣ TEAM BACKLOG CONTEXT (Most Specific)")
                    print("   - Uses Azure DevOps team backlog API")
                    print("   - Gets work items specifically assigned to the team")
                    print("   - Most accurate for team-specific results")
                    print("   - Requires proper team configuration")
                    print()
                    
                    print("2️⃣ TEAM AREA PATH (Fallback)")
                    print("   - Uses the team's configured area path")
                    print("   - Queries work items in the team's area hierarchy")
                    print("   - Good fallback if team backlog fails")
                    print("   - Requires team to have area path configured")
                    print()
                    
                    print("3️⃣ PROJECT-WIDE QUERY (Last Resort)")
                    print("   - Queries entire project for work items")
                    print("   - Applies filters (type, state) but not team context")
                    print("   - Results may include items from other teams")
                    print("   - Used when team context methods fail")
                    print()
                    
                    print("⚠️  Why You Might Get Generic Responses:")
                    print("   - Team doesn't have area path configured")
                    print("   - Team backlog API access issues")
                    print("   - Work items not properly associated with team")
                    print("   - Permission issues with team context")
                    print("   - Team configuration problems in ADO")
                    print()
                    
                    print("🔧 Troubleshooting Steps:")
                    print("1. Use 'Test Team Context' to check team configuration")
                    print("2. Verify team has area path set in ADO")
                    print("3. Check if work items are in team's area path")
                    print("4. Ensure you have proper permissions")
                    print("5. Try refreshing team selection")
                    print()
                    
                    print("💡 Best Practices:")
                    print("   - Always use 'Test Team Context' first")
                    print("   - Check area paths in retrieved work items")
                    print("   - Verify team configuration in Azure DevOps")
                    print("   - Use team backlog when possible")
                    print()
                    
                    print("=" * 60)
                    print(f"Current Team: {selected_team}")
                    print(f"Project: {project}")
                    print("Use 'Test Team Context' to diagnose specific issues.")
                
                # Update status
                self.status_var.set(f"Team query strategy explained for '{selected_team}'")
                
            except Exception as e:
                with redirect_stdout(redirect):
                    print(f"❌ Error explaining team query strategy: {str(e)}")
                
                # Update status
                self.status_var.set("Failed to explain team query strategy")
        
        # Start thread
        threading.Thread(target=explain_strategy_thread).start()
    
    def verify_team_specific_items(self):
        """Verify how team-specific the currently loaded work items are."""
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Check if work items are loaded
        if not hasattr(self, 'current_work_items') or not self.current_work_items:
            messagebox.showerror("Error", "No work items loaded. Please get work items for a team first.")
            return
        
        # Get selected team
        selected_team = self.team_selection_var.get()
        if not selected_team or selected_team == "No teams available":
            # Provide more helpful error message
            result = messagebox.askyesno(
                "No Team Selected", 
                "No team is currently selected. Would you like to load available teams now?\n\n"
                "This will automatically set the first team as default."
            )
            if result:
                self.get_teams()
            return
        
        # Get project
        project = self.team_project_var.get().strip()
        
        # Create verification window
        verify_window = tk.Toplevel(self.root)
        verify_window.title(f"Team-Specific Verification - {selected_team}")
        verify_window.geometry("800x600")
        verify_window.minsize(600, 400)
        
        # Add frame with padding
        frame = ttk.Frame(verify_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add title
        title_label = ttk.Label(frame, text=f"🔍 Team-Specific Verification for '{selected_team}'", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Add project info
        project_label = ttk.Label(frame, text=f"Project: {project}", font=("Arial", 10))
        project_label.pack(pady=(0, 10))
        
        # Analyze work items
        area_paths = {}
        total_items = len(self.current_work_items)
        
        for item in self.current_work_items:
            area_path = item.fields.get("System.AreaPath", "Unknown")
            area_paths[area_path] = area_paths.get(area_path, 0) + 1
        
        # Sort by count (descending)
        sorted_paths = sorted(area_paths.items(), key=lambda x: x[1], reverse=True)
        
        # Determine verdict
        team_area_path = None
        try:
            team_info = self.client.get_team_info(project, selected_team)
            team_area_path = team_info.get('default_area_path') if team_info else None
        except:
            pass
        
        # Calculate team-specific percentage
        team_specific_count = 0
        if team_area_path:
            for path, count in area_paths.items():
                if path.startswith(team_area_path):
                    team_specific_count += count
        
        team_specific_percentage = (team_specific_count / total_items * 100) if total_items > 0 else 0
        
        # Determine verdict
        if team_specific_percentage >= 80:
            verdict = "EXCELLENT"
            verdict_color = "green"
        elif team_specific_percentage >= 50:
            verdict = "GOOD"
            verdict_color = "orange"
        else:
            verdict = "POOR"
            verdict_color = "red"
        
        # Verdict frame
        verdict_frame = ttk.LabelFrame(frame, text="Verdict", padding="10")
        verdict_frame.pack(fill=tk.X, pady=(0, 10))
        
        verdict_label = ttk.Label(verdict_frame, text=f"Team-Specific Score: {verdict}", 
                                font=("Arial", 12, "bold"), foreground=verdict_color)
        verdict_label.pack()
        
        score_label = ttk.Label(verdict_frame, text=f"Team-Specific Items: {team_specific_count}/{total_items} ({team_specific_percentage:.1f}%)")
        score_label.pack()
        
        if team_area_path:
            area_path_label = ttk.Label(verdict_frame, text=f"Team Area Path: {team_area_path}")
            area_path_label.pack()
        
        # Area paths breakdown frame
        breakdown_frame = ttk.LabelFrame(frame, text="Area Paths Breakdown", padding="10")
        breakdown_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create treeview for breakdown
        columns = ("Area Path", "Count", "Percentage", "Team-Specific")
        tree = ttk.Treeview(breakdown_frame, columns=columns, show="headings", height=10)
        
        # Configure columns
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(breakdown_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate tree
        for path, count in sorted_paths:
            percentage = (count / total_items * 100) if total_items > 0 else 0
            is_team_specific = "Yes" if (team_area_path and path.startswith(team_area_path)) else "No"
            
            tree.insert("", "end", values=(path, count, f"{percentage:.1f}%", is_team_specific))
        
        # Recommendations frame
        recommendations_frame = ttk.LabelFrame(frame, text="Recommendations", padding="10")
        recommendations_frame.pack(fill=tk.X, pady=(0, 10))
        
        if verdict == "EXCELLENT":
            rec_text = "✅ Excellent! Your team query is working perfectly. Most work items are team-specific."
        elif verdict == "GOOD":
            rec_text = "⚠️ Good, but could be better. Some work items are from outside your team's area."
        else:
            rec_text = "❌ Poor team-specific results. Many work items are not associated with your team."
        
        rec_label = ttk.Label(recommendations_frame, text=rec_text, wraplength=700)
        rec_label.pack()
        
        # Action buttons frame
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(pady=10)
        
        # Test team context button
        test_button = ttk.Button(buttons_frame, text="🧪 Test Team Context", 
                               command=lambda: [verify_window.destroy(), self.test_team_context()])
        test_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Explain strategy button
        explain_button = ttk.Button(buttons_frame, text="📚 Explain Strategy", 
                                  command=lambda: [verify_window.destroy(), self.explain_team_query_strategy()])
        explain_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Close button
        close_button = ttk.Button(buttons_frame, text="Close", command=verify_window.destroy)
        close_button.pack(side=tk.LEFT)
        
        # Focus on the new window
        verify_window.focus_set()
    
    def on_tree_motion(self, event):
        """Handle mouse motion over treeview for tooltips."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
        
        # Get the item and column under the cursor
        item = self.work_items_tree.identify_row(event.y)
        column = self.work_items_tree.identify_column(event.x)
        
        if item and column:
            # Get column name
            col_name = self.work_items_tree.heading(column)['text']
            # Get cell value
            cell_value = self.work_items_tree.item(item)['values']
            col_index = int(column[1]) - 1  # column format is #1, #2, etc.
            
            if col_index < len(cell_value):
                cell_text = str(cell_value[col_index])
                
                # Show tooltip for long text, especially Area Path
                if len(cell_text) > 30 or col_name == 'Area Path':
                    self.show_tooltip(event.x_root, event.y_root, cell_text)
    
    def on_tree_leave(self, event):
        """Handle mouse leave from treeview."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
    
    def show_tooltip(self, x, y, text):
        """Show a tooltip with the given text."""
        if self.tooltip:
            self.tooltip.destroy()
        
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x+10}+{y+10}")
        
        # Create tooltip label
        label = tk.Label(self.tooltip, text=text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("TkDefaultFont", 8, "normal"))
        label.pack()
        
        # Auto-destroy after 3 seconds
        self.root.after(3000, lambda: self.tooltip.destroy() if self.tooltip else None)
    
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget."""
        def show_tooltip(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 20
            
            # Create tooltip window
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            
            # Create tooltip label
            label = tk.Label(tooltip, text=text, justify=tk.LEFT,
                           background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                           font=("TkDefaultFont", 8, "normal"))
            label.pack()
            
            # Auto-destroy after 2 seconds
            tooltip.after(2000, tooltip.destroy)
            
            # Store tooltip reference to widget
            widget.tooltip = tooltip
        
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip') and widget.tooltip:
                widget.tooltip.destroy()
                widget.tooltip = None
        
        # Bind events
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)
    
    def discover_area_paths(self):
        """Discover available area paths for the selected team and project."""
        # Check if connected
        if not self.client:
            messagebox.showerror("Error", "Not connected to Azure DevOps. Please connect first.")
            self.notebook.select(0)  # Switch to connection tab
            return
        
        # Check if a team is selected
        selected_team = self.team_selection_var.get()
        if not selected_team or selected_team == "No teams available":
            # Provide more helpful error message
            result = messagebox.askyesno(
                "No Team Selected", 
                "No team is currently selected. Would you like to load available teams now?\n\n"
                "This will automatically set the first team as default."
            )
            if result:
                self.get_teams()
            return
        
        # Get project
        project = self.team_project_var.get().strip()
        
        # Update status
        self.status_var.set(f"Discovering area paths for team '{selected_team}'...")
        
        # Clear output
        self.teams_output.configure(state="normal")
        self.teams_output.delete(1.0, tk.END)
        self.teams_output.configure(state="disabled")
        
        # Redirect stdout to the output text widget
        redirect = RedirectText(self.teams_output)
        
        # Discover area paths in a separate thread
        def discover_area_paths_thread():
            try:
                with redirect_stdout(redirect):
                    print(f"🔍 Discovering Area Paths for Team '{selected_team}' in Project '{project}'")
                    print("=" * 80)
                    print()
                    
                    print("📋 Discovery Strategy:")
                    print("1️⃣ Looking for team-specific area paths")
                    print("2️⃣ Checking for project-wide area paths")
                    print("3️⃣ Analyzing area path structure")
                    print()
                    
                    # Get team-specific area paths
                    print(f"🔍 Step 1: Team-Specific Area Paths for '{selected_team}'")
                    team_area_paths = self.client.get_available_area_paths(project, selected_team)
                    
                    if team_area_paths:
                        print(f"✅ Found {len(team_area_paths)} team-specific area paths:")
                        for i, path in enumerate(team_area_paths, 1):
                            print(f"   {i}. {path}")
                    else:
                        print("❌ No team-specific area paths found")
                        print("   This explains why team filtering is not working!")
                    
                    print()
                    
                    # Get project-wide area paths
                    print(f"🔍 Step 2: Project-Wide Area Paths for '{project}'")
                    project_area_paths = self.client.get_available_area_paths(project)
                    
                    if project_area_paths:
                        print(f"✅ Found {len(project_area_paths)} project-wide area paths:")
                        # Show first 20 to avoid overwhelming output
                        for i, path in enumerate(project_area_paths[:20], 1):
                            print(f"   {i}. {path}")
                        
                        if len(project_area_paths) > 20:
                            print(f"   ... and {len(project_area_paths) - 20} more")
                    else:
                        print("❌ No project-wide area paths found")
                    
                    print()
                    
                    # Analyze area path structure
                    print(f"🔍 Step 3: Area Path Structure Analysis")
                    
                    # Look for patterns in area paths
                    if project_area_paths:
                        # Find area paths that might be team-related
                        potential_team_paths = []
                        for path in project_area_paths:
                            if selected_team.lower() in path.lower() or any(word in path.lower() for word in selected_team.lower().split()):
                                potential_team_paths.append(path)
                        
                        if potential_team_paths:
                            print(f"🎯 Found {len(potential_team_paths)} potential team-related area paths:")
                            for path in potential_team_paths:
                                print(f"   • {path}")
                        else:
                            print("❌ No obvious team-related area paths found")
                            print("   This suggests the team may not have area paths configured")
                        
                        # Check for common patterns
                        path_patterns = {}
                        for path in project_area_paths:
                            parts = path.split('\\')
                            if len(parts) >= 2:
                                pattern = f"{parts[0]}\\{parts[1]}"
                                path_patterns[pattern] = path_patterns.get(pattern, 0) + 1
                        
                        if path_patterns:
                            print()
                            print("📊 Common Area Path Patterns:")
                            sorted_patterns = sorted(path_patterns.items(), key=lambda x: x[1], reverse=True)
                            for pattern, count in sorted_patterns[:10]:
                                print(f"   {pattern}: {count} work items")
                    
                    print()
                    print("=" * 80)
                    print("💡 Recommendations:")
                    
                    if team_area_paths:
                        print("✅ Team-specific area paths found - team filtering should work!")
                        print("   If you're still getting all work items, check the query logic.")
                    else:
                        print("❌ No team-specific area paths found - this is why team filtering fails!")
                        print("   Solutions:")
                        print("   1. Configure default area paths for teams in Azure DevOps")
                        print("   2. Use team backlog queries instead of area path queries")
                        print("   3. Manually specify area paths for teams")
                    
                    print()
                    print("🔧 Next Steps:")
                    print("   1. Use 'Test Team Context' to verify team configuration")
                    print("   2. Check Azure DevOps team settings for area path configuration")
                    print("   3. Consider using team backlog queries instead of area path queries")
                    
                    self.status_var.set(f"Area path discovery completed for team '{selected_team}'")
                    
            except Exception as e:
                error_msg = f"Error discovering area paths: {str(e)}"
                print(f"❌ {error_msg}")
                self.status_var.set(f"Error: {error_msg}")
        
        # Start the thread
        thread = threading.Thread(target=discover_area_paths_thread)
        thread.daemon = True
        thread.start()

    def show_enhanced_filtering_info(self):
        """Show information about the enhanced team filtering strategy."""
        info_window = tk.Toplevel(self.root)
        info_window.title("🚀 Enhanced Team Filtering Strategy")
        info_window.geometry("800x600")
        info_window.resizable(True, True)
        
        # Create main frame
        main_frame = ttk.Frame(info_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Enhanced Team Filtering Strategy", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Strategy explanation
        strategy_frame = ttk.LabelFrame(main_frame, text="📋 Strategy Overview", padding="15")
        strategy_frame.pack(fill=tk.X, pady=(0, 15))
        
        strategy_text = """
The enhanced team filtering strategy uses multiple fallback methods to ensure you get team-specific work items:

1️⃣ TEAM BACKLOG QUERY (Most Reliable)
   • Directly queries the team's backlog
   • Returns only work items assigned to the team
   • Requires team to have backlog configured

2️⃣ TEAM AREA PATH QUERY (If Configured)
   • Uses the team's configured area path in Azure DevOps
   • Searches for work items in the team's area path
   • Falls back to constructed area paths if not configured

3️⃣ MANUAL AREA PATH MAPPING (Fallback)
   • Uses custom area path mappings from configuration
   • Allows you to specify team-specific area paths
   • Provides fallback when ADO configuration is missing

4️⃣ PROJECT-WIDE QUERY WITH TEAM FILTERING (Last Resort)
   • Searches all work items in the project
   • Filters by team-related indicators (area path, assigned to, tags)
   • Less reliable but ensures you get some results
        """
        
        strategy_label = ttk.Label(strategy_frame, text=strategy_text, justify=tk.LEFT, wraplength=700)
        strategy_label.pack(anchor=tk.W)
        
        # Benefits frame
        benefits_frame = ttk.LabelFrame(main_frame, text="✅ Benefits", padding="15")
        benefits_frame.pack(fill=tk.X, pady=(0, 15))
        
        benefits_text = """
• 🎯 More accurate team filtering
• 🔄 Multiple fallback strategies
• ⚙️ Configurable area path mappings
• 📊 Better work item relevance
• 🚀 Improved user experience
        """
        
        benefits_label = ttk.Label(benefits_frame, text=benefits_text, justify=tk.LEFT, wraplength=700)
        benefits_label.pack(anchor=tk.W)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="⚙️ Configuration", padding="15")
        config_frame.pack(fill=tk.X, pady=(0, 15))
        
        config_text = """
• Edit config/team_area_paths.json to customize team mappings
• Add your team names and corresponding area paths
• The system will automatically use these mappings
• No code changes required for basic customization
        """
        
        config_label = ttk.Label(config_frame, text=config_text, justify=tk.LEFT, wraplength=700)
        config_label.pack(anchor=tk.W)
        
        # Close button
        close_button = ttk.Button(main_frame, text="Close", command=info_window.destroy)
        close_button.pack(pady=(20, 0))

    def create_ado_operations_tab(self):
        """Create the ADO Operations tab with sub-tabs for various ADO operations."""
        ado_operations_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(ado_operations_frame, text="ADO Operations")
        
        # Create notebook for sub-tabs
        self.ado_operations_notebook = ttk.Notebook(ado_operations_frame)
        self.ado_operations_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Query Work Items sub-tab
        query_frame = ttk.Frame(self.ado_operations_notebook, padding="10")
        self.ado_operations_notebook.add(query_frame, text="Query Work Items")
        
        # Copy content from create_query_items_tab method
        self.create_query_items_content(query_frame)
        
        # Get Work Item sub-tab
        get_item_frame = ttk.Frame(self.ado_operations_notebook, padding="10")
        self.ado_operations_notebook.add(get_item_frame, text="Get Work Item")
        
        # Copy content from create_get_item_tab method
        self.create_get_item_content(get_item_frame)
        
        # Create Work Item sub-tab
        create_item_frame = ttk.Frame(self.ado_operations_notebook, padding="10")
        self.ado_operations_notebook.add(create_item_frame, text="Create Work Item")
        
        # Copy content from create_create_item_tab method
        self.create_create_item_content(create_item_frame)
        
        # Update Work Item sub-tab
        update_item_frame = ttk.Frame(self.ado_operations_notebook, padding="10")
        self.ado_operations_notebook.add(update_item_frame, text="Update Work Item")
        
        # Copy content from create_update_item_tab method
        self.create_update_item_content(update_item_frame)
        
        # Refine Work Item sub-tab
        refine_item_frame = ttk.Frame(self.ado_operations_notebook, padding="10")
        self.ado_operations_notebook.add(refine_item_frame, text="Refine Work Item")
        
        # Copy content from create_refine_item_tab method
        self.create_refine_item_content(refine_item_frame)

    def create_query_items_content(self, parent_frame):
        """Create the content for Query Work Items sub-tab."""
        # Description frame
        desc_frame = ttk.LabelFrame(parent_frame, text="About Query Work Items", padding="10")
        desc_frame.pack(fill=tk.X, pady=(0, 10))
        
        desc_text = """This section allows you to query work items from Azure DevOps using various criteria. 
        You can search by work item type, state, assigned to, or custom queries."""
        
        desc_label = ttk.Label(desc_frame, text=desc_text, wraplength=600, justify=tk.LEFT)
        desc_label.pack(anchor=tk.W)
        
        # Input frame
        input_frame = ttk.LabelFrame(parent_frame, text="Query Work Items", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Work Item Type
        ttk.Label(input_frame, text="Work Item Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.query_type_var = tk.StringVar(value="User Story")
        ttk.Entry(input_frame, textvariable=self.query_type_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # State
        ttk.Label(input_frame, text="State:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.query_state_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.query_state_var, width=20).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Limit
        ttk.Label(input_frame, text="Limit:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.query_limit_var = tk.StringVar(value="10")
        ttk.Entry(input_frame, textvariable=self.query_limit_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Query button
        query_button = ttk.Button(input_frame, text="Query Work Items", command=self.query_work_items)
        query_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Output area
        output_frame = ttk.LabelFrame(parent_frame, text="Query Results", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.query_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.query_output.pack(fill=tk.BOTH, expand=True)
        self.query_output.configure(state="disabled")
        
    def create_get_item_content(self, parent_frame):
        """Create the content for Get Work Item sub-tab."""
        # Description frame
        desc_frame = ttk.LabelFrame(parent_frame, text="About Get Work Item", padding="10")
        desc_frame.pack(fill=tk.X, pady=(0, 10))
        
        desc_text = """This section allows you to retrieve a specific work item by its ID from Azure DevOps."""
        
        desc_label = ttk.Label(desc_frame, text=desc_text, wraplength=600, justify=tk.LEFT)
        desc_label.pack(anchor=tk.W)
        
        # Input frame
        input_frame = ttk.LabelFrame(parent_frame, text="Get Work Item by ID", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Work Item ID
        ttk.Label(input_frame, text="Work Item ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.get_item_id_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.get_item_id_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Get button
        get_button = ttk.Button(input_frame, text="Get Work Item", command=self.get_work_item)
        get_button.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Output area
        output_frame = ttk.LabelFrame(parent_frame, text="Work Item Details", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.get_item_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.get_item_output.pack(fill=tk.BOTH, expand=True)
        self.get_item_output.configure(state="disabled")
        
    def create_create_item_content(self, parent_frame):
        """Create the content for Create Work Item sub-tab."""
        # Description frame
        desc_frame = ttk.LabelFrame(parent_frame, text="About Create Work Item", padding="10")
        desc_frame.pack(fill=tk.X, pady=(0, 10))
        
        desc_text = """This section allows you to create new work items in Azure DevOps."""
        
        desc_label = ttk.Label(desc_frame, text=desc_text, wraplength=600, justify=tk.LEFT)
        desc_label.pack(anchor=tk.W)
        
        # Input frame
        input_frame = ttk.LabelFrame(parent_frame, text="Create New Work Item", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Work Item Type
        ttk.Label(input_frame, text="Work Item Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.create_type_var = tk.StringVar(value="User Story")
        ttk.Entry(input_frame, textvariable=self.create_type_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Title
        ttk.Label(input_frame, text="Title:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.create_title_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.create_title_var, width=50).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Description
        ttk.Label(input_frame, text="Description:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.create_desc_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.create_desc_var, width=50).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Assigned To
        ttk.Label(input_frame, text="Assigned To:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.create_assigned_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.create_assigned_var, width=30).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Tags
        ttk.Label(input_frame, text="Tags (semicolon-separated):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.create_tags_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.create_tags_var, width=50).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Create button
        create_button = ttk.Button(input_frame, text="Create Work Item", command=self.create_work_item)
        create_button.grid(row=5, column=0, columnspan=2, pady=10)
        
        # Output area
        output_frame = ttk.LabelFrame(parent_frame, text="Result", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.create_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.create_output.pack(fill=tk.BOTH, expand=True)
        self.create_output.configure(state="disabled")
        
    def create_update_item_content(self, parent_frame):
        """Create the content for Update Work Item sub-tab."""
        # Description frame
        desc_frame = ttk.LabelFrame(parent_frame, text="About Update Work Item", padding="10")
        desc_frame.pack(fill=tk.X, pady=(0, 10))
        
        desc_text = """This section allows you to update existing work items in Azure DevOps."""
        
        desc_label = ttk.Label(desc_frame, text=desc_text, wraplength=600, justify=tk.LEFT)
        desc_label.pack(anchor=tk.W)
        
        # Input frame
        input_frame = ttk.LabelFrame(parent_frame, text="Update Existing Work Item", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Work Item ID
        ttk.Label(input_frame, text="Work Item ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.update_id_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.update_id_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Title
        ttk.Label(input_frame, text="New Title:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.update_title_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.update_title_var, width=50).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Description
        ttk.Label(input_frame, text="New Description:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.update_desc_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.update_desc_var, width=50).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # State
        ttk.Label(input_frame, text="New State:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.update_state_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.update_state_var, width=20).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Assigned To
        ttk.Label(input_frame, text="New Assigned To:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.update_assigned_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.update_assigned_var, width=30).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Tags
        ttk.Label(input_frame, text="New Tags (semicolon-separated):").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.update_tags_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.update_tags_var, width=50).grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Update button
        update_button = ttk.Button(input_frame, text="Update Work Item", command=self.update_work_item)
        update_button.grid(row=6, column=0, columnspan=2, pady=10)
        
        # Output area
        output_frame = ttk.LabelFrame(parent_frame, text="Result", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.update_output = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.update_output.pack(fill=tk.BOTH, expand=True)
        self.update_output.configure(state="disabled")
        
    def create_refine_item_content(self, parent_frame):
        """Create the content for Refine Work Item sub-tab."""
        # Description frame
        desc_frame = ttk.LabelFrame(parent_frame, text="About Refine Work Item", padding="10")
        desc_frame.pack(fill=tk.X, pady=(0, 10))
        
        desc_text = """This section allows you to refine work items using AI analysis."""
        
        desc_label = ttk.Label(desc_frame, text=desc_text, wraplength=600, justify=tk.LEFT)
        desc_label.pack(anchor=tk.W)
        
        # Input frame
        input_frame = ttk.LabelFrame(parent_frame, text="Refine Work Item", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Work Item ID
        ttk.Label(input_frame, text="Work Item ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.refine_id_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.refine_id_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Refine button
        refine_button = ttk.Button(input_frame, text="Refine Work Item", command=self.refine_work_item)
        refine_button.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Output area with tabs for formatted and raw output
        output_notebook = ttk.Notebook(parent_frame)
        output_notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Formatted output tab
        formatted_frame = ttk.Frame(output_notebook, padding="10")
        output_notebook.add(formatted_frame, text="Formatted Output")
        
        self.refine_output = scrolledtext.ScrolledText(formatted_frame, wrap=tk.WORD)
        self.refine_output.pack(fill=tk.BOTH, expand=True)
        self.refine_output.configure(state="disabled")
        
        # Raw output tab
        raw_frame = ttk.Frame(output_notebook, padding="10")
        output_notebook.add(raw_frame, text="Raw LLM Output")
        
        # Raw output controls
        raw_controls_frame = ttk.Frame(raw_frame)
        raw_controls_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(raw_controls_frame, text="Raw response from OpenArena LLM:").pack(side=tk.LEFT)
        
        # Copy raw output button
        copy_raw_button = ttk.Button(raw_controls_frame, text="Copy Raw Output", 
                                   command=lambda: self.copy_to_clipboard(self.raw_output))
        copy_raw_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Clear raw output button
        clear_raw_button = ttk.Button(raw_controls_frame, text="Clear Raw Output", 
                                    command=lambda: self.clear_raw_output())
        clear_raw_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.raw_output = scrolledtext.ScrolledText(raw_frame, wrap=tk.WORD, font=("Consolas", 9), 
                                                  background="#f8f8f8", foreground="#333333")
        self.raw_output.pack(fill=tk.BOTH, expand=True)
        self.raw_output.configure(state="disabled")

    def configure_area_path_mappings(self):
        """Open the area path mappings configuration file for editing."""
        try:
            config_path = "config/team_area_paths.json"
            
            if not os.path.exists(config_path):
                # Create default config if it doesn't exist
                default_config = {
                    "team_area_path_mappings": {
                        "Practical Law": [
                            "Project\\Practical Law\\Features",
                            "Project\\Practical Law\\Core"
                        ],
                        "Westlaw": [
                            "Project\\Westlaw\\Core",
                            "Project\\Westlaw\\Search"
                        ]
                    },
                    "area_path_patterns": {
                        "team_name_in_path": True,
                        "case_sensitive": False,
                        "partial_matching": True
                    },
                    "fallback_strategies": {
                        "use_team_backlog": True,
                        "use_constructed_paths": True,
                        "use_manual_mapping": True,
                        "use_project_query": True
                    }
                }
                
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                
                messagebox.showinfo("Configuration Created", f"Default configuration file created at:\n{config_path}\n\nPlease edit this file to customize your team mappings.")
            
            # Try to open the file with the default system editor
            if sys.platform.startswith('win'):
                os.startfile(config_path)
            elif sys.platform.startswith('darwin'):
                subprocess.run(['open', config_path])
            else:
                subprocess.run(['xdg-open', config_path])
                
            messagebox.showinfo("Configuration Opened", f"Configuration file opened for editing:\n{config_path}\n\nAfter making changes, restart the application for them to take effect.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not open configuration file:\n{str(e)}")
    
    def _add_to_cache(self, cache_key, related_items):
        """Add results to cache with size management."""
        # Remove oldest entries if cache is too large
        if len(self.related_items_cache) >= self.cache_max_size:
            # Remove the first (oldest) entry
            oldest_key = next(iter(self.related_items_cache))
            del self.related_items_cache[oldest_key]
            print(f"🗑️ Cache full, removed oldest entry: {oldest_key}")
        
        self.related_items_cache[cache_key] = related_items
    
    def clear_related_items_cache(self):
        """Clear the related items cache."""
        self.related_items_cache.clear()
        print("🗑️ Related items cache cleared")
    
    def get_cache_stats(self):
        """Get cache statistics for debugging."""
        return {
            'cache_size': len(self.related_items_cache),
            'max_size': self.cache_max_size,
            'cached_items': list(self.related_items_cache.keys())
        }
    
    def on_hierarchy_toggle_changed(self):
        """Handle hierarchy toggle checkbox change."""
        if hasattr(self, 'load_hierarchy_var'):
            is_enabled = self.load_hierarchy_var.get()
            if is_enabled:
                print("📊 Hierarchy loading enabled - will load hierarchy for all work items (may be slower)")
                # Refresh the current display if there are work items
                if hasattr(self, 'current_work_items') and self.current_work_items:
                    print("🔄 Refreshing display with hierarchy information...")
                    self.display_work_items(self.current_work_items)
            else:
                print("⚡ Hierarchy loading disabled - faster performance, hierarchy only for selected work items")
                # Refresh the current display without hierarchy
                if hasattr(self, 'current_work_items') and self.current_work_items:
                    print("🔄 Refreshing display without hierarchy information...")
                    self.display_work_items(self.current_work_items)


def main():
    """Main function to run the application."""
    root = tk.Tk()
    app = ADOBoardViewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
