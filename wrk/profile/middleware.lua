--[[
WRK script for advanced middleware testing - profile mode
Tests various middleware configurations to measure overhead and performance
]]--

-- Tracking counters
requests = 0
responses = 0
errors = 0
total_middleware_time = 0
middleware_chains = {}
times = {}
slow_responses = 0

-- Configuration patterns to test
local patterns = {
  -- Default - all middleware active
  { 
    transform_heavy = "false",
    transform_response = "false",
    skip_security = "false",
    simulate_rate_limit = "false" 
  },
  -- Security checks skipped
  { 
    transform_heavy = "false", 
    transform_response = "false",
    skip_security = "true",
    simulate_rate_limit = "false" 
  },
  -- Rate limiting simulation
  { 
    transform_heavy = "false", 
    transform_response = "false",
    skip_security = "false",
    simulate_rate_limit = "true" 
  },
  -- Heavy request transformation
  { 
    transform_heavy = "true", 
    transform_response = "false",
    skip_security = "false",
    simulate_rate_limit = "false" 
  },
  -- Response transformation
  { 
    transform_heavy = "false", 
    transform_response = "true",
    skip_security = "false",
    simulate_rate_limit = "false" 
  },
  -- All transformations active
  { 
    transform_heavy = "true", 
    transform_response = "true",
    skip_security = "false",
    simulate_rate_limit = "false" 
  }
}

-- Setup function - called at the beginning of the benchmark
function setup(thread)
end

-- Request function - called for each request
function request()
  -- Track requests
  requests = requests + 1
  
  -- Select a pattern based on the request number to ensure we test all patterns
  local current_pattern = patterns[(requests % #patterns) + 1]
  
  -- Build the URL with query parameters
  local url = "/middleware-advanced?"
  local params = {}
  
  for k, v in pairs(current_pattern) do
    table.insert(params, k .. "=" .. v)
  end
  
  -- Add headers parameter
  local headers_count = math.min(5, requests % 10) -- 0-5 custom headers
  if headers_count > 0 then
    local header_list = {}
    for i=1,headers_count do
      table.insert(header_list, "header" .. i)
    end
    table.insert(params, "add_headers=" .. table.concat(header_list, ","))
  end
  
  -- Add some sleep time occasionally to simulate endpoint processing
  if requests % 7 == 0 then
    local sleep_time = (requests % 5) * 0.01 -- 0-0.04 seconds
    table.insert(params, "sleep_time=" .. sleep_time)
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
    return
  end
  
  -- Parse the JSON response
  if body and body:find("{") then
    -- Track timing information
    local middleware_time = body:match('"total_middleware_time_ms":([^,}]+)')
    if middleware_time then
      middleware_time = tonumber(middleware_time)
      total_middleware_time = total_middleware_time + middleware_time
      
      -- Track slow responses (over 20ms in middleware)
      if middleware_time > 20 then
        slow_responses = slow_responses + 1
      end
      
      -- Record chain count
      local chain = body:match('"middleware_chain":%[([^%]]+)%]')
      if chain then
        local count = 0
        for _ in chain:gmatch('"[^"]+"') do
          count = count + 1
        end
        
        middleware_chains[count] = (middleware_chains[count] or 0) + 1
      end
      
      -- Record timing between middleware
      local times_section = body:match('"times":%[(.-)%]')
      if times_section then
        for from, to, time in times_section:gmatch('"from":"([^"]+)","to":"([^"]+)","time_ms":([^,}]+)') do
          local key = from .. "->" .. to
          times[key] = (times[key] or 0) + tonumber(time)
        end
      end
    end
  end
end

-- Done function - called at the end of the benchmark
function done(summary, latency, requests)
  -- Compute averages and print summary
  local avg_middleware_time = 0
  if responses > 0 then
    avg_middleware_time = total_middleware_time / responses
  end
  
  io.write("\n----- Middleware Test Results -----\n")
  io.write("Requests: " .. requests .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  io.write("Average middleware time: " .. string.format("%.2f", avg_middleware_time) .. "ms\n")
  io.write("Slow responses (>20ms): " .. slow_responses .. "\n")
  
  -- Print chain sizes
  io.write("\nMiddleware chain sizes:\n")
  local chains = {}
  for count, num in pairs(middleware_chains) do
    table.insert(chains, {count=count, num=num})
  end
  table.sort(chains, function(a, b) return a.count < b.count end)
  
  for _, chain in ipairs(chains) do
    io.write("  " .. chain.count .. " middleware: " .. chain.num .. " responses\n")
  end
  
  -- Print timing between middleware
  io.write("\nAverage time between middleware (ms):\n")
  local transitions = {}
  for key, time in pairs(times) do
    table.insert(transitions, {key=key, time=time/responses})
  end
  table.sort(transitions, function(a, b) return a.time > b.time end)
  
  for i, t in ipairs(transitions) do
    if i <= 10 then -- Show top 10
      io.write("  " .. t.key .. ": " .. string.format("%.2f", t.time) .. "ms\n")
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