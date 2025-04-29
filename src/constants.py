"""
Application constants for RG Profiler
"""
import os
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
FRAMEWORKS_ROOT = Path(os.environ.get("RG_FRAMEWORKS_ROOT",
                                      Path.home() / "rg-profiler-frameworks")).resolve()

# Docker paths
DOCKER_DIR = PROJECT_ROOT / "docker"

# Server configuration
DEFAULT_SERVER_HOST = "0.0.0.0"
DEFAULT_SERVER_PORT = 8080
SERVER_URL = f"http://localhost:{DEFAULT_SERVER_PORT}"

# Profiling modes
MODE_PROFILE = "profile"
MODE_ENERGY = "energy"
MODE_STANDARD = "standard"
MODE_QUICK = "quick"   # For quick dev/test

# Endpoint names and paths
ENDPOINTS = {
    "json": "/json",
    "plaintext": "/plaintext",
    "db": "/db",
    "queries": "/queries",
    "complex_routing": "/complex-routing/1/test/param1/param2",
    "middleware": "/middleware",
    "template_simple": "/template-simple",
    "template_complex": "/template-complex",
    "session_write": "/session-write",
    "session_read": "/session-read",
    "error_handling": "/error-handling",
    "header_parsing": "/header-parsing",
    "regex_heavy": "/regex-heavy",
    "serialization": "/serialization",
    "deserialization": "/deserialization",
    "cpu_intensive": "/cpu-intensive",
    "memory_heavy": "/memory-heavy",
    "shutdown": "/shutdown"
}

# Database configuration
DATABASE_TYPES = ["postgres", "mysql", "mongodb"]
DEFAULT_DATABASE_TYPE = "postgres"
DATABASE_PORTS = {
    "postgres": 5432,
    "mysql": 3306,
    "mongodb": 27017
}

# Time settings
DEFAULT_STARTUP_TIMEOUT = 45  # seconds
DEFAULT_SHUTDOWN_TIMEOUT = 30  # seconds
DEFAULT_STABILIZATION_TIME = 3  # seconds
DEFAULT_RECOVERY_TIME = 5  # seconds

# Output directory structure
OUTPUT_DIR_NAME = "results"
SCALENE_OUTPUT_FILENAME = "scalene.json"
ENERGY_OUTPUT_FILENAME = "energy.json"
EMISSIONS_CSV_FILENAME = "emissions.csv"

# Default Python version
DEFAULT_PYTHON_VERSION = "3.11"

# Docker settings
DOCKER_NETWORK_NAME = "rg-profiler-network"
CONTAINER_NAME_PREFIX = "rg-profiler"

# Default config filenames
PROFILE_CONFIG_FILENAME = "profile_config.yaml"
ENERGY_CONFIG_FILENAME = "energy_config.yaml"
STANDARD_CONFIG_FILENAME = "standard_config.yaml"
QUICK_CONFIG_FILENAME = "quick_config.yaml"
