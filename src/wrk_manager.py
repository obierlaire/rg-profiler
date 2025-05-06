"""
WRK benchmarking management for RG Profiler
"""
import sys
from pathlib import Path
import docker

from src.constants import (
    DOCKER_NETWORK_NAME,
    MODE_ENERGY,
    MODE_PROFILE,
    MODE_QUICK,
    MODE_STANDARD,
    PROJECT_ROOT
)
from src.docker_utils import DockerUtils
from src.logger import logger

class WrkManager:
    """WRK benchmark manager"""
    
    @staticmethod
    def get_script_path(script_name, mode):
        """
        Get path to a WRK script
        
        Args:
            script_name: Name of the script (with or without .lua extension)
            mode: Profiling mode
            
        Returns:
            Path to the script
            
        Raises:
            FileNotFoundError: If script not found
        """
        # Map mode to subdirectory
        mode_dirs = {
            MODE_ENERGY: "energy",
            MODE_PROFILE: "profile",
            MODE_QUICK: "quick",
            MODE_STANDARD: "standard"
        }
        
        # Get directory for this mode
        mode_dir = mode_dirs.get(mode, "profile")  # Default to profile if unknown mode
        wrk_dir = PROJECT_ROOT / "wrk" / mode_dir
        
        # Try both with and without .lua extension
        paths_to_check = [
            wrk_dir / script_name,
            wrk_dir / f"{script_name}.lua" if not script_name.endswith('.lua') else None
        ]
        
        # Return first existing path
        for path in paths_to_check:
            if path and path.exists():
                return path
        
        # If we get here, script not found
        logger.warning(f"WRK script '{script_name}' not found in {wrk_dir}")
        # Default to a basic script if available
        default_script = wrk_dir / "basic.lua"
        if default_script.exists():
            logger.info(f"Using default script: {default_script}")
            return default_script
        else:
            raise FileNotFoundError(f"No valid WRK script found for {script_name} in {wrk_dir}")
    
    @staticmethod
    def run_test(url, script_name, duration, concurrency, mode, config=None):
        """
        Run a WRK benchmark test
        
        Args:
            url: URL to benchmark
            script_name: Name of the script to use
            duration: Test duration in seconds
            concurrency: Number of concurrent connections
            mode: Profiling mode
            config: Optional framework configuration
            
        Returns:
            True if test succeeded, False otherwise
        """
        try:
            # Get WRK script path
            script_path = WrkManager.get_script_path(script_name, mode)
            
            # Get WRK settings from config
            wrk_timeout = 10  # Default timeout
            wrk_pipeline = 1  # Default pipeline setting
            network_name = DOCKER_NETWORK_NAME  # Default network name
            
            if config:
                if "wrk" in config:
                    wrk_config = config["wrk"]
                    if "timeout" in wrk_config:
                        wrk_timeout = wrk_config["timeout"]
                    if "pipeline" in wrk_config:
                        wrk_pipeline = wrk_config["pipeline"]
                        
                # Get network name from docker config
                if "docker" in config and "network_name" in config["docker"]:
                    network_name = config["docker"]["network_name"]
            
            logger.start(f"Running WRK benchmark: {url}")
            logger.info(f"   - Script: {script_path}")
            logger.info(f"   - Duration: {duration}s")
            logger.info(f"   - Concurrency: {concurrency}")
            logger.info(f"   - Pipeline: {wrk_pipeline}")
            logger.info(f"   - Timeout: {wrk_timeout}s")
            
            # Use profile scripts for quick mode
            script_mode = "profile" if mode == MODE_QUICK else mode
                
            # Get script filename
            script_filename = script_path.name
            
            # Mount wrk scripts directory
            volumes = {
                str(PROJECT_ROOT / 'wrk'): {'bind': '/scripts', 'mode': 'ro'}
            }
            
            # Prepare command options
            wrk_command = [
                '-t1',  # Single thread
                f'-c{concurrency}',
                f'-d{duration}s',
                '--latency',
                f'--timeout={wrk_timeout}s'
            ]
            
            # Add pipeline option if > 1 (default is 1, only add if needed)
            if wrk_pipeline > 1:
                wrk_command.append(f'--pipeline={wrk_pipeline}')
            
            # Add script and URL
            wrk_command.extend([
                '-s', f'/scripts/{script_mode}/{script_filename}',
                url
            ])
            
            # Create container configuration
            container_config = {
                'image': "rg-profiler-wrk",
                'command': wrk_command,
                'network': network_name,
                'volumes': volumes,
                'remove': True,  # Auto-remove when done
                'environment': {
                    'WRK_MODE': mode
                }
            }
            
            # Run the container
            logger.info("🔄 Starting WRK container...")
            container = DockerUtils.run_container(**container_config, stdout=True, stderr=True)
            
            # Print output
            output = container.decode('utf-8') if isinstance(container, bytes) else str(container)
            logger.info("\n=== WRK Output ===")
            logger.info(output)
            
            return True
            
        except Exception as e:
            logger.warning(f"WRK benchmark failed: {e}")
            return False
