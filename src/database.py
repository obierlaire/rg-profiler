"""
Database management for RG Profiler
"""
import os
import subprocess
import time
from pathlib import Path

from src.constants import (
    PROJECT_ROOT,
    DOCKER_DIR,
    DATABASE_TYPES,
    DEFAULT_DATABASE_TYPE
)


def start_database(db_type=DEFAULT_DATABASE_TYPE):
    """
    Start the database container using docker-compose
    
    Args:
        db_type: Database type (postgres, mysql, mongodb)
        
    Returns:
        Boolean indicating success
    """
    from src.runners.network_manager import create_network
    from src.docker_utils import check_image_exists
    from src.constants import CONTAINER_NAME_PREFIX
    
    # Create Docker network first
    if not create_network():
        print("❌ Failed to create Docker network")
        return False
    
    db_type = db_type.lower()
    if db_type not in DATABASE_TYPES:
        print(f"❌ Unsupported database type: {db_type}")
        print(f"   Supported types: {', '.join(DATABASE_TYPES)}")
        return False

    # Check if database image exists
    db_image = f"{CONTAINER_NAME_PREFIX}-{db_type}"
    if not check_image_exists(db_image):
        print(f"❌ Required database image not found: {db_image}")
        print(f"Please run 'make {db_type}' to build the database image")
        print("Or run 'make databases' to build all database images")
        return False

    # Compose file for the specified database
    compose_file = DOCKER_DIR / f"docker-compose.{db_type}.yml"
    if not compose_file.exists():
        print(f"❌ Docker Compose file not found: {compose_file}")
        return False

    print(f"📄 Using Docker Compose file: {compose_file}")

    # Clean up any existing setup
    print(f"🧹 Cleaning up previous {db_type} database...")
    subprocess.run(["docker", "compose", "-f", str(compose_file), "down"], check=False)
    
    # Use the pre-built image (don't rebuild)
    print(f"🚀 Starting {db_type} database with pre-built image...")

    # Start the database
    print(f"🛢️ Starting {db_type} database...")
    subprocess.run(["docker", "compose", "-f", str(compose_file), "up", "-d"], check=True)

    # Wait for database to be healthy
    print("⏳ Waiting for database to become healthy...")
    container_name = f"rg-profiler-{db_type}"
    health_check_timeout = 60  # seconds
    
    for i in range(health_check_timeout):
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Health.Status}}", container_name],
                capture_output=True, 
                text=True
            )
            if result.stdout.strip() == "healthy":
                print(f"✅ {db_type.capitalize()} database is healthy!")
                return True
        except Exception as e:
            pass
        
        print(f"🔄 Waiting for database... ({i+1}/{health_check_timeout})")
        time.sleep(1)

    print("⚠️ Database health check timed out")
    return False


def stop_database(db_type=DEFAULT_DATABASE_TYPE):
    """
    Stop the database container
    
    Args:
        db_type: Database type (postgres, mysql, mongodb)
        
    Returns:
        Boolean indicating success
    """
    db_type = db_type.lower()
    if db_type not in DATABASE_TYPES:
        print(f"❌ Unsupported database type: {db_type}")
        return False

    # Compose file for the specified database
    compose_file = DOCKER_DIR / f"docker-compose.{db_type}.yml"
    if not compose_file.exists():
        print(f"❌ Docker Compose file not found: {compose_file}")
        return False

    print(f"🛑 Stopping {db_type} database...")
    subprocess.run(["docker", "compose", "-f", str(compose_file), "down"], check=False)
    print(f"✅ {db_type.capitalize()} database stopped")
    
    return True
