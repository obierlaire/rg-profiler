"""
Template rendering utilities using Jinja2
"""
import sys
from pathlib import Path
import jinja2
from src.logger import logger

class TemplateManager:
    """Template rendering using Jinja2"""
    
    @staticmethod
    def render_template(template_path, context):
        """Render a template file with given context"""
        try:
            # Load template from file
            with open(template_path, 'r') as f:
                template_content = f.read()
                
            # Create template environment
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(template_path.parent),
                undefined=jinja2.StrictUndefined  # Fail on undefined variables
            )
            
            # Parse template string directly
            template = env.from_string(template_content)
            
            # Render template with context
            return template.render(**context)
            
        except jinja2.exceptions.UndefinedError as e:
            logger.error(f"Template error - missing variable: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error rendering template {template_path}: {e}")
            sys.exit(1)
