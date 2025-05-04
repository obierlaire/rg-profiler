"""
Framework configuration parser for RG Profiler
"""
import json
from pathlib import Path
import sys

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
        print(f"❌ No conf.json found for framework: {framework_dir}")
        sys.exit(1)
    
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
        print(f"❌ Error reading framework configuration: {e}")
        sys.exit(1)
    
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
        print(f"❌ No requirements.txt found for framework: {framework_dir}")
        sys.exit(1)
    
    return requirements_file
