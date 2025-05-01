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
from src.docker_utils import DockerUtils
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
        container_name = DockerUtils.execute_command(
            container_id, ["hostname"]
        ).strip()

        # Get test parameters
        runs = config.get("energy", {}).get("runs", 3)
        run_interval = config.get("energy", {}).get("run_interval", 10)
        server_port = framework_config.get("server", {}).get("port", 8080)
        base_url = f"http://{container_name}:{server_port}"

        print(f"🔋 Running {runs} energy measurement run(s)")

        for run_num in range(1, runs + 1):
            run_dir = output_dir / "runs" / f"run_{run_num}"
            run_dir.mkdir(exist_ok=True)

            print(f"\n🔄 Starting energy run {run_num}/{runs}")

            # Run tests for this energy run
            for test in tests:
                endpoint = test["endpoint"]
                test_url = f"{base_url}{endpoint}"
                script = test.get("script", f"{test['name']}.lua")

                print(
                    f"📊 Testing: {test['name']} - {test.get('description', 'No description')}")

                # Start energy tracking before the test
                EnergyManager._start_tracking(container_id)

                success = WrkManager.run_test(
                    test_url,
                    script,
                    config["wrk"]["duration"],
                    config["wrk"]["max_concurrency"],
                    "energy"
                )

                # Stop energy tracking after the test
                EnergyManager._stop_tracking(container_id)

                if not success:
                    print(f"⚠️ Test failed for {test['name']}")

                # Recovery time between tests
                time.sleep(config["server"]["recovery_time"])

            # Save energy data for this run
            EnergyManager._save_energy_run_data(container_id, run_dir, run_num)

            # Interval between runs
            if run_num < runs:
                print(f"⏳ Waiting {run_interval} seconds before next run...")
                time.sleep(run_interval)

        # Shutdown and cleanup
        ContainerManager.shutdown_framework(container_id, framework_config)

        # Save container logs
        logs = DockerUtils.get_container_logs(container_id)
        logs_path = output_dir / "container.log"
        with open(logs_path, 'w') as f:
            f.write(logs)

        # Ensure container stops completely in energy mode
        print("🔋 Energy mode: ensuring container is fully stopped")
        DockerUtils.stop_container(container_id)

        # Process all runs
        EnergyManager.combine_energy_runs(output_dir, runs)

        return True

    @staticmethod
    def _start_tracking(container_id):
        """Start energy tracking in the container"""
        print("▶️ Energy tracking is handled by codecarbon_wrapper.py")
        return True

    @staticmethod
    def _stop_tracking(container_id):
        """Stop energy tracking in the container"""
        print("⏹️ Energy tracking is handled by codecarbon_wrapper.py")
        return True

    @staticmethod
    def _save_energy_run_data(container_id, run_dir, run_num):
        """Save energy data for a specific run"""
        try:
            # Make sure the energy directory exists in the container
            DockerUtils.execute_command(
                container_id,
                ["mkdir", "-p", "/output/energy"]
            )

            # Shutdown the server with explicit request to /shutdown endpoint
            print("🔍 Shutting down server to save energy data...")
            server_port = 8080  # Default server port

            # Execute shutdown request inside container
            shutdown_result = DockerUtils.execute_command(
                container_id,
                ["curl", "-s", "--connect-timeout", "5", "--max-time",
                    "10", f"http://localhost:{server_port}/shutdown"]
            )
            print(f"🔄 Shutdown response: {shutdown_result.strip()}")

            # Wait for emissions file to be created (with timeout)
            print("⏳ Waiting for CodeCarbon to save emissions data...")
            max_wait_time = 30  # seconds
            emissions_file = "/output/energy/emissions.csv"

            # Wait for the file to be written
            for i in range(max_wait_time):
                try:
                    # Check if the file exists and has content
                    file_exists = DockerUtils.execute_command(
                        container_id,
                        ["bash", "-c",
                            f"test -f {emissions_file} && echo 'exists' || echo 'missing'"]
                    ).strip()

                    if file_exists == "exists":
                        # Check file size to ensure it has content
                        file_size = DockerUtils.execute_command(
                            container_id,
                            ["bash", "-c", f"stat -c %s {emissions_file}"]
                        ).strip()

                        # If file has some reasonable size, assume it's valid
                        if int(file_size) > 100:  # More than 100 bytes
                            print(
                                f"✅ Emissions file found with size: {file_size} bytes")
                            break

                    # Show directory content occasionally for debugging
                    if i % 5 == 0 or i == max_wait_time - 1:
                        dir_content = DockerUtils.execute_command(
                            container_id,
                            ["ls", "-la", "/output/energy"]
                        )
                        print(f"📁 Energy directory contents:\n{dir_content}")

                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ Error checking for emissions file: {e}")
                    time.sleep(1)

            # Copy emissions data from container to run directory
            try:
                container_emissions_path = "/output/energy/emissions.csv"
                emissions_path = run_dir / "emissions.csv"

                # Get emissions data
                emissions_content = DockerUtils.execute_command(
                    container_id,
                    ["cat", container_emissions_path]
                )

                # Just header or empty
                if not emissions_content or emissions_content.count('\n') <= 1:
                    print(f"❌ No emissions data found in container")
                    return False

                # Save emissions data
                with open(emissions_path, 'w') as f:
                    f.write(emissions_content)

                print(f"✅ Saved emissions data for run {run_num}")

                # Process energy data for this run
                energy_data = EnergyManager.parse_codecarbon_output(
                    emissions_path)
                framework = run_dir.parent.parent.parent.name
                language = run_dir.parent.parent.parent.parent.name

                energy_report = EnergyManager.generate_energy_report(
                    energy_data, framework, language)
                energy_path = run_dir / "energy.json"

                with open(energy_path, 'w') as f:
                    json.dump(energy_report, f, indent=2)

                print(f"✅ Processed energy data for run {run_num}")
                return True

            except Exception as e:
                print(f"❌ Error saving emissions data: {e}")
                return False

        except Exception as e:
            print(f"❌ Error in energy run data processing: {e}")
            return False

    @staticmethod
    def parse_codecarbon_output(csv_path):
        """Parse CodeCarbon CSV output into structured data"""
        try:
            import pandas as pd

            # Check if file exists
            if not os.path.exists(csv_path):
                print(f"❌ Emissions file does not exist: {csv_path}")
                print("❌ CodeCarbon failed to generate emissions data")
                sys.exit(1)

            # Check if file is empty
            if os.path.getsize(csv_path) == 0:
                print(f"❌ Emissions file is empty: {csv_path}")
                print("❌ CodeCarbon failed to write any data to emissions file")
                sys.exit(1)

            # Try to read the CSV file
            try:
                df = pd.read_csv(csv_path)
            except pd.errors.EmptyDataError:
                print(f"❌ No data in emissions file: {csv_path}")
                print("❌ CodeCarbon failed to write valid CSV data")
                sys.exit(1)

            # Check if there's any data beyond the header
            if len(df) == 0:
                print(f"❌ No energy measurements in file: {csv_path}")
                print("❌ CodeCarbon only wrote header row without measurements")
                sys.exit(1)

            # Get the last (most recent) entry
            last_entry = df.iloc[-1]

            # Get additional info from the file
            with open(csv_path, 'r') as f:
                lines = f.readlines()
                print(
                    f"ℹ️ Found {len(lines)-1} energy measurements in emissions file")
                if len(lines) > 1:
                    print(f"ℹ️ Last measurement: {lines[-1][:100]}")

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
            print(f"❌ Error processing CodeCarbon output: {e}")
            sys.exit(1)

    @staticmethod
    def generate_energy_report(energy_data, framework, language):
        """Generate a comprehensive energy report"""
        # Convert CO2 to mg if it's in kg (CodeCarbon uses kg)
        emissions_mg = energy_data.get(
            "emissions", 0) * 1000000  # kg to mg conversion

        # Format energy report
        return {
            "framework": framework,
            "language": language,
            "timestamp": energy_data.get("timestamp", None),
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
                "tracking_mode": energy_data.get("tracking_mode", "Unknown")
            }
        }

    @staticmethod
    def combine_energy_runs(output_dir, num_runs):
        """Combine and analyze multiple energy measurement runs"""
        runs_dir = output_dir / "runs"
        if not runs_dir.exists():
            print(f"❌ Runs directory not found: {runs_dir}")
            sys.exit(1)

        run_data = []

        # Collect data from each run
        for i in range(1, num_runs + 1):
            run_dir = runs_dir / f"run_{i}"
            energy_file = run_dir / "energy.json"

            if not energy_file.exists():
                print(f"❌ Energy file not found for run {i}: {energy_file}")
                sys.exit(1)

            try:
                with open(energy_file, 'r') as f:
                    data = json.load(f)
                    run_data.append(data)
            except Exception as e:
                print(f"❌ Error reading energy file for run {i}: {e}")
                sys.exit(1)

        if not run_data:
            print("❌ No valid run data found")
            sys.exit(1)

        # Calculate statistics
        energy_values = [r["energy"]["total_watt_hours"] for r in run_data]
        cpu_energy_values = [r["energy"]["cpu_watt_hours"] for r in run_data]
        ram_energy_values = [r["energy"]["ram_watt_hours"] for r in run_data]
        emissions_values = [r["emissions"]["mg_carbon"] for r in run_data]
        duration_values = [r["duration_seconds"] for r in run_data]

        # Create statistics report
        stats = {
            "runs": len(run_data),
            "framework": run_data[0]["framework"],
            "language": run_data[0]["language"],
            "timestamp": run_data[0]["timestamp"],
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
            }
        }

        # Save stats to file
        stats_file = output_dir / "energy_runs.json"
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)

        print(f"✅ Combined energy statistics saved to {stats_file}")

        # Print summary
        print("\n🔋 Energy Statistics Summary:")
        print(f"   - Runs: {stats['runs']}")
        print(
            f"   - Mean energy: {stats['statistics']['energy_wh']['mean']:.6f} Wh (±{stats['statistics']['energy_wh']['stddev']:.6f} Wh)")
        print(
            f"   - Mean CO2: {stats['statistics']['emissions_mgCO2e']['mean']:.2f} mgCO2e (±{stats['statistics']['emissions_mgCO2e']['stddev']:.2f} mgCO2e)")
        print(
            f"   - Mean duration: {stats['statistics']['duration_s']['mean']:.2f}s (±{stats['statistics']['duration_s']['stddev']:.2f}s)")

        return stats

    @staticmethod
    def process_energy_results(output_dir, framework, language):
        """Process energy results from CodeCarbon output"""
        # Check for CodeCarbon output in the energy directory
        energy_dir = output_dir / "energy"
        energy_dir.mkdir(exist_ok=True)
        emissions_csv = energy_dir / "emissions.csv"

        if not emissions_csv.exists():
            print(f"❌ CodeCarbon output not found: {emissions_csv}")
            sys.exit(1)

        # Parse CodeCarbon output
        energy_data = EnergyManager.parse_codecarbon_output(emissions_csv)

        # Generate energy report
        energy_report = EnergyManager.generate_energy_report(
            energy_data, framework, language)

        # Save energy report
        energy_json = energy_dir / "energy.json"
        with open(energy_json, 'w') as f:
            json.dump(energy_report, f, indent=2)

        # Print summary
        print("\n🔋 Energy Consumption Summary:")
        print(
            f"   - Total energy: {energy_report['energy']['total_watt_hours']:.6f} Wh")
        print(
            f"   - CPU energy: {energy_report['energy']['cpu_watt_hours']:.6f} Wh")
        print(
            f"   - RAM energy: {energy_report['energy']['ram_watt_hours']:.6f} Wh")
        print(
            f"   - CO2 emissions: {energy_report['emissions']['mg_carbon']:.2f} mgCO2e")
        print(
            f"   - Duration: {energy_report['duration_seconds']:.2f} seconds")

        return True
