"""
Database management for RG Profiler
"""
import sys
import subprocess
import time
from pathlib import Path

from src.constants import (
    PROJECT_ROOT,
    DOCKER_DIR,
    DATABASE_TYPES,
    DEFAULT_DATABASE_TYPE
)

class DatabaseManager:
    """Database management using docker-compose"""
    
    @staticmethod
    def start_database(db_type=DEFAULT_DATABASE_TYPE):
        """Start the database container using docker-compose"""
        db_type = db_type.lower()
        if db_type not in DATABASE_TYPES:
            print(f"❌ Unsupported database type: {db_type}")
            print(f"   Supported types: {', '.join(DATABASE_TYPES)}")
            sys.exit(1)

        # Compose file for the specified database
        compose_file = DOCKER_DIR / f"docker-compose.{db_type}.yml"
        if not compose_file.exists():
            print(f"❌ Docker Compose file not found: {compose_file}")
            sys.exit(1)

        print(f"📄 Using Docker Compose file: {compose_file}")

        # Create network first
        print(f"🌐 Creating Docker network...")
        try:
            subprocess.run(
                ["docker", "network", "create", "rg-profiler-network"],
                check=False,
                capture_output=True
            )
        except Exception:
            pass  # Network might already exist

        # Clean up any existing setup
        print(f"🧹 Cleaning up previous {db_type} database...")
        subprocess.run(["docker", "compose", "-f", str(compose_file), "down"], check=False)
        
        # Start the database
        print(f"🛢️ Starting {db_type} database...")
        try:
            subprocess.run(["docker", "compose", "-f", str(compose_file), "up", "-d"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start database: {e}")
            sys.exit(1)

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
            except Exception:
                pass
            
            print(f"🔄 Waiting for database... ({i+1}/{health_check_timeout})")
            time.sleep(1)

        print("❌ Database health check timed out")
        sys.exit(1)
    
    @staticmethod
    def stop_database(db_type=DEFAULT_DATABASE_TYPE):
        """Stop the database container"""
        db_type = db_type.lower()
        if db_type not in DATABASE_TYPES:
            print(f"❌ Unsupported database type: {db_type}")
            sys.exit(1)

        # Compose file for the specified database
        compose_file = DOCKER_DIR / f"docker-compose.{db_type}.yml"
        if not compose_file.exists():
            print(f"❌ Docker Compose file not found: {compose_file}")
            sys.exit(1)

        print(f"🛑 Stopping {db_type} database...")
        try:
            subprocess.run(["docker", "compose", "-f", str(compose_file), "down"], check=True)
            print(f"✅ {db_type.capitalize()} database stopped")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to stop database: {e}")
            sys.exit(1)
