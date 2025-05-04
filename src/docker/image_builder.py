"""
Docker image building utilities for RG Profiler

This module handles building Docker images for framework containers.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path
import docker

from src.constants import (
    CONTAINER_NAME_PREFIX,
    DATABASE_PORTS,
    DEFAULT_PYTHON_VERSION,
    MODE_ENERGY,
    MODE_PROFILE,
    PROJECT_ROOT,
)
from src.docker_utils import DockerUtils
from src.template_manager import TemplateManager


class ImageBuilder:
    """
    Docker image builder for frameworks
    
    This class handles building Docker images for framework containers.
    """

    @staticmethod
    def check_image_exists(image_name):
        """
        Check if a Docker image exists
        
        Args:
            image_name: Name of the image to check
            
        Returns:
            True if the image exists, False otherwise
        """
        try:
            DockerUtils.get_image(image_name)
            return True
        except docker.errors.ImageNotFound:
            return False
        except Exception:
            return False

    @staticmethod
    def build_framework_image(framework_dir, image_name, db_type, mode):
        """
        Build Docker image for a framework
        
        Args:
            framework_dir: Directory containing framework files
            image_name: Name for the built image
            db_type: Database type to use
            mode: Profiling mode
            
        Returns:
            True if the image was built successfully
            
        Raises:
            SystemExit: If image building fails
        """
        # Check required base images
        base_image = f"{CONTAINER_NAME_PREFIX}-python-base"
        db_image = f"{CONTAINER_NAME_PREFIX}-{db_type}"

        if not ImageBuilder.check_image_exists(base_image):
            print(f"❌ Required base image not found: {base_image}")
            print(f"Please run 'make python-base' to build the Python base image")
            sys.exit(1)

        if not ImageBuilder.check_image_exists(db_image):
            print(f"❌ Required database image not found: {db_image}")
            print(f"Please run 'make {db_type}' to build the database image")
            sys.exit(1)

        print(f"🔨 Building Docker image for framework: {framework_dir.name}")

        # Check templates exist
        dockerfile_template = PROJECT_ROOT / "templates" / "Dockerfile.template"

        if not dockerfile_template.exists():
            print(f"❌ Dockerfile template not found: {dockerfile_template}")
            sys.exit(1)

        # Check additional templates for energy mode
        if mode == MODE_ENERGY:
            wrapper_template = PROJECT_ROOT / "templates" / "codecarbon_wrapper.py.template"
            if not wrapper_template.exists():
                print(
                    f"❌ CodeCarbon wrapper template not found: {wrapper_template}")
                sys.exit(1)

        # Check entrypoint script template
        entrypoint_template = PROJECT_ROOT / "templates" / "entrypoint.sh.template"
        if not entrypoint_template.exists():
            print(
                f"❌ Entrypoint script template not found: {entrypoint_template}")
            sys.exit(1)

        # Verify database port exists
        if db_type not in DATABASE_PORTS:
            print(f"❌ Unknown database type: {db_type}")
            sys.exit(1)

        db_port = DATABASE_PORTS[db_type]

        # Create build context in temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Dockerfile
            dockerfile_path = Path(temp_dir) / "Dockerfile"

            # Prepare Dockerfile context
            dockerfile_context = {
                "PYTHON_VERSION": DEFAULT_PYTHON_VERSION,
                "DB_TYPE": db_type,
                "DB_PORT": str(db_port),
                # Add empty string as default for ENERGY_COPY_INSTRUCTIONS
                "ENERGY_COPY_INSTRUCTIONS": ""
            }

            # Add energy-specific instructions if in energy mode
            if mode == MODE_ENERGY:
                dockerfile_context["ENERGY_COPY_INSTRUCTIONS"] = """COPY codecarbon_wrapper.py /app/codecarbon_wrapper.py
RUN chmod +x /app/codecarbon_wrapper.py"""

            # Render Dockerfile template
            dockerfile_content = TemplateManager.render_template(
                dockerfile_template, dockerfile_context)

            # Write Dockerfile
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)

            # If in energy mode, copy the CodeCarbon wrapper script
            if mode == MODE_ENERGY:
                wrapper_path = Path(temp_dir) / "codecarbon_wrapper.py"
                shutil.copy2(wrapper_template, wrapper_path)
                os.chmod(wrapper_path, 0o755)

                # Prepare RUN_COMMAND for energy mode
                run_command = "python /app/codecarbon_wrapper.py python /app/app.py"
            elif mode == MODE_PROFILE:
                # For profile mode, use Scalene to profile the application
                # Set up Scalene with parameters from profile_config.yaml (handled automatically)
                run_command = "scalene --json --outfile=/output/scalene/scalene.json --profile-all --reduced-profile /app/app.py"
            else:
                # Default run command for other modes (can be expanded later)
                run_command = "python /app/app.py"

            # Render and copy entrypoint.sh template
            entrypoint_path = Path(temp_dir) / "entrypoint.sh"
            entrypoint_context = {"RUN_COMMAND": run_command}
            entrypoint_content = TemplateManager.render_template(
                entrypoint_template, entrypoint_context)

            # Write entrypoint.sh
            with open(entrypoint_path, 'w') as f:
                f.write(entrypoint_content)
            os.chmod(entrypoint_path, 0o755)  # Make executable

            # Copy framework files
            for item in os.listdir(framework_dir):
                src = os.path.join(framework_dir, item)
                dst = os.path.join(temp_dir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

            # Build the image
            try:
                print(f"🔨 Building image: {image_name}")

                # Use docker-py's API to build the image
                image, logs = DockerUtils.build_image(
                    path=temp_dir,
                    tag=image_name,
                    dockerfile=str(dockerfile_path.relative_to(temp_dir)),
                    rm=True
                )

                print(f"✅ Successfully built image: {image_name}")
                return True

            except Exception as e:
                print(f"❌ Failed to build Docker image: {e}")
                sys.exit(1)
