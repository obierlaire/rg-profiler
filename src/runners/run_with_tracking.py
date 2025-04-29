"""
Energy consumption tracking wrapper for RG Profiler
"""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# For energy tracking
try:
    from codecarbon import EmissionsTracker
except ImportError:
    EmissionsTracker = None


def run_with_energy_tracking(command, output_dir, framework_name, language, runs=1, run_interval=10):
    """
    Run a command with energy consumption tracking
    
    Args:
        command: Command to run (list or string)
        output_dir: Directory to store energy data
        framework_name: Name of the framework
        language: Programming language
        runs: Number of runs for energy mode
        run_interval: Interval between runs
        
    Returns:
        Exit code of the command
    """
    # Check if CodeCarbon is available
    if EmissionsTracker is None:
        print("❌ codecarbon is not installed. Energy tracking is not available.")
        return run_without_tracking(command)
    
    # Flag to track if we're in the process of shutting down
    shutting_down = False
    
    # Define signal handler
    def signal_handler(sig, frame):
        nonlocal shutting_down
        if shutting_down:
            return
        
        shutting_down = True
        print(f"Received signal {sig}, saving data before exit...")
        
        # Stop the tracker to save data
        try:
            tracker.stop()
            print(f"Saved energy data to: {output_dir}/emissions.csv")
        except Exception as e:
            print(f"Error saving energy data: {e}")
        
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Ensure output directory exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Runs directory for multiple runs
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(exist_ok=True)
    
    # Get energy tracking settings
    sampling_frequency = float(os.environ.get('CODECARBON_MEASURE_POWER_SECS', '0.5'))
    
    # If multiple runs are requested, run each one separately
    total_exit_code = 0
    for run_num in range(1, runs + 1):
        print(f"\n🔄 Starting energy measurement run {run_num}/{runs}")
        
        # Create run output directory
        run_dir = runs_dir / f"run_{run_num}"
        run_dir.mkdir(exist_ok=True)
        
        # Create tracker with run-specific settings
        tracker = EmissionsTracker(
            output_dir=str(run_dir),
            output_file="emissions.csv",
            save_to_file=True,
            log_level='WARNING',
            measure_power_secs=sampling_frequency,
            save_to_api=False,
            tracking_mode='process',
            project_name=framework_name,
            experiment_id=f"{language}-{run_num}"
        )
        
        # Start tracking
        tracker.start()
        
        # Run the command
        try:
            if isinstance(command, list):
                proc = subprocess.Popen(command)
            else:
                proc = subprocess.Popen(command, shell=True)
            
            # Wait for command to complete
            exit_code = proc.wait()
            total_exit_code = exit_code if exit_code != 0 else total_exit_code
            
            # Stop tracking and save data
            emissions = tracker.stop()
            print(f"Energy run {run_num} complete. Total emissions: {emissions*1000000:.2f} mgCO2e")
            
            # Copy emissions data to main output directory for the last run
            if run_num == runs:
                # Copy the emissions.csv file
                with open(run_dir / "emissions.csv", "r") as src:
                    with open(output_dir / "emissions.csv", "w") as dst:
                        dst.write(src.read())
            
            # Wait between runs if not the last run
            if run_num < runs:
                print(f"⏳ Waiting {run_interval} seconds before next run...")
                time.sleep(run_interval)
        
        except Exception as e:
            # Stop tracker on error
            try:
                tracker.stop()
            except Exception as stop_error:
                print(f"Error stopping tracker: {stop_error}")
            
            print(f"Error running command: {e}")
            return 1
    
    return total_exit_code


def run_without_tracking(command):
    """
    Run a command without energy tracking
    
    Args:
        command: Command to run (list or string)
        
    Returns:
        Exit code of the command
    """
    try:
        if isinstance(command, list):
            return subprocess.call(command)
        else:
            return subprocess.call(command, shell=True)
    except Exception as e:
        print(f"Error running command: {e}")
        return 1


def main():
    """Main entry point when run as a script"""
    # Extract command line arguments
    args = sys.argv[1:]
    if not args:
        print("Usage: python -m src.runners.run_with_tracking <command>")
        sys.exit(1)
    
    # Get settings from environment
    output_dir = os.environ.get('CODECARBON_OUTPUT_DIR', '.')
    framework_name = os.environ.get('FRAMEWORK_NAME', 'unknown')
    language = os.environ.get('LANGUAGE', 'python')
    energy_mode = os.environ.get('ENERGY_MODE', 'false').lower() == 'true'
    runs = int(os.environ.get('ENERGY_RUNS', '1'))
    run_interval = int(os.environ.get('ENERGY_RUN_INTERVAL', '10'))
    
    # Run with or without tracking based on mode
    if energy_mode:
        exit_code = run_with_energy_tracking(
            args,
            output_dir,
            framework_name,
            language,
            runs=runs,
            run_interval=run_interval
        )
    else:
        exit_code = run_without_tracking(args)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
