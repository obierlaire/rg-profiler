--[[
WRK script for advanced routing testing - profile mode
Tests complex URL pattern recognition, parameter extraction, and type conversions
]]--

-- Tracking counters
local request_counter = 0
local responses = 0
local errors = 0
local total_routes_checked = 0
local total_processing_time = 0
local segment_counts = {}
local param_counts = {}

-- Routing patterns to test
local patterns = {
  -- Numeric ID routes
  "/routing/123/users",
  "/routing/456/products",
  "/routing/789/orders",
  
  -- Nested parameters
  "/routing/1/users/filter/active/sort/name",
  "/routing/2/users/filter/inactive/sort/date",
  "/routing/3/products/filter/instock/sort/price",
  
  -- Type conversion tests
  "/routing/42/convert/2023-01-15/true/3.14",
  "/routing/99/convert/2023-05-20/false/9.81",
  
  -- Complex paths
  "/routing/1/users/2/orders/3/items",
  "/routing/2/categories/electronics/products/featured"
}

-- Complexity levels to test
local complexity_levels = { 1, 2, 3, 5 }

-- Setup function
function setup(thread)
end

-- Request function - called for each request
function request()
  request_counter = request_counter + 1
  
  -- Select a routing pattern
  local pattern_idx = (request_counter % #patterns) + 1
  local path = patterns[pattern_idx]
  
  -- Select a complexity level
  local complexity_idx = (math.floor(request_counter / #patterns) % #complexity_levels) + 1
  local complexity = complexity_levels[complexity_idx]
  
  -- Build the URL with query parameters
  local url = path .. "?complexity=" .. complexity
  
  -- Add delay occasionally for performance testing
  if request_counter % 5 == 0 then
    url = url .. "&delay=" .. (request_counter % 10) * 0.01  -- 0 to 0.09 seconds
  end
  
  -- Set Accept header
  wrk.headers["Accept"] = "application/json"
  
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
  
  -- Parse the JSON response to extract routing information
  if body and body:find("{") then
    -- Count segments
    local segments_json = body:match('"segments":%[(.-)%]')
    if segments_json then
      local segment_count = 0
      for _ in segments_json:gmatch('{') do
        segment_count = segment_count + 1
      end
      
      segment_counts[segment_count] = (segment_counts[segment_count] or 0) + 1
    end
    
    -- Count parameters
    local params_json = body:match('"params":{(.-)}')
    if params_json then
      local param_count = 0
      for _ in params_json:gmatch(':') do
        param_count = param_count + 1
      end
      
      param_counts[param_count] = (param_counts[param_count] or 0) + 1
    end
    
    -- Extract route analysis data if available
    local patterns_checked = body:match('"patterns_checked":(%d+)')
    if patterns_checked then
      total_routes_checked = total_routes_checked + tonumber(patterns_checked)
    end
    
    -- Extract timing information if present in the response
    local response_time = headers["X-Response-Time"]
    if response_time then
      response_time = tonumber(response_time)
      if response_time then
        total_processing_time = total_processing_time + response_time
      end
    end
  end
end

-- Done function - called at the end of the benchmark
function done(summary, latency, requests)
  local avg_routes_checked = 0
  if responses > 0 then
    avg_routes_checked = total_routes_checked / responses
  end
  
  local avg_processing_time = 0
  if responses > 0 then
    avg_processing_time = total_processing_time / responses
  end
  
  io.write("\n----- Advanced Routing Test Results -----\n")
  io.write("Requests: " .. requests.total .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  io.write("Average routes checked: " .. string.format("%.2f", avg_routes_checked) .. "\n")
  
  if avg_processing_time > 0 then
    io.write("Average processing time: " .. string.format("%.4f", avg_processing_time) .. " seconds\n")
  end
  
  -- Print segment count distribution
  io.write("\nURL segment count distribution:\n")
  local segments = {}
  for count, num in pairs(segment_counts) do
    table.insert(segments, {count=count, num=num})
  end
  table.sort(segments, function(a, b) return a.count < b.count end)
  
  for _, s in ipairs(segments) do
    io.write(string.format("  %d segments: %d responses\n", s.count, s.num))
  end
  
  -- Print parameter count distribution
  io.write("\nParameter count distribution:\n")
  local params = {}
  for count, num in pairs(param_counts) do
    table.insert(params, {count=count, num=num})
  end
  table.sort(params, function(a, b) return a.count < b.count end)
  
  for _, p in ipairs(params) do
    io.write(string.format("  %d parameters: %d responses\n", p.count, p.num))
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