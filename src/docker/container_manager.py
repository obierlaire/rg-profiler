"""
Container management for RG Profiler
"""
import sys
import time
from pathlib import Path

import docker
from src.constants import DEFAULT_SERVER_PORT, DEFAULT_STARTUP_TIMEOUT, DOCKER_NETWORK_NAME
from src.docker_utils import DockerUtils


class ContainerManager:
    """Manages Docker containers for frameworks"""

    @staticmethod
    def run_container(image_name, output_dir, framework_config, mode, env_vars=None):
        """Run framework container with profiling enabled"""
        client = DockerUtils.get_client()
        network = DockerUtils.create_network()

        container_name = f"rg-profiler-{image_name.split(':')[0]}"

        # Stop any existing container with the same name
        try:
            existing = client.containers.get(container_name)
            existing.stop(timeout=5)
            existing.remove()
            print(f"✅ Removed existing container: {container_name}")
        except docker.errors.NotFound:
            pass
        except Exception as e:
            print(f"❌ Error removing existing container: {e}")
            sys.exit(1)

        # Prepare mount point for output directory
        volumes = {
            str(output_dir.resolve()): {'bind': '/output', 'mode': 'rw'}
        }

        # Ensure database type is specified
        if "database" not in framework_config or "type" not in framework_config["database"]:
            print(f"❌ Database type not specified in framework configuration")
            sys.exit(1)

        # Prepare environment variables
        environment = {
            "PROFILING_MODE": mode,
            "DB_TYPE": framework_config["database"]["type"],
            "DB_HOST": f"rg-profiler-{framework_config['database']['type']}",
            "SERVER_PORT": str(framework_config.get("server", {}).get("port", DEFAULT_SERVER_PORT)),
            "PYTHONUNBUFFERED": "1"
        }

        # Add energy tracking configuration if in energy mode
        if mode == "energy":
            environment.update({
                "CODECARBON_TRACKING_MODE": "machine",
                "CODECARBON_OUTPUT_DIR": "/output/energy",
                "CODECARBON_OUTPUT_FILE": "emissions.csv",
                "CODECARBON_SAVE_INTERVAL": "10",
                "CODECARBON_LOG_LEVEL": "info",
                "CODECARBON_PROJECT_NAME": "rg-profiler",
                "CODECARBON_EXPERIMENT_ID": "energy-measurement",
                "CODECARBON_SAVE_TO_FILE": "True",
                "ENERGY_MODE": "true"
            })

        # Add additional environment variables if provided
        if env_vars:
            environment.update(env_vars)

        try:
            # Run the container - no port exposure needed for internal network communication
            print(f"🚀 Starting container: {container_name}")
            container = client.containers.run(
                image_name,
                name=container_name,
                detach=True,
                network=DOCKER_NETWORK_NAME,
                volumes=volumes,
                environment=environment
            )

            print(f"✅ Started container {container_name} with ID: {container.id[:12]}")

            # Wait for container to be ready
            if ContainerManager.wait_for_container_ready(container.id, framework_config):
                return container.id
            else:
                DockerUtils.stop_container(container.id)
                print("❌ Container failed to become ready")
                sys.exit(1)

        except Exception as e:
            print(f"❌ Failed to start container: {e}")
            sys.exit(1)

    @staticmethod
    def wait_for_container_ready(container_id, framework_config, timeout=DEFAULT_STARTUP_TIMEOUT):
        """Wait for the container to be ready to receive requests"""
        client = DockerUtils.get_client()
        server_port = framework_config.get("server", {}).get("port", 8080)
        
        print(f"⏳ Waiting for framework server to be ready...")
        
        # Give the container a few seconds to start
        time.sleep(3)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if container is still running
            try:
                container = client.containers.get(container_id)
                if container.status != "running":
                    print(f"❌ Container stopped with status: {container.status}")
                    return False
                
                # Try HTTP request to check if server is responding
                curl_cmd = f"curl -s --connect-timeout 1 --max-time 2 http://127.0.0.1:{server_port}/"
                result = DockerUtils.execute_command(container_id, ["sh", "-c", curl_cmd], check_exit_code=False)
                
                if result.strip():
                    print(f"✅ Server is ready")
                    return True
                
                # Wait before trying again
                print(f"⏳ Waiting for server... ({int(time.time() - start_time)}/{timeout}s)")
                time.sleep(2)
                
            except Exception as e:
                print(f"⚠️ Error checking readiness: {e}")
                time.sleep(2)
        
        print("❌ Timeout waiting for server to become ready")
        return False

    @staticmethod
    def shutdown_framework(container_id, framework_config):
        """Shutdown framework server using /shutdown endpoint"""
        # Ensure server port is specified
        if "server" not in framework_config or "port" not in framework_config["server"]:
            print(f"❌ Server port not specified in framework configuration")
            sys.exit(1)
            
        server_port = framework_config["server"]["port"]

        print(f"🛑 Sending shutdown signal to framework...")

        # Execute curl in container to hit shutdown endpoint
        try:
            # Use 127.0.0.1 to refer to the container itself
            curl_cmd = f"curl -s --connect-timeout 1 --max-time 2 http://127.0.0.1:{server_port}/shutdown"
            print(f"🔍 Executing shutdown command: {curl_cmd}")
            
            result = DockerUtils.execute_command(container_id, ["sh", "-c", curl_cmd], check_exit_code=False)
            if result.strip():
                print(f"🔄 Shutdown response: {result.strip()}")

            # Wait for container to stop
            client = DockerUtils.get_client()
            for i in range(10):
                try:
                    container = client.containers.get(container_id)
                    if container.status != "running":
                        print("✅ Server shutdown gracefully")
                        return True
                except docker.errors.NotFound:
                    print("✅ Container no longer exists")
                    return True

                print(f"⏳ Waiting for graceful shutdown... ({i+1}/10)")
                time.sleep(1)

            print("⚠️ Container didn't shutdown gracefully, forcing stop")
            DockerUtils.stop_container(container_id)
            return False

        except Exception as e:
            print(f"❌ Error during graceful shutdown: {e}")
            DockerUtils.stop_container(container_id)
            sys.exit(1)
