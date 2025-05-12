--[[
WRK script for JSON parsing energy testing - maximizes reproducibility
This script makes POST requests with JSON payload to test parsing
]]--

-- Track statistics
local request_counter = 0
local responses = 0
local errors = 0
local success_responses = 0
local bytes_sent = 0
local processing_time_total = 0

-- Generate a JSON payload with items for testing
function generate_payload(item_count)
   -- Create beginning of JSON
   local payload = [[
{
  "metadata": {
    "test": "json-parsing",
    "timestamp": "]] .. os.date("!%Y-%m-%dT%H:%M:%SZ") .. [[",
    "client": "wrk-test"
  },
  "items": []]
   
   -- Generate items
   for i = 1, item_count do
      -- Add comma for all but first item
      if i > 1 then
         payload = payload .. ","
      end
      
      -- Generate a test item with various data types
      payload = payload .. [[
    {
      "id": ]] .. i .. [[,
      "name": "Test Item ]] .. i .. [[",
      "active": ]] .. (i % 2 == 0 and "true" or "false") .. [[,
      "priority": ]] .. (i % 5 + 1) .. [[,
      "tags": ["tag1", "tag2", "tag]] .. (i % 10) .. [["],
      "values": []] .. (i * 1.5) .. [[, ]] .. (i * 2.5) .. [[, ]] .. (i * 3.5) .. [[],
      "properties": {
        "color": "]] .. ({"red", "green", "blue", "yellow", "purple"})[i % 5 + 1] .. [[",
        "size": ]] .. (i * 10) .. [[,
        "visible": ]] .. (i % 3 == 0 and "true" or "false") .. [[
      }
    }]]
   end
   
   -- Close the JSON structure
   payload = payload .. [[
  ]
}]]
   
   return payload
end

-- Pre-generate payloads of different sizes
local small_payload = generate_payload(5)
local medium_payload = generate_payload(20)
local large_payload = generate_payload(50)

-- Track sizes for reporting
local payload_sizes = {
   small = #small_payload,
   medium = #medium_payload,
   large = #large_payload
}

-- Choose payload based on request number for variety
function get_payload(request_num)
   if request_num % 3 == 0 then
      return small_payload, "small"
   elseif request_num % 3 == 1 then
      return medium_payload, "medium"
   else
      return large_payload, "large"
   end
end

function request()
   -- Increment request counter
   request_counter = request_counter + 1
   
   -- Get payload for this request
   local payload, size_name = get_payload(request_counter)
   
   -- Track bytes sent
   bytes_sent = bytes_sent + #payload
   
   -- Set required headers
   wrk.headers["Content-Type"] = "application/json"
   wrk.headers["Accept"] = "application/json"
   
   -- Return formatted POST request with JSON payload
   return wrk.format("POST", "/json-parse", wrk.headers, payload)
end

function response(status, headers, body)
   -- Track responses
   responses = responses + 1
   
   -- Count errors
   if status >= 400 then
      errors = errors + 1
   else
      -- Simple validation of response body
      if body and body:find("{") then
         -- Parse processing time if available
         local processing_time = body:match('"processing_time_ms":([0-9%.]+)')
         if processing_time then
            processing_time_total = processing_time_total + tonumber(processing_time)
         end
         
         -- Check for success status
         if body:find('"status":"success"') then
            success_responses = success_responses + 1
         end
      end
   end
end

function done(summary, latency, requests)
   -- Print summary stats
   io.write("JSON Parsing Test Results:\n")
   io.write("Requests: " .. requests.total .. ", Responses: " .. responses .. "\n")
   io.write("Successful: " .. success_responses .. ", Errors: " .. errors .. "\n")
   io.write("Avg Latency: " .. string.format("%.2f", latency.mean / 1000) .. "ms" .. "\n")
   io.write("Max Latency: " .. string.format("%.2f", latency.max / 1000) .. "ms" .. "\n")
   
   -- Payload stats
   io.write("Payload Sizes - Small: " .. string.format("%.2f", payload_sizes.small / 1024) .. "KB, " ..
           "Medium: " .. string.format("%.2f", payload_sizes.medium / 1024) .. "KB, " ..
           "Large: " .. string.format("%.2f", payload_sizes.large / 1024) .. "KB\n")
   
   -- Data transfer stats
   io.write("Total Data Sent: " .. string.format("%.2f", bytes_sent / (1024 * 1024)) .. " MB" .. "\n")
   
   -- Processing time stats if available
   if responses > 0 and processing_time_total > 0 then
      io.write("Avg Server Processing Time: " .. string.format("%.2f", processing_time_total / responses) .. "ms" .. "\n")
   end
end