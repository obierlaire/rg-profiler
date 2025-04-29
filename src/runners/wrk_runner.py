"""
WRK benchmarking runner for RG Profiler
"""
import os
import subprocess
import time
from pathlib import Path

from src.constants import DOCKER_NETWORK_NAME, MODE_ENERGY, MODE_PROFILE, MODE_QUICK, PROJECT_ROOT


def get_wrk_script_path(script_name, mode):
    """
    Get path to a WRK script

    Args:
        script_name: Script filename
        mode: Profiling mode

    Returns:
        Path to WRK script or None if not found
    """
    # Base WRK directory
    wrk_base = PROJECT_ROOT / "wrk"
    
    # Different directories based on mode
    if mode == MODE_ENERGY:
        wrk_dir = wrk_base / "energy"
    elif mode == MODE_PROFILE:
        wrk_dir = wrk_base / "profile"
    elif mode == MODE_QUICK:
        wrk_dir = wrk_base / "quick"
    else:
        wrk_dir = wrk_base / "standard"
    
    # Check if the directory exists
    if not wrk_dir.exists():
        print(f"❌ Error: WRK directory for mode '{mode}' not found: {wrk_dir}")
        return None
        
    # Check for script with and without .lua extension
    script_path = wrk_dir / script_name
    if script_path.exists():
        return script_path
        
    # Try adding .lua extension if not included
    if not script_name.endswith(".lua"):
        script_path = wrk_dir / f"{script_name}.lua"
        if script_path.exists():
            return script_path
            
    # Script not found
    print(f"❌ Error: WRK script '{script_name}' not found in {wrk_dir}")
    return None


def run_wrk_test(url, script_name, duration=15, concurrency=8, mode="standard"):
    """
    Run a WRK benchmark test using Docker for network resolution

    Args:
        url: URL to benchmark
        script_name: WRK script name
        duration: Test duration in seconds
        concurrency: Concurrent connections
        mode: Profiling mode

    Returns:
        Boolean indicating success
    """
    # Get WRK script path
    script_path = get_wrk_script_path(script_name, mode)
    if not script_path:
        print(f"❌ Cannot run WRK test: script '{script_name}' not found for mode '{mode}'")
        return False

    print(f"🚀 Running WRK benchmark: {url}")
    print(f"   - Script: {script_path}")
    print(f"   - Duration: {duration}s")
    print(f"   - Concurrency: {concurrency}")
    print(f"   - Mode: {mode}")

    # Only use Docker-based WRK testing for reliable network resolution
    print("   - Using Docker network (DNS resolution)")

    # Determine script directory for volume mounting
    script_mode = mode
    if mode == MODE_QUICK:
        # Quick mode uses the profile scripts directory
        script_mode = MODE_PROFILE

    # Get just the filename from the script path
    script_filename = script_path.name

    # Create Docker WRK command - note that the wrk container has WRK as its entrypoint
    docker_cmd = [
        "docker", "run", "--rm", "--network", DOCKER_NETWORK_NAME,
        "-v", f"{str(PROJECT_ROOT / 'wrk')}:/scripts",
        "rg-profiler-wrk"
    ]

    # Add WRK parameters directly (without the 'wrk' command since it's the entrypoint)
    docker_cmd.extend([
        "-t1",  # Single thread
        f"-c{concurrency}",
        f"-d{duration}s",
        "--latency"
    ])

    # Add script if it exists
    docker_cmd.extend(["-s", f"/scripts/{script_mode}/{script_filename}"])

    # Add URL
    docker_cmd.append(url)

    print(f"   - Docker command: {' '.join(docker_cmd)}")

    # Set up environment
    env = os.environ.copy()
    env.update({
        "WRK_URL": url,
        "WRK_DURATION": str(duration),
        "WRK_CONCURRENCY": str(concurrency),
        "WRK_MODE": mode
    })

    try:
        process = subprocess.run(
            docker_cmd,
            env=env,
            check=False,
            capture_output=True,
            text=True
        )

        # Print output
        print("\n=== WRK Output ===")
        print(process.stdout)

        if process.stderr:
            print("=== WRK Errors ===")
            print(process.stderr)

        # Check for success
        if process.returncode != 0:
            print(
                f"❌ WRK benchmark failed with return code: {process.returncode}")
            return False

        return True

    except Exception as e:
        print(f"❌ Error running WRK benchmark: {e}")
        return False
