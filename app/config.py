"""
Production configuration for Azure DevOps Board Viewer
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
SRC_DIR = BASE_DIR / "src"
CONFIG_DIR = BASE_DIR / "config"
APP_DIR = BASE_DIR / "app"

# Configuration file paths
ADO_SETTINGS_FILE = CONFIG_DIR / "ado_settings.txt"
TEAM_AREA_PATHS_FILE = CONFIG_DIR / "team_area_paths.json"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = BASE_DIR / "logs" / "app.log"

# Application settings
APP_NAME = "Azure DevOps Board Viewer"
APP_VERSION = "1.0.0"
MAX_WORK_ITEMS = int(os.getenv("MAX_WORK_ITEMS", "19950"))

# GUI settings
WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}"
WINDOW_SIZE = "1200x800"
WINDOW_MIN_SIZE = "800x600"

# OpenArena settings
OPENARENA_WEBSOCKET_URL = os.getenv(
    "OPENARENA_WEBSOCKET_URL", 
    "wss://wymocw0zke.execute-api.us-east-1.amazonaws.com/prod"
)
OPENARENA_TIMEOUT = int(os.getenv("OPENARENA_TIMEOUT", "30"))
OPENARENA_MAX_RETRIES = int(os.getenv("OPENARENA_MAX_RETRIES", "3"))

# Create logs directory if it doesn't exist
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
