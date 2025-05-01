# Energy Mode for RG Profiler

This document describes the Energy Mode feature in RG Profiler, which focuses on reproducible energy consumption measurements.

## Overview

Energy Mode is designed to provide statistically significant measurements of energy consumption when running web frameworks. It utilizes CodeCarbon to track power usage and calculate CO2 emissions, with a focus on producing consistent, reproducible results.

## Key Features

- **Multiple Runs**: Executes each test multiple times (default: 3) to calculate averages and standard deviation
- **CPU Isolation**: Uses CPU pinning on Linux systems for more consistent measurements
- **Reproducible Tests**: Uses fixed workload patterns that minimize variability
- **Statistical Analysis**: Calculates mean, median, standard deviation, min, and max for key metrics
- **Detailed Reports**: Provides energy consumption in Wh and emissions in mgCO2e

## Usage

To run RG Profiler in energy mode:

```bash
./run.py --framework <framework> --mode energy
```

Additional options:

```bash
# Customize number of runs
./run.py --framework flask --mode energy --runs 5

# Adjust sampling frequency (seconds)
./run.py --framework flask --mode energy --sampling-frequency 0.2

# Control CPU isolation (Linux only)
./run.py --framework flask --mode energy --cpu-isolation on
```

## Energy Test Endpoints

The following endpoints are measured in energy mode:

- `/json` - Simple JSON serialization
- `/plaintext` - Plain text response 
- `/db` - Single database query
- `/template-simple` - Simple template rendering
- `/cpu-intensive` - Compute-heavy operation (fixed complexity)
- `/memory-heavy` - Memory-intensive operation (fixed size)

Each endpoint uses a specialized test configuration to ensure reproducible measurements.

## Output Structure

Energy mode produces output in the following structure:

```
results/
├── <language>/
│   ├── <framework>/
│   │   ├── <timestamp>/
│   │   │   ├── energy/
│   │   │   │   ├── emissions.csv         # Raw CodeCarbon data
│   │   │   │   └── energy.json           # Processed energy report
│   │   │   ├── runs/
│   │   │   │   ├── run_1/                # Data for first run
│   │   │   │   │   ├── emissions.csv
│   │   │   │   │   └── energy.json
│   │   │   │   ├── run_2/                # Data for second run
│   │   │   │   └── run_3/                # Data for third run
│   │   │   ├── energy_runs.json          # Statistical analysis across runs
│   │   │   └── container.log             # Container output log
```

## Energy Report Format

The `energy.json` file contains a comprehensive report of energy consumption:

```json
{
  "framework": "flask",
  "language": "python",
  "timestamp": "2023-05-30T12:34:56.789Z",
  "energy": {
    "total_watt_hours": 0.125,
    "cpu_watt_hours": 0.098,
    "ram_watt_hours": 0.027,
    "gpu_watt_hours": 0.0,
    "kilowatt_hours": 0.000125
  },
  "power": {
    "cpu_watts": 3.27,
    "ram_watts": 0.9,
    "gpu_watts": 0.0
  },
  "emissions": {
    "mg_carbon": 49.5,
    "g_carbon": 0.0495,
    "kg_carbon": 0.0000495
  },
  "duration_seconds": 45.2,
  "metadata": {
    "country_name": "United States",
    "country_iso_code": "USA",
    "region": "california",
    "cpu_model": "Intel(R) Core(TM) i7-10700K",
    "cpu_count": 8,
    "ram_total_size": 32.0,
    "tracking_mode": "process"
  }
}
```

The `energy_runs.json` file contains statistical analyses across multiple runs:

```json
{
  "runs": 3,
  "framework": "flask",
  "language": "python",
  "timestamp": "2023-05-30T13:00:00.000Z",
  "statistics": {
    "energy_wh": {
      "values": [0.124, 0.128, 0.123],
      "mean": 0.125,
      "median": 0.124,
      "stddev": 0.0022,
      "min": 0.123,
      "max": 0.128
    },
    "emissions_mgCO2e": {
      "values": [49.2, 50.4, 48.9],
      "mean": 49.5,
      "median": 49.2,
      "stddev": 0.68,
      "min": 48.9,
      "max": 50.4
    },
    "duration_s": {
      "values": [45.1, 45.3, 45.2],
      "mean": 45.2,
      "median": 45.2,
      "stddev": 0.08,
      "min": 45.1,
      "max": 45.3
    }
  }
}
```

## Implementation Details

Energy Mode uses several strategies to ensure reproducible measurements:

1. **Fixed Test Parameters**: Uses predictable workloads with fixed parameters (complexity, size, etc.)
2. **Single-threaded Execution**: Runs tests with single concurrency to avoid threading variability
3. **CPU Isolation**: On Linux, pins the process to a specific CPU core and assigns high priority
4. **Longer Test Duration**: Uses longer test durations to ensure stable measurements
5. **Proper Warm-up**: Ensures the server is properly warmed up before measurements begin
6. **Multiple Runs**: Performs multiple measurements to calculate statistical significance

## Internal Components

Key components that implement Energy Mode include:

1. `wrk/energy/` - Directory containing specialized test scripts
2. `config/energy_config.yaml` - Energy-specific configuration
3. `src/energy_manager.py` - Energy measurement processing and reporting
4. `src/runners/run_with_tracking.py` - Execution wrapper for energy measurement
5. `src/runners/profiler.py` - Energy testing orchestration

## Compatibility

Energy Mode works with all frameworks supported by RG Profiler. It has been tested on:

- Linux (Ubuntu 20.04+)
- macOS (10.15+)
- Windows (10+) - Note: CPU isolation is only supported on Linux

## Dependencies

- CodeCarbon 2.2.0+
- Pandas 1.3.0+
- NumPy 1.20.0+
- WRK 4.1.0+

## Limitations

- Energy measurement precision depends on the capabilities of the underlying hardware
- Mobile GPU energy tracking is limited or unavailable on some platforms
- Energy measurements include overhead from the measurement tools themselves
- Measurement accuracy can vary between different hardware configurations
