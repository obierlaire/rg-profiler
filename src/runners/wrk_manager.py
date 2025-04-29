"""
WRK Docker container management for RG Profiler
"""
import os
import subprocess
from pathlib import Path

from src.constants import (
    PROJECT_ROOT,
    DOCKER_NETWORK_NAME,
    CONTAINER_NAME_PREFIX
)
from src.runners.network_manager import create_network, connect_container

def build_wrk_image():
    """
    Build WRK Docker image
    
    Returns:
        Boolean indicating success
    """
    image_name = f"{CONTAINER_NAME_PREFIX}-wrk"
    dockerfile_path = PROJECT_ROOT / "docker" / "wrk" / "Dockerfile"
    
    if not dockerfile_path.exists():
        print(f"❌ WRK Dockerfile not found: {dockerfile_path}")
        return False
    
    print(f"🔨 Building WRK Docker image: {image_name}")
    try:
        # Build the image
        result = subprocess.run(
            ["docker", "build", "-t", image_name, "-f", str(dockerfile_path), str(PROJECT_ROOT / "docker" / "wrk")],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ Successfully built WRK image: {image_name}")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build WRK Docker image: {e}")
        print(f"Error output: {e.stderr}")
        return False


def run_wrk_container(url, script_path, duration, concurrency, mode, output_dir=None):
    """
    Run WRK in a Docker container
    
    Args:
        url: Target URL to benchmark
        script_path: Path to LUA script file
        duration: Duration in seconds
        concurrency: Number of concurrent connections
        mode: Profiling mode
        output_dir: Directory to mount for output (optional)
        
    Returns:
        Boolean indicating success
    """
    # Ensure Docker network exists
    if not create_network():
        print("❌ Failed to create Docker network")
        return False
    
    # Use the pre-built WRK image from Makefile
    image_name = f"{CONTAINER_NAME_PREFIX}-wrk"
    try:
        # Check if image exists
        result = subprocess.run(
            ["docker", "image", "inspect", image_name],
            capture_output=True,
            check=False
        )
        
        if result.returncode != 0:
            print(f"⚠️ WRK image not found: {image_name}")
            print("Please run 'make wrk' to build the WRK image")
            return False
    except Exception as e:
        print(f"⚠️ Error checking WRK image: {e}")
        print("Please run 'make wrk' to build the WRK image")
        return False
    
    # Make sure script exists
    if not script_path.exists():
        print(f"❌ Script file not found: {script_path}")
        return False
    
    # Create container name
    container_name = f"{CONTAINER_NAME_PREFIX}-wrk-run"
    
    # Stop existing container if it exists
    try:
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            check=False
        )
    except Exception:
        pass
    
    # Get script directory and filename
    script_dir = script_path.parent
    script_filename = script_path.name
    
    # Create the run command
    cmd = [
        "docker", "run",
        "--name", container_name,
        "--rm",
        "--network", DOCKER_NETWORK_NAME,
    ]
    
    # Mount scripts directory if provided
    cmd.extend(["-v", f"{script_dir.resolve()}:/scripts"])
    
    # Mount output directory if provided
    if output_dir:
        cmd.extend(["-v", f"{output_dir.resolve()}:/output"])
    
    # Add environment variables
    cmd.extend([
        "-e", f"WRK_MODE={mode}",
        "-e", f"WRK_URL={url}",
        "-e", f"WRK_DURATION={duration}",
        "-e", f"WRK_CONCURRENCY={concurrency}"
    ])
    
    # Add WRK arguments
    cmd.extend([
        image_name,
        "-t1",  # Single thread
        f"-c{concurrency}",
        f"-d{duration}s",
        "--latency",
        "-s", f"/scripts/{script_filename}",
        url
    ])
    
    print(f"🚀 Running WRK benchmark: {url}")
    print(f"   - Script: {script_path}")
    print(f"   - Duration: {duration}s")
    print(f"   - Concurrency: {concurrency}")
    
    try:
        # Run the container
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True
        )
        
        # Print output
        print("\n=== WRK Output ===")
        print(result.stdout)
        
        if result.stderr:
            print("=== WRK Errors ===")
            print(result.stderr)
        
        # Check for success
        if result.returncode != 0:
            print(f"❌ WRK benchmark failed with return code: {result.returncode}")
            return False
        
        return True
    
    except Exception as e:
        print(f"❌ Error running WRK benchmark: {e}")
        return False


def get_wrk_script_path(script_name, mode):
    """
    Get path to a WRK script
    
    Args:
        script_name: Script filename
        mode: Profiling mode
        
    Returns:
        Path to WRK script
    """
    # Base WRK directory
    wrk_base = PROJECT_ROOT / "wrk"
    
    # Different directories based on mode
    mode_dir = wrk_base / mode.lower()
    
    # Check for script with and without .lua extension
    script_path = mode_dir / script_name
    if script_path.exists():
        return script_path
    
    # Try adding .lua extension if not included
    if not script_name.endswith(".lua"):
        script_path = mode_dir / f"{script_name}.lua"
        if script_path.exists():
            return script_path
    
    # If specific script not found, use basic script
    basic_script = mode_dir / "basic.lua"
    if basic_script.exists():
        print(f"⚠️ Script {script_name} not found, using basic.lua")
        return basic_script
    
    # As a last resort, use a script from a different mode directory
    for fallback_mode in ["profile", "standard", "energy"]:
        if fallback_mode == mode:
            continue
        
        fallback_dir = wrk_base / fallback_mode
        fallback_script = fallback_dir / "basic.lua"
        if fallback_script.exists():
            print(f"⚠️ Using fallback script from {fallback_mode}")
            return fallback_script
    
    # Nothing found, return None
    print(f"❌ No WRK script found for {script_name}")
    return None
