"""
Test type definitions for RG Profiler
"""

# Standard test types for regular benchmarking
STANDARD_TEST_TYPES = {
    "json": {
        "script": "json.lua",
        "accept": "application/json",
        "url": "/json"
    },
    "plaintext": {
        "script": "plaintext.lua",
        "accept": "text/plain",
        "url": "/plaintext"
    },
    "db": {
        "script": "db.lua",
        "accept": "application/json",
        "url": "/db"
    },
    "queries": {
        "script": "queries.lua",
        "accept": "application/json",
        "url": "/queries"
    },
    "complex_routing": {
        "script": "routing.lua",
        "accept": "application/json",
        "url": "/complex-routing/1/test/param1/param2"
    },
    "template_simple": {
        "script": "template_simple.lua",
        "accept": "text/html",
        "url": "/template-simple"
    },
    "template_complex": {
        "script": "template_complex.lua",
        "accept": "text/html",
        "url": "/template-complex"
    },
    "session_write": {
        "script": "session_write.lua",
        "accept": "application/json",
        "url": "/session-write"
    },
    "session_read": {
        "script": "session_read.lua",
        "accept": "application/json",
        "url": "/session-read"
    }
}

# Test types optimized for profiling
PROFILING_TEST_TYPES = {
    "json": {
        "script": "json.lua",
        "accept": "application/json",
        "url": "/json"
    },
    "plaintext": {
        "script": "plaintext.lua",
        "accept": "text/plain",
        "url": "/plaintext"
    },
    "db": {
        "script": "db.lua",
        "accept": "application/json",
        "url": "/db"
    },
    "complex_routing": {
        "script": "routing.lua",
        "accept": "application/json",
        "url": "/complex-routing/1/test/param1/param2"
    },
    "middleware": {
        "script": "middleware.lua",
        "accept": "application/json",
        "url": "/middleware"
    },
    "template_simple": {
        "script": "template_simple.lua",
        "accept": "text/html",
        "url": "/template-simple"
    },
    "template_complex": {
        "script": "template_complex.lua",
        "accept": "text/html",
        "url": "/template-complex"
    },
    "header_parsing": {
        "script": "headers.lua",
        "accept": "application/json",
        "url": "/header-parsing"
    },
    "regex_heavy": {
        "script": "regex.lua",
        "accept": "application/json",
        "url": "/regex-heavy"
    },
    "cpu_intensive": {
        "script": "cpu.lua",
        "accept": "application/json",
        "url": "/cpu-intensive"
    },
    "memory_heavy": {
        "script": "memory.lua",
        "accept": "application/json",
        "url": "/memory-heavy"
    }
}

# Test types optimized for energy measurement
ENERGY_TEST_TYPES = {
    "json": {
        "script": "energy_json.lua",
        "accept": "application/json",
        "url": "/json"
    },
    "plaintext": {
        "script": "energy_plaintext.lua",
        "accept": "text/plain",
        "url": "/plaintext"
    },
    "db": {
        "script": "energy_db.lua", 
        "accept": "application/json",
        "url": "/db"
    },
    "template_simple": {
        "script": "energy_template.lua",
        "accept": "text/html",
        "url": "/template-simple"
    },
    "cpu_intensive": {
        "script": "energy_cpu.lua",
        "accept": "application/json",
        "url": "/cpu-intensive"
    },
    "memory_heavy": {
        "script": "energy_memory.lua",
        "accept": "application/json",
        "url": "/memory-heavy"
    }
}

# Test types for quick mode - just a single JSON endpoint test
QUICK_TEST_TYPES = {
    "json": {
        "script": "basic.lua",
        "accept": "application/json",
        "url": "/json"
    }
}


def get_test_types(mode):
    """
    Get test types for the specified mode
    
    Args:
        mode: Profiling mode (standard, profile, energy, quick)
        
    Returns:
        Dictionary of test types
    """
    if mode == "profile":
        return PROFILING_TEST_TYPES
    elif mode == "energy":
        return ENERGY_TEST_TYPES
    elif mode == "quick":
        return QUICK_TEST_TYPES
    else:
        return STANDARD_TEST_TYPES
