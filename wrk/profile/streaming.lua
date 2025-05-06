--[[
WRK script for streaming response testing - profile mode
Tests different streaming configurations to measure performance impact
]]--

-- Tracking counters
local request_counter = 0
local responses = 0
local errors = 0
local streaming_sizes = {}
local chunk_counts = {}
local total_response_time = 0
local avg_response_size = 0

-- Configuration patterns for testing different streaming scenarios
local patterns = {
  -- Different sizes
  { mode = "json", size = 1000, chunk_size = 64, delay = 0 },
  { mode = "json", size = 2000, chunk_size = 64, delay = 0 },
  { mode = "json", size = 5000, chunk_size = 64, delay = 0 },
  
  -- Different chunk sizes
  { mode = "json", size = 2000, chunk_size = 32, delay = 0 },
  { mode = "json", size = 2000, chunk_size = 128, delay = 0 },
  { mode = "json", size = 2000, chunk_size = 256, delay = 0 },
  
  -- Different content types
  { mode = "csv", size = 2000, chunk_size = 64, delay = 0 },
  { mode = "plaintext", size = 2000, chunk_size = 64, delay = 0 },
  
  -- With delays between chunks
  { mode = "json", size = 2000, chunk_size = 64, delay = 0.001 }, -- 1ms
  { mode = "json", size = 2000, chunk_size = 64, delay = 0.005 }  -- 5ms
}

-- Setup function
function setup(thread)
end

-- Request function - called for each request
function request()
  request_counter = request_counter + 1
  
  -- Select a pattern based on the request number
  local pattern_idx = (request_counter % #patterns) + 1
  local pattern = patterns[pattern_idx]
  
  -- Build the URL with query parameters
  local url = string.format(
    "/streaming?mode=%s&size=%d&chunk_size=%d&delay=%.3f",
    pattern.mode, pattern.size, pattern.chunk_size, pattern.delay
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
  streaming_sizes[size_category] = (streaming_sizes[size_category] or 0) + 1
  
  -- Estimate the number of chunks based on the body size and pattern
  local pattern = patterns[(responses % #patterns) + 1]
  local estimated_chunks = math.ceil(#body / (pattern.chunk_size * 1024))
  chunk_counts[estimated_chunks] = (chunk_counts[estimated_chunks] or 0) + 1
  
  -- Track response time from header if available
  local response_time = headers["X-Response-Time"]
  if response_time then
    response_time = tonumber(response_time)
    if response_time then
      total_response_time = total_response_time + response_time
    end
  end
  
  -- Track average response size
  avg_response_size = avg_response_size + #body
end

-- Done function - called at the end of the benchmark
function done(summary, latency, requests)
  if responses > 0 then
    avg_response_size = avg_response_size / responses
  end
  
  local avg_response_time = 0
  if responses > 0 then
    avg_response_time = total_response_time / responses
  end
  
  io.write("\n----- Streaming Test Results -----\n")
  io.write("Requests: " .. requests.total .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  io.write("Average response size: " .. string.format("%.2f", avg_response_size / 1024) .. " KB\n")
  
  if avg_response_time > 0 then
    io.write("Average response time: " .. string.format("%.4f", avg_response_time) .. " seconds\n")
  end
  
  -- Print response size distribution
  io.write("\nResponse size distribution (KB):\n")
  local sizes = {}
  for size, count in pairs(streaming_sizes) do
    table.insert(sizes, {size=size, count=count})
  end
  table.sort(sizes, function(a, b) return a.size < b.size end)
  
  for _, s in ipairs(sizes) do
    io.write(string.format("  %d KB: %d responses\n", s.size, s.count))
  end
  
  -- Print estimated chunk counts
  io.write("\nEstimated chunk counts:\n")
  local chunks = {}
  for count, num in pairs(chunk_counts) do
    table.insert(chunks, {count=count, num=num})
  end
  table.sort(chunks, function(a, b) return a.count < b.count end)
  
  for _, c in ipairs(chunks) do
    io.write(string.format("  %d chunks: %d responses\n", c.count, c.num))
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