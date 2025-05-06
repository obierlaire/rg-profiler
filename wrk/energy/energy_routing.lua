--[[
WRK script for complex routing testing - energy mode
Uses a fixed, deterministic pattern for energy measurement
]]--

-- Tracking counters
local request_counter = 0
local responses = 0
local errors = 0

-- Fixed configuration for reproducible energy measurement
local config = {
  path = "/routing/123/users/filter/active/sort/name",
  complexity = 3,  -- Route matching complexity (1-5)
  delay = 0       -- No additional processing delay
}

-- Request function - called for each request
function request()
  request_counter = request_counter + 1
  
  -- Build the URL with fixed query parameters
  local url = config.path .. "?complexity=" .. config.complexity
  
  if config.delay > 0 then
    url = url .. "&delay=" .. config.delay
  end
  
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
  io.write("\n----- Complex Routing Energy Test Results -----\n")
  io.write("Requests: " .. requests.total .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  io.write("Configuration: path=/routing/123/users/filter/active/sort/name, complexity=3\n")
  io.write("This test measures complex routing energy consumption with a fixed pattern\n")
end