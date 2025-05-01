"""
Configuration management for RG Profiler
"""
import sys
from pathlib import Path
import yaml

from src.constants import (
    PROJECT_ROOT,
    MODE_PROFILE, MODE_ENERGY, MODE_STANDARD, MODE_QUICK,
    PROFILE_CONFIG_FILENAME, ENERGY_CONFIG_FILENAME, 
    STANDARD_CONFIG_FILENAME, QUICK_CONFIG_FILENAME
)

class ConfigManager:
    """Configuration management for RG Profiler"""
    
    @staticmethod
    def load_config(config_path=None, mode=MODE_PROFILE):
        """Load configuration from file or exit in error"""
        # If custom config path provided, use it
        if config_path:
            config_path = Path(config_path)
            if not config_path.exists():
                print(f"❌ Custom config file not found: {config_path}")
                sys.exit(1)
            return ConfigManager.load_config_file(config_path)
            
        # Otherwise use the default config file for the specified mode
        default_config_path = ConfigManager.get_default_config_path(mode)
        if not default_config_path.exists():
            print(f"❌ Default config file not found for mode '{mode}': {default_config_path}")
            sys.exit(1)
            
        return ConfigManager.load_config_file(default_config_path)
    
    @staticmethod
    def get_default_config_path(mode):
        """Get the default config file path based on mode"""
        if mode == MODE_PROFILE:
            return PROJECT_ROOT / "config" / PROFILE_CONFIG_FILENAME
        elif mode == MODE_ENERGY:
            return PROJECT_ROOT / "config" / ENERGY_CONFIG_FILENAME
        elif mode == MODE_QUICK:
            return PROJECT_ROOT / "config" / QUICK_CONFIG_FILENAME
        elif mode == MODE_STANDARD:
            return PROJECT_ROOT / "config" / STANDARD_CONFIG_FILENAME
        else:
            print(f"❌ Invalid mode: {mode}")
            sys.exit(1)
    
    @staticmethod
    def load_config_file(file_path):
        """Load a YAML configuration file or exit in error"""
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
                
            if not config:
                print(f"❌ Empty or invalid config file: {file_path}")
                sys.exit(1)
                
            print(f"✅ Loaded configuration from {file_path}")
            return config
            
        except yaml.YAMLError as e:
            print(f"❌ YAML error in config file {file_path}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error loading config file {file_path}: {e}")
            sys.exit(1)
    
    @staticmethod
    def get_tests_for_mode(config):
        """Get the list of tests to run based on the configuration"""
        tests = config.get("tests", [])
        
        if not tests:
            print("❌ No tests defined in configuration")
            sys.exit(1)
        
        return tests