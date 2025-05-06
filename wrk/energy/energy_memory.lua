--[[
WRK script for memory-intensive energy testing - fixed memory allocations
]]--

-- Track statistics
local request_counter = 0
local responses = 0
local errors = 0
local valid_responses = 0

function request()
   -- Increment request counter
   request_counter = request_counter + 1
   
   -- Use fixed size value for reproducible results
   local size = 5
   
   -- Set Accept header for JSON response
   wrk.headers["Accept"] = "application/json"
   
   -- Return formatted request with fixed size parameter
   return wrk.format("GET", "/memory-heavy?size=" .. size)
end

function response(status, headers, body)
   -- Track responses
   responses = responses + 1
   
   -- Count errors
   if status >= 400 then
      errors = errors + 1
   else
      -- Check for valid response
      if body and body:find("memory") then
         valid_responses = valid_responses + 1
      end
   end
end

function done(summary, latency, requests)
   -- Print summary stats
   io.write("Requests: " .. requests.total .. ", Responses: " .. responses)
   io.write(", Valid responses: " .. valid_responses)
   io.write(", Errors: " .. errors)
   io.write(", Avg Latency: " .. string.format("%.2f", latency.mean / 1000) .. "ms")
   io.write(", Max Latency: " .. string.format("%.2f", latency.max / 1000) .. "ms\n")
end