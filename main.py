#!/usr/bin/env python3
"""
Azure DevOps AI Studio - Modern React UI Launcher
Complete modern UI replacement for the Tkinter application
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

def input_with_timeout(prompt, timeout=3, default="1"):
    """Get user input with timeout, return default if no input within timeout."""
    import msvcrt
    import sys
    
    print(prompt, end='', flush=True)
    print(f"[Auto-selecting option {default} in {timeout}s, or press Enter to choose]", end='', flush=True)
    
    user_input = ""
    start_time = time.time()
    
    while (time.time() - start_time) < timeout:
        if msvcrt.kbhit():
            char = msvcrt.getch().decode('utf-8')
            if char == '\r' or char == '\n':  # Enter pressed
                print()
                return user_input if user_input else default
            elif char == '\b':  # Backspace
                if user_input:
                    user_input = user_input[:-1]
                    print('\b \b', end='', flush=True)
            elif char.isprintable():
                user_input += char
                print(char, end='', flush=True)
        else:
            time.sleep(0.1)
    
    print(f"\n Auto-selected option {default} (timeout reached)")
    return default

def kill_process_on_port(port):
    """Kill any process running on the specified port using Windows netstat and taskkill."""
    try:
        print(f" Checking for processes on port {port}...")
        
        # Use netstat to find processes on the port
        result = subprocess.run(
            f'netstat -ano | findstr ":{port} "', 
            capture_output=True, text=True, shell=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            pids_killed = set()
            
            for line in lines:
                # Parse netstat output: Proto Local-Address Foreign-Address State PID
                parts = line.strip().split()
                if len(parts) >= 5:
                    local_address = parts[1]
                    state = parts[3] if len(parts) > 3 else ""
                    pid = parts[-1]
                    
                    # Only kill processes in LISTENING state or ESTABLISHED on our port
                    if (f":{port}" in local_address and 
                        pid.isdigit() and 
                        pid != "0" and 
                        pid not in pids_killed):
                        
                        try:
                            # Get process name first for better logging
                            name_result = subprocess.run(
                                f'tasklist /fi "PID eq {pid}" /fo csv /nh', 
                                capture_output=True, text=True, shell=True
                            )
                            
                            process_name = "Unknown"
                            if name_result.returncode == 0 and name_result.stdout.strip():
                                # Parse CSV output to get process name
                                csv_line = name_result.stdout.strip().split(',')
                                if len(csv_line) > 0:
                                    process_name = csv_line[0].strip('"')
                            
                            print(f"   Found process: {process_name} (PID: {pid}) on {local_address}")
                            print(f"   Killing PID {pid}...")
                            
                            # Kill the process
                            kill_result = subprocess.run(
                                f'taskkill /f /pid {pid}', 
                                capture_output=True, text=True, shell=True
                            )
                            
                            if kill_result.returncode == 0:
                                print(f"   Successfully killed PID {pid}")
                                pids_killed.add(pid)
                            else:
                                print(f"   Failed to kill PID {pid}: {kill_result.stderr}")
                                
                        except Exception as e:
                            print(f"   Error killing PID {pid}: {e}")
            
            if pids_killed:
                print(f"   Waiting for port {port} to be released...")
                time.sleep(2)  # Give time for port to be released
                print(f" Port {port} is now clear!")
                return True
            else:
                print(f"   No active processes found on port {port}")
                return True
        else:
            print(f"   Port {port} is already free")
            return True
            
    except Exception as e:
        print(f" Error checking port {port}: {e}")
        return False

def check_node_installed():
    """Check if Node.js is installed."""
    try:
        result = subprocess.run('node --version', capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"Node.js version: {result.stdout.strip()}")
            return True
        else:
            print("Node.js not found")
            return False
    except FileNotFoundError:
        print("Node.js not installed")
        return False

def check_npm_installed():
    """Check if npm is installed."""
    try:
        result = subprocess.run('npm --version', capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"npm version: {result.stdout.strip()}")
            return True
        else:
            print("npm not found")
            return False
    except FileNotFoundError:
        print("npm not installed")
        return False

def install_react_dependencies():
    """Install React application dependencies."""
    ui_path = Path("modern_ui")
    if not ui_path.exists():
        print("modern_ui directory not found")
        return False
    
    print("Installing React dependencies...")
    original_dir = os.getcwd()
    
    try:
        os.chdir(ui_path)
        result = subprocess.run('npm install', capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            print("React dependencies installed successfully")
            return True
        else:
            print(f"Failed to install React dependencies: {result.stderr}")
            return False
    finally:
        os.chdir(original_dir)

def install_python_dependencies():
    """Install Python backend dependencies."""
    backend_path = Path("modern_ui_backend")
    requirements_file = backend_path / "requirements.txt"
    
    if not requirements_file.exists():
        print("Backend requirements.txt not found, skipping Python dependencies")
        return True
    
    print("Installing Python backend dependencies...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Python dependencies installed successfully")
            return True
        else:
            print(f"Failed to install Python dependencies: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error installing Python dependencies: {e}")
        return False

def start_backend_server():
    """Start the enhanced Python backend server."""
    def run_backend():
        try:
            print("Starting enhanced Python backend server...")
            subprocess.run([
                sys.executable, 'modern_ui_backend/enhanced_app.py'
            ], cwd=os.getcwd(), check=True)
        except Exception as e:
            print(f"Error starting backend server: {e}")
    
    # Start backend in a separate thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # Wait for server to start
    print("Waiting for backend server to start...")
    time.sleep(3)
    return True

def start_react_dev_server():
    """Start the React development server."""
    ui_path = Path("modern_ui")
    if not ui_path.exists():
        print("modern_ui directory not found")
        return False
    
    print("Starting React development server...")
    original_dir = os.getcwd()
    
    try:
        os.chdir(ui_path)
        # Set environment variable to fix webpack dev server allowedHosts error
        env = os.environ.copy()
        env['DANGEROUSLY_DISABLE_HOST_CHECK'] = 'true'
        
        # Start React dev server (this will block)
        subprocess.run('npm start', shell=True, env=env)
    except KeyboardInterrupt:
        print("\nReact development server stopped")
    except Exception as e:
        print(f"Error starting React server: {e}")
    finally:
        os.chdir(original_dir)

def build_react_for_production():
    """Build React application for production."""
    ui_path = Path("modern_ui")
    if not ui_path.exists():
        print("modern_ui directory not found")
        return False
    
    print("Building React application for production...")
    original_dir = os.getcwd()
    
    try:
        os.chdir(ui_path)
        # Set environment variable to fix webpack dev server allowedHosts error
        env = os.environ.copy()
        env['DANGEROUSLY_DISABLE_HOST_CHECK'] = 'true'
        
        result = subprocess.run('npm run build', capture_output=True, text=True, shell=True, env=env)
        
        if result.returncode == 0:
            print("React application built successfully")
            build_dir = ui_path / "build"
            print(f"Build files are available at: {build_dir.absolute()}")
            return True
        else:
            print(f"Failed to build React application: {result.stderr}")
            return False
    finally:
        os.chdir(original_dir)

def main():
    """Main launcher function."""
    print("Azure DevOps AI Studio - Modern React UI Launcher")
    print("=" * 60)
    
    # Check prerequisites
    if not check_node_installed():
        print("\nPlease install Node.js from https://nodejs.org/")
        return
    
    if not check_npm_installed():
        print("\nnpm should come with Node.js. Please reinstall Node.js.")
        return
    
    # Install dependencies
    print("\nInstalling dependencies...")
    if not install_react_dependencies():
        print("\nFailed to install React dependencies")
        return
    
    if not install_python_dependencies():
        print("\nFailed to install Python dependencies")
        return
    
    print("\nChoose launch mode:")
    print("1. Development mode (React dev server + Python backend)")
    print("2. Production build (Build React app for production)")
    print("3. Backend only (Start Python backend server only)")
    
    print("\nAuto-starting Development mode...")
    choice = "1"
    
    try:
        
        if choice == "1":
            print("\nStarting development mode...")
            
            # Clear port 5001 before starting backend server
            print("\nEnsuring port 5001 is available for backend...")
            kill_process_on_port(5001)
            
            # Start backend server in background
            if start_backend_server():
                print("Backend server started at http://localhost:5001")
            
            # Wait a bit more for backend to fully initialize
            time.sleep(2)
            
            # Clear port 3000 before starting React dev server
            print("\nEnsuring port 3000 is available...")
            kill_process_on_port(3000)
            
            print("\nStarting React development server...")
            print("React app will be available at http://localhost:3000")
            print("API calls will proxy to http://localhost:5001")
            print("\nPress Ctrl+C to stop both servers")
            
            # This will block until user stops it
            start_react_dev_server()
            
        elif choice == "2":
            print("\nBuilding for production...")
            if build_react_for_production():
                print("\nProduction build completed!")
                print("You can now serve the build directory with any static file server")
                print("Don't forget to start the Python backend: python modern_ui_backend/enhanced_app.py")
            
        elif choice == "3":
            print("\nStarting backend server only...")
            
            # Clear port 5001 before starting backend server
            print("\nEnsuring port 5001 is available...")
            kill_process_on_port(5001)
            
            print("Backend API will be available at http://localhost:5001")
            print("Press Ctrl+C to stop the server")
            
            # Start backend and wait
            subprocess.run([sys.executable, 'modern_ui_backend/enhanced_app.py'])
            
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
            
    except KeyboardInterrupt:
        print("\n\nLauncher stopped by user")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()
