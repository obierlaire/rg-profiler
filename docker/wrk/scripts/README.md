## Architecture

The RG Profiler uses a fully containerized approach for consistent performance measurements:

1. **Docker Network**: All components (database, framework, and WRK) run in the same Docker network for reliable connectivity
2. **Database Containers**: PostgreSQL, MySQL, and MongoDB are run in Docker containers
3. **Framework Containers**: Each framework implementation is built into a Docker image and run in a container
4. **WRK Container**: The benchmarking tool is also containerized for consistent testing

This containerized approach offers several advantages:
- Eliminates networking issues between components
- Provides consistent environments across different systems
- Makes it easy to test with different database types
- Ensures reproducible results# RG Profiler

A comprehensive profiling system for web frameworks, measuring both performance and energy consumption.

## Features

- CPU and memory profiling with Scalene
- Energy consumption measurement with CodeCarbon
- Docker-based testing for consistent environments
- Support for PostgreSQL, MySQL, and MongoDB databases
- Standardized endpoints across frameworks for fair comparison
- Multiple profiling modes (standard, profile, energy)
- Statistical analysis for energy measurements

## Installation

1. Clone the repositories:

   ```bash
   git clone https://github.com/your-username/rg-profiler.git
   git clone https://github.com/your-username/rg-profiler-frameworks.git
   ```

2. Install dependencies:

   ```bash
   cd rg-profiler
   pip install -r requirements.txt
   ```

3. Set up environment:

   ```bash
   # Set the path to your frameworks repository
   export RG_FRAMEWORKS_ROOT=/path/to/rg-profiler-frameworks
   ```

4. Install WRK if not already installed:

   ```bash
   # Ubuntu/Debian
   sudo apt-get install -y build-essential libssl-dev git
   git clone https://github.com/wg/wrk.git
   cd wrk
   make
   sudo cp wrk /usr/local/bin
   ```

## Usage

The RG Profiler offers three distinct modes of operation:

### Profile Mode (Default)

Focused on CPU/memory profiling with Scalene:

```bash
./run.py --framework flask --mode profile
```

### Energy Mode

Measures energy consumption with statistical significance:

```bash
./run.py --framework flask --mode energy
```

Key features of energy mode:
- Runs each test multiple times (default: 3 runs) to calculate averages and standard deviation
- Uses CPU pinning on Linux for more consistent measurements
- Employs reproducible test patterns that minimize variability
- Outputs energy in Wh and CO2 emissions in mgCO2e

Energy mode options:
```bash
# Customize number of runs
./run.py --framework flask --mode energy --runs 5

# Adjust sampling frequency (seconds)
./run.py --framework flask --mode energy --sampling-frequency 0.2

# Control CPU isolation (Linux only)
./run.py --framework flask --cpu-isolation on
```

### Standard Mode

Combines both profiling and energy measurement:

```bash
./run.py --framework flask --mode standard
```

Additional options for all modes:

```bash
# Skip database startup
./run.py --framework flask --skip-db

# Use a custom configuration file
./run.py --framework flask --config my_custom_config.yaml

# Test with a different language (future support)
./run.py --framework express --language javascript
```

## Endpoint Definitions

The profiler tests a standard set of endpoints across all frameworks:

- `/json` - Simple JSON serialization
- `/plaintext` - Plain text response 
- `/db` - Single database query
- `/queries?queries=n` - Multiple database queries
- `/complex-routing/:id/:name/:param1/:param2` - Tests URL routing and parameter parsing complexity
- `/middleware` - Tests middleware/filter chain overhead with multiple middleware components
- `/template-simple` - Simple template rendering
- `/template-complex` - Complex template with loops, conditionals and includes
- `/session-write` - Session creation and storage performance
- `/session-read` - Session retrieval performance
- `/error-handling` - Error handling and exception processing
- `/header-parsing` - Tests header parsing with many headers
- `/regex-heavy` - Route or processing with complex regex
- `/serialization` - Complex object serialization
- `/deserialization` - Complex object deserialization from JSON
- `/cpu-intensive` - Compute-heavy operation to test CPU efficiency
- `/memory-heavy` - Memory-intensive operation
- `/shutdown` - Special endpoint for graceful termination

## Output

Results are stored in a structured directory format:

```
results/
├── python/
│   ├── flask/
│   │   ├── 20230530_120000/              # Timestamp-based run
│   │   │   ├── scalene/
│   │   │   │   └── scalene.json          # Scalene profiling results
│   │   │   ├── energy/
│   │   │   │   └── energy.json           # Energy measurement results
│   │   │   ├── runs/
│   │   │   │   ├── run_1/                # Individual run data for energy mode
│   │   │   │   ├── run_2/
│   │   │   │   └── run_3/
│   │   │   ├── container.log             # Docker container logs
│   │   │   └── summary.json              # Overall results summary
```

## Framework Implementation

To add a new framework to test, create a directory in the `rg-profiler-frameworks` repository following this structure:

```
frameworks/
├── python/
│   ├── flask/
│   │   ├── app.py                 # Main entry point
│   │   ├── requirements.txt       # Dependencies
│   │   ├── conf.json              # Optional framework configuration
│   │   └── server/                # Framework implementation
│   │       ├── __init__.py
│   │       ├── routes.py          # Route definitions
│   │       ├── models.py          # Data models
│   │       ├── templates/         # Templates
│   │       └── middleware.py      # Middleware components
```

Each `conf.json` can include optional configurations:

```json
{
  "database": {
    "type": "postgres" // or "mysql" or "mongodb", defaults to postgres if not specified
  },
  "server": {
    "port": 8080,     // Optional, defaults to 8080
    "host": "0.0.0.0" // Optional, defaults to 0.0.0.0
  }
}
```

## License

MIT
