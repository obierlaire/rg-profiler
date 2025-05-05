"""
Container operations for RG Profiler

This module provides specific container operations like executing commands,
copying files, retrieving logs, and health checking containers.
"""
import sys
import logging
import time
from pathlib import Path
from functools import wraps

import docker
from src.constants import DEFAULT_SERVER_PORT
from src.docker_utils import DockerUtils
from src.output_manager import save_container_logs
from src.logger import logger

def with_retry(operation_name=None):
    """
    Decorator for retrying operations with backoff
    
    Args:
        operation_name: Optional name of the operation for logging
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get configuration from kwargs
            config = kwargs.get('config', {})
            
            # Extract retry settings from config
            max_attempts = 3  # Default max attempts
            backoff_factor = 2  # Default backoff factor
            initial_wait = 1  # Default initial wait
            
            if config and "retry" in config:
                retry_config = config["retry"]
                if "max_attempts" in retry_config:
                    max_attempts = retry_config["max_attempts"]
                if "backoff_factor" in retry_config:
                    backoff_factor = retry_config["backoff_factor"]
                if "initial_wait" in retry_config:
                    initial_wait = retry_config["initial_wait"]
                    
            op_name = operation_name or func.__name__
            
            # Execute with retry
            attempt = 1
            wait_time = initial_wait
            last_error = None
            
            while attempt <= max_attempts:
                try:
                    if attempt > 1:
                        logger.info(f"Retrying {op_name} (attempt {attempt}/{max_attempts}, waiting {wait_time}s)...")
                        time.sleep(wait_time)
                        wait_time *= backoff_factor  # Increase wait time for next attempt
                    
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(f"Attempt {attempt}/{max_attempts} of {op_name} failed: {e}")
                    attempt += 1
            
            # If we get here, all attempts failed
            logger.error(f"Operation {op_name} failed after {max_attempts} attempts")
            if last_error:
                raise last_error
                
        return wrapper
    return decorator

class ContainerOperations:
    """
    Container operations for Docker containers
    
    This class provides higher-level container operations, building on
    the low-level Docker API provided by DockerUtils.
    """
    
    @staticmethod
    @with_retry(operation_name="execute_command")
    def execute_command(container_id, command, check_exit_code=True, config=None):
        """
        Execute a command inside a running container
        
        Args:
            container_id: ID or name of the container
            command: List of command and arguments to execute
            check_exit_code: Whether to check the exit code (default: True)
            config: Optional configuration dictionary for retry settings
            
        Returns:
            Command output as string
            
        Raises:
            Exception: If command execution fails
        """
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Executing command in container {container_id}: {command}")
                
            container = DockerUtils.get_container(container_id)
            result = container.exec_run(command)
            
            if check_exit_code and result.exit_code != 0:
                logger.warning(f"Command returned non-zero exit code: {result.exit_code}")
                logger.warning(f"Command: {command}")
                if logger.isEnabledFor(logging.DEBUG):
                    output = result.output.decode('utf-8', errors='replace')
                    logger.debug(f"Command output:\n{output}")
            elif logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Command executed successfully with exit code: {result.exit_code}")
                
            return result.output.decode('utf-8')
        except docker.errors.NotFound:
            logger.error(f"Container {container_id} not found")
            raise
        except Exception as e:
            logger.error(f"Error executing command in container: {e}")
            raise
    
    @staticmethod
    def get_container_logs(container_id, tail=100):
        """
        Get logs from a container
        
        Args:
            container_id: ID or name of the container
            tail: Number of log lines to retrieve (default: 100)
            
        Returns:
            Container logs as string
            
        Raises:
            SystemExit: If log retrieval fails
        """
        try:
            container = DockerUtils.get_container(container_id)
            return container.logs(tail=tail).decode('utf-8')
        except docker.errors.NotFound:
            logger.error(f"Container {container_id} not found")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error getting container logs: {e}")
            sys.exit(1)
    
    @staticmethod
    def save_container_logs(container_id, output_dir, tail=None):
        """
        Save container logs to a file
        
        Args:
            container_id: ID or name of the container
            output_dir: Directory to save logs to
            tail: Number of log lines to retrieve (default: all logs)
            
        Returns:
            Path to the saved log file
        """
        logs = ContainerOperations.get_container_logs(container_id, tail)
        return save_container_logs(logs, output_dir)
    
    @staticmethod
    def get_container_hostname(container_id):
        """
        Get the hostname of a container
        
        Args:
            container_id: ID or name of the container
            
        Returns:
            Container hostname
        """
        hostname = ContainerOperations.execute_command(
            container_id, ["hostname"]
        ).strip()
        return hostname
    
    @staticmethod
    @with_retry(operation_name="check_server_health")
    def check_server_health(container_id, port=DEFAULT_SERVER_PORT, endpoint="/", config=None):
        """
        Check if a web server in a container is healthy
        
        Args:
            container_id: ID or name of the container
            port: Server port
            endpoint: Endpoint to check
            config: Optional configuration dictionary for HTTP settings and retry
            
        Returns:
            True if server is responding, False otherwise
        """
        try:
            # Use HTTP timeouts from config if available
            connect_timeout = 1  # Default connect timeout
            request_timeout = 2  # Default request timeout
            
            if config and "http" in config:
                if "connect_timeout" in config["http"]:
                    connect_timeout = config["http"]["connect_timeout"]
                if "request_timeout" in config["http"]:
                    request_timeout = config["http"]["request_timeout"]
            
            curl_cmd = f"curl -s --connect-timeout {connect_timeout} --max-time {request_timeout} http://127.0.0.1:{port}{endpoint}"
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Checking server health with: {curl_cmd}")
                
            result = ContainerOperations.execute_command(
                container_id, ["sh", "-c", curl_cmd], check_exit_code=False
            )
            
            is_healthy = len(result.strip()) > 0
            
            if logger.isEnabledFor(logging.DEBUG):
                status = "healthy" if is_healthy else "not responding"
                logger.debug(f"Server health check result: {status}")
                if is_healthy and logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Server response: {result[:200]}...")
                    
            return is_healthy
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Server health check failed with exception: {e}")
            return False
    
    @staticmethod
    def send_server_shutdown(container_id, port=DEFAULT_SERVER_PORT, timeout=10, config=None):
        """
        Send a shutdown signal to a server in a container
        
        Args:
            container_id: ID or name of the container
            port: Server port
            timeout: Shutdown timeout in seconds
            config: Optional configuration dictionary
            
        Returns:
            True if shutdown succeeded, False otherwise
        """
        try:
            # Use HTTP timeouts from config if available
            connect_timeout = 1  # Default connect timeout
            request_timeout = 2  # Default request timeout
            
            if config and "http" in config:
                if "connect_timeout" in config["http"]:
                    connect_timeout = config["http"]["connect_timeout"]
                if "request_timeout" in config["http"]:
                    request_timeout = config["http"]["request_timeout"]
            
            logger.info("🛑 Sending shutdown signal to server...")
            curl_cmd = f"curl -s --connect-timeout {connect_timeout} --max-time {request_timeout} http://127.0.0.1:{port}/shutdown"
            result = ContainerOperations.execute_command(
                container_id, ["sh", "-c", curl_cmd], check_exit_code=False
            )
            
            if result.strip():
                logger.info(f"🔄 Shutdown response: {result.strip()}")
            
            return True
        except Exception as e:
            logger.warning(f"Error sending shutdown signal: {e}")
            return False
    
    @staticmethod
    def copy_file_from_container(container_id, container_path, host_path):
        """
        Copy a file from a container to the host
        
        Args:
            container_id: ID or name of the container
            container_path: Path to the file in the container
            host_path: Path to save the file on the host
            
        Returns:
            True if file was copied successfully, False otherwise
        """
        try:
            container = DockerUtils.get_container(container_id)
            
            # Get file content
            bits, _ = container.get_archive(container_path)
            
            # Save to temporary tar file
            import tempfile
            import tarfile
            
            with tempfile.NamedTemporaryFile() as tmp:
                for chunk in bits:
                    tmp.write(chunk)
                tmp.flush()
                
                # Extract file from tar
                with tarfile.open(tmp.name) as tar:
                    filename = Path(container_path).name
                    member = tar.getmember(filename)
                    member.name = Path(host_path).name
                    tar.extract(member, path=Path(host_path).parent)
            
            return True
        except Exception as e:
            logger.error(f"Error copying file from container: {e}")
            return False
    
    @staticmethod
    def copy_file_to_container(container_id, host_path, container_path):
        """
        Copy a file from the host to a container
        
        Args:
            container_id: ID or name of the container
            host_path: Path to the file on the host
            container_path: Path to save the file in the container
            
        Returns:
            True if file was copied successfully, False otherwise
        """
        try:
            container = DockerUtils.get_container(container_id)
            
            # Create tar archive of the file
            import io
            import tarfile
            
            host_path = Path(host_path)
            filename = host_path.name
            
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                tar.add(host_path, arcname=filename)
            
            tar_stream.seek(0)
            
            # Copy to container
            container_dir = Path(container_path).parent
            ContainerOperations.execute_command(
                container_id, ["mkdir", "-p", str(container_dir)]
            )
            container.put_archive(container_dir, tar_stream)
            
            return True
        except Exception as e:
            logger.error(f"Error copying file to container: {e}")
            return False