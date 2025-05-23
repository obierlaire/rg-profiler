--[[
WRK script for complex routing testing - measures URL parameter parsing performance
]]--

-- Track statistics
local request_counter = 0
local responses = 0
local errors = 0
local valid_responses = 0

-- Sample IDs and parameters
local ids = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10"}
local names = {"user", "admin", "test", "guest", "customer", "client", "staff", "member", "visitor", "student"}
local param1s = {"active", "disabled", "pending", "approved", "rejected", "success", "error", "warning", "info", "debug"}
local param2s = {"high", "medium", "low", "urgent", "normal", "critical", "minor", "major", "blocker", "trivial"}

function request()
   -- Increment request counter
   request_counter = request_counter + 1
   
   -- Build complex route with different parameters each time
   local id = ids[request_counter % #ids + 1]
   local name = names[request_counter % #names + 1]
   local param1 = param1s[request_counter % #param1s + 1]
   local param2 = param2s[request_counter % #param2s + 1]
   
   local path = "/complex-routing/" .. id .. "/" .. name .. "/" .. param1 .. "/" .. param2
   
   -- Set Accept header for JSON response
   wrk.headers["Accept"] = "application/json"
   
   -- Return formatted request
   return wrk.format("GET", path)
end

function response(status, headers, body)
   -- Track responses
   responses = responses + 1
   
   -- Count errors
   if status >= 400 then
      errors = errors + 1
   else
      -- Verify response contains the parameters
      if body and body:find("id") then
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