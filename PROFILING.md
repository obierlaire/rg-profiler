# Framework Profiling Tests

This document describes the standardized profiling endpoints implemented across all frameworks in the rg-profiler system. Each endpoint is designed to test specific aspects of framework performance and resource usage to identify inefficiencies, optimize performance, and reduce resource consumption.

## Overview

The profiling tests aim to reveal:

- CPU usage inefficiencies
- Memory allocation patterns and leaks
- Energy consumption hotspots
- Framework overhead for common operations
- Performance bottlenecks in request processing
- Resource usage patterns

## Standard Profiling Endpoints

| Endpoint | Description | Purpose |
|----------|-------------|---------|
| `/json` | Simple JSON serialization | Tests the framework's JSON handling performance, serialization speed, and memory usage during JSON object creation |
| `/plaintext` | Plain text response | Measures baseline framework overhead with minimal processing - useful for identifying the framework's base request handling costs |
| `/db` | Single database query | Tests database connection pooling, query execution, result processing, and ORM overhead |
| `/queries?queries=n` | Multiple database queries | Evaluates framework performance with multiple DB operations, connection pooling efficiency, and result aggregation |
| `/complex-routing/:id/:name/:param1/:param2` | Complex URL routing and parameter parsing | Identifies inefficiencies in the framework's routing system, parameter extraction, validation, and type conversion |
| `/middleware` | Middleware/filter chain overhead | Measures performance impact of middleware stacks, especially with multiple components in the request/response processing pipeline |
| `/template-simple` | Simple template rendering | Tests basic template engine performance, variable substitution efficiency, and output generation |
| `/template-complex` | Complex template with loops, conditionals and includes | Evaluates advanced template rendering with loops, conditionals, includes, and filters to find inefficient rendering code |
| `/session-write` | Session creation and storage performance | Measures session creation overhead, serialization performance, and storage mechanism efficiency |
| `/session-read` | Session retrieval performance | Tests session retrieval, deserialization, and access patterns to identify inefficient lookup or caching |
| `/error-handling` | Error handling and exception processing | Evaluates exception handling overhead, error page generation, and logging performance |
| `/header-parsing` | Tests header parsing with many headers | Measures HTTP header parsing efficiency, especially with numerous or complex headers |
| `/regex-heavy` | Route or processing with complex regex | Identifies bottlenecks in regular expression processing, especially in routing or input validation |
| `/serialization` | Complex object serialization | Tests the framework's ability to efficiently serialize complex nested objects into various formats |
| `/deserialization` | Complex object deserialization from JSON | Evaluates JSON parsing and object mapping performance with complex data structures |
| `/cpu-intensive` | Compute-heavy operation to test CPU efficiency | Measures how efficiently the framework handles CPU-bound tasks and identifies threading/processing inefficiencies |
| `/memory-heavy` | Memory-intensive operation | Tests memory allocation patterns, garbage collection triggering, and performance under memory pressure |
| `/shutdown` | Special endpoint for graceful termination | Ensures proper resource cleanup and profiling data collection when stopping the server |

## Implementation Details

### `/json` Endpoint
- Returns a simple JSON response: `{"message": "Hello, World!"}`
- Tests the overhead of framework's JSON serialization
- Reveals inefficiencies in content-type negotiation and response formatting

### `/plaintext` Endpoint
- Returns a simple string: "Hello, World!"
- Provides a baseline for measuring framework overhead
- Identifies the minimum cost of request handling

### `/db` Endpoint
- Performs a single database query retrieving a random record
- Tests database connectivity, query execution, and result processing
- Reveals ORM overhead and serialization costs

### `/queries?queries=n` Endpoint
- Performs multiple database queries (parameter controlled)
- Tests connection pooling efficiency and query batching
- Reveals how the framework handles multiple similar operations

### `/complex-routing/:id/:name/:param1/:param2` Endpoint
- Tests complex URL pattern matching and parameter extraction
- Reveals inefficiencies in route resolution and parameter type conversion
- Helps identify regex or string parsing overhead in routing

### `/middleware` Endpoint
- Passes request through multiple middleware components
- Measures middleware chain traversal overhead
- Identifies inefficient context switching between middleware components

### `/template-simple` Endpoint
- Renders a simple template with a few variables
- Tests basic template engine initialization and rendering
- Identifies template compilation and caching inefficiencies

### `/template-complex` Endpoint
- Renders a complex template with loops, conditionals, includes, and filters
- Tests advanced template rendering features
- Reveals inefficiencies in complex rendering logic

### `/session-write` Endpoint
- Creates a new session and stores data in it
- Tests session initialization, serialization, and storage
- Identifies bottlenecks in session creation and persistence

### `/session-read` Endpoint
- Retrieves data from an existing session
- Tests session lookup, deserialization, and access
- Reveals inefficiencies in session retrieval mechanisms

### `/error-handling` Endpoint
- Deliberately triggers different types of errors
- Tests exception handling, error page generation, and logging
- Identifies overhead in error processing and recovery

### `/header-parsing` Endpoint
- Processes requests with numerous HTTP headers
- Tests header collection parsing and access efficiency
- Reveals string manipulation inefficiencies in header processing

### `/regex-heavy` Endpoint
- Applies complex regular expressions to input data
- Tests regex compilation, execution, and result processing
- Identifies inefficient regex patterns or implementations

### `/serialization` Endpoint
- Serializes complex nested objects into response formats
- Tests object traversal, property access, and format conversion
- Reveals inefficiencies in handling complex data structures

### `/deserialization` Endpoint
- Parses complex JSON input and creates object structures
- Tests JSON parsing, validation, and object mapping
- Identifies bottlenecks in input processing

### `/cpu-intensive` Endpoint
- Performs CPU-bound operations (calculations, sorting, etc.)
- Tests how the framework manages compute-intensive tasks
- Reveals threading inefficiencies or suboptimal task handling

### `/memory-heavy` Endpoint
- Allocates and processes large data structures
- Tests memory management, garbage collection, and resource handling
- Identifies memory leaks or inefficient allocation patterns

### `/shutdown` Endpoint
- Gracefully terminates the server
- Ensures profiling data is properly saved
- Tests resource cleanup and shutdown procedures

## Profiling Methodology

The rg-profiler system runs these endpoints with controlled load patterns and collects:
1. CPU profiling data via Scalene
2. Memory allocation patterns
3. Energy consumption metrics via CodeCarbon
4. Request latency and throughput statistics

The results help identify framework-specific inefficiencies, highlighting areas where optimization would yield the most significant improvements in performance and resource usage.