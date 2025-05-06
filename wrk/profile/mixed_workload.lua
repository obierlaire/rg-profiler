--[[
WRK script for mixed workload testing - profile mode
Simulates real-world usage patterns with different workload configurations
]]--

-- Tracking counters
local request_counter = 0
local responses = 0
local errors = 0
local pattern_counts = {}
local task_counts = {}
local task_times = {}
local total_times = {}

-- Workload patterns to test
local patterns = {
  "balanced",     -- Even distribution of all workload types
  "cpu-heavy",    -- CPU-intensive operations dominant
  "memory-heavy", -- Memory-intensive operations dominant
  "io-heavy"      -- I/O and string processing operations dominant
}

-- Intensity levels to test
local intensities = { 1, 2, 3, 5 }

-- Fixed seed settings
local fixed_seeds = { "true", "false" }

-- Setup function
function setup(thread)
end

-- Request function - called for each request
function request()
  request_counter = request_counter + 1
  
  -- Select a workload pattern
  local pattern_idx = (request_counter % #patterns) + 1
  local pattern = patterns[pattern_idx]
  
  -- Select an intensity level
  local intensity_idx = (math.floor(request_counter / #patterns) % #intensities) + 1
  local intensity = intensities[intensity_idx]
  
  -- Select fixed seed setting
  local seed_idx = (math.floor(request_counter / (#patterns * #intensities)) % #fixed_seeds) + 1
  local fixed_seed = fixed_seeds[seed_idx]
  
  -- Build the URL with query parameters
  local url = string.format(
    "/mixed-workload?pattern=%s&intensity=%d&fixed_seed=%s",
    pattern, intensity, fixed_seed
  )
  
  -- Set Accept header
  wrk.headers["Accept"] = "application/json"
  
  -- Track the pattern used for this request
  pattern_counts[pattern] = (pattern_counts[pattern] or 0) + 1
  
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
  
  -- Parse the JSON response to extract workload information
  if body and body:find("{") then
    -- Extract pattern and intensity
    local pattern = body:match('"pattern":"([^"]+)"')
    local intensity = body:match('"intensity":(%d+)')
    
    if pattern then
      -- Extract task types
      local tasks_section = body:match('"tasks":%[(.-)%]')
      if tasks_section then
        -- Count task types
        for task_type in tasks_section:gmatch('"type":"([^"]+)"') do
          task_counts[task_type] = (task_counts[task_type] or 0) + 1
        end
      end
      
      -- Extract timing information
      local timing_section = body:match('"timing":{(.-)}')
      if timing_section then
        local pattern_key = pattern
        if intensity then
          pattern_key = pattern .. "_" .. intensity
        end
        
        -- Initialize pattern timing storage if needed
        task_times[pattern_key] = task_times[pattern_key] or {}
        
        -- Extract timings for each task type
        for task_type, time in timing_section:gmatch('"([^"]+)":([%d%.]+)') do
          if task_type ~= "total" then
            task_times[pattern_key][task_type] = task_times[pattern_key][task_type] or {}
            table.insert(task_times[pattern_key][task_type], tonumber(time))
          end
        end
        
        -- Extract total time
        local total_time = timing_section:match('"total":([%d%.]+)')
        if total_time then
          total_times[pattern_key] = total_times[pattern_key] or {}
          table.insert(total_times[pattern_key], tonumber(total_time))
        end
      end
    end
  end
end

-- Helper function to calculate average
function average(list)
  if not list or #list == 0 then return 0 end
  local sum = 0
  for _, val in ipairs(list) do
    sum = sum + val
  end
  return sum / #list
end

-- Done function - called at the end of the benchmark
function done(summary, latency, requests)
  io.write("\n----- Mixed Workload Test Results -----\n")
  io.write("Requests: " .. requests.total .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  
  -- Print pattern distribution
  io.write("\nWorkload pattern distribution:\n")
  for pattern, count in pairs(pattern_counts) do
    io.write(string.format("  %s: %d requests\n", pattern, count))
  end
  
  -- Print task type distribution
  io.write("\nTask type distribution:\n")
  local task_list = {}
  for task_type, count in pairs(task_counts) do
    table.insert(task_list, {type=task_type, count=count})
  end
  table.sort(task_list, function(a, b) return a.count > b.count end)
  
  for _, task in ipairs(task_list) do
    io.write(string.format("  %s: %d tasks\n", task.type, task.count))
  end
  
  -- Print timing statistics for each pattern
  io.write("\nAverage execution time by pattern (ms):\n")
  for pattern_key, times in pairs(total_times) do
    if #times > 0 then
      io.write(string.format("  %s: %.2fms\n", pattern_key, average(times)))
    end
  end
  
  -- Print detailed timing statistics for a few key patterns
  for _, pattern in ipairs({"balanced_3", "cpu-heavy_3", "memory-heavy_3"}) do
    if task_times[pattern] then
      io.write(string.format("\nDetailed timing for %s pattern (ms):\n", pattern))
      
      for task_type, times in pairs(task_times[pattern]) do
        if #times > 0 then
          io.write(string.format("  %s: %.2fms\n", task_type, average(times)))
        end
      end
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