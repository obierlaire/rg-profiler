#!/usr/bin/env python3
"""
Entry point for the Django implementation in the RG Profiler framework
"""
import json
import os
import signal
import sys
from datetime import datetime

# Add the current directory to the path so we can import the server module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Get configuration
config_path = os.path.join(os.path.dirname(__file__), 'conf.json')
config = {}

if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)

# Get database configuration
db_type = config.get('database', {}).get('type', 'postgres')
db_host = os.environ.get('DB_HOST', 'localhost')
db_port = os.environ.get('DB_PORT', '5432')  # Default to postgres port
db_user = os.environ.get('DB_USER', 'benchmarkdbuser')
db_pass = os.environ.get('DB_PASSWORD', 'benchmarkdbpass')
db_name = os.environ.get('DB_NAME', 'hello_world')

# Get server configuration
server_host = config.get('server', {}).get('host', '0.0.0.0')
server_port = int(config.get('server', {}).get('port', os.environ.get('SERVER_PORT', 8080)))

# Handle shutdown gracefully
shutdown_requested = False

def signal_handler(sig, frame):
    """Handle termination signals gracefully to ensure profiling data is saved"""
    global shutdown_requested
    print(f"Received signal {sig}, initiating graceful shutdown...")
    shutdown_requested = True
    # Wait briefly before exiting to allow for profiling to complete
    import time
    time.sleep(2)
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")

# Configure database settings based on environment variables
os.environ["DB_TYPE"] = db_type
os.environ["DB_HOST"] = db_host
os.environ["DB_PORT"] = db_port
os.environ["DB_USER"] = db_user 
os.environ["DB_PASSWORD"] = db_pass
os.environ["DB_NAME"] = db_name

# Import Django and run
import django
django.setup()

# Import the Django development server runner
from django.core.management import execute_from_command_line

if __name__ == "__main__":
    # Check if running with profiling
    profiling_mode = os.environ.get('PROFILING_MODE', 'profile')
    use_scalene = os.environ.get('USE_SCALENE', 'true').lower() == 'true'
    
    print(f"Starting Django server in {profiling_mode} mode")
    print(f"Database: {db_type} at {db_host}:{db_port}")
    print(f"Scalene profiling: {'enabled' if use_scalene else 'disabled'}")
    
    # Run the Django development server
    execute_from_command_line([
        'manage.py', 
        'runserver', 
        f"{server_host}:{server_port}"
    ])
