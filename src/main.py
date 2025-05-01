"""
Main execution function for RG Profiler
"""
import sys
from pathlib import Path

from src.cli import parse_args
from src.config_manager import ConfigManager
from src.constants import PROJECT_ROOT, FRAMEWORKS_ROOT
from src.database_manager import DatabaseManager
from src.docker_utils import DockerUtils
from src.docker.image_builder import ImageBuilder
from src.docker.container_manager import ContainerManager
from src.output_manager import setup_output_directory
from src.parsers.framework_parser import parse_framework_config
from src.profiler import Profiler
from src.energy_manager import EnergyManager

def main():
    """Main execution function for RG Profiler"""
    # Check for required Docker images
    DockerUtils.check_required_images()
    
    # Parse command line arguments
    args = parse_args()
    
    # Validate framework directory exists
    framework_dir = get_framework_dir(args.framework, args.language)
    
    # Load configuration
    config = ConfigManager.load_config(args.config, args.mode)
    config["mode"] = args.mode  # Ensure mode is set
    
    # Apply CLI overrides
    apply_cli_overrides(config, args)
    
    # Parse framework-specific configuration
    framework_config = parse_framework_config(framework_dir)
    
    # Set up output directory
    output_dir = setup_output_directory(args.framework, args.language)
    
    # Start database if not skipped
    if not args.skip_db:
        db_type = framework_config["database"]["type"]
        DatabaseManager.start_database(db_type)
    else:
        print("⏩ Skipping database startup")
    
    # Build framework Docker image
    image_name = f"rg-profiler-{args.language}-{args.framework}"
    db_type = framework_config["database"]["type"]
    ImageBuilder.build_framework_image(framework_dir, image_name, db_type, args.mode)
    
    # Run framework container
    container_id = ContainerManager.run_container(
        image_name, 
        output_dir, 
        framework_config, 
        args.mode
    )
    
    # Run profiling tests
    Profiler.run(
        container_id,
        framework_config,
        config,
        output_dir,
        args.mode
    )

def get_framework_dir(framework, language="python"):
    """Get the framework directory and validate it exists"""
    framework_dir = FRAMEWORKS_ROOT / language / framework
    if not framework_dir.exists():
        print(f"❌ Framework directory not found: {framework_dir}")
        sys.exit(1)
    return framework_dir

def apply_cli_overrides(config, args):
    """Apply command line argument overrides to configuration"""
    # Override energy mode specific settings
    if args.mode == "energy" and "energy" in config:
        if args.runs is not None:
            config["energy"]["runs"] = args.runs
        if args.sampling_frequency is not None:
            config["energy"]["sampling_frequency"] = args.sampling_frequency
        if args.cpu_isolation is not None:
            config["energy"]["cpu_isolation"] = 0 if args.cpu_isolation == "on" else 1

if __name__ == "__main__":
    main()