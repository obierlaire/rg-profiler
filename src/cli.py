"""
Command line interface for RG Profiler
"""
import argparse
import os
from pathlib import Path

from src.constants import PROJECT_ROOT, FRAMEWORKS_ROOT
from src.logger import logger


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Profile web frameworks for performance and energy consumption"
    )
    
    parser.add_argument(
        "--framework", 
        required=True,
        help="Framework name (e.g., flask, django)"
    )
    
    parser.add_argument(
        "--language", 
        default="python",
        help="Programming language (default: python)"
    )
    
    parser.add_argument(
        "--skip-db", 
        action="store_true",
        help="Skip database startup"
    )
    
    parser.add_argument(
        "--mode", 
        choices=["profile", "energy", "standard", "quick"], 
        default="profile",
        help="Profiling mode: profile (CPU/memory), energy (consumption), standard (both), or quick (dev testing)"
    )
    
    parser.add_argument(
        "--config", 
        type=str, 
        default=None,
        help="Path to custom configuration file"
    )
    
    parser.add_argument(
        "--endpoint", 
        type=str, 
        default=None,
        help="Test only a specific endpoint"
    )
    
    parser.add_argument(
        "--runs", 
        type=int, 
        default=None,
        help="Number of runs for energy mode (overrides config)"
    )
    
    parser.add_argument(
        "--sampling-frequency", 
        type=float, 
        default=None,
        help="Sampling frequency in seconds for energy mode (overrides config)"
    )
    
    parser.add_argument(
        "--cpu-isolation", 
        choices=["on", "off"], 
        default=None,
        help="Enable/disable CPU isolation for energy mode (Linux only)"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--repo", 
        type=str, 
        default=None,
        help="GitHub repository URL for custom framework version (e.g., https://github.com/user/flask@branch)"
    )
    
    args = parser.parse_args()
    
    # Display environment information
    print_environment_info(args)
    
    return args


def print_environment_info(args):
    """Print environment information"""
    logger.info("🔍 RG Profiler Environment:")
    logger.info(f"   - Project root: {PROJECT_ROOT}")
    logger.info(f"   - Frameworks root: {FRAMEWORKS_ROOT}")
    logger.info(f"   - Framework: {args.framework} ({args.language})")
    logger.info(f"   - Mode: {args.mode}")
    if args.repo:
        logger.info(f"   - Custom repository: {args.repo}")
    
    framework_dir = FRAMEWORKS_ROOT / args.language / args.framework
    if framework_dir.exists():
        logger.info(f"   - Framework directory: {framework_dir} ✅")
    else:
        logger.info(f"   - Framework directory: {framework_dir} ❌")
