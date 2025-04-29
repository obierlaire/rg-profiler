"""
Server management utilities for RG Profiler
"""
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

from src.constants import (
    DEFAULT_SERVER_PORT,
    DEFAULT_STARTUP_TIMEOUT,
    DEFAULT_SHUTDOWN_TIMEOUT,
    DEFAULT_STABILIZATION_TIME,
    SERVER_URL
)


def wait_for_server(container_id, framework_config, timeout=DEFAULT_STARTUP_TIMEOUT):
    """
    Wait for server to become responsive
    
    Args:
        container_id: Docker container ID
        framework_config: Framework configuration
        timeout: Timeout in seconds
        
    Returns:
        Boolean indicating if server is responsive
    """
    server_port = framework_config.get("server", {}).get("port", DEFAULT_SERVER_PORT)
    server_url = f"http://localhost:{server_port}"
    
    print(f"⏳ Waiting for server at {server_url} to respond...")
    
    # Test endpoints to try
    test_paths = ["/json", "/plaintext", "/", "/health"]
    
    # Start time for timeout tracking
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # First check if container is still running
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format={{.State.Running}}", container_id],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip() != "true":
                print(f"⚠️ Container {container_id} is no longer running")
                return False
        except Exception as e:
            print(f"⚠️ Error checking container state: {e}")
            return False
        
        # Try endpoints
        for path in test_paths:
            try:
                url = f"{server_url}{path}"
                print(f"🔍 Checking endpoint: {url}")
                
                # Use curl to check endpoint
                result = subprocess.run(
                    ["curl", "-s", "--fail", "--connect-timeout", "2", url],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print(f"✅ Server is responding at {path}")
                    # Give server additional time to stabilize
                    time.sleep(DEFAULT_STABILIZATION_TIME)
                    return True
                else:
                    print(f"⚠️ Endpoint not ready: {path} (Status: {result.returncode})")
            except Exception as e:
                print(f"⚠️ Error checking endpoint: {e}")
        
        # Show recent container logs
        try:
            subprocess.run(
                ["docker", "logs", "--tail", "10", container_id],
                check=False
            )
        except Exception:
            pass
        
        # Wait before retrying
        print(f"⏳ Waiting for server... ({int(time.time() - start_time)}/{timeout}s)")
        time.sleep(2)
    
    print(f"❌ Server did not respond within {timeout}s")
    return False


def shutdown_server_gracefully(container_id, timeout=DEFAULT_SHUTDOWN_TIMEOUT):
    """
    Shutdown server gracefully by calling /shutdown endpoint
    
    Args:
        container_id: Docker container ID
        timeout: Timeout in seconds
        
    Returns:
        Boolean indicating if server shutdown gracefully
    """
    print("🛑 Sending shutdown signal to server...")
    
    try:
        # Get container IP address
        result = subprocess.run(
            ["docker", "inspect", "--format={{.NetworkSettings.IPAddress}}", container_id],
            capture_output=True,
            text=True,
            check=True
        )
        
        ip_address = result.stdout.strip()
        
        # If no IP address, try to get container name
        if not ip_address:
            container_name = subprocess.run(
                ["docker", "inspect", "--format={{.Name}}", container_id],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip().lstrip('/')
            
            # Use container name for shutdown
            ip_address = container_name
        
        # Send HTTP request to shutdown endpoint
        url = f"http://{ip_address}:8080/shutdown"
        print(f"🔍 Sending shutdown request to: {url}")
        
        result = subprocess.run(
            ["curl", "-s", "--fail", "--connect-timeout", "5", url],
            capture_output=True,
            text=True
        )
        
        # Wait for container to stop
        for i in range(timeout):
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format={{.State.Running}}", container_id],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                if result.stdout.strip() != "true":
                    print("✅ Server shutdown gracefully")
                    return True
            except Exception:
                # Container might be gone already
                print("✅ Server container no longer exists")
                return True
            
            print(f"⏳ Waiting for server to shutdown... ({i+1}/{timeout}s)")
            time.sleep(1)
        
        print("⚠️ Server didn't shut down gracefully within timeout")
        return False
    
    except Exception as e:
        print(f"⚠️ Error during graceful shutdown: {e}")
        return False


def stop_container(container_id):
    """
    Stop and remove a Docker container
    
    Args:
        container_id: Docker container ID or name
        
    Returns:
        Boolean indicating success
    """
    try:
        print(f"🛑 Stopping container: {container_id}")
        
        # Try graceful shutdown first
        if shutdown_server_gracefully(container_id):
            # Container might already be gone
            return True
        
        # Force stop container
        subprocess.run(
            ["docker", "stop", container_id],
            capture_output=True,
            check=False
        )
        
        # Remove container
        subprocess.run(
            ["docker", "rm", "-f", container_id],
            capture_output=True,
            check=False
        )
        
        print(f"✅ Container {container_id} stopped and removed")
        return True
    
    except Exception as e:
        print(f"⚠️ Error stopping container: {e}")
        return False


def get_container_logs(container_id, tail=100):
    """
    Get logs from a container
    
    Args:
        container_id: Docker container ID
        tail: Number of log lines to retrieve
        
    Returns:
        Container logs as string
    """
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail), container_id],
            capture_output=True,
            text=True
        )
        return result.stdout
    except Exception as e:
        print(f"⚠️ Error getting container logs: {e}")
        return "Error retrieving logs"
