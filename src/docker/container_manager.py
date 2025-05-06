"""
Container management for RG Profiler

This module handles the lifecycle of Docker containers for framework profiling,
including creation, startup, health checking, and graceful shutdown.
"""
import sys
import time
import logging
from pathlib import Path

import docker
from src.constants import DEFAULT_SERVER_PORT, DEFAULT_STARTUP_TIMEOUT, DOCKER_NETWORK_NAME
from src.docker_utils import DockerUtils
from src.docker.container_operations import ContainerOperations
from src.logger import logger


class ContainerManager:
    """
    Container lifecycle management for Docker containers
    
    This class handles the complete lifecycle of Docker containers including
    creation, startup, health checking, and graceful shutdown.
    """

    @staticmethod
    def create_container(image_name, output_dir, framework_config, mode, env_vars=None):
        """
        Create and configure a framework container
        
        Args:
            image_name: Docker image to run
            output_dir: Directory to mount for output
            framework_config: Framework configuration
            mode: Profiling mode
            env_vars: Additional environment variables
            
        Returns:
            Container name
            
        Raises:
            SystemExit: If container creation fails
        """
        # Use container prefix from config if available, otherwise use default
        container_prefix = framework_config.get("docker", {}).get("container_prefix", "rg-profiler")
        container_name = f"{container_prefix}-{image_name.split(':')[0]}"
        
        # Stop any existing container with the same name
        ContainerManager.stop_container_if_exists(container_name, framework_config)

        # Prepare mount point for output directory
        volumes = {
            str(output_dir.resolve()): {'bind': '/output', 'mode': 'rw'}
        }

        # Ensure database type is specified
        if "database" not in framework_config or "type" not in framework_config["database"]:
            logger.error(f"Database type not specified in framework configuration")
            sys.exit(1)

        # Prepare environment variables
        environment = ContainerManager._prepare_environment(framework_config, mode, env_vars)

        logger.info(f"⚙️ Container configured: {container_name}")
        return container_name, volumes, environment

    @staticmethod
    def _prepare_environment(framework_config, mode, env_vars=None):
        """
        Prepare environment variables for container
        
        Args:
            framework_config: Framework configuration
            mode: Profiling mode
            env_vars: Additional environment variables
            
        Returns:
            Dictionary of environment variables
        """
        # Base environment variables
        environment = {
            "PROFILING_MODE": mode,
            "DB_TYPE": framework_config["database"]["type"],
            "DB_HOST": f"rg-profiler-{framework_config['database']['type']}",
            "SERVER_PORT": str(framework_config.get("server", {}).get("port", DEFAULT_SERVER_PORT)),
            "PYTHONUNBUFFERED": "1"
        }

        # Add energy tracking configuration if in energy mode
        if mode == "energy":
            # Get tracking mode from framework config (default to "process")
            tracking_mode = "process"
            if "energy" in framework_config and "tracking_mode" in framework_config["energy"]:
                tracking_mode = framework_config["energy"]["tracking_mode"]
                
            environment.update({
                "CODECARBON_TRACKING_MODE": tracking_mode,
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
            
        return environment

    @staticmethod
    def run_container(image_name, output_dir, framework_config, mode, env_vars=None):
        """
        Create and run a framework container
        
        Args:
            image_name: Docker image to run
            output_dir: Directory to mount for output
            framework_config: Framework configuration
            mode: Profiling mode
            env_vars: Additional environment variables
            
        Returns:
            Container ID
            
        Raises:
            SystemExit: If container creation or startup fails
        """
        # Get network name from config if available, otherwise use default
        network_name = framework_config.get("docker", {}).get("network_name", DOCKER_NETWORK_NAME)
        
        # Ensure Docker network exists
        networks = DockerUtils.list_networks(names=[network_name])
        if not networks:
            DockerUtils.create_network(network_name)
            logger.success(f"Created Docker network: {network_name}")
        else:
            logger.success(f"Using existing network: {network_name}")
        
        # Configure container
        container_name, volumes, environment = ContainerManager.create_container(
            image_name, output_dir, framework_config, mode, env_vars
        )

        try:
            # Run the container
            logger.start(f"Starting container: {container_name}")
            
            # Log detailed configuration when in debug mode
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Container configuration:")
                logger.debug(f"  Image: {image_name}")
                logger.debug(f"  Network: {DOCKER_NETWORK_NAME}")
                logger.debug(f"  Volumes: {volumes}")
                logger.debug(f"  Environment variables:")
                for key, value in environment.items():
                    logger.debug(f"    {key}: {value}")
            
            container = DockerUtils.run_container(
                image_name,
                name=container_name,
                detach=True,
                network=network_name,
                volumes=volumes,
                environment=environment
            )

            logger.success(f"Started container {container_name} with ID: {container.id[:12]}")

            # Wait for container to be ready
            if ContainerManager.wait_for_container_ready(container.id, framework_config):
                return container.id
            else:
                ContainerManager.stop_container(container.id, framework_config)
                logger.error(f"Container failed to become ready")
                sys.exit(1)

        except Exception as e:
            logger.error(f"Failed to start container: {e}")
            sys.exit(1)

    @staticmethod
    def stop_container_if_exists(container_name, config=None):
        """
        Stop and remove a container if it exists
        
        Args:
            container_name: Name of the container
            config: Optional configuration dictionary
            
        Returns:
            True if container was stopped, False if it didn't exist
        """
        try:
            # Get stop timeout from config if available
            stop_timeout = 5  # Default value
            if config and "docker" in config and "stop_timeout" in config["docker"]:
                stop_timeout = config["docker"]["stop_timeout"]
            
            container = DockerUtils.get_container(container_name)
            logger.info(f"🛑 Stopping existing container: {container_name}")
            container.stop(timeout=stop_timeout)
            logger.info(f"🗑️ Removing container: {container_name}")
            container.remove()
            logger.success(f"Removed existing container: {container_name}")
            return True
        except docker.errors.NotFound:
            return False
        except Exception as e:
            logger.error(f"Error removing existing container: {e}")
            sys.exit(1)

    @staticmethod
    def stop_container(container_id_or_name, config=None):
        """
        Stop and remove a Docker container
        
        Args:
            container_id_or_name: Container ID or name
            config: Optional configuration dictionary
            
        Returns:
            True if container was stopped successfully
            
        Raises:
            SystemExit: If container stop fails
        """
        try:
            # Get stop timeout from config if available
            stop_timeout = 10  # Default value
            if config and "docker" in config and "stop_timeout" in config["docker"]:
                stop_timeout = config["docker"]["stop_timeout"]
                
            container = DockerUtils.get_container(container_id_or_name)
            logger.info(f"🛑 Stopping container: {container.name}")
            container.stop(timeout=stop_timeout)
            logger.info(f"🗑️ Removing container: {container.name}")
            container.remove()
            return True
        except docker.errors.NotFound:
            logger.info(f"Container {container_id_or_name} not found (already removed)")
            return True
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
            sys.exit(1)

    @staticmethod
    def wait_for_container_ready(container_id, framework_config, timeout=None):
        """
        Wait for the container to be ready to receive requests
        
        Args:
            container_id: Container ID
            framework_config: Framework configuration
            timeout: Maximum time to wait in seconds (optional, uses config or default)
            
        Returns:
            True if container is ready, False otherwise
        """
        server_port = framework_config.get("server", {}).get("port", DEFAULT_SERVER_PORT)
        
        # Get timeout from arguments, config, or use default
        if timeout is None:
            timeout = framework_config.get("docker", {}).get("health_check_timeout", DEFAULT_STARTUP_TIMEOUT)
        
        # Get health check interval from config or use default
        check_interval = framework_config.get("docker", {}).get("health_check_interval", 2)
        
        logger.info(f"⏳ Waiting for framework server to be ready (timeout: {timeout}s, interval: {check_interval}s)...")
        
        # Give the container a few seconds to start
        time.sleep(3)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if container is still running
            try:
                container = DockerUtils.get_container(container_id)
                if container.status != "running":
                    logger.error(f"Container stopped with status: {container.status}")
                    
                    # In debug mode, get container logs to help diagnose the issue
                    if logger.isEnabledFor(logging.DEBUG):
                        logs = container.logs().decode('utf-8', errors='replace')
                        logger.debug(f"Container logs:\n{logs}")
                    
                    return False
                
                # Check if server is responding
                if ContainerOperations.check_server_health(container_id, server_port, "/", framework_config):
                    logger.success(f"Server is ready")
                    return True
                
                # Wait before trying again
                logger.info(f"⏳ Waiting for server... ({int(time.time() - start_time)}/{timeout}s)")
                
                # In debug mode, show recent container logs
                if logger.isEnabledFor(logging.DEBUG):
                    try:
                        # Get only recent logs (tail)
                        logs = container.logs(tail=10).decode('utf-8', errors='replace')
                        if logs.strip():
                            logger.debug(f"Recent container logs:\n{logs}")
                    except Exception as log_error:
                        logger.debug(f"Could not fetch container logs: {log_error}")
                
                time.sleep(check_interval)
                
            except Exception as e:
                logger.warning(f"Error checking readiness: {e}")
                time.sleep(check_interval)
        
        logger.error("Timeout waiting for server to become ready")
        return False

    @staticmethod
    def shutdown_framework(container_id, framework_config):
        """
        Shutdown framework server using /shutdown endpoint
        
        Args:
            container_id: Container ID
            framework_config: Framework configuration
            
        Returns:
            True if server shut down gracefully, False otherwise
            
        Raises:
            SystemExit: If shutdown fails
        """
        # Ensure server port is specified
        if "server" not in framework_config or "port" not in framework_config["server"]:
            logger.error(f"Server port not specified in framework configuration")
            sys.exit(1)
            
        server_port = framework_config["server"]["port"]

        # Send shutdown signal to server
        ContainerOperations.send_server_shutdown(container_id, server_port, 10, framework_config)

        # Wait for container to stop
        try:
            for i in range(10):
                try:
                    container = DockerUtils.get_container(container_id)
                    if container.status != "running":
                        logger.success("Server shutdown gracefully")
                        return True
                except docker.errors.NotFound:
                    logger.success("Container no longer exists")
                    return True

                logger.info(f"⏳ Waiting for graceful shutdown... ({i+1}/10)")
                time.sleep(1)

            logger.warning("Container didn't shutdown gracefully, forcing stop")
            ContainerManager.stop_container(container_id, framework_config)
            return False

        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")
            ContainerManager.stop_container(container_id, framework_config)
            sys.exit(1)
