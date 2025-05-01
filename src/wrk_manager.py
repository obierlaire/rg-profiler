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

class WrkManager:
    """WRK benchmark manager"""
    
    @staticmethod
    def get_script_path(script_name, mode):
        """Get path to a WRK script"""
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
        print(f"⚠️ WRK script '{script_name}' not found in {wrk_dir}")
        # Default to a basic script if available
        default_script = wrk_dir / "basic.lua"
        if default_script.exists():
            print(f"Using default script: {default_script}")
            return default_script
        else:
            raise FileNotFoundError(f"No valid WRK script found for {script_name} in {wrk_dir}")
    
    @staticmethod
    def run_test(url, script_name, duration, concurrency, mode):
        """Run a WRK benchmark test"""
        try:
            # Get WRK script path
            script_path = WrkManager.get_script_path(script_name, mode)
            
            print(f"🚀 Running WRK benchmark: {url}")
            print(f"   - Script: {script_path}")
            print(f"   - Duration: {duration}s")
            print(f"   - Concurrency: {concurrency}")
            
            # Use profile scripts for quick mode
            script_mode = "profile" if mode == MODE_QUICK else mode
                
            # Get script filename
            script_filename = script_path.name
            
            # Mount wrk scripts directory
            volumes = {
                str(PROJECT_ROOT / 'wrk'): {'bind': '/scripts', 'mode': 'ro'}
            }
            
            # Create container configuration
            container_config = {
                'image': "rg-profiler-wrk",
                'command': [
                    '-t1',  # Single thread
                    f'-c{concurrency}',
                    f'-d{duration}s',
                    '--latency',
                    '-s', f'/scripts/{script_mode}/{script_filename}',
                    url
                ],
                'network': DOCKER_NETWORK_NAME,
                'volumes': volumes,
                'remove': True,  # Auto-remove when done
                'environment': {
                    'WRK_MODE': mode
                }
            }
            
            # Run the container
            client = DockerUtils.get_client()
            container = client.containers.run(**container_config, stdout=True, stderr=True)
            
            # Print output
            output = container.decode('utf-8') if isinstance(container, bytes) else str(container)
            print("\n=== WRK Output ===")
            print(output)
            
            return True
            
        except Exception as e:
            print(f"⚠️ WRK benchmark failed: {e}")
            return False
