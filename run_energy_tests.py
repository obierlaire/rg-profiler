#!/usr/bin/env python3
"""
Energy mode testing script for RG Profiler.
This script runs energy measurements across multiple frameworks and generates comparison reports.
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.resolve()
sys.path.append(str(project_root))

from src.constants import FRAMEWORKS_ROOT
from src.visualization.energy_viz import generate_energy_report


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Run energy measurements across multiple frameworks and generate comparison report"
    )
    
    parser.add_argument(
        "--frameworks", 
        nargs='+',
        default=["flask", "django"],
        help="List of frameworks to test (default: flask django)"
    )
    
    parser.add_argument(
        "--language", 
        default="python",
        help="Programming language for frameworks (default: python)"
    )
    
    parser.add_argument(
        "--runs", 
        type=int, 
        default=3,
        help="Number of runs per framework (default: 3)"
    )
    
    parser.add_argument(
        "--sampling-frequency", 
        type=float, 
        default=0.5,
        help="Sampling frequency in seconds (default: 0.5)"
    )
    
    parser.add_argument(
        "--cpu-isolation", 
        choices=["on", "off"], 
        default="on",
        help="Enable/disable CPU isolation for Linux (default: on)"
    )
    
    parser.add_argument(
        "--output-dir", 
        type=str,
        default=None,
        help="Custom output directory for report (default: results/reports)"
    )
    
    parser.add_argument(
        "--skip-tests", 
        action="store_true",
        help="Skip running tests and only generate report from existing data"
    )
    
    parser.add_argument(
        "--skip-db", 
        action="store_true",
        help="Skip database startup for each framework"
    )
    
    parser.add_argument(
        "--config", 
        type=str,
        default=None,
        help="Custom energy configuration file"
    )
    
    return parser.parse_args()


def run_energy_test(framework, language="python", runs=3, sampling_frequency=0.5, 
                    cpu_isolation="on", skip_db=False, config=None):
    """
    Run energy test for a specific framework
    
    Args:
        framework: Framework name
        language: Programming language
        runs: Number of runs
        sampling_frequency: Sampling frequency in seconds
        cpu_isolation: "on" or "off" for CPU isolation
        skip_db: Whether to skip database startup
        config: Custom configuration file
        
    Returns:
        Boolean indicating success
    """
    print(f"\n{'='*80}")
    print(f"  TESTING FRAMEWORK: {language}/{framework}")
    print(f"{'='*80}\n")
    
    # Validate framework directory exists
    framework_dir = FRAMEWORKS_ROOT / language / framework
    if not framework_dir.exists():
        print(f"❌ Framework directory not found: {framework_dir}")
        return False
    
    # Build command
    cmd = ["python", "run.py", "--framework", framework, "--language", language, 
           "--mode", "energy", "--runs", str(runs), 
           "--sampling-frequency", str(sampling_frequency)]
    
    # Add CPU isolation option
    cmd.extend(["--cpu-isolation", cpu_isolation])
    
    # Add config if specified
    if config:
        cmd.extend(["--config", config])
    
    # Add skip-db if requested
    if skip_db:
        cmd.append("--skip-db")
    
    # Run the command
    print(f"🚀 Running command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running energy test for {framework}: {e}")
        return False


def main():
    """Main function"""
    args = parse_args()
    
    start_time = time.time()
    
    print(f"🔋 RG Profiler Energy Test Suite")
    print(f"   Language: {args.language}")
    print(f"   Frameworks: {', '.join(args.frameworks)}")
    print(f"   Runs per framework: {args.runs}")
    print(f"   CPU Isolation: {args.cpu_isolation}")
    
    if not args.skip_tests:
        # Run energy tests for each framework
        results = {}
        for framework in args.frameworks:
            success = run_energy_test(
                framework, 
                language=args.language,
                runs=args.runs,
                sampling_frequency=args.sampling_frequency,
                cpu_isolation=args.cpu_isolation,
                skip_db=args.skip_db,
                config=args.config
            )
            results[framework] = "✅ Success" if success else "❌ Failed"
        
        # Print summary
        print("\n📋 Energy Test Results Summary:")
        for framework, result in results.items():
            print(f"   - {framework}: {result}")
    else:
        print("⏩ Skipping tests as requested")
    
    # Generate energy report
    print("\n📊 Generating energy comparison report...")
    report_dir = generate_energy_report(
        "results",
        output_dir=args.output_dir,
        frameworks=args.frameworks
    )
    
    # Print completion
    duration = time.time() - start_time
    print(f"\n✅ Energy test suite completed in {duration:.1f} seconds")
    print(f"📄 Energy report available at: {report_dir}/energy_report.html")


if __name__ == "__main__":
    main()
