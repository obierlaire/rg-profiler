"""
Energy consumption tracking and reporting for RG Profiler
"""
import json
import os
from datetime import datetime
from pathlib import Path

from src.constants import EMISSIONS_CSV_FILENAME, ENERGY_OUTPUT_FILENAME


def parse_codecarbon_output(csv_path):
    """
    Parse CodeCarbon CSV output into structured data
    
    Args:
        csv_path: Path to the emissions.csv file
        
    Returns:
        Dict with parsed energy data
    """
    try:
        import pandas as pd
        
        # Read the CSV file
        df = pd.read_csv(csv_path)
        
        # Get the last (most recent) entry
        if len(df) > 0:
            last_entry = df.iloc[-1]
            
            # Convert to dictionary with normalized keys
            energy_data = {
                "energy_consumed": float(last_entry.get("energy_consumed", 0)),  # in Wh
                "emissions": float(last_entry.get("emissions", 0)),  # in kg
                "duration": float(last_entry.get("duration", 0)),  # in seconds
                "timestamp": last_entry.get("timestamp", datetime.now().isoformat()),
                "cpu_power": float(last_entry.get("cpu_power", 0)),  # in W
                "gpu_power": float(last_entry.get("gpu_power", 0)),  # in W
                "ram_power": float(last_entry.get("ram_power", 0)),  # in W
                "cpu_energy": float(last_entry.get("cpu_energy", 0)),  # in Wh
                "gpu_energy": float(last_entry.get("gpu_energy", 0)),  # in Wh
                "ram_energy": float(last_entry.get("ram_energy", 0)),  # in Wh
                "country_name": last_entry.get("country_name", "Unknown"),
                "country_iso_code": last_entry.get("country_iso_code", "Unknown"),
                "region": last_entry.get("region", "Unknown"),
                "cpu_model": last_entry.get("cpu_model", "Unknown"),
                "cpu_count": int(last_entry.get("cpu_count", 0)),
                "ram_total_size": float(last_entry.get("ram_total_size", 0)),
                "tracking_mode": last_entry.get("tracking_mode", "process")
            }
            
            return energy_data
        else:
            print("⚠️ CodeCarbon CSV file is empty")
            return create_empty_energy_data()
    
    except Exception as e:
        print(f"❌ Error parsing CodeCarbon output: {e}")
        return create_empty_energy_data()


def create_empty_energy_data():
    """Create empty energy data structure"""
    return {
        "energy_consumed": 0,
        "emissions": 0,
        "duration": 0,
        "timestamp": datetime.now().isoformat(),
        "cpu_power": 0,
        "gpu_power": 0,
        "ram_power": 0,
        "cpu_energy": 0,
        "gpu_energy": 0,
        "ram_energy": 0,
        "country_name": "Unknown",
        "country_iso_code": "Unknown",
        "region": "Unknown",
        "cpu_model": "Unknown",
        "cpu_count": 0,
        "ram_total_size": 0,
        "tracking_mode": "process"
    }


def generate_energy_report(energy_data, framework, language):
    """
    Generate a comprehensive energy report
    
    Args:
        energy_data: Energy data from CodeCarbon
        framework: Framework name
        language: Programming language
        
    Returns:
        Dict with formatted energy report
    """
    # Convert CO2 to mg if it's in kg (CodeCarbon uses kg)
    emissions_mg = energy_data.get("emissions", 0) * 1000000  # kg to mg conversion
    
    # Format energy report
    energy_report = {
        "framework": framework,
        "language": language,
        "timestamp": datetime.now().isoformat(),
        "energy": {
            "total_watt_hours": energy_data.get("energy_consumed", 0),
            "cpu_watt_hours": energy_data.get("cpu_energy", 0),
            "ram_watt_hours": energy_data.get("ram_energy", 0),
            "gpu_watt_hours": energy_data.get("gpu_energy", 0),
            "kilowatt_hours": energy_data.get("energy_consumed", 0) / 1000,
        },
        "power": {
            "cpu_watts": energy_data.get("cpu_power", 0),
            "ram_watts": energy_data.get("ram_power", 0),
            "gpu_watts": energy_data.get("gpu_power", 0),
        },
        "emissions": {
            "mg_carbon": emissions_mg,
            "g_carbon": emissions_mg / 1000,
            "kg_carbon": emissions_mg / 1000000
        },
        "duration_seconds": energy_data.get("duration", 0),
        "metadata": {
            "country_name": energy_data.get("country_name", "Unknown"),
            "country_iso_code": energy_data.get("country_iso_code", "Unknown"),
            "region": energy_data.get("region", "Unknown"),
            "cpu_model": energy_data.get("cpu_model", "Unknown"),
            "cpu_count": energy_data.get("cpu_count", 0),
            "ram_total_size": energy_data.get("ram_total_size", 0),
            "tracking_mode": energy_data.get("tracking_mode", "Unknown"),
            "timestamp": energy_data.get("timestamp", datetime.now().isoformat())
        },
        "raw_data": energy_data
    }
    
    return energy_report


