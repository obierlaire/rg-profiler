"""
Energy visualization utilities for RG Profiler
"""
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def plot_energy_comparison(results_dir, frameworks=None, output_file=None):
    """
    Create comparative energy consumption visualizations for multiple frameworks
    
    Args:
        results_dir: Path to the results directory
        frameworks: List of framework names to include (or None for all)
        output_file: Path to save output image (or None to display)
        
    Returns:
        Path to saved plot or None
    """
    results_dir = Path(results_dir)
    
    if not results_dir.exists():
        print(f"❌ Results directory not found: {results_dir}")
        return None
    
    # Find all frameworks that have energy data
    framework_data = {}
    languages = [d for d in results_dir.iterdir() if d.is_dir()]
    
    for lang_dir in languages:
        framework_dirs = [d for d in lang_dir.iterdir() if d.is_dir()]
        
        for fw_dir in framework_dirs:
            fw_name = fw_dir.name
            
            # Skip if we're only looking at specific frameworks
            if frameworks and fw_name not in frameworks:
                continue
                
            # Find latest run for this framework
            run_dirs = sorted([d for d in fw_dir.iterdir() if d.is_dir()], reverse=True)
            if not run_dirs:
                continue
                
            latest_run = run_dirs[0]
            energy_file = latest_run / "energy_runs.json"
            
            if not energy_file.exists():
                # Try basic energy.json if not found
                energy_file = latest_run / "energy" / "energy.json"
                if not energy_file.exists():
                    continue
            
            # Load energy data
            try:
                with open(energy_file, 'r') as f:
                    data = json.load(f)
                
                # Store relevant metrics
                language = lang_dir.name
                framework_key = f"{language}/{fw_name}"
                
                if "statistics" in data:
                    # Multi-run data
                    framework_data[framework_key] = {
                        "energy_wh": data["statistics"]["energy_wh"]["mean"],
                        "energy_stddev": data["statistics"]["energy_wh"]["stddev"],
                        "emissions_mg": data["statistics"]["emissions_mgCO2e"]["mean"],
                        "emissions_stddev": data["statistics"]["emissions_mgCO2e"]["stddev"],
                        "runs": data["runs"],
                        "language": language
                    }
                else:
                    # Single run data
                    framework_data[framework_key] = {
                        "energy_wh": data["energy"]["total_watt_hours"],
                        "energy_stddev": 0,
                        "emissions_mg": data["emissions"]["mg_carbon"],
                        "emissions_stddev": 0,
                        "runs": 1,
                        "language": language
                    }
            
            except Exception as e:
                print(f"⚠️ Error processing {energy_file}: {e}")
    
    if not framework_data:
        print("❌ No energy data found for any frameworks")
        return None
    
    # Create comparative visualization
    return _create_energy_plot(framework_data, output_file)


def _create_energy_plot(framework_data, output_file=None):
    """
    Create energy consumption plot
    
    Args:
        framework_data: Dictionary of framework energy data
        output_file: Path to save output image (or None to display)
        
    Returns:
        Path to saved plot or None
    """
    # Extract values for plotting
    frameworks = list(framework_data.keys())
    energy_values = [framework_data[fw]["energy_wh"] for fw in frameworks]
    energy_errors = [framework_data[fw]["energy_stddev"] for fw in frameworks]
    emissions_values = [framework_data[fw]["emissions_mg"] for fw in frameworks]
    emissions_errors = [framework_data[fw]["emissions_stddev"] for fw in frameworks]
    
    # Sort frameworks by energy consumption
    sorted_indices = np.argsort(energy_values)
    frameworks = [frameworks[i] for i in sorted_indices]
    energy_values = [energy_values[i] for i in sorted_indices]
    energy_errors = [energy_errors[i] for i in sorted_indices]
    emissions_values = [emissions_values[i] for i in sorted_indices]
    emissions_errors = [emissions_errors[i] for i in sorted_indices]
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 8))
    
    # Energy consumption plot
    ax1.barh(frameworks, energy_values, xerr=energy_errors, alpha=0.7, color='blue')
    ax1.set_title('Energy Consumption (Watt-hours)')
    ax1.set_xlabel('Watt-hours (Wh)')
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    # Add values to bars
    for i, v in enumerate(energy_values):
        ax1.text(v + energy_errors[i] + max(energy_values) * 0.01, i, f"{v:.6f} Wh", 
                 va='center', fontsize=9)
    
    # Emissions plot
    ax2.barh(frameworks, emissions_values, xerr=emissions_errors, alpha=0.7, color='green')
    ax2.set_title('CO₂ Emissions (mg)')
    ax2.set_xlabel('Emissions (mgCO₂e)')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    # Add values to bars
    for i, v in enumerate(emissions_values):
        ax2.text(v + emissions_errors[i] + max(emissions_values) * 0.01, i, f"{v:.2f} mgCO₂e", 
                 va='center', fontsize=9)
    
    plt.tight_layout()
    plt.suptitle('Framework Energy Efficiency Comparison', fontsize=16, y=1.05)
    
    # Add subtitle with run info
    run_info = [f"{fw} ({framework_data[fw]['runs']} runs)" for fw in frameworks]
    plt.figtext(0.5, 0.01, f"Lower values are better. Error bars show standard deviation where available.", 
               ha='center', fontsize=10, style='italic')
    
    # Save or display the plot
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
        print(f"✅ Energy plot saved to {output_path}")
        plt.close(fig)
        return output_path
    else:
        plt.show()
        return None


