#!/usr/bin/env python3
"""
Entry point for the Flask implementation in the RG Profiler framework
"""
import json
import os
import signal
import sys
from datetime import datetime

# Import flask app
from server import create_app

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

# Flag to track if we should shutdown
shutdown_requested = False

def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    global shutdown_requested
    print(f"Received signal {sig}, initiating graceful shutdown...")
    shutdown_requested = True
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Create Flask app
app = create_app(db_type, db_host, db_port, db_user, db_pass, db_name)

# Add shutdown endpoint
@app.route('/shutdown', methods=['GET'])
def shutdown():
    """Endpoint to initiate graceful server shutdown"""
    global shutdown_requested
    shutdown_requested = True
    print("Shutdown requested via /shutdown endpoint")
    
    response = json.dumps({"status": "shutting_down", "timestamp": datetime.now().isoformat()})
    
    # Use Werkzeug's shutdown function if available
    from flask import request
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is not None:
        print("Using Werkzeug shutdown function")
        # Schedule shutdown after response is sent
        def shutdown_server():
            import time
            time.sleep(0.5)  # Short delay to ensure response is sent
            shutdown_func()
            
        import threading
        threading.Thread(target=shutdown_server).start()
    else:
        # Fallback to os._exit
        print("Werkzeug shutdown function not available, using os._exit")
        def trigger_shutdown():
            import time
            import signal
            time.sleep(0.5)  # Short delay to ensure response is sent
            
            # Try sending SIGINT to self first (more graceful)
            try:
                import os
                pid = os.getpid()
                os.kill(pid, signal.SIGINT)
                time.sleep(0.5)  # Wait for signal to be processed
            except:
                pass
                
            # If still running, use os._exit
            os._exit(0)
            
        import threading
        threading.Thread(target=trigger_shutdown).start()
    
    return response

if __name__ == '__main__':
    # Create a test file to verify volume mounting
    os.makedirs("/output", exist_ok=True)
    with open("/output/test-file.txt", "w") as f:
        f.write("Volume mounting is working correctly")
    
    print(f"Starting Flask server in {os.environ.get('PROFILING_MODE', 'default')} mode")
    print(f"Database: {db_type} at {db_host}:{db_port}")
    
    # Run the Flask app
    app.run(host=server_host, port=server_port, threaded=False, debug=False)