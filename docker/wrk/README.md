# WRK Docker Container

This directory contains the Dockerfile and related files for running WRK (HTTP benchmarking tool) in a Docker container as part of the RG Profiler system.

## Overview

The WRK Docker container provides several advantages:
- Consistent benchmarking environment across different systems
- Integrated with the Docker network for direct container-to-container communication
- Self-contained with all necessary Lua scripting capabilities

## Usage

The WRK container is automatically built and used by the RG Profiler system. However, you can also build and run it manually for testing:

```bash
# Build the image
docker build -t rg-profiler-wrk .

# Run a simple benchmark
docker run --rm rg-profiler-wrk -t1 -c10 -d10s http://example.com/

# Run with a Lua script
docker run --rm -v $(pwd)/scripts:/scripts rg-profiler-wrk -t1 -c10 -d10s -s /scripts/test.lua http://example.com/
```

## Scripts Directory

The `/scripts` directory in the container is designed to be mounted as a volume, allowing you to use your own Lua scripts for custom benchmarks. The system automatically mounts the appropriate scripts directory based on the selected profiling mode.

## Network Integration

When run by the RG Profiler system, the WRK container is connected to the same Docker network as the framework and database containers, allowing it to directly reference the framework container by name rather than using localhost.

This approach eliminates network-related issues and provides more accurate benchmarking results by measuring the direct container-to-container communication performance.

## Lua Script Requirements

Lua scripts should follow these guidelines:
- Use the `request()` function to format the HTTP request
- Optionally use the `response(status, headers, body)` function to process responses
- Use the `done(summary, latency, requests)` function to output results

## Example Lua Script

```lua
-- Basic WRK script for standard benchmarking

function request()
   return wrk.format("GET", wrk.path or "/")
end

function response(status, headers, body)
   -- Optional response handling
end

function done(summary, latency, requests)
   -- Print summary stats
   io.write("Requests: " .. requests.total)
   io.write(", Avg Latency: " .. string.format("%.2f", latency.mean / 1000) .. "ms")
   io.write(", Max Latency: " .. string.format("%.2f", latency.max / 1000) .. "ms\n")
end
```