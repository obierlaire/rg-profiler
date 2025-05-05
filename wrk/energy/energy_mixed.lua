--[[
WRK script for mixed workload testing - energy mode
Uses a fixed, deterministic pattern for energy measurement
]]--

-- Tracking counters
requests = 0
responses = 0
errors = 0

-- Fixed configuration for reproducible energy measurement
local config = {
  pattern = "balanced",  -- Even mix of different workload types
  intensity = 3,         -- Medium intensity (1-5 scale)
  fixed_seed = "true"    -- Use deterministic random seed for reproducibility
}

-- Request function - called for each request
function request()
  requests = requests + 1
  
  -- Build the URL with fixed query parameters
  local url = string.format(
    "/mixed-workload?pattern=%s&intensity=%d&fixed_seed=%s",
    config.pattern, config.intensity, config.fixed_seed
  )
  
  -- Set Accept header
  wrk.headers["Accept"] = "application/json"
  
  -- Return the formatted request
  return wrk.format("GET", url)
end

-- Response handler
function response(status, headers, body)
  -- Track responses
  responses = responses + 1
  
  -- Check for errors
  if status >= 400 then
    errors = errors + 1
  end
end

-- Done function - called at the end of the benchmark
function done(summary, latency, requests)
  io.write("\n----- Mixed Workload Energy Test Results -----\n")
  io.write("Requests: " .. requests .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  io.write("Configuration: pattern=balanced, intensity=3, fixed_seed=true\n")
  io.write("This test measures mixed workload energy consumption with a fixed pattern\n")
end