--[[
WRK script for error handling testing - energy mode
Uses a fixed, deterministic pattern for energy measurement
]]--

-- Tracking counters
requests = 0
responses = 0
errors = 0

-- Fixed configuration for reproducible energy measurement
local config = {
  type = "validation",  -- Validation errors for repeatable behavior
  code = 400,          -- HTTP status code
  recovery = 5,        -- 5ms recovery time
  params = "name=a&age=xyz&email=invalidemail"  -- Invalid parameters for validation error
}

-- Request function - called for each request
function request()
  requests = requests + 1
  
  -- Build the URL with fixed query parameters
  local url = string.format(
    "/errors?type=%s&code=%d&recovery=%d&%s",
    config.type, config.code, config.recovery, config.params
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
  
  -- Check for errors (expected in this test)
  if status >= 400 then
    errors = errors + 1
  end
end

-- Done function - called at the end of the benchmark
function done(summary, latency, requests)
  io.write("\n----- Error Handling Energy Test Results -----\n")
  io.write("Requests: " .. requests .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  io.write("Configuration: type=validation, code=400, recovery=5ms, with invalid parameters\n")
  io.write("This test measures error handling energy consumption with a fixed pattern\n")
end