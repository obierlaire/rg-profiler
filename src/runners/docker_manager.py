"""
Docker management for RG Profiler
"""
import os
import subprocess
import tempfile
import time
from pathlib import Path

from src.constants import (
    CONTAINER_NAME_PREFIX,
    DATABASE_PORTS,
    DEFAULT_SERVER_PORT,
    DEFAULT_STARTUP_TIMEOUT,
    DOCKER_NETWORK_NAME,
    MODE_ENERGY,
    MODE_PROFILE,
    MODE_QUICK,
    MODE_STANDARD,
    PROJECT_ROOT,
)


def build_framework_image(framework_dir, image_name, db_type, mode=MODE_PROFILE):
    """
    Build Docker image for a framework

    Args:
        framework_dir: Path to the framework directory
        image_name: Name for the Docker image
        db_type: Database type (postgres, mysql, mongodb)
        mode: Profiling mode (profile, energy, standard, quick)

    Returns:
        Boolean indicating success
    """
    # Initialize temp directory variable
    temp_context_dir = None
    from src.docker_utils import check_image_exists

    # Check if Python base image exists
    base_image = f"{CONTAINER_NAME_PREFIX}-python-base"
    if not check_image_exists(base_image):
        print(f"❌ Required base image not found: {base_image}")
        print(f"Please run 'make python-base' to build the Python base image")
        return False

    # Check if database image exists for this db_type
    db_image = f"{CONTAINER_NAME_PREFIX}-{db_type}"
    if not check_image_exists(db_image):
        print(f"❌ Required database image not found: {db_image}")
        print(f"Please run 'make {db_type}' to build the database image")
        return False

    print(f"🔨 Building Docker image for framework: {framework_dir.name}")

    # Check if entrypoint script template exists
    entrypoint_template = PROJECT_ROOT / "templates" / "entrypoint.sh.template"
    if not entrypoint_template.exists():
        print(f"❌ Entrypoint template not found: {entrypoint_template}")
        return False

    # Create temporary entrypoint script from template
    try:
        # Based on db_type, determine run commands
        run_cmd = "python app.py"
        # Extract framework name from the directory path
        framework_name = framework_dir.name
        scalene_cmd = f"scalene --json --profile-all --profile-only {framework_name} --outfile=/output/scalene/scalene.json --reduced-profile app.py"
        print(f"Will run server with : {scalene_cmd}")

        # Read the template
        with open(entrypoint_template, 'r') as f:
            template_content = f.read()

        # Replace template variables based on mode
        if mode == MODE_ENERGY:
            # For energy mode, use python directly
            final_content = template_content.replace(
                "{{RUN_COMMAND}}", run_cmd)
        elif mode == MODE_STANDARD:
            # For standard mode, use scalene
            final_content = template_content.replace(
                "{{RUN_COMMAND}}", scalene_cmd)
        else:
            # Default to scalene for profiling
            final_content = template_content.replace(
                "{{RUN_COMMAND}}", scalene_cmd)

        # Create a temporary directory for build context
        temp_dir = tempfile.mkdtemp()

        # Write the processed template to a temporary file
        temp_entrypoint = Path(temp_dir) / "entrypoint.sh"
        with open(temp_entrypoint, 'w') as f:
            f.write(final_content)

        # Make executable
        import os
        os.chmod(temp_entrypoint, 0o755)
        print(f"✅ Created temporary entrypoint script from template")

        # Remember temp directory path to use in build context
        temp_context_dir = temp_dir
    except Exception as e:
        print(f"❌ Error creating entrypoint script: {e}")
        return False

    # Create a temporary Dockerfile using the template
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.dockerfile') as tmp:
        dockerfile_path = tmp.name

        # Use fixed Python version from constants
        from src.constants import DEFAULT_PYTHON_VERSION
        python_version = DEFAULT_PYTHON_VERSION

        # Get database port based on db_type
        db_port = DATABASE_PORTS.get(db_type, 5432)

        # Use Dockerfile template
        dockerfile_template = PROJECT_ROOT / "templates" / "Dockerfile.template"
        if not dockerfile_template.exists():
            print(f"❌ Dockerfile template not found: {dockerfile_template}")
            return False

        try:
            with open(dockerfile_template, 'r') as template_file:
                template_content = template_file.read()

            # Replace template variables
            dockerfile_content = template_content.replace(
                "{{PYTHON_VERSION}}", python_version)
            dockerfile_content = dockerfile_content.replace(
                "{{DB_TYPE}}", db_type)
            dockerfile_content = dockerfile_content.replace(
                "{{DB_PORT}}", str(db_port))

            tmp.write(dockerfile_content)
        except Exception as e:
            print(f"❌ Error creating Dockerfile from template: {e}")
            return False

    try:
        # Set up a command to copy the framework code to the temp directory
        # This ensures Docker can find both the framework code and our entrypoint
        import shutil
        for item in os.listdir(framework_dir):
            src = os.path.join(framework_dir, item)
            dst = os.path.join(temp_context_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        # Build the image using the temp directory as build context
        result = subprocess.run(
            ["docker", "build", "-t", image_name, "-f",
                dockerfile_path, temp_context_dir],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ Successfully built image: {image_name}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to build Docker image: {e}")
        print(f"Error output: {e.stderr}")
        return False

    finally:
        # Clean up the temporary files
        if os.path.exists(dockerfile_path):
            os.unlink(dockerfile_path)
        if temp_context_dir and os.path.exists(temp_context_dir):
            shutil.rmtree(temp_context_dir)

        # Clean up any existing entrypoint.sh from framework directory
        framework_entrypoint = framework_dir / "entrypoint.sh"
        if framework_entrypoint.exists():
            try:
                os.unlink(framework_entrypoint)
                print(f"Removed existing entrypoint.sh from framework directory")
            except Exception as e:
                print(
                    f"Warning: Could not remove framework entrypoint.sh: {e}")


def run_framework_container(image_name, output_dir, framework_config, mode=MODE_PROFILE):
    """
    Run the framework container with profiling enabled

    Args:
        image_name: Docker image name
        output_dir: Directory to mount for output files
        framework_config: Framework configuration
        mode: Profiling mode

    Returns:
        Container ID if successful, None otherwise
    """
    from src.runners.network_manager import connect_container, create_network

    # Ensure Docker network exists
    if not create_network():
        print("❌ Failed to create Docker network")
        return None

    container_name = f"{CONTAINER_NAME_PREFIX}-{image_name.split(':')[0]}"

    # Stop any existing container with the same name
    stop_container(container_name)

    # Create the output directory structure properly
    output_dir.mkdir(parents=True, exist_ok=True)
    scalene_dir = output_dir / "scalene"
    energy_dir = output_dir / "energy"
    runs_dir = output_dir / "runs"

    # Ensure all subdirectories exist
    scalene_dir.mkdir(exist_ok=True)
    energy_dir.mkdir(exist_ok=True)
    runs_dir.mkdir(exist_ok=True)

    # Determine database configuration
    db_type = framework_config.get("database", {}).get("type", "postgres")
    db_port = DATABASE_PORTS.get(db_type, 5432)

    # Get server port from framework config
    server_port = framework_config.get(
        "server", {}).get("port", DEFAULT_SERVER_PORT)

    # Prepare environment variables
    env_vars = [
        f"PROFILING_MODE={mode}",
        f"DB_TYPE={db_type}",
        f"DB_HOST=rg-profiler-{db_type}",
        f"DB_PORT={db_port}",
        f"SERVER_PORT={server_port}",
        f"PYTHONUNBUFFERED=1"
    ]

    # Configure profiling tools based on mode
    if mode == MODE_ENERGY:
        env_vars.extend([
            "CODECARBON_TRACKING_MODE=process",
            "CODECARBON_OUTPUT_DIR=/output/energy",
            "CODECARBON_OUTPUT_FILE=emissions.csv",
            "CODECARBON_SAVE_INTERVAL=15",
            "CODECARBON_LOG_LEVEL=debug",  # Add debug logging
            "USE_SCALENE=false"
        ])
    elif mode == MODE_QUICK:
        # For quick mode, use both energy and scalene profiling
        env_vars.extend([
            "CODECARBON_TRACKING_MODE=process",
            "CODECARBON_OUTPUT_DIR=/output/energy",
            "CODECARBON_OUTPUT_FILE=emissions.csv",
            "CODECARBON_SAVE_INTERVAL=1",
            "CODECARBON_LOG_LEVEL=debug",  # Add debug logging
            "SCALENE_OUTPUT=/output/scalene/scalene.json",
            "USE_SCALENE=true"
        ])
    else:
        # Default for profile or standard mode
        env_vars.extend([
            "SCALENE_OUTPUT=/output/scalene/scalene.json",
            "USE_SCALENE=true"
        ])

        # If standard mode, also configure energy monitoring
        if mode == MODE_STANDARD:
            env_vars.extend([
                "CODECARBON_TRACKING_MODE=process",
                "CODECARBON_OUTPUT_DIR=/output/energy",
                "CODECARBON_OUTPUT_FILE=emissions.csv",
                "CODECARBON_SAVE_INTERVAL=15",
                "CODECARBON_LOG_LEVEL=debug"  # Add debug logging
            ])

    # Create the run command
    cmd = [
        "docker", "run",
        "--name", container_name,
        # Skip --rm flag to keep container around for debugging if it fails
        "-d",  # Detached mode
        # No need to expose ports externally, containers communicate within the network
        "-v", f"{output_dir.resolve()}:/output",
        "--network", DOCKER_NETWORK_NAME,
    ]

    # Add environment variables
    for env_var in env_vars:
        cmd.extend(["-e", env_var])

    # Add image name
    cmd.append(image_name)

    try:
        # Run the container
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )

        container_id = result.stdout.strip()
        print(
            f"✅ Started container {container_name} with ID: {container_id[:12]}")

        # Make sure container is connected to the network
        connect_container(container_id)

        # Wait for container to be ready
        if wait_for_container_ready(container_id, framework_config):
            return container_id
        else:
            stop_container(container_id)
            return None

    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start container: {e}")
        print(f"Error output: {e.stderr}")
        return None


def wait_for_container_ready(container_id, framework_config, timeout=DEFAULT_STARTUP_TIMEOUT):
    """
    Wait for the container to be ready to receive requests

    Args:
        container_id: Docker container ID
        framework_config: Framework configuration
        timeout: Timeout in seconds

    Returns:
        Boolean indicating if container is ready
    """
    server_port = framework_config.get(
        "server", {}).get("port", DEFAULT_SERVER_PORT)

    print(f"⏳ Waiting for framework server to be ready...")

    # Check container status and health
    start_time = time.time()

    while time.time() - start_time < timeout:
        # Check if container exists and is running
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter",
                    f"id={container_id}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                check=True
            )

            if not result.stdout.strip():
                # Container isn't running, check if it exists but stopped
                exists_result = subprocess.run(
                    ["docker", "ps", "-a", "--filter",
                        f"id={container_id}", "--format", "{{.Status}}"],
                    capture_output=True,
                    text=True,
                    check=True
                )

                if exists_result.stdout.strip():
                    # Container exists but stopped, get its exit status and logs
                    exit_code_result = subprocess.run(
                        ["docker", "inspect", "--format",
                            "{{.State.ExitCode}}", container_id],
                        capture_output=True,
                        text=True,
                        check=False
                    )

                    exit_code = exit_code_result.stdout.strip()

                    print(
                        f"⚠️ Container exited with code {exit_code}, getting logs...")

                    # Get container logs to see why it failed
                    logs_result = subprocess.run(
                        ["docker", "logs", container_id],
                        capture_output=True,
                        text=True,
                        check=False
                    )

                    if logs_result.stdout:
                        print("===== Container Logs =====")
                        print(logs_result.stdout[:1000])
                        print("==========================")

                    print(f"❌ Container exited with code {exit_code}")
                    return False
                else:
                    print(f"⚠️ Container {container_id[:12]} no longer exists")
                    return False

            # Container is running, check service endpoints
            print(f"Container status: {result.stdout.strip()}")

            # Check endpoints from inside the container
            has_curl = subprocess.run(
                ["docker", "exec", container_id, "which", "curl"],
                capture_output=True,
                check=False
            ).returncode == 0

            if has_curl:
                # Try internal health checks
                for endpoint in ["/json", "/plaintext", "/", "/health"]:
                    try:
                        print(
                            f"🔍 Checking internal endpoint: http://localhost:{server_port}{endpoint}")

                        result = subprocess.run(
                            ["docker", "exec", container_id, "curl", "-s", "--fail",
                             "--max-time", "2", f"http://localhost:{server_port}{endpoint}"],
                            capture_output=True,
                            text=True
                        )

                        if result.returncode == 0:
                            print(f"✅ Server is ready at {endpoint}")
                            # Give server a moment to stabilize
                            time.sleep(2)
                            return True
                    except Exception as e:
                        pass
            else:
                # If curl is not available, try checking container logs for startup messages
                logs_result = subprocess.run(
                    ["docker", "logs", container_id],
                    capture_output=True,
                    text=True,
                    check=False
                )

                # Look for common "server ready" indicators in logs
                if "Server is ready" in logs_result.stdout or "Application started" in logs_result.stdout:
                    print("✅ Server appears to be ready based on logs")
                    time.sleep(2)
                    return True

            # Show logs every few seconds for debugging
            if int(time.time() - start_time) % 5 == 0:
                try:
                    print("===== Recent Container Logs =====")
                    subprocess.run(
                        ["docker", "logs", "--tail", "10", container_id],
                        check=False
                    )
                    print("================================")
                except Exception:
                    pass

            print(
                f"⏳ Waiting for server to be ready... ({int(time.time() - start_time)}/{timeout}s)")
            time.sleep(2)

        except Exception as e:
            print(f"⚠️ Error checking container: {e}")
            time.sleep(2)

    print("⚠️ Timeout waiting for server to be ready")

    # Get final logs before giving up
    try:
        print("===== Final Container Logs =====")
        subprocess.run(
            ["docker", "logs", container_id],
            check=False
        )
        print("===============================")
    except Exception:
        pass

    return False


