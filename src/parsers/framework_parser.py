"""
Framework configuration parser for RG Profiler
"""
import json
from pathlib import Path

from src.constants import DEFAULT_SERVER_PORT, DEFAULT_SERVER_HOST, DEFAULT_DATABASE_TYPE


def parse_framework_config(framework_dir):
    """
    Parse framework configuration from conf.json
    
    Args:
        framework_dir: Path to the framework directory
        
    Returns:
        Dict with framework configuration
    """
    # Default configuration
    config = {
        "database": {
            "type": DEFAULT_DATABASE_TYPE
        },
        "server": {
            "port": DEFAULT_SERVER_PORT,
            "host": DEFAULT_SERVER_HOST
        },
        "endpoints": {}
    }
    
    # Try to load framework configuration
    config_file = framework_dir / "conf.json"
    if not config_file.exists():
        print(f"ℹ️ No conf.json found for framework, using defaults")
        return config
    
    try:
        with open(config_file, "r") as f:
            framework_config = json.load(f)
        
        # Merge database settings
        if "database" in framework_config:
            if isinstance(framework_config["database"], dict):
                config["database"].update(framework_config["database"])
            elif isinstance(framework_config["database"], str):
                config["database"]["type"] = framework_config["database"]
        
        # Merge server settings
        if "server" in framework_config and isinstance(framework_config["server"], dict):
            config["server"].update(framework_config["server"])
        
        # Extract any custom endpoint information
        if "endpoints" in framework_config and isinstance(framework_config["endpoints"], dict):
            config["endpoints"] = framework_config["endpoints"]
        
        print(f"✅ Loaded framework configuration from {config_file}")
    
    except Exception as e:
        print(f"⚠️ Error reading framework configuration: {e}")
    
    return config


def get_requirements_path(framework_dir):
    """
    Get path to requirements.txt file
    
    Args:
        framework_dir: Path to the framework directory
        
    Returns:
        Path to requirements.txt or None if not found
    """
    requirements_file = framework_dir / "requirements.txt"
    if not requirements_file.exists():
        print(f"⚠️ No requirements.txt found for framework: {framework_dir}")
        return None
    
    return requirements_file


def get_entry_point(framework_dir):
    """
    Get framework entry point (app.py)
    
    Args:
        framework_dir: Path to the framework directory
        
    Returns:
        Path to app.py or None if not found
    """
    entry_point = framework_dir / "app.py"
    if not entry_point.exists():
        print(f"❌ No app.py entry point found for framework: {framework_dir}")
        return None
    
    return entry_point


def extract_framework_version(framework_dir):
    """
    Extract framework version from requirements.txt
    
    Args:
        framework_dir: Path to the framework directory
        
    Returns:
        Framework version string or None if not found
    """
    requirements_file = get_requirements_path(framework_dir)
    if not requirements_file:
        return None
    
    try:
        framework_name = framework_dir.name.lower()
        with open(requirements_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith(framework_name):
                    # Try to extract version from line like "flask==2.0.1"
                    parts = line.split("==")
                    if len(parts) == 2:
                        return parts[1]
                    # Try for version specifiers like "flask>=2.0.1"
                    parts = line.split(">=")
                    if len(parts) == 2:
                        return f">={parts[1]}"
    except Exception as e:
        print(f"⚠️ Error extracting framework version: {e}")
    
    return None
