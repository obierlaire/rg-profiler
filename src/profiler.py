"""
Profiling system for web frameworks
"""
import sys
import time
from pathlib import Path

from src.constants import MODE_ENERGY, MODE_PROFILE, MODE_QUICK, MODE_STANDARD
from src.docker.container_manager import ContainerManager
from src.docker.container_operations import ContainerOperations
from src.energy_manager import EnergyManager
from src.logger import logger
from src.output_manager import save_report, summarize_profiling_results
from src.wrk_manager import WrkManager

# Base run commands for different modes
MODE_RUN_COMMANDS = {
    # MODE_PROFILE: "scalene --json --outfile=/output/scalene/scalene.json  --profile-all --profile-only site-packages --reduced-profile /app/app.py",
    MODE_PROFILE: "scalene --json --outfile=/output/scalene/scalene.json  --profile-all --profile-only {framework} --reduced-profile /app/app.py",
    MODE_ENERGY: "python /app/codecarbon_wrapper.py python /app/app.py",
    MODE_STANDARD: "python /app/app.py",
    MODE_QUICK: "scalene --json --outfile=/output/scalene/scalene.json  --profile-all --profile-only {framework} --reduced-profile /app/app.py"
}


class Profiler:
    """Profiling system for web frameworks"""

    @staticmethod
    def get_tests_for_mode(config, mode):
        """
        Get list of tests to run for a specific mode

        Args:
            config: Configuration dictionary
            mode: Profiling mode (profile, energy, standard, quick)

        Returns:
            List of test configurations
        """
        # Get tests from config
        tests = config.get("tests", [])

        # If tests are not directly in the config, filter them based on endpoints
        if not tests and "endpoints" in config:
            endpoints_config = config["endpoints"]
            # Implement endpoint filtering logic if needed

        # For quick mode, only return the first test
        if mode == MODE_QUICK and tests:
            return [tests[0]]

        return tests

    @staticmethod
    def run(container_id, framework_config, config, output_dir, mode):
        """Run profiling tests based on mode"""
        logger.start(f"Starting profiling in {mode} mode")

        # Get tests for the specified mode
        tests = Profiler.get_tests_for_mode(config, mode)

        if not tests:
            logger.error("No tests defined in configuration")
            sys.exit(1)

        # Energy mode has a different workflow due to specialized measurement requirements
        if mode == MODE_ENERGY:
            success = EnergyManager.run_tests(
                container_id,
                framework_config,
                config,
                output_dir,
                tests
            )
        else:
            # Use common test running logic for all other modes
            success = Profiler._run_tests(
                container_id, framework_config, config, output_dir, tests, mode)

        if not success:
            logger.error("Profiling failed")
            sys.exit(1)

        # Generate summary report
        framework = output_dir.parent.name
        language = output_dir.parent.parent.name
        summarize_profiling_results(output_dir, framework, language)

        logger.success("Profiling completed successfully")
        return True

    @staticmethod
    def _prepare_test_url(container_id, framework_config):
        """
        Prepare base URL for testing from container hostname and port

        Args:
            container_id: Container ID
            framework_config: Framework configuration

        Returns:
            Base URL for testing
        """
        # Verify framework_config has required fields
        if "server" not in framework_config or "port" not in framework_config["server"]:
            logger.error("Framework configuration missing server port")
            sys.exit(1)

        container_name = ContainerOperations.get_container_hostname(
            container_id)
        server_port = framework_config["server"]["port"]
        return f"http://{container_name}:{server_port}"

    @staticmethod
    def _cleanup_container(container_id, framework_config, output_dir):
        """
        Perform container cleanup after testing

        Args:
            container_id: Container ID
            framework_config: Framework configuration
            output_dir: Output directory for logs

        Returns:
            True if cleanup was successful
        """
        # Shutdown framework server gracefully
        ContainerManager.shutdown_framework(container_id, framework_config)

        # Save container logs
        ContainerOperations.save_container_logs(container_id, output_dir)

        # Stop container
        ContainerManager.stop_container(container_id, framework_config)

        return True

    @staticmethod
    def _run_tests(container_id, framework_config, config, output_dir, tests, mode):
        """
        Run profiling tests with a unified implementation

        Args:
            container_id: Container ID
            framework_config: Framework configuration
            config: Test configuration
            output_dir: Output directory
            tests: List of tests to run
            mode: Profiling mode

        Returns:
            True if tests ran successfully
        """
        # Verify container_id is valid
        if not container_id:
            logger.error("Invalid container ID")
            sys.exit(1)

        # Get base URL for tests
        base_url = Profiler._prepare_test_url(container_id, framework_config)

        # Run each test
        for test in tests:
            # Verify test has required fields
            if "name" not in test or "endpoint" not in test:
                logger.error(f"Invalid test configuration: {test}")
                sys.exit(1)

            endpoint = test["endpoint"]
            test_url = f"{base_url}{endpoint}"
            script = test.get("script", f"{test['name']}.lua")

            logger.info(
                f"📊 Testing: {test['name']} - {test.get('description', 'No description')}")

            success = WrkManager.run_test(
                test_url,
                script,
                config["wrk"]["duration"],
                config["wrk"]["max_concurrency"],
                mode,
                config
            )

            # For quick mode, we exit immediately on failure, for other modes we just log a warning
            if not success:
                if mode == MODE_QUICK:
                    logger.error(f"Quick test failed for {test['name']}")
                    sys.exit(1)
                else:
                    logger.warning(f"Test failed for {test['name']}")

            # Recovery time between tests
            recovery_time = config.get("server", {}).get("recovery_time", 5)
            time.sleep(recovery_time)

        # Cleanup container
        return Profiler._cleanup_container(container_id, framework_config, output_dir)
