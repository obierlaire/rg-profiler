"""
Configuration management for RG Profiler
"""
import argparse
import collections.abc
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from src.constants import (
    PROJECT_ROOT,
    MODE_PROFILE, MODE_ENERGY, MODE_STANDARD, MODE_QUICK,
    PROFILE_CONFIG_FILENAME, ENERGY_CONFIG_FILENAME, 
    STANDARD_CONFIG_FILENAME, QUICK_CONFIG_FILENAME
)
from src.logger import logger


class ConfigManager:
    """
    Configuration management for RG Profiler with hierarchical configuration

    The configuration is loaded in the following order, with each level overriding the previous:
    1. Base configuration (config/base_config.yaml)
    2. Mode-specific configuration (config/{mode}_config.yaml)
    3. Custom configuration file (if provided)
    4. Mode variant configuration (if specified)
    5. Command-line arguments
    """
    
    BASE_CONFIG_FILENAME = "base_config.yaml"
    
    def __init__(self, mode: str = MODE_PROFILE, custom_config_path: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            mode: Profiling mode to use (profile, energy, standard, quick)
            custom_config_path: Optional path to custom configuration file
        """
        self.mode = mode
        self.custom_config_path = custom_config_path
        self.config: Dict[str, Any] = {}
    
    def load_configuration(self, cli_args: Optional[argparse.Namespace] = None):
        """
        Load configuration from base and mode-specific files
        
        Args:
            cli_args: Optional command-line arguments to override configuration
            
        Returns:
            Complete configuration dictionary
        """
        # 1. Load base configuration
        base_config = self._load_base_config()
        
        # 2. Load mode-specific configuration
        mode_config = self._load_mode_config()
        
        # 3. Load custom configuration if provided
        custom_config = {}
        if self.custom_config_path:
            custom_config = self._load_custom_config()
        
        # Merge configurations
        self.config = self._deep_merge(base_config, mode_config)
        self.config = self._deep_merge(self.config, custom_config)
        
        # Add mode to configuration
        self.config["mode"] = self.mode
        
        # 4. Apply variant configuration if specified
        variant = None
        if cli_args and hasattr(cli_args, 'variant') and cli_args.variant:
            variant = cli_args.variant
        elif custom_config and 'variant' in custom_config:
            variant = custom_config['variant']
            
        if variant:
            variant_config = self._get_variant_config(variant)
            if variant_config:
                self.config = self._deep_merge(self.config, variant_config)
                logger.success(f"Applied variant configuration: {variant}")
        
        # 5. Override with CLI arguments
        if cli_args:
            self._apply_cli_overrides(cli_args)
        
        logger.info(f"Configuration loaded for mode: {self.mode}")
        return self.config
    
    def _load_base_config(self) -> Dict[str, Any]:
        """Load base configuration"""
        base_config_path = PROJECT_ROOT / "config" / self.BASE_CONFIG_FILENAME
        if not base_config_path.exists():
            logger.error(f"Base config file not found: {base_config_path}")
            return {}
        
        config = self._load_yaml_file(base_config_path)
        logger.info(f"Base configuration loaded from {base_config_path}")
        return config
    
    def _load_mode_config(self) -> Dict[str, Any]:
        """Load mode-specific configuration"""
        mode_config_path = self._get_mode_config_path()
        if not mode_config_path.exists():
            logger.error(f"Mode config file not found: {mode_config_path}")
            return {}
        
        config = self._load_yaml_file(mode_config_path)
        logger.info(f"Mode configuration loaded from {mode_config_path}")
        return config
    
    def _load_custom_config(self) -> Dict[str, Any]:
        """Load custom configuration file"""
        if not self.custom_config_path:
            return {}
            
        config_path = Path(self.custom_config_path)
        if not config_path.exists():
            logger.error(f"Custom config file not found: {config_path}")
            sys.exit(1)
            
        config = self._load_yaml_file(config_path)
        logger.success(f"Custom configuration loaded from {config_path}")
        return config
    
    def _get_mode_config_path(self) -> Path:
        """Get the mode-specific config file path"""
        if self.mode == MODE_PROFILE:
            return PROJECT_ROOT / "config" / PROFILE_CONFIG_FILENAME
        elif self.mode == MODE_ENERGY:
            return PROJECT_ROOT / "config" / ENERGY_CONFIG_FILENAME
        elif self.mode == MODE_QUICK:
            return PROJECT_ROOT / "config" / QUICK_CONFIG_FILENAME
        elif self.mode == MODE_STANDARD:
            return PROJECT_ROOT / "config" / STANDARD_CONFIG_FILENAME
        else:
            logger.error(f"Invalid mode: {self.mode}")
            sys.exit(1)
    
    def _get_variant_config(self, variant: str) -> Dict[str, Any]:
        """
        Get variant-specific configuration overrides
        
        Args:
            variant: Name of the variant to load
            
        Returns:
            Variant configuration dictionary or empty dict if not found
        """
        mode_key = f"{self.mode}_variants"
        variant_key = variant
        
        # Check for mode-specific variant
        if mode_key in self.config and variant_key in self.config[mode_key]:
            return self.config[mode_key][variant_key]
        
        # Check for global variant
        if "variants" in self.config and variant_key in self.config["variants"]:
            return self.config["variants"][variant_key]
        
        logger.warning(f"Variant '{variant}' not found for mode '{self.mode}'")
        return {}
    
    def _apply_cli_overrides(self, args: argparse.Namespace):
        """
        Apply command line argument overrides to configuration
        
        Args:
            args: Command line arguments
        """
        # Common overrides
        if hasattr(args, 'tests') and args.tests:
            self.config["endpoints"] = {
                "include_all": False,
                "include": args.tests.split(',')
            }
        
        # Mode-specific overrides
        if self.mode == MODE_ENERGY and "energy" in self.config:
            if hasattr(args, 'runs') and args.runs is not None:
                self.config["energy"]["runs"] = args.runs
                
            if hasattr(args, 'sampling_frequency') and args.sampling_frequency is not None:
                self.config["energy"]["sampling_frequency"] = args.sampling_frequency
                
            if hasattr(args, 'cpu_isolation') and args.cpu_isolation is not None:
                self.config["energy"]["cpu_isolation"] = 0 if args.cpu_isolation == "on" else 1
        
        # WRK settings overrides
        if hasattr(args, 'wrk_duration') and args.wrk_duration is not None:
            self.config["wrk"]["duration"] = args.wrk_duration
            
        if hasattr(args, 'wrk_connections') and args.wrk_connections is not None:
            self.config["wrk"]["max_concurrency"] = args.wrk_connections
            self.config["wrk"]["levels"] = str(args.wrk_connections)
            
        # Server settings overrides
        if hasattr(args, 'warmup') and args.warmup is not None:
            self.config["server"]["warmup_time"] = args.warmup
            
        if hasattr(args, 'recovery') and args.recovery is not None:
            self.config["server"]["recovery_time"] = args.recovery
    
    @staticmethod
    def _load_yaml_file(file_path: Path) -> Dict[str, Any]:
        """
        Load a YAML configuration file
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Configuration dictionary
            
        Raises:
            SystemExit: If file loading fails
        """
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
                
            if not config:
                logger.error(f"Empty or invalid config file: {file_path}")
                return {}
                
            return config
            
        except yaml.YAMLError as e:
            logger.error(f"YAML error in config file {file_path}: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading config file {file_path}: {e}")
            sys.exit(1)
    
    @staticmethod
    def _deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries
        
        Values from dict2 will override values from dict1 for same keys.
        For nested dictionaries, they will be merged recursively.
        
        Args:
            dict1: Base dictionary
            dict2: Dictionary with overrides
            
        Returns:
            Merged dictionary
        """
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def get_tests_for_mode(self) -> list:
        """
        Get the list of tests to run based on the configuration
        
        Returns:
            List of test configurations
        """
        # If tests are directly defined in the config, use them
        tests = self.config.get("tests", [])
        
        # If endpoints are specified with include/exclude rules, filter the tests
        if "endpoints" in self.config:
            endpoints_config = self.config["endpoints"]
            
            # If include_all is False and include list is provided, filter tests
            if not endpoints_config.get("include_all", True) and "include" in endpoints_config:
                included_endpoints = endpoints_config["include"]
                tests = [test for test in tests if test["name"] in included_endpoints]
                
            # If exclude list is provided, filter tests
            if "exclude" in endpoints_config:
                excluded_endpoints = endpoints_config["exclude"]
                tests = [test for test in tests if test["name"] not in excluded_endpoints]
        
        if not tests:
            logger.error("No tests defined in configuration")
            sys.exit(1)
        
        return tests
    
    def get_value(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value by dot-separated path
        
        Args:
            key_path: Dot-separated path to the configuration value
            default: Default value to return if path is not found
            
        Returns:
            Configuration value or default if not found
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def save_effective_config(self, output_path: Path):
        """
        Save the effective configuration to a file
        
        Args:
            output_path: Path to save the configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.success(f"Saved effective configuration to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False