# RG Profiler Framework Implementation Specification

This document provides specifications for implementing a web framework for the RG Profiler system. The implementation should follow a consistent pattern to enable accurate performance and energy consumption comparison between frameworks.

## Project Structure

Create the following file structure:

```
frameworks/python/[framework_name]/
├── app.py                 # Main entry point
├── conf.json              # Framework configuration
├── requirements.txt       # Dependencies
└── server/                # Framework implementation
    ├── __init__.py        # App initialization
    └── [other files]      # Framework-specific implementation
```

## Required Files

### 1. Main Entry Point (`app.py`)

Create an entry point script that:
- Loads configuration from `conf.json`
- Sets up environment variables
- Creates and configures the application
- Handles shutdown signals gracefully (SIGTERM, SIGINT)
- Exposes the server on 0.0.0.0:8080
- Includes a `/shutdown` endpoint for graceful termination

The signal handler must include a delay (2 seconds is recommended) to allow the profiling tools to save their data:

```python
def signal_handler(sig, frame):
    """Handle termination signals gracefully to ensure profiling data is saved"""
    global shutdown_requested
    print(f"Received signal {sig}, initiating graceful shutdown...")
    shutdown_requested = True
    # Wait briefly before exiting to allow for profiling to complete
    import time
    time.sleep(2)
    sys.exit(0)
```

The `/shutdown` endpoint must trigger the termination by sending a SIGTERM signal to itself:

```python
@app.route('/shutdown', method='GET')
def shutdown():
    """Endpoint to initiate graceful server shutdown"""
    response_data = {"status": "shutting_down", "timestamp": datetime.now().isoformat()}
    
    # Schedule shutdown after response is sent
    def shutdown_server():
        import time
        import os
        import signal
        time.sleep(0.5)  # Short delay to ensure response is sent
        
        # Send SIGTERM to self
        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)
        
    import threading
    threading.Thread(target=shutdown_server).start()
    
    return response_data
```

### 2. Configuration (`conf.json`)

```json
{
  "database": {
    "type": "postgres"
  },
  "server": {
    "port": 8080,
    "host": "0.0.0.0"
  }
}
```

### 3. Dependencies (`requirements.txt`)

Include:
- The web framework itself
- Database drivers (psycopg2-binary, pymysql, pymongo)
- Any additional dependencies required by the framework
- Do NOT include profiling tools (they're in the base image)

### 4. App Initialization (`server/__init__.py`)

Create a function that:
- Sets up the application instance
- Configures database connection
- Registers all required endpoints
- Configures middleware/request handlers
- Returns the configured application

## Required Endpoints

Implement all of the following endpoints with consistent behavior across frameworks:

| Endpoint | Description | Method |
|----------|-------------|--------|
| `/json` | Return `{"message": "Hello, World!", "timestamp": "ISO-format", "framework": "[framework_name]"}` | GET |
| `/plaintext` | Return "Hello, World!" with Content-Type text/plain | GET |
| `/db` | Query a random row from the 'world' table and return as JSON | GET |
| `/queries?queries=n` | Perform n random queries (default 1, max 500) and return as JSON array | GET |
| `/complex-routing/:id/:name/:param1/:param2` | Return JSON with parsed parameters | GET |
| `/middleware` | Return timing data about the middleware execution chain | GET |
| `/template-simple` | Render a simple template with title, message, and timestamp | GET |
| `/template-complex` | Render a complex template with fortune data, loops, conditions, and includes | GET |
| `/session-write` | Create a new session with sample data and return session info | GET |
| `/session-read` | Read and return data from an existing session | GET |
| `/error-handling?type=[error_type]` | Trigger and handle different error types | GET |
| `/header-parsing` | Return parsed HTTP headers as JSON | GET |
| `/regex-heavy` | Apply multiple regex patterns and return results | GET |
| `/serialization` | Serialize complex nested object structures to JSON | GET |
| `/deserialization` | Parse and process complex JSON input | POST |
| `/cpu-intensive?complexity=[1-10]` | Perform CPU-intensive operations (Fibonacci, primes, matrix, sorting) | GET |
| `/memory-heavy?size=[1-10]` | Allocate and process large memory structures | GET |
| `/shutdown` | Gracefully terminate the server | GET |

## Database Models

Implement models for:
1. `World` - Table with id and randomnumber fields
2. `Fortune` - Table with id and message fields
3. `User` - Table for session testing
4. `ComplexData` - Table with JSON/JSONB data for serialization tests

## Templates

Create two templates:
1. `simple.html` - Basic template with title, message, and timestamp
2. `complex.html` - Complex template with loops, conditionals, and includes (include a footer template)

## Request Middleware

Implement middleware to:
1. Measure response time
2. Simulate security checks
3. Track rate limiting statistics
4. Add timing information to request objects

## Implementation Guidelines

1. Use the framework's native patterns and idioms
2. Ensure consistent behavior across all endpoints
3. Use the database type from configuration for database connections
4. Handle errors gracefully and return appropriate status codes
5. Follow framework-specific best practices for performance
6. Implement graceful shutdown to ensure profiling data collection
7. Use the built-in server of the framework for profiling (avoid external WSGI servers like Gunicorn)
8. Use single-threaded or single-process mode when possible (for better profiling accuracy)
9. For Scalene compatibility, avoid multi-process or multi-worker configurations

## Testing

The implementation will be tested by:
1. Verifying all endpoints return the expected data
2. Checking for consistent behavior across frameworks
3. Profiling performance characteristics
4. Measuring energy consumption

## Example

For reference, the Flask and Django implementations are available in the repository. Follow their patterns while adapting to your framework's specific architecture.