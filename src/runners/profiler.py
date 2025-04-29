"""
Profiling orchestration for RG Profiler
"""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from src.config_loader import get_tests_for_mode
from src.constants import (
    MODE_ENERGY,
    MODE_PROFILE,
    MODE_QUICK,
    MODE_STANDARD,
    DOCKER_NETWORK_NAME
)
from src.output_manager import (
    get_energy_output_path,
    get_run_output_path,
    get_scalene_output_path,
    save_report
)
from src.runners.docker_manager import (
    execute_in_container,
    get_container_logs,
    get_container_name_from_id,
    shutdown_framework_gracefully,
    stop_container
)
from src.runners.wrk_runner import run_wrk_test


def run_profiling_tests(container_id, framework_config, config, output_dir, mode):
    """
    Run profiling tests based on configuration
    
    Args:
        container_id: Docker container ID
        framework_config: Framework configuration
        config: Profiler configuration
        output_dir: Directory for output
        mode: Profiling mode
        
    Returns:
        Boolean indicating success
    """
    print(f"🚀 Starting profiling in {mode} mode...")
    
    # Allow the server to stabilize
    time.sleep(config["server"]["stabilization_time"])
    
    # Load test definitions for the current mode
    tests = get_tests_for_mode(config)
    if not tests:
        print("❌ No tests defined for this mode")
        return False
        
    # Handle energy mode with multiple runs
    if mode == MODE_ENERGY:
        return run_energy_tests(container_id, framework_config, config, output_dir, tests)
    
    # Handle quick mode (minimal single endpoint test)
    elif mode == MODE_QUICK:
        return run_quick_tests(container_id, framework_config, config, output_dir, tests)
    
    # Standard or profile mode
    else:
        return run_standard_tests(container_id, framework_config, config, output_dir, mode, tests)


def run_standard_tests(container_id, framework_config, config, output_dir, mode, tests):
    """
    Run standard profiling with all configured endpoints
    
    Args:
        container_id: Docker container ID
        framework_config: Framework configuration
        config: Profiler configuration
        output_dir: Directory for output
        mode: Profiling mode
        tests: List of test configurations
        
    Returns:
        Boolean indicating success
    """
    print(f"🔍 Running {len(tests)} tests in {mode} mode")
    
    # Get container name for URL construction
    container_name = get_container_name_from_id(container_id)
    server_port = framework_config.get("server", {}).get("port", 8080)
    
    # Base URL using container name within Docker network
    if container_name:
        base_url = f"http://{container_name}:{server_port}"
    else:
        print("⚠️ Could not resolve container name, using container ID")
        base_url = f"http://{container_id}:{server_port}"
    
    # Run each test
    for test in tests:
        print(f"\n📊 Testing: {test['name']} - {test['description']}")
        
        # Construct full URL
        endpoint = test["endpoint"]
        test_url = f"{base_url}{endpoint}"
        
        # Get script name
        script = test.get("script", f"{test['name']}.lua")
        
        # Run the WRK test
        success = run_wrk_test(
            test_url,
            script,
            config["wrk"]["duration"],
            config["wrk"]["max_concurrency"],
            mode
        )
        
        if not success:
            print(f"⚠️ Test failed for {test['name']}")
        
        # Recovery time between tests
        time.sleep(config["server"]["recovery_time"])
    
    # Shutdown the server gracefully
    print("\n🛑 Sending shutdown signal to framework...")
    shutdown_framework_gracefully(container_id, framework_config)
    
    # Get container logs
    logs = get_container_logs(container_id, tail=500)
    save_container_logs(logs, output_dir)
    
    # Stop container
    stop_container(container_id)
    
    # Generate summary report
    from src.output_manager import summarize_profiling_results
    framework = output_dir.parent.name
    language = output_dir.parent.parent.name
    summarize_profiling_results(output_dir, framework, language)
    
    # Process energy metrics if this is standard mode
    if mode == MODE_STANDARD:
        from src.energy_manager import process_energy_results
        process_energy_results(output_dir, framework, language)
    
    return True


def run_energy_tests(container_id, framework_config, config, output_dir, tests):
    """
    Run energy profiling with multiple runs
    
    Args:
        container_id: Docker container ID
        framework_config: Framework configuration
        config: Profiler configuration
        output_dir: Directory for output
        tests: List of test configurations
        
    Returns:
        Boolean indicating success
    """
    print("🔋 Starting energy profiling...")
    
    # Get number of runs from config
    runs = config.get("energy", {}).get("runs", 3)
    run_interval = config.get("energy", {}).get("run_interval", 10)
    
    print(f"🔄 Running {runs} energy measurement run(s)")
    
    # Create runs directory
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(exist_ok=True)
    
    # Get container name for URL construction
    container_name = get_container_name_from_id(container_id)
    server_port = framework_config.get("server", {}).get("port", 8080)
    
    # Base URL using container name within Docker network
    if container_name:
        base_url = f"http://{container_name}:{server_port}"
    else:
        print("⚠️ Could not resolve container name, using container ID")
        base_url = f"http://{container_id}:{server_port}"
    
    for run_num in range(1, runs + 1):
        run_dir = get_run_output_path(output_dir, run_num)
        run_dir.mkdir(exist_ok=True)
        
        print(f"\n🔄 Starting energy run {run_num}/{runs}")
        
        # Run tests for this energy run
        for test in tests:
            print(f"📊 Testing: {test['name']} - {test['description']}")
            
            # Construct full URL
            endpoint = test["endpoint"]
            test_url = f"{base_url}{endpoint}"
            
            # Get script name
            script = test.get("script", f"{test['name']}.lua")
            
            # Run the WRK test
            success = run_wrk_test(
                test_url,
                script,
                config["wrk"]["duration"],
                config["wrk"]["max_concurrency"],
                MODE_ENERGY
            )
            
            if not success:
                print(f"⚠️ Test failed for {test['name']}")
            
            # Recovery time between tests
            time.sleep(config["server"]["recovery_time"])
        
        # Save energy data for this run
        save_energy_run_data(container_id, run_dir, run_num)
        
        # Interval between runs
        if run_num < runs:
            print(f"⏳ Waiting {run_interval} seconds before next run...")
            time.sleep(run_interval)
    
    # Shutdown the server gracefully
    print("\n🛑 Sending shutdown signal to framework...")
    shutdown_framework_gracefully(container_id, framework_config)
    
    # Get container logs
    logs = get_container_logs(container_id, tail=500)
    save_container_logs(logs, output_dir)
    
    # Stop container
    stop_container(container_id)
    
    # Process all runs
    from src.energy_manager import combine_energy_runs
    combine_energy_runs(output_dir, runs)
    
    # Generate summary report
    from src.output_manager import summarize_profiling_results
    framework = output_dir.parent.name
    language = output_dir.parent.parent.name
    summarize_profiling_results(output_dir, framework, language)
    
    return True


