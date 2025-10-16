#!/usr/bin/env python3
"""
Azure DevOps AI Studio Launcher
Launches the main application with options for GUI, CLI, or Modern UI
"""

import sys
import os
import subprocess
import argparse
import threading
import time
import webbrowser
from pathlib import Path

def start_modern_ui_services():
    """Start the modern UI services (React build + Flask backend) in background."""
    try:
        print("Starting modern UI services...")
        
        # Start Flask backend immediately in background
        def start_flask_backend():
            try:
                print("Starting Flask backend server...")
                subprocess.run([sys.executable, 'modern_ui_backend/app.py'], 
                             cwd=os.getcwd(), check=True)
            except Exception as e:
                print(f" Error starting Flask backend: {e}")
        
        # Start backend in a separate thread
        backend_thread = threading.Thread(target=start_flask_backend, daemon=True)
        backend_thread.start()
        
        # Build React app in background (non-blocking)
        def build_react_app():
            ui_path = Path("modern_ui")
            if ui_path.exists():
                print(" Building React application in background...")
                # Change to modern_ui directory and build
                original_dir = os.getcwd()
                os.chdir(ui_path)
                
                try:
                    result = subprocess.run(['npm', 'run', 'build'], 
                                         capture_output=True, text=True, shell=True)
                    if result.returncode == 0:
                        print(" React application built successfully")
                    else:
                        print(f" React build warning: {result.stderr}")
                finally:
                    os.chdir(original_dir)
            else:
                print(" modern_ui directory not found, skipping React build")
        
        # Start React build in a separate thread
        react_thread = threading.Thread(target=build_react_app, daemon=True)
        react_thread.start()
        
        # Wait for server to start (shorter wait)
        time.sleep(2)
        print(" Modern UI services started successfully")
        print(" Backend is running at http://localhost:5000")
        print(" React build is running in background...")
        
    except Exception as e:
        print(f" Error starting modern UI services: {e}")
        print(" You can manually start the services later")

def main():
    """Launch Azure DevOps AI Studio with different modes"""
    print(" Azure DevOps AI Studio Launcher")
    print("=" * 50)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Launch Azure DevOps AI Studio')
    parser.add_argument('--mode', choices=['gui', 'cli', 'modern-ui'], 
                       default='gui', help='Launch mode (default: modern-ui)')
    parser.add_argument('--work-item', type=int, help='Work item ID to analyze (CLI mode)')
    
    args = parser.parse_args()
    
    if args.mode == 'gui':
        print("  Launching GUI version...")
        print(" Custom icon should appear in the title bar")
        print(" Starting modern UI services in background...")
        
        try:
            # Start modern UI services in background
            start_modern_ui_services()
            
            # Add src directory to Python path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            src_path = os.path.join(current_dir, '..', '..', 'src')
            sys.path.insert(0, src_path)
            
            # Import and launch the application
            from gui.ado_gui import ADOBoardViewerApp
            import tkinter as tk
            
            # Create the main window
            root = tk.Tk()
            app = ADOBoardViewerApp(root)
            
            print(" Azure DevOps AI Studio launched successfully!")
            print(" Look for the custom icon in the title bar")
            print(" The icon combines Azure DevOps branding with AI elements")
            print(" Modern UI services are running at http://localhost:5000")
            
            # Start the application
            root.mainloop()
            
        except ImportError as e:
            print(f" Import error: {e}")
            print(" Make sure all dependencies are installed:")
            print("   pip install -r requirements.txt")
        except Exception as e:
            print(f" Error launching application: {e}")
            print(" Check the error message above")
    
    elif args.mode == 'cli':
        print(" Launching CLI version...")
        try:
            # Add src directory to Python path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            src_path = os.path.join(current_dir, '..', '..', 'src')
            sys.path.insert(0, src_path)
            
            from ado.ado_access import AzureDevOpsClient
            client = AzureDevOpsClient()
            
            if args.work_item:
                print(f"Analyzing work item {args.work_item}...")
                work_item = client.get_work_item(args.work_item)
                if work_item:
                    print(f"Work Item: {work_item.fields.get('System.Title', 'No Title')}")
                    print(f"State: {work_item.fields.get('System.State', 'Unknown')}")
                    print(f"Type: {work_item.fields.get('System.WorkItemType', 'Unknown')}")
                else:
                    print("Work item not found.")
            else:
                print("Please specify a work item ID with --work-item")
        except ImportError as e:
            print(f" Error importing CLI module: {e}")
            print("Please ensure all dependencies are installed.")
            sys.exit(1)
    
    elif args.mode == 'modern-ui':
        print(" Launching Modern UI version...")
        print(" This is the new modern, elegant interface with confidence scoring!")
        print(" The application will open in your web browser.")
        print(" Features include:")
        print("    Beautiful Material-UI design")
        print("    Confidence scoring (High/Medium/Low)")
        print("    Interactive filtering and search")
        print("    Visual analytics and charts")
        print("    Azure DevOps-inspired styling")
        print()
        try:
            # Launch the modern UI
            subprocess.run([sys.executable, 'launch_modern_ui.py'])
        except Exception as e:
            print(f" Error launching modern UI: {e}")
            print(" Make sure you have Node.js installed and run:")
            print("   pip install -r modern_ui_backend/requirements.txt")
            print("   python launch_modern_ui.py")
            sys.exit(1)

if __name__ == "__main__":
    main()