def stop_container(container_id_or_name):
    """
    Stop and remove a Docker container

    Args:
        container_id_or_name: Container ID or name

    Returns:
        Boolean indicating success
    """
    try:
        # Check if container exists and is running
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={container_id_or_name}"],
            capture_output=True,
            text=True
        )

        if result.stdout.strip():
            print(f"🛑 Stopping container: {container_id_or_name}")
            subprocess.run(
                ["docker", "stop", container_id_or_name],
                capture_output=True,
                check=False
            )

        # Check if container exists (even if not running)
        result = subprocess.run(
            ["docker", "ps", "-a", "-q", "-f", f"name={container_id_or_name}"],
            capture_output=True,
            text=True
        )

        if result.stdout.strip():
            print(f"🗑️ Removing container: {container_id_or_name}")
            subprocess.run(
                ["docker", "rm", "-f", container_id_or_name],
                capture_output=True,
                check=False
            )

        return True

    except Exception as e:
        print(f"⚠️ Error stopping container: {e}")
        return False


def get_container_logs(container_id, tail=100):
    """
    Get logs from a container

    Args:
        container_id: Container ID
        tail: Number of log lines to retrieve

    Returns:
        Container logs as string
    """
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail), container_id],
            capture_output=True,
            text=True
        )
        return result.stdout
    except Exception as e:
        print(f"⚠️ Error getting container logs: {e}")
        return "Error retrieving logs"


