"""
Profiling system for web frameworks
"""
import sys
import time
from pathlib import Path

from src.constants import MODE_ENERGY, MODE_QUICK
from src.docker.container_manager import ContainerManager
from src.docker.container_operations import ContainerOperations
from src.wrk_manager import WrkManager
from src.output_manager import save_report, summarize_profiling_results
from src.energy_manager import EnergyManager

class Profiler:
    """Profiling system for web frameworks"""
    
    @staticmethod
    def run(container_id, framework_config, config, output_dir, mode):
        """Run profiling tests based on mode"""
        print(f"🚀 Starting profiling in {mode} mode...")
        
        # Get tests from config
        tests = config.get("tests", [])
        
        # If tests are not directly in the config, filter them based on endpoints
        if not tests and "endpoints" in config:
            endpoints_config = config["endpoints"]
            # Implement endpoint filtering logic if needed
        
        if not tests:
            print("❌ No tests defined in configuration")
            sys.exit(1)
            
        # Run appropriate test mode
        if mode == MODE_ENERGY:
            success = Profiler._run_energy_tests(container_id, framework_config, config, output_dir, tests)
        elif mode == MODE_QUICK:
            success = Profiler._run_quick_tests(container_id, framework_config, config, output_dir, tests)
        else:
            success = Profiler._run_standard_tests(container_id, framework_config, config, output_dir, tests)
            
        if not success:
            print("❌ Profiling failed")
            sys.exit(1)
            
        # Generate summary report
        framework = output_dir.parent.name
        language = output_dir.parent.parent.name
        summarize_profiling_results(output_dir, framework, language)
        
        print("✅ Profiling completed successfully")
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
            print("❌ Framework configuration missing server port")
            sys.exit(1)
        
        container_name = ContainerOperations.get_container_hostname(container_id)
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
        ContainerManager.stop_container(container_id)
        
        return True
    
    @staticmethod
    def _run_standard_tests(container_id, framework_config, config, output_dir, tests):
        """Run standard profiling tests"""
        # Verify container_id is valid
        if not container_id:
            print("❌ Invalid container ID")
            sys.exit(1)
        
        # Get base URL for tests
        base_url = Profiler._prepare_test_url(container_id, framework_config)
        
        # Run each test
        for test in tests:
            # Verify test has required fields
            if "name" not in test or "endpoint" not in test:
                print(f"❌ Invalid test configuration: {test}")
                sys.exit(1)
                
            endpoint = test["endpoint"]
            test_url = f"{base_url}{endpoint}"
            script = test.get("script", f"{test['name']}.lua")
            
            print(f"\n📊 Testing: {test['name']} - {test.get('description', 'No description')}")
            
            success = WrkManager.run_test(
                test_url,
                script,
                config["wrk"]["duration"],
                config["wrk"]["max_concurrency"],
                config["mode"]
            )
            
            if not success:
                print(f"⚠️ Test failed for {test['name']}")
                
            # Recovery time between tests
            recovery_time = config.get("server", {}).get("recovery_time", 5)
            time.sleep(recovery_time)
        
        # Cleanup container
        return Profiler._cleanup_container(container_id, framework_config, output_dir)
    
    @staticmethod
    def _run_energy_tests(container_id, framework_config, config, output_dir, tests):
        """Run energy profiling tests"""
        # Implementation delegated to energy manager
        return EnergyManager.run_tests(
            container_id, 
            framework_config, 
            config, 
            output_dir, 
            tests
        )
    
    @staticmethod
    def _run_quick_tests(container_id, framework_config, config, output_dir, tests):
        """Run quick test - simplified for development"""
        if not tests:
            print("❌ No tests defined for quick mode")
            sys.exit(1)
            
        # Just run the first test
        test = tests[0]
        
        # Verify test has required fields
        if "name" not in test or "endpoint" not in test:
            print(f"❌ Invalid test configuration: {test}")
            sys.exit(1)
        
        # Get base URL for tests
        base_url = Profiler._prepare_test_url(container_id, framework_config)
        
        # Run quick test
        endpoint = test["endpoint"]
        test_url = f"{base_url}{endpoint}"
        script = test.get("script", f"{test['name']}.lua")
        
        print(f"📊 Testing: {test['name']} - {test.get('description', 'No description')}")
        
        success = WrkManager.run_test(
            test_url,
            script,
            config["wrk"]["duration"],
            config["wrk"]["max_concurrency"],
            "quick"
        )
        
        if not success:
            print(f"⚠️ Quick test failed for {test['name']}")
            sys.exit(1)
        
        # Cleanup container
        return Profiler._cleanup_container(container_id, framework_config, output_dir)
    