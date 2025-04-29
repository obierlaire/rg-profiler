"""
Main entry point for RG Profiler
"""
import os
import sys
from pathlib import Path

from src.cli import parse_args
from src.config_loader import load_config
from src.constants import PROJECT_ROOT, FRAMEWORKS_ROOT
from src.database import start_database
from src.energy_manager import process_energy_results
from src.output_manager import setup_output_directory
from src.parsers.framework_parser import parse_framework_config
from src.runners.docker_manager import build_framework_image, run_framework_container
from src.runners.profiler import run_profiling_tests


def main():
    """Main execution function for RG Profiler"""
    # Check for required Docker images before starting
    from src.docker_utils import check_required_images
    
    if not check_required_images():
        print("❌ Cannot continue without required Docker images")
        sys.exit(1)
        
    # Parse command line arguments
    args = parse_args()
    
    # Validate framework directory exists
    framework_dir = get_framework_dir(args.framework, args.language)
    if not framework_dir:
        sys.exit(1)
    
    # Load configuration
    config = load_config(args.config, args.mode)
    
    # Apply CLI overrides to config
    apply_cli_overrides(config, args)
    
    # Parse framework-specific configuration
    framework_config = parse_framework_config(framework_dir)
    
    # Set up output directory
    output_dir = setup_output_directory(args.framework, args.language)
    
    # Start database if not skipped
    if not args.skip_db:
        db_type = framework_config.get("database", {}).get("type", "postgres")
        if not start_database(db_type):
            print("❌ Failed to start database")
            sys.exit(1)
    else:
        print("⏩ Skipping database startup")
    
    # Build framework Docker image
    image_name = f"rg-profiler-{args.language}-{args.framework}"
    db_type = framework_config.get("database", {}).get("type", "postgres")
    if not build_framework_image(framework_dir, image_name, db_type, args.mode):
        print("❌ Failed to build framework Docker image")
        sys.exit(1)
    
    # Run framework container with profiling
    container_id = run_framework_container(
        image_name, 
        output_dir, 
        framework_config, 
        mode=args.mode
    )
    
    if not container_id:
        print("❌ Failed to start framework container")
        sys.exit(1)
    
    # Run profiling tests
    success = run_profiling_tests(
        container_id, 
        framework_config, 
        config, 
        output_dir, 
        args.mode
    )
    
    if success:
        # Process results based on mode
        if args.mode == "energy":
            process_energy_results(output_dir, args.framework, args.language)
        
        print("✅ Profiling completed successfully")
    else:
        print("❌ Profiling failed")
        sys.exit(1)


def get_framework_dir(framework, language="python"):
    """Get the framework directory and validate it exists"""
    framework_dir = FRAMEWORKS_ROOT / language / framework
    if not framework_dir.exists():
        print(f"❌ Framework directory not found: {framework_dir}")
        return None
    return framework_dir


def apply_cli_overrides(config, args):
    """Apply command line argument overrides to configuration"""
    # Override energy mode specific settings
    if args.mode == "energy" and "energy" in config:
        if args.runs:
            config["energy"]["runs"] = args.runs
        if args.sampling_frequency:
            config["energy"]["sampling_frequency"] = args.sampling_frequency
        if args.cpu_isolation is not None:
            config["energy"]["cpu_isolation"] = 0 if args.cpu_isolation == "on" else 1


if __name__ == "__main__":
    main()
