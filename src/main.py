"""
Main execution function for RG Profiler
"""
import sys
from pathlib import Path

from src.cli import parse_args
from src.config_manager import ConfigManager
from src.constants import PROJECT_ROOT, FRAMEWORKS_ROOT, CONTAINER_NAME_PREFIX
from src.database_manager import DatabaseManager
from src.docker.image_builder import ImageBuilder
from src.docker.container_manager import ContainerManager
from src.logger import logger, setup_logging
from src.output_manager import setup_output_directory
from src.parsers.framework_parser import parse_framework_config
from src.profiler import Profiler
from src.energy_manager import EnergyManager

def main():
    """Main execution function for RG Profiler"""
    # Parse command line arguments
    args = parse_args()
    
    # Configure logging level based on verbose flag
    if args.verbose:
        from src.logger import setup_logging
        import logging
        setup_logging(console_level=logging.DEBUG)
    
    # Check for required Docker images
    check_required_images()
    
    # Set up logging based on verbose flag
    if args.verbose:
        import logging
        setup_logging(console_level=logging.DEBUG, detailed_format=True)
        logger.debug("Verbose logging enabled")
    
    # Validate framework directory exists
    framework_dir = get_framework_dir(args.framework, args.language)
    
    # Load configuration
    config_manager = ConfigManager(args.mode, args.config)
    config = config_manager.load_configuration(args)
    
    # Parse framework-specific configuration
    framework_config = parse_framework_config(framework_dir)
    
    # Set up output directory
    output_dir = setup_output_directory(args.framework, args.language)
    
    # Start database if not skipped
    if not args.skip_db:
        db_type = framework_config["database"]["type"]
        DatabaseManager.start_database(db_type)
    else:
        logger.info("⏩ Skipping database startup")
    
    # Build framework Docker image
    image_name = f"rg-profiler-{args.language}-{args.framework}"
    db_type = framework_config["database"]["type"]
    ImageBuilder.build_framework_image(framework_dir, image_name, db_type, args.mode, args.framework)
    
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
    
def check_required_images():
    """Check if all required Docker images exist"""
    required_images = [
        f"{CONTAINER_NAME_PREFIX}-python-base",
        f"{CONTAINER_NAME_PREFIX}-wrk",
        f"{CONTAINER_NAME_PREFIX}-postgres",
        f"{CONTAINER_NAME_PREFIX}-mysql",
        f"{CONTAINER_NAME_PREFIX}-mongodb"
    ]
    
    missing_images = []
    
    for image in required_images:
        if not ImageBuilder.check_image_exists(image):
            missing_images.append(image)
    
    if missing_images:
        logger.error("Required Docker images are missing:")
        for image in missing_images:
            logger.error(f"  - {image}")
        logger.error("\nPlease run the following commands to build the required images:")
        logger.error("  make all              # Build all required images")
        logger.error("  make start-databases  # Start database containers")
        sys.exit(1)
    
    return True

def get_framework_dir(framework, language="python"):
    """Get the framework directory and validate it exists"""
    framework_dir = FRAMEWORKS_ROOT / language / framework
    if not framework_dir.exists():
        logger.error(f"Framework directory not found: {framework_dir}")
        sys.exit(1)
    return framework_dir

if __name__ == "__main__":
    main()