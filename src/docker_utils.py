"""
Docker utility functions using docker-py library

This module provides low-level Docker API interactions. It focuses solely on the direct
communication with the Docker daemon and provides basic operations without higher-level
container lifecycle management or specialized operations.
"""
import docker

class DockerUtils:
    """
    Docker utility functions using docker-py library
    
    This class provides low-level Docker API operations. It maintains a single
    client connection that can be reused across multiple operations.
    """
    
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
    
    @classmethod
    def get_container(cls, container_id_or_name):
        """
        Get a container by ID or name
        
        Args:
            container_id_or_name: Container ID or name
            
        Returns:
            Container object
            
        Raises:
            docker.errors.NotFound: If container not found
        """
        client = cls.get_client()
        return client.containers.get(container_id_or_name)
    
    @classmethod
    def get_image(cls, image_name):
        """
        Get an image by name or ID
        
        Args:
            image_name: Image name or ID
            
        Returns:
            Image object
            
        Raises:
            docker.errors.ImageNotFound: If image not found
        """
        client = cls.get_client()
        return client.images.get(image_name)
    
    @classmethod
    def list_images(cls):
        """
        List all available Docker images
        
        Returns:
            List of image objects
        """
        client = cls.get_client()
        return client.images.list()
    
    @classmethod
    def list_containers(cls, **filters):
        """
        List containers with optional filters
        
        Args:
            **filters: Filters to apply (e.g., all=True)
            
        Returns:
            List of container objects
        """
        client = cls.get_client()
        return client.containers.list(**filters)
    
    @classmethod
    def list_networks(cls, **filters):
        """
        List Docker networks with optional filters
        
        Args:
            **filters: Filters to apply (e.g., names=['my-network'])
            
        Returns:
            List of network objects
        """
        client = cls.get_client()
        return client.networks.list(**filters)
    
    @classmethod
    def create_network(cls, name, **kwargs):
        """
        Create a Docker network
        
        Args:
            name: Network name
            **kwargs: Additional network creation parameters
            
        Returns:
            Network object
        """
        client = cls.get_client()
        return client.networks.create(name, **kwargs)
    
    @classmethod
    def run_container(cls, image, **kwargs):
        """
        Run a Docker container
        
        Args:
            image: Image name or ID
            **kwargs: Additional container run parameters
            
        Returns:
            Container object
        """
        client = cls.get_client()
        return client.containers.run(image, **kwargs)
    
    @classmethod
    def build_image(cls, path, tag, **kwargs):
        """
        Build a Docker image
        
        Args:
            path: Path to build context
            tag: Image tag
            **kwargs: Additional image build parameters
            
        Returns:
            Built image and build logs
        """
        client = cls.get_client()
        return client.images.build(path=path, tag=tag, **kwargs)
