#!/usr/bin/env python3
"""
Entry point for the Flask implementation in the RG Profiler framework
"""
import json
import os
import signal
import sys
from datetime import datetime
from wsgiref.simple_server import make_server

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
server_port = int(config.get('server', {}).get(
    'port', os.environ.get('SERVER_PORT', 8080)))

# Flag to track if we should shutdown
shutdown_requested = False


def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
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

# Create Flask app
app = create_app(db_type, db_host, db_port, db_user, db_pass, db_name)


# Add shutdown endpoint
@app.route('/shutdown', methods=['GET'])
def shutdown():
    """Endpoint to initiate graceful server shutdown with energy data saving"""
    global shutdown_requested
    shutdown_requested = True

    print("Shutdown requested via /shutdown endpoint")

    response = json.dumps({
        "status": "shutting_down",
        "timestamp": datetime.now().isoformat()
    })

    # Schedule shutdown after response is sent
    def shutdown_server():
        import time
        time.sleep(1)  # Allow time for response to be sent

        # Send SIGTERM to self
        import os
        import signal
        pid = os.getpid()

        # Log before sending signal
        print(f"Sending SIGTERM to self (PID: {pid})")

        # Use os.kill to send signal to self
        os.kill(pid, signal.SIGTERM)

    import threading
    threading.Thread(target=shutdown_server).start()

    return response


if __name__ == '__main__':
    # Check if we're running in a profiling mode
    profiling_mode = os.environ.get('PROFILING_MODE', 'profile')
    use_scalene = os.environ.get('USE_SCALENE', 'true').lower() == 'true'

    print(f"Starting Flask server in {profiling_mode} mode")
    print(f"Database: {db_type} at {db_host}:{db_port}")
    print(f"Scalene profiling: {'enabled' if use_scalene else 'disabled'}")

    # Create output directory for tests if needed
    os.makedirs("/output", exist_ok=True)
    with open("/output/test-file.txt", "w") as f:
        f.write("Volume mounting is working correctly")

    # Use a standard WSGI server instead of Flask's development server
    # This provides better profiling capabilities
    httpd = make_server(server_host, server_port, app)
    print(f"Starting WSGI server on {server_host}:{server_port}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Keyboard interrupt received, shutting down server")
        httpd.server_close()