def run_quick_tests(container_id, framework_config, config, output_dir, tests):
    """
    Run quick test - simplified for development and debugging
    
    Args:
        container_id: Docker container ID
        framework_config: Framework configuration
        config: Profiler configuration
        output_dir: Directory for output
        tests: List of test configurations
        
    Returns:
        Boolean indicating success
    """
    print("🏃 Running quick test mode...")
    
    # Should have at least one test
    if not tests:
        print("❌ No tests defined for quick mode")
        return False
    
    # Take just the first test for quick mode
    test = tests[0]
    
    # Get container name for URL construction
    container_name = get_container_name_from_id(container_id)
    server_port = framework_config.get("server", {}).get("port", 8080)
    
    # Base URL using container name within Docker network
    if container_name:
        base_url = f"http://{container_name}:{server_port}"
    else:
        print("⚠️ Could not resolve container name, using container ID")
        base_url = f"http://{container_id}:{server_port}"
    
    # Construct full URL
    endpoint = test["endpoint"]
    test_url = f"{base_url}{endpoint}"
    
    # Get script name
    script = test.get("script", f"{test['name']}.lua")
    
    # Run the WRK test
    print(f"📊 Testing: {test['name']} - {test['description']}")
    success = run_wrk_test(
        test_url,
        script,
        config["wrk"]["duration"],
        config["wrk"]["max_concurrency"],
        MODE_QUICK
    )
    
    if not success:
        print(f"⚠️ Quick test failed for {test['name']}")
    
    # Wait a moment for any data to be written
    print("⏳ Waiting for files to be written...")
    time.sleep(2)
    
    # Shutdown the server gracefully
    print("\n🛑 Sending shutdown signal to framework...")
    shutdown_framework_gracefully(container_id, framework_config)
    
    # Get container logs
    logs = get_container_logs(container_id, tail=200)
    save_container_logs(logs, output_dir)
    
    # Stop container
    stop_container(container_id)
    
    # Generate summary report
    from src.output_manager import summarize_profiling_results
    framework = output_dir.parent.name
    language = output_dir.parent.parent.name
    summarize_profiling_results(output_dir, framework, language)
    
    return True


def save_energy_run_data(container_id, run_dir, run_num):
    """
    Save energy data for a specific run
    
    Args:
        container_id: Docker container ID
        run_dir: Directory to save run data
        run_num: Run number
        
    Returns:
        Boolean indicating success
    """
    try:
        print(f"📋 Retrieving energy data for run {run_num}...")
        
        # Emissions file path inside container - consistently use energy directory
        container_emissions_path = "/output/energy/emissions.csv"
        
        # Get emissions CSV content
        emissions_content = execute_in_container(
            container_id, 
            ["cat", container_emissions_path]
        )
        
        if emissions_content:
            emissions_path = run_dir / "emissions.csv"
            with open(emissions_path, 'w') as f:
                f.write(emissions_content)
            print(f"✅ Saved emissions data for run {run_num}")
            
            # Process energy data for this run
            from src.energy_manager import parse_codecarbon_output, generate_energy_report
            
            if emissions_path.exists():
                energy_data = parse_codecarbon_output(emissions_path)
                framework = run_dir.parent.parent.parent.name
                language = run_dir.parent.parent.parent.parent.name
                
                energy_report = generate_energy_report(energy_data, framework, language)
                energy_path = run_dir / f"run_{run_num}_energy.json"
                
                with open(energy_path, 'w') as f:
                    import json
                    json.dump(energy_report, f, indent=2)
                
                print(f"✅ Processed energy data for run {run_num}")
                return True
            else:
                print(f"⚠️ No emissions data found for run {run_num}")
                return False
        else:
            print(f"⚠️ No emissions data found in container at {container_emissions_path}")
            return False
        
    except Exception as e:
        print(f"❌ Error saving energy run data: {e}")
        return False


def save_container_logs(logs, output_dir):
    """
    Save container logs to file
    
    Args:
        logs: Container logs
        output_dir: Output directory
        
    Returns:
        Path to logs file
    """
    logs_path = output_dir / "container.log"
    try:
        with open(logs_path, 'w') as f:
            f.write(logs)
        print(f"✅ Container logs saved to {logs_path}")
        return logs_path
    except Exception as e:
        print(f"⚠️ Error saving container logs: {e}")
        return None