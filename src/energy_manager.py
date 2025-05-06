"""
Energy consumption tracking and reporting for RG Profiler
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from src.constants import PROJECT_ROOT
from src.docker.container_manager import ContainerManager
from src.docker.container_operations import ContainerOperations
from src.logger import logger
from src.wrk_manager import WrkManager


class EnergyManager:
    """Energy consumption tracking and reporting"""

    @staticmethod
    def run_tests(container_id, framework_config, config, output_dir, tests):
        """Run energy profiling tests"""
        # Create runs directory
        runs_dir = output_dir / "runs"
        runs_dir.mkdir(exist_ok=True)

        # Get container name for URL construction
        container_name = ContainerOperations.get_container_hostname(container_id)

        # Get test parameters
        runs = config.get("energy", {}).get("runs", 3)
        run_interval = config.get("energy", {}).get("run_interval", 10)
        server_port = framework_config.get("server", {}).get("port", 8080)
        base_url = f"http://{container_name}:{server_port}"

        logger.info(f"🔋 Running {runs} energy measurement run(s)")

        for run_num in range(1, runs + 1):
            run_dir = output_dir / "runs" / f"run_{run_num}"
            run_dir.mkdir(exist_ok=True)

            logger.info(f"\n🔄 Starting energy run {run_num}/{runs}")

            # Run tests for this energy run
            for test in tests:
                endpoint = test["endpoint"]
                test_url = f"{base_url}{endpoint}"
                script = test.get("script", f"{test['name']}.lua")

                logger.info(
                    f"📊 Testing: {test['name']} - {test.get('description', 'No description')}")

                # Start energy tracking before the test
                EnergyManager._start_tracking(container_id)

                success = WrkManager.run_test(
                    test_url,
                    script,
                    config["wrk"]["duration"],
                    config["wrk"]["max_concurrency"],
                    "energy",
                    config
                )

                # Stop energy tracking after the test
                EnergyManager._stop_tracking(container_id)

                if not success:
                    logger.warning(f"Test failed for {test['name']}")

                # Recovery time between tests
                time.sleep(config["server"]["recovery_time"])

            # Save energy data for this run
            EnergyManager._save_energy_run_data(container_id, run_dir, run_num, config)

            # Interval between runs
            if run_num < runs:
                logger.info(f"⏳ Waiting {run_interval} seconds before next run...")
                time.sleep(run_interval)

        # Cleanup container
        ContainerManager.shutdown_framework(container_id, framework_config)
        ContainerOperations.save_container_logs(container_id, output_dir)
        
        # Ensure container stops completely in energy mode
        logger.info("🔋 Energy mode: ensuring container is fully stopped")
        ContainerManager.stop_container(container_id, framework_config)

        # Process all runs
        EnergyManager.combine_energy_runs(output_dir, runs, config)

        return True

    @staticmethod
    def _start_tracking(container_id):
        """Start energy tracking in the container"""
        logger.info("▶️ Energy tracking is handled by codecarbon_wrapper.py")
        return True

    @staticmethod
    def _stop_tracking(container_id):
        """Stop energy tracking in the container"""
        logger.info("⏹️ Energy tracking is handled by codecarbon_wrapper.py")
        return True

    @staticmethod
    def _save_energy_run_data(container_id, run_dir, run_num, config=None):
        """Save energy data for a specific run
        
        Args:
            container_id: Container ID
            run_dir: Directory to save run data to
            run_num: Run number
            config: Optional configuration for HTTP settings
        """
        try:
            # Make sure the energy directory exists in the container
            ContainerOperations.execute_command(
                container_id,
                ["mkdir", "-p", "/output/energy"]
            )

            # Shutdown the server with explicit request to /shutdown endpoint
            logger.info("🔍 Shutting down server to save energy data...")
            server_port = 8080  # Default server port

            # Send shutdown signal to server
            ContainerOperations.send_server_shutdown(container_id, server_port, 10, config)

            # Wait for emissions file to be created (with timeout)
            logger.info("⏳ Waiting for CodeCarbon to save emissions data...")
            max_wait_time = 30  # seconds
            emissions_file = "/output/energy/emissions.csv"

            # Wait for the file to be written
            for i in range(max_wait_time):
                try:
                    # Check if the file exists and has content
                    file_exists = ContainerOperations.execute_command(
                        container_id,
                        ["bash", "-c",
                            f"test -f {emissions_file} && echo 'exists' || echo 'missing'"]
                    ).strip()

                    if file_exists == "exists":
                        # Check file size to ensure it has content
                        file_size = ContainerOperations.execute_command(
                            container_id,
                            ["bash", "-c", f"stat -c %s {emissions_file}"]
                        ).strip()

                        # If file has some reasonable size, assume it's valid
                        if int(file_size) > 100:  # More than 100 bytes
                            logger.success(
                                f"Emissions file found with size: {file_size} bytes")
                            break

                    # Show directory content occasionally for debugging
                    if i % 5 == 0 or i == max_wait_time - 1:
                        dir_content = ContainerOperations.execute_command(
                            container_id,
                            ["ls", "-la", "/output/energy"]
                        )
                        logger.info(f"📁 Energy directory contents:\n{dir_content}")

                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"Error checking for emissions file: {e}")
                    time.sleep(1)

            # Copy emissions data from container to run directory
            try:
                container_emissions_path = "/output/energy/emissions.csv"
                emissions_path = run_dir / "emissions.csv"

                # Get emissions data
                emissions_content = ContainerOperations.execute_command(
                    container_id,
                    ["cat", container_emissions_path]
                )

                # Just header or empty
                if not emissions_content or emissions_content.count('\n') <= 1:
                    logger.error(f"No emissions data found in container")
                    return False

                # Save emissions data
                with open(emissions_path, 'w') as f:
                    f.write(emissions_content)

                logger.success(f"Saved emissions data for run {run_num}")

                # Process energy data for this run
                energy_data = EnergyManager.parse_codecarbon_output(
                    emissions_path)
                framework = run_dir.parent.parent.parent.name
                language = run_dir.parent.parent.parent.parent.name

                energy_report = EnergyManager.generate_energy_report(
                    energy_data, framework, language, config)
                energy_path = run_dir / "energy.json"

                with open(energy_path, 'w') as f:
                    json.dump(energy_report, f, indent=2)

                logger.success(f"Processed energy data for run {run_num}")
                return True

            except Exception as e:
                logger.error(f"Error saving emissions data: {e}")
                return False

        except Exception as e:
            logger.error(f"Error in energy run data processing: {e}")
            return False

    @staticmethod
    def parse_codecarbon_output(csv_path):
        """Parse CodeCarbon CSV output into structured data"""
        try:
            import pandas as pd

            # Check if file exists
            if not os.path.exists(csv_path):
                logger.error(f"Emissions file does not exist: {csv_path}")
                logger.error("CodeCarbon failed to generate emissions data")
                sys.exit(1)

            # Check if file is empty
            if os.path.getsize(csv_path) == 0:
                logger.error(f"Emissions file is empty: {csv_path}")
                logger.error("CodeCarbon failed to write any data to emissions file")
                sys.exit(1)

            # Try to read the CSV file
            try:
                df = pd.read_csv(csv_path)
            except pd.errors.EmptyDataError:
                logger.error(f"No data in emissions file: {csv_path}")
                logger.error("CodeCarbon failed to write valid CSV data")
                sys.exit(1)

            # Check if there's any data beyond the header
            if len(df) == 0:
                logger.error(f"No energy measurements in file: {csv_path}")
                logger.error("CodeCarbon only wrote header row without measurements")
                sys.exit(1)

            # Get the last (most recent) entry
            last_entry = df.iloc[-1]

            # Get additional info from the file
            with open(csv_path, 'r') as f:
                lines = f.readlines()
                logger.info(
                    f"ℹ️ Found {len(lines)-1} energy measurements in emissions file")
                if len(lines) > 1:
                    logger.info(f"ℹ️ Last measurement: {lines[-1][:100]}")

            # Convert to dictionary with normalized keys
            return {
                "energy_consumed": float(last_entry.get("energy_consumed", 0)),
                "emissions": float(last_entry.get("emissions", 0)),
                "duration": float(last_entry.get("duration", 0)),
                "timestamp": last_entry.get("timestamp", None),
                "cpu_power": float(last_entry.get("cpu_power", 0)),
                "gpu_power": float(last_entry.get("gpu_power", 0)),
                "ram_power": float(last_entry.get("ram_power", 0)),
                "cpu_energy": float(last_entry.get("cpu_energy", 0)),
                "gpu_energy": float(last_entry.get("gpu_energy", 0)),
                "ram_energy": float(last_entry.get("ram_energy", 0)),
                "country_name": last_entry.get("country_name", "Unknown"),
                "country_iso_code": last_entry.get("country_iso_code", "Unknown"),
                "region": last_entry.get("region", "Unknown"),
                "cpu_model": last_entry.get("cpu_model", "Unknown"),
                "cpu_count": int(last_entry.get("cpu_count", 0)),
                "ram_total_size": float(last_entry.get("ram_total_size", 0)),
                "tracking_mode": last_entry.get("tracking_mode", "process")
            }

        except Exception as e:
            logger.error(f"Error processing CodeCarbon output: {e}")
            sys.exit(1)

    @staticmethod
    def generate_energy_report(energy_data, framework, language, config=None):
        """
        Generate a comprehensive energy report
        
        Args:
            energy_data: Energy data from CodeCarbon
            framework: Framework name
            language: Language name
            config: Configuration dictionary with units settings
            
        Returns:
            Energy report dictionary
        """
        # Get units from config if available
        units = {
            "energy": "Wh",     # Default unit for energy
            "co2": "mgCO2e",    # Default unit for CO2
            "time": "s"         # Default unit for time
        }
        
        if config and "energy" in config and "units" in config["energy"]:
            config_units = config["energy"]["units"]
            if "energy" in config_units:
                units["energy"] = config_units["energy"]
            if "co2" in config_units:
                units["co2"] = config_units["co2"]
            if "time" in config_units:
                units["time"] = config_units["time"]
                
        # Convert base energy value (CodeCarbon outputs Wh)
        total_energy = energy_data.get("energy_consumed", 0)
        cpu_energy = energy_data.get("cpu_energy", 0)
        ram_energy = energy_data.get("ram_energy", 0)
        gpu_energy = energy_data.get("gpu_energy", 0)
        
        # Convert energy to requested units
        energy_values = {}
        if units["energy"] == "Wh":
            energy_values = {
                f"total_{units['energy']}": total_energy,
                f"cpu_{units['energy']}": cpu_energy,
                f"ram_{units['energy']}": ram_energy,
                f"gpu_{units['energy']}": gpu_energy
            }
        elif units["energy"] == "kWh":
            energy_values = {
                f"total_{units['energy']}": total_energy / 1000,
                f"cpu_{units['energy']}": cpu_energy / 1000,
                f"ram_{units['energy']}": ram_energy / 1000,
                f"gpu_{units['energy']}": gpu_energy / 1000
            }
        elif units["energy"] == "J":
            # 1 Wh = 3600 J
            energy_values = {
                f"total_{units['energy']}": total_energy * 3600,
                f"cpu_{units['energy']}": cpu_energy * 3600,
                f"ram_{units['energy']}": ram_energy * 3600,
                f"gpu_{units['energy']}": gpu_energy * 3600
            }
        elif units["energy"] == "kJ":
            # 1 Wh = 3.6 kJ
            energy_values = {
                f"total_{units['energy']}": total_energy * 3.6,
                f"cpu_{units['energy']}": cpu_energy * 3.6,
                f"ram_{units['energy']}": ram_energy * 3.6,
                f"gpu_{units['energy']}": gpu_energy * 3.6
            }
        else:
            # Default to Wh if unknown unit
            energy_values = {
                "total_Wh": total_energy,
                "cpu_Wh": cpu_energy,
                "ram_Wh": ram_energy,
                "gpu_Wh": gpu_energy
            }
            
        # Convert CO2 emissions (CodeCarbon outputs kg)
        emissions = energy_data.get("emissions", 0)
        emission_values = {}
        
        if units["co2"] == "mgCO2e":
            # Convert kg to mg (1 kg = 1,000,000 mg)
            emission_values = {
                f"{units['co2']}": emissions * 1000000,
                "g_carbon": emissions * 1000,
                "kg_carbon": emissions
            }
        elif units["co2"] == "gCO2e":
            # Convert kg to g (1 kg = 1,000 g)
            emission_values = {
                f"{units['co2']}": emissions * 1000,
                "mg_carbon": emissions * 1000000,
                "kg_carbon": emissions
            }
        elif units["co2"] == "kgCO2e":
            emission_values = {
                f"{units['co2']}": emissions,
                "mg_carbon": emissions * 1000000,
                "g_carbon": emissions * 1000
            }
        else:
            # Default to mgCO2e if unknown unit
            emission_values = {
                "mgCO2e": emissions * 1000000,
                "g_carbon": emissions * 1000,
                "kg_carbon": emissions
            }
            
        # Convert duration (CodeCarbon outputs seconds)
        duration = energy_data.get("duration", 0)
        if units["time"] == "s":
            duration_value = duration
        elif units["time"] == "ms":
            duration_value = duration * 1000
        elif units["time"] == "min":
            duration_value = duration / 60
        else:
            # Default to seconds
            duration_value = duration
            
        # Format energy report
        return {
            "framework": framework,
            "language": language,
            "timestamp": energy_data.get("timestamp", None),
            "energy": energy_values,
            "power": {
                "cpu_watts": energy_data.get("cpu_power", 0),
                "ram_watts": energy_data.get("ram_power", 0),
                "gpu_watts": energy_data.get("gpu_power", 0),
            },
            "emissions": emission_values,
            "duration": {
                f"duration_{units['time']}": duration_value
            },
            "units": units,  # Include the units in the output
            "metadata": {
                "country_name": energy_data.get("country_name", "Unknown"),
                "country_iso_code": energy_data.get("country_iso_code", "Unknown"),
                "region": energy_data.get("region", "Unknown"),
                "cpu_model": energy_data.get("cpu_model", "Unknown"),
                "cpu_count": energy_data.get("cpu_count", 0),
                "ram_total_size": energy_data.get("ram_total_size", 0),
                "tracking_mode": energy_data.get("tracking_mode", "Unknown")
            }
        }

    @staticmethod
    def combine_energy_runs(output_dir, num_runs, config=None):
        """
        Combine and analyze multiple energy measurement runs
        
        Args:
            output_dir: Directory containing run data
            num_runs: Number of runs to analyze
            config: Configuration dictionary with units settings
            
        Returns:
            Statistics dictionary
        """
        runs_dir = output_dir / "runs"
        if not runs_dir.exists():
            logger.error(f"Runs directory not found: {runs_dir}")
            sys.exit(1)

        run_data = []
        individual_runs = []

        # Collect data from each run
        for i in range(1, num_runs + 1):
            run_dir = runs_dir / f"run_{i}"
            energy_file = run_dir / "energy.json"

            if not energy_file.exists():
                logger.error(f"Energy file not found for run {i}: {energy_file}")
                sys.exit(1)

            try:
                with open(energy_file, 'r') as f:
                    data = json.load(f)
                    run_data.append(data)
                    
                    # Store individual run data with run number
                    run_info = data.copy()
                    run_info["run_number"] = i
                    individual_runs.append(run_info)
            except Exception as e:
                logger.error(f"Error reading energy file for run {i}: {e}")
                sys.exit(1)

        if not run_data:
            logger.error("No valid run data found")
            sys.exit(1)
            
        # Extract units from the first run data
        units = run_data[0].get("units", {
            "energy": "Wh",
            "co2": "mgCO2e",
            "time": "s"
        })
        
        # Extract all energy, emissions, and duration keys
        all_keys = {}
        for r in run_data:
            for section in ["energy", "emissions", "duration"]:
                if section in r:
                    for key in r[section].keys():
                        if key not in ["units"]:  # Skip the units key
                            all_keys.setdefault(section, set()).add(key)
        
        # Calculate statistics for all metrics
        statistics = {}
        
        # Process energy data
        for key in all_keys.get("energy", []):
            try:
                values = [r["energy"][key] for r in run_data if key in r["energy"]]
                if values:
                    statistics[f"{key}"] = {
                        "values": values,
                        "mean": float(np.mean(values)),
                        "median": float(np.median(values)),
                        "stddev": float(np.std(values)),
                        "min": float(np.min(values)),
                        "max": float(np.max(values)),
                        "coefficient_of_variation": float(np.std(values) / np.mean(values) * 100) if np.mean(values) > 0 else 0
                    }
            except Exception as e:
                logger.warning(f"Error calculating statistics for {key}: {e}")
        
        # Process emissions data
        for key in all_keys.get("emissions", []):
            try:
                values = [r["emissions"][key] for r in run_data if key in r["emissions"]]
                if values:
                    statistics[f"{key}"] = {
                        "values": values,
                        "mean": float(np.mean(values)),
                        "median": float(np.median(values)),
                        "stddev": float(np.std(values)),
                        "min": float(np.min(values)),
                        "max": float(np.max(values)),
                        "coefficient_of_variation": float(np.std(values) / np.mean(values) * 100) if np.mean(values) > 0 else 0
                    }
            except Exception as e:
                logger.warning(f"Error calculating statistics for {key}: {e}")
                
        # Process duration data
        for key in all_keys.get("duration", []):
            try:
                values = [r["duration"][key] for r in run_data if key in r["duration"]]
                if values:
                    statistics[f"{key}"] = {
                        "values": values,
                        "mean": float(np.mean(values)),
                        "median": float(np.median(values)),
                        "stddev": float(np.std(values)),
                        "min": float(np.min(values)),
                        "max": float(np.max(values)),
                        "coefficient_of_variation": float(np.std(values) / np.mean(values) * 100) if np.mean(values) > 0 else 0
                    }
            except Exception as e:
                logger.warning(f"Error calculating statistics for {key}: {e}")
                
        # Find the main energy key, CO2 key and duration key for logging
        main_energy_key = f"total_{units['energy']}"
        if main_energy_key not in statistics:
            # Try to find any total energy key
            for key in statistics:
                if key.startswith("total_"):
                    main_energy_key = key
                    break
            # If still not found, use the first energy key
            if main_energy_key not in statistics and all_keys.get("energy"):
                main_energy_key = next(iter(all_keys["energy"]))
                
        main_co2_key = units["co2"]
        if main_co2_key not in statistics:
            # Try to find any CO2 key
            for key in statistics:
                if "co2" in key.lower() or "carbon" in key.lower():
                    main_co2_key = key
                    break
                    
        main_duration_key = f"duration_{units['time']}"
        if main_duration_key not in statistics:
            # Try to find any duration key
            for key in statistics:
                if "duration" in key.lower():
                    main_duration_key = key
                    break

        # Create statistics report
        stats = {
            "runs": len(run_data),
            "framework": run_data[0]["framework"],
            "language": run_data[0]["language"],
            "timestamp": run_data[0]["timestamp"],
            "units": units,
            "individual_runs": individual_runs,
            "statistics": statistics
        }

        # Save stats to file
        stats_file = output_dir / "energy_runs.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)

        logger.success(f"Combined energy statistics saved to {stats_file}")

        # Print summary with appropriate units
        logger.info("\n🔋 Energy Statistics Summary:")
        logger.info(f"   - Runs: {stats['runs']}")
        
        if main_energy_key in statistics:
            logger.info(
                f"   - Mean energy: {statistics[main_energy_key]['mean']:.6f} {main_energy_key.split('_')[-1]} "
                f"(±{statistics[main_energy_key]['stddev']:.6f} {main_energy_key.split('_')[-1]})")
                
        if main_co2_key in statistics:
            logger.info(
                f"   - Mean CO2: {statistics[main_co2_key]['mean']:.2f} {main_co2_key} "
                f"(±{statistics[main_co2_key]['stddev']:.2f} {main_co2_key})")
                
        if main_duration_key in statistics:
            time_unit = main_duration_key.split('_')[-1]
            logger.info(
                f"   - Mean duration: {statistics[main_duration_key]['mean']:.2f}{time_unit} "
                f"(±{statistics[main_duration_key]['stddev']:.2f}{time_unit})")

        return stats

    @staticmethod
    def process_energy_results(output_dir, framework, language, config=None):
        """
        Process energy results from CodeCarbon output
        
        Args:
            output_dir: Directory containing energy data
            framework: Framework name
            language: Language name
            config: Configuration dictionary with units settings
            
        Returns:
            True if processing was successful
        """
        # Check for CodeCarbon output in the energy directory
        energy_dir = output_dir / "energy"
        energy_dir.mkdir(exist_ok=True)
        emissions_csv = energy_dir / "emissions.csv"

        if not emissions_csv.exists():
            logger.error(f"CodeCarbon output not found: {emissions_csv}")
            sys.exit(1)

        # Parse CodeCarbon output
        energy_data = EnergyManager.parse_codecarbon_output(emissions_csv)

        # Generate energy report with units from config
        energy_report = EnergyManager.generate_energy_report(
            energy_data, framework, language, config)

        # Save energy report
        energy_json = energy_dir / "energy.json"
        with open(energy_json, 'w') as f:
            json.dump(energy_report, f, indent=2)

        # Get the units used in the report
        units = energy_report.get("units", {
            "energy": "Wh",
            "co2": "mgCO2e",
            "time": "s"
        })
        
        # Get the main energy field name using the energy unit
        energy_field = f"total_{units['energy']}"
        cpu_energy_field = f"cpu_{units['energy']}"
        ram_energy_field = f"ram_{units['energy']}"
        
        # Get the main duration field name using the time unit
        duration_field = f"duration_{units['time']}"
        
        # Print summary with appropriate units
        logger.info("\n🔋 Energy Consumption Summary:")
        
        if energy_field in energy_report["energy"]:
            logger.info(f"   - Total energy: {energy_report['energy'][energy_field]:.6f} {units['energy']}")
            
        if cpu_energy_field in energy_report["energy"]:
            logger.info(f"   - CPU energy: {energy_report['energy'][cpu_energy_field]:.6f} {units['energy']}")
            
        if ram_energy_field in energy_report["energy"]:
            logger.info(f"   - RAM energy: {energy_report['energy'][ram_energy_field]:.6f} {units['energy']}")
            
        if units["co2"] in energy_report["emissions"]:
            logger.info(f"   - CO2 emissions: {energy_report['emissions'][units['co2']]:.2f} {units['co2']}")
            
        if duration_field in energy_report["duration"]:
            logger.info(f"   - Duration: {energy_report['duration'][duration_field]:.2f} {units['time']}")

        return True
