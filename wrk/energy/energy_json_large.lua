--[[
WRK script for large JSON energy testing - maximizes reproducibility
Modified to support repeat parameter and Unicode options
]]--

-- Track statistics
local request_counter = 0
local responses = 0
local errors = 0
local valid_json = 0
local bytes_received = 0
local max_response_size = 0

-- Configuration
local item_size = 100     -- Number of items per dataset
local repeat_count = 5    -- Number of times to repeat the dataset 
local use_unicode = true  -- Whether to request Unicode output (ensure_ascii=False)

function request()
   -- Increment request counter
   request_counter = request_counter + 1
   
   -- Set Accept header for JSON response
   wrk.headers["Accept"] = "application/json"
   
   -- Generate URL with parameters
   local url = string.format("/json-large?size=%d&repeat=%d&unicode=%s", 
                             item_size, 
                             repeat_count, 
                             use_unicode and "true" or "false")
   
   -- Return formatted request
   return wrk.format("GET", url)
end

function response(status, headers, body)
   -- Track responses
   responses = responses + 1
   
   -- Count errors
   if status >= 400 then
      errors = errors + 1
   else
      -- Track response size
      if body then
         bytes_received = bytes_received + #body
         max_response_size = math.max(max_response_size, #body)
         
         -- Validate JSON response 
         if body:find("{") and body:find("}") then
            -- Simple check if it has braces
            valid_json = valid_json + 1
            
            -- Verify the response contains expected JSON structure
            if body:find("metadata") and body:find("items") then
               -- Further validation could be done here
            end
         end
      end
   end
end

function done(summary, latency, requests)
   -- Print summary stats
   io.write("Large JSON Test Results:\n")
   io.write("Requests: " .. requests.total .. ", Responses: " .. responses .. "\n")
   io.write("Valid JSON: " .. valid_json .. ", Errors: " .. errors .. "\n")
   io.write("Avg Latency: " .. string.format("%.2f", latency.mean / 1000) .. "ms" .. "\n")
   io.write("Max Latency: " .. string.format("%.2f", latency.max / 1000) .. "ms" .. "\n")
   io.write("Total Data Received: " .. string.format("%.2f", bytes_received / (1024 * 1024)) .. " MB" .. "\n")
   io.write("Avg Response Size: " .. string.format("%.2f", bytes_received / responses / 1024) .. " KB" .. "\n")
   io.write("Max Response Size: " .. string.format("%.2f", max_response_size / 1024) .. " KB" .. "\n")
end