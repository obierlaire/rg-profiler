"""
Output management for RG Profiler
"""
import json
import os
from datetime import datetime
from pathlib import Path

from src.constants import (
    OUTPUT_DIR_NAME,
    PROJECT_ROOT,
    SCALENE_OUTPUT_FILENAME,
    ENERGY_OUTPUT_FILENAME
)


def setup_output_directory(framework, language="python"):
    """
    Set up directory structure for output files
    
    Args:
        framework: Framework name
        language: Programming language
        
    Returns:
        Path to output directory
    """
    # Create base output directory
    output_base = PROJECT_ROOT / OUTPUT_DIR_NAME
    
    # Create framework-specific directory
    framework_dir = output_base / language / framework
    
    # Create timestamp-based directory for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = framework_dir / timestamp
    
    # Create directories
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories for different result types
    (output_dir / "scalene").mkdir(exist_ok=True)
    (output_dir / "energy").mkdir(exist_ok=True)
    (output_dir / "runs").mkdir(exist_ok=True)
    
    print(f"📁 Created output directory: {output_dir}")
    return output_dir


def get_scalene_output_path(output_dir):
    """
    Get path for Scalene output file
    
    Args:
        output_dir: Base output directory
        
    Returns:
        Path for Scalene output file
    """
    return output_dir / "scalene" / SCALENE_OUTPUT_FILENAME


def get_energy_output_path(output_dir):
    """
    Get path for energy output file
    
    Args:
        output_dir: Base output directory
        
    Returns:
        Path for energy output file
    """
    return output_dir / "energy" / ENERGY_OUTPUT_FILENAME


def get_run_output_path(output_dir, run_number):
    """
    Get path for a specific run output
    
    Args:
        output_dir: Base output directory
        run_number: Run number
        
    Returns:
        Path for run output directory
    """
    return output_dir / "runs" / f"run_{run_number}"


def summarize_profiling_results(output_dir, framework, language):
    """
    Generate a summary of profiling results
    
    Args:
        output_dir: Directory containing results
        framework: Framework name
        language: Programming language
        
    Returns:
        Dict with summary
    """
    # Check for Scalene output
    scalene_path = get_scalene_output_path(output_dir)
    energy_path = get_energy_output_path(output_dir)
    
    summary = {
        "framework": framework,
        "language": language,
        "timestamp": datetime.now().isoformat(),
        "profiling": {
            "available": scalene_path.exists(),
            "path": str(scalene_path) if scalene_path.exists() else None
        },
        "energy": {
            "available": energy_path.exists(),
            "path": str(energy_path) if energy_path.exists() else None
        }
    }
    
    # Add energy data if available
    if energy_path.exists():
        try:
            with open(energy_path, 'r') as f:
                energy_data = json.load(f)
                
                # Extract key metrics
                summary["energy"]["metrics"] = {
                    "total_watt_hours": energy_data.get("energy", {}).get("total_watt_hours", 0),
                    "cpu_watt_hours": energy_data.get("energy", {}).get("cpu_watt_hours", 0),
                    "emissions_mg": energy_data.get("emissions", {}).get("mg_carbon", 0),
                    "duration_seconds": energy_data.get("duration_seconds", 0)
                }
        except Exception as e:
            print(f"⚠️ Error reading energy data: {e}")
    
    # Add Scalene summary if available
    if scalene_path.exists():
        try:
            with open(scalene_path, 'r') as f:
                scalene_data = json.load(f)
                
                # Extract basic program info
                summary["profiling"]["metrics"] = {
                    "program": scalene_data.get("program", "Unknown"),
                    "elapsed_time_sec": scalene_data.get("elapsed_time_sec", 0),
                    "total_files": len(scalene_data.get("files", {}))
                }
                
                # Find top CPU and memory consumers
                top_cpu = extract_top_consumers(scalene_data, "cpu")
                top_memory = extract_top_consumers(scalene_data, "memory")
                
                summary["profiling"]["top_cpu"] = top_cpu[:5] if top_cpu else []
                summary["profiling"]["top_memory"] = top_memory[:5] if top_memory else []
        except Exception as e:
            print(f"⚠️ Error reading Scalene data: {e}")
    
    # Save summary to file
    summary_path = output_dir / "summary.json"
    try:
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"✅ Summary saved to {summary_path}")
    except Exception as e:
        print(f"⚠️ Error saving summary: {e}")
    
    return summary


def extract_top_consumers(scalene_data, metric_type):
    """
    Extract top CPU or memory consumers from Scalene data
    
    Args:
        scalene_data: Scalene profiling data
        metric_type: Type of metric ("cpu" or "memory")
        
    Returns:
        List of top consumers
    """
    all_functions = []
    
    for file_path, file_data in scalene_data.get("files", {}).items():
        for func_info in file_data.get("functions", []):
            if metric_type == "cpu":
                cpu_python = func_info.get("n_cpu_percent_python", 0)
                cpu_c = func_info.get("n_cpu_percent_c", 0)
                total_value = cpu_python + cpu_c
                metric_name = "cpu_percent"
            else:  # memory
                total_value = func_info.get("n_avg_mb", 0)
                metric_name = "memory_mb"
            
            all_functions.append({
                "name": func_info.get("line", "Unknown"),
                "filename": os.path.basename(file_path),
                "path": file_path,
                "lineno": func_info.get("lineno", 0),
                metric_name: total_value
            })
    
    # Sort by the specified metric
    all_functions.sort(key=lambda x: x.get(metric_name, 0), reverse=True)
    
    return all_functions


def save_report(data, output_path):
    """
    Save data to a JSON file
    
    Args:
        data: Data to save
        output_path: Path to save to
        
    Returns:
        Boolean indicating success
    """
    try:
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write data to file
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Report saved to {output_path}")
        return True
    
    except Exception as e:
        print(f"❌ Error saving report: {e}")
        return False
