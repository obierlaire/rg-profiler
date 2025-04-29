"""
Docker network management for RG Profiler
"""
import subprocess
from src.constants import DOCKER_NETWORK_NAME

def create_network():
    """
    Create Docker network for all components
    
    Returns:
        Boolean indicating success
    """
    try:
        # Check if network already exists
        result = subprocess.run(
            ["docker", "network", "inspect", DOCKER_NETWORK_NAME],
            capture_output=True,
            check=False
        )
        
        # If network doesn't exist, create it
        if result.returncode != 0:
            print(f"🌐 Creating Docker network: {DOCKER_NETWORK_NAME}")
            subprocess.run(
                ["docker", "network", "create", DOCKER_NETWORK_NAME],
                check=True
            )
            print(f"✅ Network {DOCKER_NETWORK_NAME} created")
        else:
            print(f"✅ Using existing network: {DOCKER_NETWORK_NAME}")
        
        return True
    
    except Exception as e:
        print(f"❌ Failed to create Docker network: {e}")
        return False


def remove_network():
    """
    Remove Docker network
    
    Returns:
        Boolean indicating success
    """
    try:
        # Check if network exists
        result = subprocess.run(
            ["docker", "network", "inspect", DOCKER_NETWORK_NAME],
            capture_output=True,
            check=False
        )
        
        # If network exists, remove it
        if result.returncode == 0:
            print(f"🧹 Removing Docker network: {DOCKER_NETWORK_NAME}")
            
            # Remove all containers from the network first
            containers = get_network_containers()
            for container in containers:
                disconnect_container(container)
            
            # Remove the network
            subprocess.run(
                ["docker", "network", "rm", DOCKER_NETWORK_NAME],
                check=False
            )
            print(f"✅ Network {DOCKER_NETWORK_NAME} removed")
        
        return True
    
    except Exception as e:
        print(f"⚠️ Error removing Docker network: {e}")
        return False


def connect_container(container_id):
    """
    Connect a container to the Docker network
    
    Args:
        container_id: Container ID or name
        
    Returns:
        Boolean indicating success
    """
    try:
        print(f"🔌 Connecting container {container_id} to network: {DOCKER_NETWORK_NAME}")
        subprocess.run(
            ["docker", "network", "connect", DOCKER_NETWORK_NAME, container_id],
            check=False
        )
        return True
    
    except Exception as e:
        print(f"⚠️ Error connecting container to network: {e}")
        return False


def disconnect_container(container_id):
    """
    Disconnect a container from the Docker network
    
    Args:
        container_id: Container ID or name
        
    Returns:
        Boolean indicating success
    """
    try:
        print(f"🔌 Disconnecting container {container_id} from network: {DOCKER_NETWORK_NAME}")
        subprocess.run(
            ["docker", "network", "disconnect", "--force", DOCKER_NETWORK_NAME, container_id],
            check=False
        )
        return True
    
    except Exception as e:
        print(f"⚠️ Error disconnecting container from network: {e}")
        return False


def get_network_containers():
    """
    Get a list of containers connected to the network
    
    Returns:
        List of container IDs
    """
    try:
        result = subprocess.run(
            ["docker", "network", "inspect", "--format", "{{range .Containers}}{{.Name}} {{end}}", DOCKER_NETWORK_NAME],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            containers = result.stdout.strip().split()
            return containers
        
        return []
    
    except Exception as e:
        print(f"⚠️ Error getting network containers: {e}")
        return []
