"""
Configuration loading and management for RG Profiler
"""
import os
from pathlib import Path

import yaml

from src.constants import (
    PROJECT_ROOT,
    MODE_PROFILE,
    MODE_ENERGY,
    MODE_STANDARD,
    MODE_QUICK,
    PROFILE_CONFIG_FILENAME,
    ENERGY_CONFIG_FILENAME,
    STANDARD_CONFIG_FILENAME,
    QUICK_CONFIG_FILENAME
)


def load_config(config_path=None, mode=MODE_PROFILE):
    """
    Load configuration from file with defaults based on mode
    
    Args:
        config_path: Optional path to custom config file
        mode: Profiling mode (profile, energy, standard, quick)
        
    Returns:
        Dict with merged configuration
    """
    # Start with default configuration
    config = get_default_config(mode)
    
    # If custom config path provided, load and merge it
    if config_path:
        custom_config = load_config_file(config_path)
        if custom_config:
            merge_configs(config, custom_config)
    # Otherwise load the default config file for the specified mode
    else:
        default_config_path = get_default_config_path(mode)
        if default_config_path.exists():
            mode_config = load_config_file(default_config_path)
            if mode_config:
                merge_configs(config, mode_config)
    
    # Ensure mode is set in config
    config["mode"] = mode
    
    return config


def get_default_config(mode):
    """Get default configuration based on mode"""
    # Common default configuration across all modes
    config = {
        "wrk": {
            "duration": 15,
            "pipeline": 1,
            "max_concurrency": 8,
            "levels": "8",
            "timeout": 8
        },
        "server": {
            "warmup_time": 2,
            "recovery_time": 5,
            "startup_timeout": 45,
            "stabilization_time": 3
        },
        "database": {
            "type": "postgres"
        },
        "tests": []  # Default empty tests list
    }
    
    # Mode-specific defaults
    if mode == MODE_PROFILE:
        config.update({
            "profiling": {
                "scalene": {
                    "enabled": True,
                    "profile_all": True,
                    "reduced_profile": True
                }
            }
        })
    elif mode == MODE_ENERGY:
        config.update({
            "energy": {
                "runs": 3,
                "run_interval": 10,
                "sampling_frequency": 0.5,
                "cpu_isolation": 0,
                "units": {
                    "energy": "Wh",
                    "co2": "mgCO2e",
                    "time": "s"
                }
            },
            "profiling": {
                "scalene": {
                    "enabled": False
                }
            }
        })
    elif mode == MODE_STANDARD:
        config.update({
            "profiling": {
                "scalene": {
                    "enabled": True,
                    "profile_all": True,
                    "reduced_profile": True
                }
            },
            "energy": {
                "runs": 1,
                "sampling_frequency": 1.0,
                "cpu_isolation": 0
            }
        })
    elif mode == MODE_QUICK:
        config.update({
            "profiling": {
                "scalene": {
                    "enabled": False
                }
            },
            "wrk": {
                "duration": 1,
                "pipeline": 1,
                "max_concurrency": 1,
                "levels": "1",
                "timeout": 2
            },
            "server": {
                "warmup_time": 0,
                "recovery_time": 0,
                "startup_timeout": 10,
                "stabilization_time": 0.5
            }
        })
    
    return config


def get_default_config_path(mode):
    """Get the default config file path based on mode"""
    if mode == MODE_PROFILE:
        return PROJECT_ROOT / "config" / PROFILE_CONFIG_FILENAME
    elif mode == MODE_ENERGY:
        return PROJECT_ROOT / "config" / ENERGY_CONFIG_FILENAME
    elif mode == MODE_QUICK:
        return PROJECT_ROOT / "config" / QUICK_CONFIG_FILENAME
    else:  # standard mode
        return PROJECT_ROOT / "config" / STANDARD_CONFIG_FILENAME


def load_config_file(file_path):
    """Load a YAML configuration file"""
    try:
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        print(f"✅ Loaded configuration from {file_path}")
        return config
    except Exception as e:
        print(f"⚠️ Error loading config file {file_path}: {e}")
        return {}


def merge_configs(base_config, override_config):
    """
    Recursively merge override_config into base_config
    
    Args:
        base_config: Base configuration dict to be updated
        override_config: Dict with values to override
        
    Returns:
        None (base_config is updated in place)
    """
    for key, value in override_config.items():
        if (
            key in base_config and 
            isinstance(base_config[key], dict) and 
            isinstance(value, dict)
        ):
            merge_configs(base_config[key], value)
        else:
            base_config[key] = value


def get_tests_for_mode(config):
    """
    Get the list of tests to run based on the configuration
    
    Args:
        config: Configuration dict
        
    Returns:
        List of test definitions
    """
    # Get tests directly from config
    tests = config.get("tests", [])
    
    # For backward compatibility, if no tests are defined but endpoints are,
    # convert the old endpoints format to the new test format
    if not tests and "endpoints" in config:
        endpoints = config.get("endpoints", {})
        include_all = endpoints.get("include_all", True)
        
        if include_all:
            # Import here to avoid circular imports
            from src.constants import ENDPOINTS
            
            # Generate tests from all available endpoints
            for name, path in ENDPOINTS.items():
                # Skip shutdown endpoint
                if name == "shutdown":
                    continue
                
                tests.append({
                    "name": name,
                    "endpoint": path,
                    "script": f"{name}.lua" if name != "plaintext" else "basic.lua",
                    "description": f"Test for {name}"
                })
        else:
            # Only include specified endpoints
            include_list = endpoints.get("include", [])
            # Import here to avoid circular imports
            from src.constants import ENDPOINTS
            
            for name in include_list:
                if name in ENDPOINTS:
                    tests.append({
                        "name": name,
                        "endpoint": ENDPOINTS[name],
                        "script": f"{name}.lua" if name != "plaintext" else "basic.lua",
                        "description": f"Test for {name}"
                    })
    
    return tests