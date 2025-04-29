"""
Benchmark orchestration for RG Profiler
"""
import os
import time
from pathlib import Path

from src.constants import SERVER_URL
from src.runners.network_manager import create_network
from src.runners.server_manager import wait_for_server, stop_server
from src.runners.wrk_manager import run_wrk_container, get_wrk_script_path


def run_benchmarks(framework_config, config, container_id=None, mode="standard"):
    """
    Run benchmarks against a framework
    
    Args:
        framework_config: Framework configuration
        config: Profiler configuration
        container_id: Container ID of the running framework
        mode: Profiling mode
    
    Returns:
        Boolean indicating success
    """
    # Ensure Docker network exists
    if not create_network():
        print("❌ Failed to create Docker network for benchmarking")
        return False
    
    print(f"🚀 Starting benchmarks in {mode} mode")
    
    # Get test endpoints
    endpoints = prepare_endpoints(framework_config, config, mode)
    if not endpoints:
        print("❌ No endpoints found to benchmark")
        return False
    
    # Get server port from framework config
    server_port = framework_config.get("server", {}).get("port", 8080)
    
    # Allow server to stabilize
    time.sleep(config["server"]["stabilization_time"])
    
    # Run benchmarks against each endpoint
    for i, endpoint in enumerate(endpoints):
        # Get container name for direct network access
        container_name = container_id
        if "." in container_id:
            container_name = container_id.split('.')[0]
        
        # Construct URL using container name instead of localhost
        url = endpoint["url"].replace("localhost", container_name)
        url = url.replace("http://127.0.0.1", f"http://{container_name}")
        
        print(f"\n📊 Benchmarking endpoint: {url}")
        
        # Get script path
        script_path = get_wrk_script_path(endpoint["script"], mode)
        if not script_path:
            print(f"⚠️ Script not found for {endpoint['script']}, skipping endpoint")
            continue
        
        # Run the benchmark
        success = run_wrk_container(
            url,
            script_path,
            config["wrk"]["duration"],
            int(config["wrk"]["max_concurrency"]),
            mode
        )
        
        if not success:
            print(f"⚠️ Benchmark failed for endpoint: {url}")
        
        # Give server time to recover before next benchmark
        if i < len(endpoints) - 1:
            print(f"💤 Allowing server recovery time ({config['server']['recovery_time']}s)")
            time.sleep(config["server"]["recovery_time"])
    
    return True


def prepare_endpoints(framework_config, config, mode):
    """
    Prepare endpoints for benchmarking
    
    Args:
        framework_config: Framework configuration
        config: Profiler configuration
        mode: Profiling mode
    
    Returns:
        List of endpoint dictionaries with URL, script, and metadata
    """
    endpoints = []
    
    # Get test types based on mode
    if mode == "profile":
        from src.runners.test_types import PROFILING_TEST_TYPES as test_types
    elif mode == "energy":
        from src.runners.test_types import ENERGY_TEST_TYPES as test_types
    else:
        from src.runners.test_types import STANDARD_TEST_TYPES as test_types
    
    # Get server port
    server_port = framework_config.get("server", {}).get("port", 8080)
    
    # Check if we should include all endpoints or just specific ones
    include_all = config.get("endpoints", {}).get("include_all", True)
    include_endpoints = config.get("endpoints", {}).get("include", [])
    
    # Get custom endpoint paths from framework configuration
    custom_endpoints = framework_config.get("endpoints", {})
    
    for name, test_info in test_types.items():
        # Skip if not in include list when include_all is False
        if not include_all and name not in include_endpoints:
            continue
        
        # Get endpoint path (use custom if defined, otherwise default)
        path = test_info.get("url", f"/{name.replace('_', '-')}")
        
        # Override with custom path if defined in framework config
        if name in custom_endpoints:
            path = custom_endpoints[name]
        
        # Handle query parameter for multiple queries test
        if name in ["query", "queries"] and "?" not in path:
            query_count = config.get("queries", {}).get("count", 20)
            path = f"{path}?queries={query_count}"
        
        # Build URL
        url = f"http://localhost:{server_port}{path}"
        
        # Add to endpoints list
        endpoints.append({
            "name": name,
            "url": url,
            "script": test_info.get("script", "basic.lua"),
            "accept": test_info.get("accept", "application/json")
        })
    
    return endpoints