def save_energy_report(energy_report, output_dir):
    """
    Save energy report to file
    
    Args:
        energy_report: Energy report dict
        output_dir: Directory to save the report
        
    Returns:
        Path to saved file
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create file path
    output_file = output_dir / ENERGY_OUTPUT_FILENAME
    
    try:
        # Write energy report to file
        with open(output_file, 'w') as f:
            json.dump(energy_report, f, indent=2)
        
        print(f"✅ Energy report saved to {output_file}")
        return output_file
    
    except Exception as e:
        print(f"❌ Error saving energy report: {e}")
        return None


def process_energy_results(output_dir, framework, language):
    """
    Process energy results from CodeCarbon output
    
    Args:
        output_dir: Directory containing results
        framework: Framework name
        language: Programming language
        
    Returns:
        Boolean indicating success
    """
    # Check for CodeCarbon output in the energy directory
    energy_dir = output_dir / "energy"
    energy_dir.mkdir(exist_ok=True)  # Ensure the directory exists
    emissions_csv = energy_dir / EMISSIONS_CSV_FILENAME
    
    if not emissions_csv.exists():
        print(f"❌ CodeCarbon output not found: {emissions_csv}")
        return False
    
    # Parse CodeCarbon output
    energy_data = parse_codecarbon_output(emissions_csv)
    
    # Generate energy report
    energy_report = generate_energy_report(energy_data, framework, language)
    
    # Save energy report
    output_file = save_energy_report(energy_report, output_dir)
    if not output_file:
        return False
    
    # Print summary
    print("\n🔋 Energy Consumption Summary:")
    print(f"   - Total energy: {energy_report['energy']['total_watt_hours']:.6f} Wh")
    print(f"   - CPU energy: {energy_report['energy']['cpu_watt_hours']:.6f} Wh")
    print(f"   - RAM energy: {energy_report['energy']['ram_watt_hours']:.6f} Wh")
    print(f"   - CO2 emissions: {energy_report['emissions']['mg_carbon']:.2f} mgCO2e")
    print(f"   - Duration: {energy_report['duration_seconds']:.2f} seconds")
    
    return True


def combine_energy_runs(output_dir, num_runs):
    """
    Combine and analyze multiple energy measurement runs
    
    Args:
        output_dir: Directory containing run results
        num_runs: Number of runs performed
        
    Returns:
        Dict with combined statistics
    """
    runs_dir = output_dir / "runs"
    if not runs_dir.exists():
        print(f"❌ Runs directory not found: {runs_dir}")
        return None
    
    run_data = []
    
    # Collect data from each run
    for i in range(1, num_runs + 1):
        run_file = runs_dir / f"run_{i}_energy.json"
        if not run_file.exists():
            print(f"⚠️ Run file not found: {run_file}")
            continue
        
        try:
            with open(run_file, 'r') as f:
                data = json.load(f)
                run_data.append(data)
        except Exception as e:
            print(f"⚠️ Error reading run file {run_file}: {e}")
    
    if not run_data:
        print("❌ No valid run data found")
        return None
    
    # Calculate statistics
    stats = calculate_energy_statistics(run_data)
    
    # Save combined results
    stats_file = output_dir / "energy_runs.json"
    try:
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"✅ Combined energy statistics saved to {stats_file}")
        return stats
    except Exception as e:
        print(f"❌ Error saving combined statistics: {e}")
        return None


def calculate_energy_statistics(run_data):
    """
    Calculate statistics from multiple energy measurement runs
    
    Args:
        run_data: List of energy report dicts
        
    Returns:
        Dict with statistics
    """
    import numpy as np
    
    # Extract key metrics from each run
    energy_values = [r["energy"]["total_watt_hours"] for r in run_data]
    cpu_energy_values = [r["energy"]["cpu_watt_hours"] for r in run_data]
    ram_energy_values = [r["energy"]["ram_watt_hours"] for r in run_data]
    emissions_values = [r["emissions"]["mg_carbon"] for r in run_data]
    duration_values = [r["duration_seconds"] for r in run_data]
    
    # Calculate statistics
    stats = {
        "runs": len(run_data),
        "framework": run_data[0]["framework"],
        "language": run_data[0]["language"],
        "timestamp": datetime.now().isoformat(),
        "statistics": {
            "energy_wh": {
                "values": energy_values,
                "mean": float(np.mean(energy_values)),
                "median": float(np.median(energy_values)),
                "stddev": float(np.std(energy_values)),
                "min": float(np.min(energy_values)),
                "max": float(np.max(energy_values))
            },
            "cpu_energy_wh": {
                "values": cpu_energy_values,
                "mean": float(np.mean(cpu_energy_values)),
                "median": float(np.median(cpu_energy_values)),
                "stddev": float(np.std(cpu_energy_values)),
                "min": float(np.min(cpu_energy_values)),
                "max": float(np.max(cpu_energy_values))
            },
            "ram_energy_wh": {
                "values": ram_energy_values,
                "mean": float(np.mean(ram_energy_values)),
                "median": float(np.median(ram_energy_values)),
                "stddev": float(np.std(ram_energy_values)),
                "min": float(np.min(ram_energy_values)),
                "max": float(np.max(ram_energy_values))
            },
            "emissions_mgCO2e": {
                "values": emissions_values,
                "mean": float(np.mean(emissions_values)),
                "median": float(np.median(emissions_values)),
                "stddev": float(np.std(emissions_values)),
                "min": float(np.min(emissions_values)),
                "max": float(np.max(emissions_values))
            },
            "duration_s": {
                "values": duration_values,
                "mean": float(np.mean(duration_values)),
                "median": float(np.median(duration_values)),
                "stddev": float(np.std(duration_values)),
                "min": float(np.min(duration_values)),
                "max": float(np.max(duration_values))
            }
        },
        "individual_runs": run_data
    }
    
    return stats
