"""
Container operations for RG Profiler

This module provides specific container operations like executing commands,
copying files, retrieving logs, and health checking containers.
"""
import sys
from pathlib import Path

import docker
from src.constants import DEFAULT_SERVER_PORT
from src.docker_utils import DockerUtils
from src.output_manager import save_container_logs
from src.logger import logger

class ContainerOperations:
    """
    Container operations for Docker containers
    
    This class provides higher-level container operations, building on
    the low-level Docker API provided by DockerUtils.
    """
    
    @staticmethod
    def execute_command(container_id, command, check_exit_code=True):
        """
        Execute a command inside a running container
        
        Args:
            container_id: ID or name of the container
            command: List of command and arguments to execute
            check_exit_code: Whether to check the exit code (default: True)
            
        Returns:
            Command output as string
            
        Raises:
            Exception: If command execution fails
        """
        try:
            container = DockerUtils.get_container(container_id)
            result = container.exec_run(command)
            
            if check_exit_code and result.exit_code != 0:
                logger.warning(f"Command returned non-zero exit code: {result.exit_code}")
                logger.warning(f"Command: {command}")
                
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
    def check_server_health(container_id, port=DEFAULT_SERVER_PORT, endpoint="/"):
        """
        Check if a web server in a container is healthy
        
        Args:
            container_id: ID or name of the container
            port: Server port
            endpoint: Endpoint to check
            
        Returns:
            True if server is responding, False otherwise
        """
        try:
            curl_cmd = f"curl -s --connect-timeout 1 --max-time 2 http://127.0.0.1:{port}{endpoint}"
            result = ContainerOperations.execute_command(
                container_id, ["sh", "-c", curl_cmd], check_exit_code=False
            )
            return len(result.strip()) > 0
        except Exception:
            return False
    
    @staticmethod
    def send_server_shutdown(container_id, port=DEFAULT_SERVER_PORT, timeout=10):
        """
        Send a shutdown signal to a server in a container
        
        Args:
            container_id: ID or name of the container
            port: Server port
            timeout: Shutdown timeout in seconds
            
        Returns:
            True if shutdown succeeded, False otherwise
        """
        try:
            logger.info("🛑 Sending shutdown signal to server...")
            curl_cmd = f"curl -s --connect-timeout 1 --max-time 2 http://127.0.0.1:{port}/shutdown"
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