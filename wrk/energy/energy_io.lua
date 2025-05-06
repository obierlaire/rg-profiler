--[[
WRK script for I/O operations testing - energy mode
Uses a fixed, deterministic pattern for energy measurement
]]--

-- Tracking counters
local request_counter = 0
local responses = 0
local errors = 0

-- Fixed configuration for reproducible energy measurement
local config = {
  op = "combined",      -- Combined read and write operations
  buffer = 8192,        -- 8KB buffer size
  size = 1024,          -- 1MB file size
  iterations = 3,       -- Number of operations to perform
  sync = "buffered"     -- Use buffered I/O (not forced sync)
}

-- Request function - called for each request
function request()
  request_counter = request_counter + 1
  
  -- Build the URL with fixed query parameters
  local url = string.format(
    "/io-ops?op=%s&buffer=%d&size=%d&iterations=%d&sync=%s",
    config.op, config.buffer, config.size, config.iterations, config.sync
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
  io.write("\n----- I/O Operations Energy Test Results -----\n")
  io.write("Requests: " .. requests.total .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  io.write("Configuration: op=combined, buffer=8KB, size=1MB, iterations=3, sync=buffered\n")
  io.write("This test measures I/O operations energy consumption with a fixed pattern\n")
end