def plot_energy_metrics(energy_runs_file, output_file=None):
    """
    Create detailed energy metrics visualization for a single framework
    
    Args:
        energy_runs_file: Path to energy_runs.json file
        output_file: Path to save output image (or None to display)
        
    Returns:
        Path to saved plot or None
    """
    energy_runs_file = Path(energy_runs_file)
    
    if not energy_runs_file.exists():
        print(f"❌ Energy runs file not found: {energy_runs_file}")
        return None
    
    try:
        with open(energy_runs_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading energy runs file: {e}")
        return None
    
    if "statistics" not in data or "individual_runs" not in data:
        print("❌ Energy runs file does not contain required data")
        return None
    
    # Extract statistics
    stats = data["statistics"]
    runs = data["runs"]
    framework = data["framework"]
    language = data["language"]
    
    # Create figure with multiple subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 1: Energy consumption across runs
    ax1 = axes[0, 0]
    run_labels = [f"Run {i+1}" for i in range(runs)]
    energy_values = stats["energy_wh"]["values"]
    ax1.bar(run_labels, energy_values, alpha=0.7, color='blue')
    ax1.axhline(y=stats["energy_wh"]["mean"], color='red', linestyle='--', 
               label=f'Mean: {stats["energy_wh"]["mean"]:.6f} Wh')
    ax1.fill_between(run_labels, 
                    stats["energy_wh"]["mean"] - stats["energy_wh"]["stddev"],
                    stats["energy_wh"]["mean"] + stats["energy_wh"]["stddev"],
                    alpha=0.2, color='red',
                    label=f'StdDev: ±{stats["energy_wh"]["stddev"]:.6f} Wh')
    ax1.set_title('Energy Consumption per Run')
    ax1.set_xlabel('Run')
    ax1.set_ylabel('Watt-hours (Wh)')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend()
    
    # Plot 2: Emissions across runs
    ax2 = axes[0, 1]
    emissions_values = stats["emissions_mgCO2e"]["values"]
    ax2.bar(run_labels, emissions_values, alpha=0.7, color='green')
    ax2.axhline(y=stats["emissions_mgCO2e"]["mean"], color='red', linestyle='--',
               label=f'Mean: {stats["emissions_mgCO2e"]["mean"]:.2f} mgCO₂e')
    ax2.fill_between(run_labels,
                    stats["emissions_mgCO2e"]["mean"] - stats["emissions_mgCO2e"]["stddev"],
                    stats["emissions_mgCO2e"]["mean"] + stats["emissions_mgCO2e"]["stddev"],
                    alpha=0.2, color='red',
                    label=f'StdDev: ±{stats["emissions_mgCO2e"]["stddev"]:.2f} mgCO₂e')
    ax2.set_title('CO₂ Emissions per Run')
    ax2.set_xlabel('Run')
    ax2.set_ylabel('Emissions (mgCO₂e)')
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.legend()
    
    # Plot 3: Duration across runs
    ax3 = axes[1, 0]
    duration_values = stats["duration_s"]["values"]
    ax3.bar(run_labels, duration_values, alpha=0.7, color='purple')
    ax3.axhline(y=stats["duration_s"]["mean"], color='red', linestyle='--',
               label=f'Mean: {stats["duration_s"]["mean"]:.2f}s')
    ax3.fill_between(run_labels,
                     stats["duration_s"]["mean"] - stats["duration_s"]["stddev"],
                     stats["duration_s"]["mean"] + stats["duration_s"]["stddev"],
                     alpha=0.2, color='red',
                     label=f'StdDev: ±{stats["duration_s"]["stddev"]:.2f}s')
    ax3.set_title('Test Duration per Run')
    ax3.set_xlabel('Run')
    ax3.set_ylabel('Duration (seconds)')
    ax3.grid(True, linestyle='--', alpha=0.7)
    ax3.legend()
    
    # Plot 4: Energy composition (if available)
    ax4 = axes[1, 1]
    try:
        cpu_energy = stats["cpu_energy_wh"]["mean"]
        ram_energy = stats["ram_energy_wh"]["mean"]
        other_energy = stats["energy_wh"]["mean"] - cpu_energy - ram_energy
        
        components = ['CPU', 'RAM', 'Other']
        values = [cpu_energy, ram_energy, other_energy]
        
        ax4.pie(values, labels=components, autopct='%1.1f%%', 
               startangle=90, colors=['#ff9999','#66b3ff','#99ff99'])
        ax4.axis('equal')
        ax4.set_title('Energy Consumption by Component')
    except KeyError:
        # If component data is not available, show test reliability metrics
        reliability_data = [
            stats["energy_wh"]["stddev"] / stats["energy_wh"]["mean"] * 100,  # CV for energy
            stats["emissions_mgCO2e"]["stddev"] / stats["emissions_mgCO2e"]["mean"] * 100,  # CV for emissions
            stats["duration_s"]["stddev"] / stats["duration_s"]["mean"] * 100  # CV for duration
        ]
        labels = ['Energy CV (%)', 'Emissions CV (%)', 'Duration CV (%)']
        
        ax4.bar(labels, reliability_data, alpha=0.7, color=['blue', 'green', 'purple'])
        ax4.set_title('Coefficient of Variation (Lower is Better)')
        ax4.set_ylabel('Coefficient of Variation (%)')
        ax4.grid(True, linestyle='--', alpha=0.7)
        
        # Add values to bars
        for i, v in enumerate(reliability_data):
            ax4.text(i, v + 0.5, f"{v:.2f}%", ha='center', fontsize=9)
    
    plt.tight_layout()
    plt.suptitle(f'Energy Metrics for {language}/{framework}', fontsize=16, y=1.02)
    
    # Save or display the plot
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
        print(f"✅ Energy metrics plot saved to {output_path}")
        plt.close(fig)
        return output_path
    else:
        plt.show()
        return None


def generate_energy_report(results_dir, output_dir=None, frameworks=None):
    """
    Generate comprehensive energy report with visualizations
    
    Args:
        results_dir: Path to results directory
        output_dir: Path to save output files (or None to use results_dir/reports)
        frameworks: List of framework names to include (or None for all)
        
    Returns:
        Path to output directory
    """
    results_dir = Path(results_dir)
    
    if not output_dir:
        output_dir = results_dir / "reports"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate comparison plot
    comparison_plot = plot_energy_comparison(
        results_dir,
        frameworks=frameworks,
        output_file=output_dir / "energy_comparison.png"
    )
    
    # Generate individual framework plots
    languages = [d for d in results_dir.iterdir() if d.is_dir()]
    for lang_dir in languages:
        framework_dirs = [d for d in lang_dir.iterdir() if d.is_dir()]
        
        for fw_dir in framework_dirs:
            fw_name = fw_dir.name
            
            # Skip if we're only looking at specific frameworks
            if frameworks and fw_name not in frameworks:
                continue
                
            # Find latest run for this framework
            run_dirs = sorted([d for d in fw_dir.iterdir() if d.is_dir()], reverse=True)
            if not run_dirs:
                continue
                
            latest_run = run_dirs[0]
            energy_runs_file = latest_run / "energy_runs.json"
            
            if energy_runs_file.exists():
                fw_output_file = output_dir / f"{lang_dir.name}_{fw_name}_energy.png"
                plot_energy_metrics(energy_runs_file, output_file=fw_output_file)
    
    # Generate HTML report
    html_report = output_dir / "energy_report.html"
    _generate_html_report(results_dir, html_report, frameworks)
    
    return output_dir


def _generate_html_report(results_dir, output_file, frameworks=None):
    """
    Generate HTML report with energy data and visualizations
    
    Args:
        results_dir: Path to results directory
        output_file: Path to save HTML report
        frameworks: List of framework names to include (or None for all)
        
    Returns:
        Path to HTML report
    """
    results_dir = Path(results_dir)
    output_file = Path(output_file)
    
    # Collect data from all frameworks
    framework_data = {}
    languages = [d for d in results_dir.iterdir() if d.is_dir()]
    
    for lang_dir in languages:
        framework_dirs = [d for d in lang_dir.iterdir() if d.is_dir()]
        
        for fw_dir in framework_dirs:
            fw_name = fw_dir.name
            
            # Skip if we're only looking at specific frameworks
            if frameworks and fw_name not in frameworks:
                continue
                
            # Find latest run for this framework
            run_dirs = sorted([d for d in fw_dir.iterdir() if d.is_dir()], reverse=True)
            if not run_dirs:
                continue
                
            latest_run = run_dirs[0]
            energy_file = latest_run / "energy_runs.json"
            
            if not energy_file.exists():
                # Try basic energy.json if not found
                energy_file = latest_run / "energy" / "energy.json"
                if not energy_file.exists():
                    continue
            
            # Load energy data
            try:
                with open(energy_file, 'r') as f:
                    data = json.load(f)
                
                # Store relevant metrics
                language = lang_dir.name
                framework_key = f"{language}/{fw_name}"
                
                if "statistics" in data:
                    # Multi-run data
                    framework_data[framework_key] = {
                        "energy_wh": data["statistics"]["energy_wh"]["mean"],
                        "energy_stddev": data["statistics"]["energy_wh"]["stddev"],
                        "emissions_mg": data["statistics"]["emissions_mgCO2e"]["mean"],
                        "emissions_stddev": data["statistics"]["emissions_mgCO2e"]["stddev"],
                        "duration_s": data["statistics"]["duration_s"]["mean"],
                        "duration_stddev": data["statistics"]["duration_s"]["stddev"],
                        "runs": data["runs"],
                        "language": language,
                        "framework": fw_name,
                        "timestamp": data.get("timestamp", "Unknown"),
                        "file_path": str(energy_file)
                    }
                else:
                    # Single run data
                    framework_data[framework_key] = {
                        "energy_wh": data["energy"]["total_watt_hours"],
                        "energy_stddev": 0,
                        "emissions_mg": data["emissions"]["mg_carbon"],
                        "emissions_stddev": 0,
                        "duration_s": data.get("duration_seconds", 0),
                        "duration_stddev": 0,
                        "runs": 1,
                        "language": language,
                        "framework": fw_name,
                        "timestamp": data.get("timestamp", "Unknown"),
                        "file_path": str(energy_file)
                    }
            
            except Exception as e:
                print(f"⚠️ Error processing {energy_file}: {e}")
    
    if not framework_data:
        print("❌ No energy data found for any frameworks")
        return None
    
    # Sort frameworks by energy consumption
    sorted_data = sorted(framework_data.items(), key=lambda x: x[1]["energy_wh"])
    
    # Generate HTML
    html_content = _generate_html_content(sorted_data, output_file.parent)
    
    # Write HTML file
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"✅ HTML energy report saved to {output_file}")
    return output_file


