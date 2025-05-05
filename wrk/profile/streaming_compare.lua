--[[
WRK script for comparing streaming vs non-streaming responses - profile mode
Directly compares performance characteristics of streaming and non-streaming endpoints
]]--

-- Tracking counters
requests = 0
responses = 0
errors = 0
sizes = {}
content_types = {}
response_times = {}

-- Configuration patterns for testing
local patterns = {
  -- Different sizes
  { mode = "json", size = 1000 },
  { mode = "json", size = 2000 },
  { mode = "json", size = 5000 },
  
  -- Different content types
  { mode = "csv", size = 2000 },
  { mode = "plaintext", size = 2000 }
}

-- Setup function
function setup(thread)
end

-- Request function - called for each request
function request()
  requests = requests + 1
  
  -- Select a pattern based on the request number
  local pattern_idx = (requests % #patterns) + 1
  local pattern = patterns[pattern_idx]
  
  -- Build the URL with query parameters
  local url = string.format(
    "/streaming/non-streaming?mode=%s&size=%d",
    pattern.mode, pattern.size
  )
  
  -- Set appropriate Accept header based on mode
  if pattern.mode == "json" then
    wrk.headers["Accept"] = "application/json"
  elseif pattern.mode == "csv" then
    wrk.headers["Accept"] = "text/csv"
  else
    wrk.headers["Accept"] = "text/plain"
  end
  
  -- Return the formatted request
  return wrk.format("GET", url)
end

-- Response handler
function response(status, headers, body)
  responses = responses + 1
  
  -- Check for errors
  if status >= 400 then
    errors = errors + 1
    return
  end
  
  -- Record response size
  local size_category = math.floor(#body / 1024) -- Size in KB
  sizes[size_category] = (sizes[size_category] or 0) + 1
  
  -- Track content type
  local content_type = headers["Content-Type"] or "unknown"
  content_types[content_type] = (content_types[content_type] or 0) + 1
  
  -- Track response time from header if available
  local response_time = headers["X-Response-Time"]
  if response_time then
    response_time = tonumber(response_time)
    if response_time then
      table.insert(response_times, response_time)
    end
  end
end

-- Helper function to calculate percentile
function percentile(list, p)
  if #list == 0 then return 0 end
  table.sort(list)
  local index = math.ceil(#list * p / 100)
  return list[math.min(index, #list)]
end

-- Done function - called at the end of the benchmark
function done(summary, latency, requests)
  io.write("\n----- Non-Streaming Response Test Results -----\n")
  io.write("Requests: " .. requests .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  
  -- Calculate average response time
  local avg_response_time = 0
  if #response_times > 0 then
    local sum = 0
    for _, time in ipairs(response_times) do
      sum = sum + time
    end
    avg_response_time = sum / #response_times
    
    io.write(string.format("Average server response time: %.4f seconds\n", avg_response_time))
    
    -- Calculate percentiles for server-side timing
    if #response_times >= 10 then
      io.write("\nServer-side response time percentiles:\n")
      for _, p in ipairs({50, 75, 90, 99}) do
        io.write(string.format("  %s%%: %.4fs\n", p, percentile(response_times, p)))
      end
    end
  end
  
  -- Print content type distribution
  io.write("\nContent type distribution:\n")
  for content_type, count in pairs(content_types) do
    io.write(string.format("  %s: %d responses\n", content_type, count))
  end
  
  -- Print response size distribution
  io.write("\nResponse size distribution (KB):\n")
  local size_list = {}
  for size, count in pairs(sizes) do
    table.insert(size_list, {size=size, count=count})
  end
  table.sort(size_list, function(a, b) return a.size < b.size end)
  
  for _, s in ipairs(size_list) do
    io.write(string.format("  %d KB: %d responses\n", s.size, s.count))
  end
  
  -- Print latency stats
  io.write("\nClient-side latency stats:\n")
  io.write("  Avg: " .. string.format("%.2f", latency.mean / 1000) .. "ms\n")
  io.write("  Max: " .. string.format("%.2f", latency.max / 1000) .. "ms\n")
  io.write("  Stdev: " .. string.format("%.2f", latency.stdev / 1000) .. "ms\n")
  
  -- Print percentiles
  io.write("\nClient-side percentiles:\n")
  for _, p in ipairs({50, 75, 90, 99, 99.9}) do
    io.write(string.format("  %s%%: %.2fms\n", p, latency:percentile(p) / 1000))
  end
  
  -- Performance comparison notes
  io.write("\nNOTE: Compare these results with the streaming endpoint results\n")
  io.write("to evaluate the performance trade-offs between streaming and non-streaming.\n")
end