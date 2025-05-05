--[[
WRK script for error handling testing - profile mode
Tests various error scenarios and measures recovery performance
]]--

-- Tracking counters
requests = 0
responses = 0
errors = 0
status_codes = {}
error_types = {}
recovery_times = {}
request_times = {}

-- Error scenarios to test
local scenarios = {
  -- HTTP error codes
  { type = "http", code = 400 },
  { type = "http", code = 404 },
  { type = "http", code = 500 },
  
  -- Programming errors
  { type = "division", code = 500 },
  { type = "type", code = 500 },
  { type = "key", code = 500 },
  
  -- Custom errors
  { type = "custom", code = 500 },
  { type = "timeout", code = 500 },
  { type = "io", code = 500 },
  
  -- Validation errors
  { type = "validation", code = 400, params = "name=a&age=xyz&email=invalidemail" },
  
  -- Control case (no error)
  { type = "none", code = 200 }
}

-- Recovery time settings to test
local recovery_settings = { 0, 5, 10, 20 }

-- Setup function
function setup(thread)
end

-- Request function - called for each request
function request()
  requests = requests + 1
  
  -- Select an error scenario
  local scenario_idx = (requests % #scenarios) + 1
  local scenario = scenarios[scenario_idx]
  
  -- Select a recovery time setting
  local recovery_idx = (math.floor(requests / #scenarios) % #recovery_settings) + 1
  local recovery = recovery_settings[recovery_idx]
  
  -- Build the URL with query parameters
  local url = "/errors?type=" .. scenario.type .. "&code=" .. scenario.code .. "&recovery=" .. recovery
  
  -- Add validation parameters if needed
  if scenario.params then
    url = url .. "&" .. scenario.params
  end
  
  -- Set Accept header
  wrk.headers["Accept"] = "application/json"
  
  -- Return the formatted request
  return wrk.format("GET", url)
end

-- Response handler
function response(status, headers, body)
  responses = responses + 1
  
  -- Track status codes
  status_codes[status] = (status_codes[status] or 0) + 1
  
  -- Check if this was an error response
  local is_error = status >= 400
  if is_error then
    errors = errors + 1
  end
  
  -- Parse the JSON response to extract error details
  if body and body:find("{") then
    -- Extract error type
    local error_type = body:match('"error_type":"([^"]+)"')
    if error_type then
      error_types[error_type] = (error_types[error_type] or 0) + 1
    end
    
    -- Extract error handling time if available
    local handling_time = body:match('"error_handling_ms":([^,}]+)')
    if handling_time then
      handling_time = tonumber(handling_time)
      if handling_time then
        recovery_times[error_type] = recovery_times[error_type] or {}
        table.insert(recovery_times[error_type], handling_time)
      end
    end
    
    -- Extract total request time if available
    local request_time = body:match('"total_request_ms":([^,}]+)')
    if request_time then
      request_time = tonumber(request_time)
      if request_time then
        request_times[status] = request_times[status] or {}
        table.insert(request_times[status], request_time)
      end
    end
  end
end

-- Helper function to calculate average
function average(list)
  if #list == 0 then return 0 end
  local sum = 0
  for _, val in ipairs(list) do
    sum = sum + val
  end
  return sum / #list
end

-- Done function - called at the end of the benchmark
function done(summary, latency, requests)
  io.write("\n----- Error Handling Test Results -----\n")
  io.write("Requests: " .. requests .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  
  -- Print status code distribution
  io.write("\nStatus code distribution:\n")
  local status_list = {}
  for status, count in pairs(status_codes) do
    table.insert(status_list, {status=status, count=count})
  end
  table.sort(status_list, function(a, b) return a.status < b.status end)
  
  for _, s in ipairs(status_list) do
    io.write(string.format("  %d: %d responses\n", s.status, s.count))
  end
  
  -- Print error type distribution
  io.write("\nError type distribution:\n")
  local error_list = {}
  for err_type, count in pairs(error_types) do
    if err_type ~= "none" then
      table.insert(error_list, {type=err_type, count=count})
    end
  end
  table.sort(error_list, function(a, b) return a.count > b.count end)
  
  for _, e in ipairs(error_list) do
    io.write(string.format("  %s: %d occurrences\n", e.type, e.count))
  end
  
  -- Print recovery time statistics
  io.write("\nError recovery times (ms):\n")
  for err_type, times in pairs(recovery_times) do
    if #times > 0 then
      io.write(string.format("  %s: avg=%.2fms, count=%d\n", 
        err_type, average(times), #times))
    end
  end
  
  -- Print request time by status code
  io.write("\nRequest time by status code (ms):\n")
  for status, times in pairs(request_times) do
    if #times > 0 then
      io.write(string.format("  %d: avg=%.2fms, count=%d\n", 
        status, average(times), #times))
    end
  end
  
  -- Print latency stats
  io.write("\nLatency stats:\n")
  io.write("  Avg: " .. string.format("%.2f", latency.mean / 1000) .. "ms\n")
  io.write("  Max: " .. string.format("%.2f", latency.max / 1000) .. "ms\n")
  io.write("  Stdev: " .. string.format("%.2f", latency.stdev / 1000) .. "ms\n")
  
  -- Print percentiles
  io.write("\nPercentiles:\n")
  for _, p in ipairs({50, 75, 90, 99, 99.9}) do
    io.write(string.format("  %s%%: %.2fms\n", p, latency:percentile(p) / 1000))
  end
end