def get_container_name_from_id(container_id):
    """
    Get the container name from its ID

    Args:
        container_id: Container ID

    Returns:
        Container name or None if not found
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.Name}}", container_id],
            capture_output=True,
            text=True,
            check=True
        )

        # Container names from Docker inspect have a leading slash, remove it
        name = result.stdout.strip()
        if name.startswith('/'):
            name = name[1:]

        if name:
            return name
        return None

    except Exception as e:
        print(f"⚠️ Error getting container name: {e}")
        return None


def execute_in_container(container_id, command):
    """
    Execute a command inside a running container

    Args:
        container_id: Container ID
        command: Command to execute (as list)

    Returns:
        Command output as string
    """
    try:
        result = subprocess.run(
            ["docker", "exec", container_id] + command,
            capture_output=True,
            text=True
        )
        return result.stdout
    except Exception as e:
        print(f"⚠️ Error executing command in container: {e}")
        return f"Error: {str(e)}"


def shutdown_framework_gracefully(container_id, framework_config):
    """
    Shutdown the framework server gracefully using the /shutdown endpoint

    Args:
        container_id: Container ID
        framework_config: Framework configuration

    Returns:
        Boolean indicating success
    """
    server_port = framework_config.get(
        "server", {}).get("port", DEFAULT_SERVER_PORT)
    shutdown_endpoint = "/shutdown"

    print(f"🛑 Gracefully shutting down framework via {shutdown_endpoint}...")

    try:
        # Check if curl is available in the container
        has_curl = subprocess.run(
            ["docker", "exec", container_id, "which", "curl"],
            capture_output=True,
            check=False
        ).returncode == 0

        if has_curl:
            # Try to hit the shutdown endpoint from within the container
            subprocess.run(
                ["docker", "exec", container_id, "curl", "-s", "--fail",
                 "--connect-timeout", "5", f"http://localhost:{server_port}{shutdown_endpoint}"],
                capture_output=True,
                text=True
            )
        else:
            # If curl is not available, try to send a signal to the container
            print("curl not available in container, using SIGTERM signal...")
            subprocess.run(
                ["docker", "kill", "--signal=SIGTERM", container_id],
                capture_output=True,
                check=False
            )

        # Give the server time to shutdown gracefully
        for i in range(10):
            # Check if container is still running
            result = subprocess.run(
                ["docker", "inspect",
                    "--format={{.State.Running}}", container_id],
                capture_output=True,
                text=True,
                check=False
            )

            if result.stdout.strip() != "true":
                print("✅ Framework shutdown gracefully")
                return True

            print(f"⏳ Waiting for graceful shutdown... ({i+1}/10)")
            time.sleep(1)

        # Force stop if it didn't shut down gracefully
        print("⚠️ Framework didn't shut down gracefully, forcing stop...")
        stop_container(container_id)
        return False

    except Exception as e:
        print(f"⚠️ Error during graceful shutdown: {e}")
        stop_container(container_id)
        return False
