"""
Docker utility functions using docker-py library
"""
import sys
import docker

from src.constants import (
    CONTAINER_NAME_PREFIX,
    DOCKER_NETWORK_NAME
)

class DockerUtils:
    """Docker utility functions using docker-py library"""
    
    # Class-level client for reuse
    _client = None
    
    @classmethod
    def get_client(cls):
        """Get Docker client, creating one if needed"""
        if cls._client is None:
            try:
                cls._client = docker.from_env()
            except Exception as e:
                print(f"❌ Failed to connect to Docker: {e}")
                raise
        return cls._client
    
    @staticmethod
    def check_image_exists(image_name):
        """Check if Docker image exists"""
        client = DockerUtils.get_client()
        try:
            client.images.get(image_name)
            return True
        except docker.errors.ImageNotFound:
            return False
        except Exception:
            # Let caller handle the exception
            return False
    
    @staticmethod
    def check_required_images():
        """Check if all required Docker images exist"""
        required_images = [
            f"{CONTAINER_NAME_PREFIX}-python-base",
            f"{CONTAINER_NAME_PREFIX}-wrk",
            f"{CONTAINER_NAME_PREFIX}-postgres",
            f"{CONTAINER_NAME_PREFIX}-mysql",
            f"{CONTAINER_NAME_PREFIX}-mongodb"
        ]
        
        missing_images = []
        client = DockerUtils.get_client()
        
        # Get all existing images in one call
        existing_images = [img.tags for img in client.images.list() if img.tags]
        existing_image_tags = [tag for tags in existing_images for tag in tags]
        
        for image in required_images:
            if not any(image in tag for tag in existing_image_tags):
                missing_images.append(image)
        
        if missing_images:
            print("❌ Required Docker images are missing:")
            for image in missing_images:
                print(f"  - {image}")
            print("\nPlease run the following commands to build the required images:")
            print("  make all              # Build all required images")
            print("  make start-databases  # Start database containers")
            sys.exit(1)
        
        return True
    
    @staticmethod
    def create_network():
        """Create Docker network"""
        client = DockerUtils.get_client()
        try:
            # Check if network already exists
            networks = client.networks.list(names=[DOCKER_NETWORK_NAME])
            if networks:
                print(f"✅ Using existing network: {DOCKER_NETWORK_NAME}")
                return networks[0]
            
            # Create network
            print(f"🌐 Creating Docker network: {DOCKER_NETWORK_NAME}")
            network = client.networks.create(DOCKER_NETWORK_NAME)
            print(f"✅ Network {DOCKER_NETWORK_NAME} created")
            return network
            
        except Exception as e:
            print(f"❌ Failed to create Docker network: {e}")
            sys.exit(1)
    
    @staticmethod
    def stop_container(container_id_or_name):
        """Stop and remove a Docker container"""
        client = DockerUtils.get_client()
        try:
            container = client.containers.get(container_id_or_name)
            print(f"🛑 Stopping container: {container.name}")
            container.stop(timeout=10)
            print(f"🗑️ Removing container: {container.name}")
            container.remove()
            return True
        except docker.errors.NotFound:
            print(f"Container {container_id_or_name} not found (already removed)")
            return True
        except Exception as e:
            print(f"❌ Error stopping container: {e}")
            sys.exit(1)
    
    @staticmethod
    def get_container_logs(container_id, tail=100):
        """Get logs from a container"""
        client = DockerUtils.get_client()
        try:
            container = client.containers.get(container_id)
            return container.logs(tail=tail).decode('utf-8')
        except docker.errors.NotFound:
            print(f"❌ Container {container_id} not found")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error getting container logs: {e}")
            sys.exit(1)
    
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
        """
        client = DockerUtils.get_client()
        try:
            container = client.containers.get(container_id)
            result = container.exec_run(command)
            
            if check_exit_code and result.exit_code != 0:
                print(f"⚠️ Command returned non-zero exit code: {result.exit_code}")
                print(f"Command: {command}")
                
            return result.output.decode('utf-8')
        except docker.errors.NotFound:
            print(f"❌ Container {container_id} not found")
            raise
        except Exception as e:
            print(f"❌ Error executing command in container: {e}")
            raise
