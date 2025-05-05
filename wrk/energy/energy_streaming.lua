--[[
WRK script for streaming response testing - energy mode
Uses a fixed, deterministic pattern for energy measurement
]]--

-- Tracking counters
requests = 0
responses = 0
errors = 0

-- Fixed configuration for reproducible energy measurement
local config = {
  mode = "json",
  size = 2000,    -- 2MB
  chunk_size = 64, -- 64KB chunks
  delay = 0       -- No delay between chunks
}

-- Request function - called for each request
function request()
  requests = requests + 1
  
  -- Build the URL with fixed query parameters
  local url = string.format(
    "/streaming?mode=%s&size=%d&chunk_size=%d&delay=%.1f",
    config.mode, config.size, config.chunk_size, config.delay
  )
  
  -- Set appropriate Accept header
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
  io.write("\n----- Streaming Energy Test Results -----\n")
  io.write("Requests: " .. requests .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  io.write("Configuration: mode=json, size=2000KB, chunk_size=64KB, no delay\n")
  io.write("This test measures streaming response energy consumption with a fixed pattern\n")
end