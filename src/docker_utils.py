"""
Docker utility functions for RG Profiler
"""
import os
import shutil
import subprocess
from pathlib import Path

from src.constants import (
    CONTAINER_NAME_PREFIX,
    DOCKER_NETWORK_NAME,
    PROJECT_ROOT
)

def check_image_exists(image_name):
    """
    Check if Docker image exists
    
    Args:
        image_name: Name of the Docker image
        
    Returns:
        Boolean indicating if image exists
    """
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image_name],
            capture_output=True,
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def check_required_images():
    """
    Check if all required Docker images exist
    
    Returns:
        Boolean indicating if all required images exist
    """
    # Define required images
    required_images = [
        f"{CONTAINER_NAME_PREFIX}-python-base",
        f"{CONTAINER_NAME_PREFIX}-wrk",
        f"{CONTAINER_NAME_PREFIX}-postgres",
        f"{CONTAINER_NAME_PREFIX}-mysql",
        f"{CONTAINER_NAME_PREFIX}-mongodb"
    ]
    
    missing_images = []
    
    # Check each required image
    for image in required_images:
        if not check_image_exists(image):
            missing_images.append(image)
    
    if missing_images:
        print("❌ Required Docker images are missing:")
        for image in missing_images:
            print(f"  - {image}")
        print("\nPlease run the following commands to build the required images:")
        print("  make all              # Build all required images")
        print("  make start-databases  # Start database containers")
        return False
    
    return True