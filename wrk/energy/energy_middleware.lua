--[[
WRK script for middleware testing - energy mode
Uses a fixed, deterministic pattern for energy measurement
]]--

-- Tracking counters
local request_counter = 0
local responses = 0
local errors = 0

-- Fixed configuration for reproducible energy measurement
local config = {
  skip_security = "false",
  simulate_rate_limit = "false",
  transform_heavy = "true",
  transform_response = "true",
  add_headers = "header1,header2,header3",
  sleep_time = "0.01"  -- 10ms processing time
}

-- Request function - called for each request
function request()
  request_counter = request_counter + 1
  
  -- Build the URL with fixed query parameters
  local url = "/middleware-advanced?"
  local params = {}
  
  for k, v in pairs(config) do
    table.insert(params, k .. "=" .. v)
  end
  
  -- Combine parameters into URL
  url = url .. table.concat(params, "&")
  
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
  io.write("\n----- Middleware Energy Test Results -----\n")
  io.write("Requests: " .. requests.total .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  io.write("Configuration: transform_heavy=true, transform_response=true, with headers\n")
  io.write("This test measures middleware chain energy consumption with a fixed pattern\n")
end