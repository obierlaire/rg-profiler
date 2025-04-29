"""
Profiling orchestration for RG Profiler
"""
from src.runners.profiler import run_profiling_tests

# This module now just delegates to the more detailed implementation in src/runners/profiler.py
# This maintains API compatibility while allowing for refactoring of the implementation details