def _generate_html_content(sorted_data, report_dir):
    """
    Generate HTML content for energy report
    
    Args:
        sorted_data: List of (framework_key, data) tuples
        report_dir: Directory containing report files
        
    Returns:
        HTML content as string
    """
    # Get relative paths to images
    comparison_img = "energy_comparison.png"
    
    framework_imgs = {}
    for fw_key, data in sorted_data:
        language = data["language"]
        framework = data["framework"]
        img_path = f"{language}_{framework}_energy.png"
        if Path(report_dir / img_path).exists():
            framework_imgs[fw_key] = img_path
    
    # Generate HTML content
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RG Profiler Energy Report</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            h1, h2, h3 {
                color: #2c3e50;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                padding: 12px 15px;
                border: 1px solid #ddd;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
            tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            tr:hover {
                background-color: #f2f2f2;
            }
            .chart {
                margin: 30px 0;
                text-align: center;
            }
            .chart img {
                max-width: 100%;
                height: auto;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            .framework-section {
                margin: 40px 0;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
            .footer {
                margin-top: 50px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                text-align: center;
                font-size: 0.9em;
                color: #666;
            }
            .best {
                background-color: #d4edda;
            }
            .units {
                font-size: 0.8em;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>RG Profiler Energy Consumption Report</h1>
            <p>
                This report provides an analysis of energy consumption and CO<sub>2</sub> emissions 
                across different frameworks. The data is collected using CodeCarbon during benchmarking
                with RG Profiler's energy mode.
            </p>
            
            <h2>Framework Comparison</h2>
            <div class="chart">
                <img src="{comparison_img}" alt="Energy Comparison Chart">
            </div>
            
            <h2>Summary Table</h2>
            <table>
                <tr>
                    <th>Framework</th>
                    <th>Energy <span class="units">(Wh)</span></th>
                    <th>Emissions <span class="units">(mgCO<sub>2</sub>e)</span></th>
                    <th>Duration <span class="units">(s)</span></th>
                    <th>Runs</th>
                </tr>
    """.format(comparison_img=comparison_img)
    
    # Add rows for each framework
    for i, (fw_key, data) in enumerate(sorted_data):
        row_class = "best" if i == 0 else ""
        html += f"""
                <tr class="{row_class}">
                    <td>{fw_key}</td>
                    <td>{data['energy_wh']:.6f} ± {data['energy_stddev']:.6f}</td>
                    <td>{data['emissions_mg']:.2f} ± {data['emissions_stddev']:.2f}</td>
                    <td>{data['duration_s']:.2f} ± {data['duration_stddev']:.2f}</td>
                    <td>{data['runs']}</td>
                </tr>"""
    
    html += """
            </table>
            
            <h2>Individual Framework Analysis</h2>
    """
    
    # Add section for each framework
    for fw_key, data in sorted_data:
        html += f"""
            <div class="framework-section">
                <h3>{fw_key}</h3>
                <p>
                    <strong>Energy:</strong> {data['energy_wh']:.6f} Wh ± {data['energy_stddev']:.6f} Wh<br>
                    <strong>Emissions:</strong> {data['emissions_mg']:.2f} mgCO<sub>2</sub>e ± {data['emissions_stddev']:.2f} mgCO<sub>2</sub>e<br>
                    <strong>Duration:</strong> {data['duration_s']:.2f}s ± {data['duration_stddev']:.2f}s<br>
                    <strong>Runs:</strong> {data['runs']}<br>
                    <strong>Timestamp:</strong> {data['timestamp']}<br>
                </p>
        """
        
        # Add framework image if available
        if fw_key in framework_imgs:
            html += f"""
                <div class="chart">
                    <img src="{framework_imgs[fw_key]}" alt="{fw_key} Energy Analysis">
                </div>
            """
        
        html += """
            </div>
        """
    
    # Add footer
    html += """
            <div class="footer">
                <p>Generated with RG Profiler's Energy Mode</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def main():
    """Command line interface for energy visualization"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RG Profiler Energy Visualization Tool")
    parser.add_argument("--results-dir", required=True, help="Path to results directory")
    parser.add_argument("--output-dir", help="Path to output directory (default: results/reports)")
    parser.add_argument("--frameworks", nargs='+', help="Frameworks to include (default: all)")
    
    args = parser.parse_args()
    
    generate_energy_report(args.results_dir, args.output_dir, args.frameworks)


if __name__ == "__main__":
    main()
