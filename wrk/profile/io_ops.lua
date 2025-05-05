--[[
WRK script for I/O operations testing - profile mode
Tests various file I/O configurations to measure performance impact
]]--

-- Tracking counters
requests = 0
responses = 0
errors = 0
operation_counts = {}
buffer_counts = {}
size_counts = {}
sync_mode_counts = {}
timing_data = {}

-- I/O operation types to test
local operations = { "read", "write", "append", "combined" }

-- Buffer sizes to test (in bytes)
local buffer_sizes = { 4096, 8192, 16384, 32768, 65536 }

-- File sizes to test (in KB)
local file_sizes = { 512, 1024, 2048 }

-- Synchronization modes to test
local sync_modes = { "buffered", "fsync", "fdatasync" }

-- Setup function
function setup(thread)
end

-- Request function - called for each request
function request()
  requests = requests + 1
  
  -- Select parameters based on request number to ensure coverage of all combinations
  local op_idx = (requests % #operations) + 1
  local operation = operations[op_idx]
  
  local buffer_idx = (math.floor(requests / #operations) % #buffer_sizes) + 1
  local buffer_size = buffer_sizes[buffer_idx]
  
  local size_idx = (math.floor(requests / (#operations * #buffer_sizes)) % #file_sizes) + 1
  local file_size = file_sizes[size_idx]
  
  local sync_idx = (math.floor(requests / (#operations * #buffer_sizes * #file_sizes)) % #sync_modes) + 1
  local sync_mode = sync_modes[sync_idx]
  
  -- Determine iterations (keep low for larger files)
  local iterations = 1
  if file_size <= 1024 then
    iterations = 3
  elseif file_size <= 2048 then
    iterations = 2
  end
  
  -- Build the URL with query parameters
  local url = string.format(
    "/io-ops?op=%s&buffer=%d&size=%d&iterations=%d&sync=%s",
    operation, buffer_size, file_size, iterations, sync_mode
  )
  
  -- Track the operations used for this request
  operation_counts[operation] = (operation_counts[operation] or 0) + 1
  buffer_counts[buffer_size] = (buffer_counts[buffer_size] or 0) + 1
  size_counts[file_size] = (size_counts[file_size] or 0) + 1
  sync_mode_counts[sync_mode] = (sync_mode_counts[sync_mode] or 0) + 1
  
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
  
  -- Parse the JSON response to extract I/O information
  if body and body:find("{") then
    -- Extract operation details
    local operation = body:match('"operation":"([^"]+)"')
    local buffer_size = body:match('"buffer_size":(%d+)')
    local file_size = body:match('"file_size":(%d+)')
    local sync_mode = body:match('"sync_mode":"([^"]+)"')
    
    if operation and buffer_size and file_size and sync_mode then
      buffer_size = tonumber(buffer_size)
      file_size = tonumber(file_size)
      
      -- Create a key for this configuration
      local config_key = string.format("%s_%d_%d_%s", operation, buffer_size, file_size, sync_mode)
      
      -- Extract timing information
      local timing_section = body:match('"timing":{(.-)}')
      if timing_section then
        timing_data[config_key] = timing_data[config_key] or {}
        
        -- Extract timings for each operation type
        for op_type, time in timing_section:gmatch('"([^"]+)":([%d%.]+)') do
          timing_data[config_key][op_type] = timing_data[config_key][op_type] or {}
          table.insert(timing_data[config_key][op_type], tonumber(time))
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
  io.write("\n----- I/O Operations Test Results -----\n")
  io.write("Requests: " .. requests .. ", Responses: " .. responses .. ", Errors: " .. errors .. "\n")
  
  -- Print operation distribution
  io.write("\nOperation type distribution:\n")
  for op, count in pairs(operation_counts) do
    io.write(string.format("  %s: %d requests\n", op, count))
  end
  
  -- Print buffer size distribution
  io.write("\nBuffer size distribution:\n")
  local buffer_list = {}
  for size, count in pairs(buffer_counts) do
    table.insert(buffer_list, {size=size, count=count})
  end
  table.sort(buffer_list, function(a, b) return a.size < b.size end)
  
  for _, b in ipairs(buffer_list) do
    io.write(string.format("  %d bytes: %d requests\n", b.size, b.count))
  end
  
  -- Print file size distribution
  io.write("\nFile size distribution:\n")
  local size_list = {}
  for size, count in pairs(size_counts) do
    table.insert(size_list, {size=size, count=count})
  end
  table.sort(size_list, function(a, b) return a.size < b.size end)
  
  for _, s in ipairs(size_list) do
    io.write(string.format("  %d KB: %d requests\n", s.size, s.count))
  end
  
  -- Print sync mode distribution
  io.write("\nSync mode distribution:\n")
  for mode, count in pairs(sync_mode_counts) do
    io.write(string.format("  %s: %d requests\n", mode, count))
  end
  
  -- Print timing analysis for key configurations
  io.write("\nTiming analysis for key configurations (ms):\n")
  
  -- Create sorted list of configurations
  local configs = {}
  for config, data in pairs(timing_data) do
    table.insert(configs, config)
  end
  table.sort(configs)
  
  -- Get total times for each configuration
  local total_times = {}
  for _, config in ipairs(configs) do
    local data = timing_data[config]
    if data["total"] then
      total_times[config] = average(data["total"])
    end
  end
  
  -- Sort configurations by total time
  table.sort(configs, function(a, b) 
    return (total_times[a] or 0) < (total_times[b] or 0)
  end)
  
  -- Print top and bottom 5 configurations
  local count = 0
  for i, config in ipairs(configs) do
    if count < 5 or i > #configs - 5 then
      local parts = {}
      for part in config:gmatch("[^_]+") do
        table.insert(parts, part)
      end
      
      local data = timing_data[config]
      local total_time = total_times[config] or 0
      
      if parts[1] and parts[2] and parts[3] and parts[4] then
        io.write(string.format("  %s, %s KB, %s bytes, %s: %.2fms\n", 
          parts[1], parts[3], parts[2], parts[4], total_time))
      end
      
      count = count + 1
    elseif count == 5 and #configs > 10 then
      io.write("  ...\n")
    end
  end
  
  -- Print detailed timing for read vs write operations
  io.write("\nRead vs Write performance (buffer=8192, size=1024):\n")
  local read_key = "read_8192_1024_buffered"
  local write_key = "write_8192_1024_buffered"
  
  if timing_data[read_key] and timing_data[read_key]["read"] then
    io.write(string.format("  Read: %.2fms\n", average(timing_data[read_key]["read"])))
  end
  
  if timing_data[write_key] and timing_data[write_key]["write"] then
    io.write(string.format("  Write: %.2fms\n", average(timing_data[write_key]["write"])))
  end
  
  -- Print synced vs non-synced write
  io.write("\nSync mode impact (write, buffer=8192, size=1024):\n")
  local buffered_key = "write_8192_1024_buffered"
  local fsync_key = "write_8192_1024_fsync"
  
  if timing_data[buffered_key] and timing_data[buffered_key]["write"] then
    io.write(string.format("  Buffered: %.2fms\n", average(timing_data[buffered_key]["write"])))
  end
  
  if timing_data[fsync_key] and timing_data[fsync_key]["write"] then
    io.write(string.format("  fsync: %.2fms\n", average(timing_data[fsync_key]["write"])))
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