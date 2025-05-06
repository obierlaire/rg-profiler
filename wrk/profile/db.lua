--[[
WRK script for database query testing - measures ORM and database performance
]]--

-- Track statistics
local request_counter = 0
local responses = 0
local errors = 0
local valid_json = 0

function request()
   -- Increment request counter
   request_counter = request_counter + 1
   
   -- Set Accept header for JSON response
   wrk.headers["Accept"] = "application/json"
   
   -- Return formatted request
   return wrk.format("GET", "/db")
end

function response(status, headers, body)
   -- Track responses
   responses = responses + 1
   
   -- Count errors
   if status >= 400 then
      errors = errors + 1
   else
      -- Validate JSON response contains expected fields
      if body and body:find("id") and body:find("randomnumber") then
         valid_json = valid_json + 1
      end
   end
end

function done(summary, latency, requests)
   -- Print summary stats
   io.write("Requests: " .. requests.total .. ", Responses: " .. responses)
   io.write(", Valid DB responses: " .. valid_json)
   io.write(", Errors: " .. errors)
   io.write(", Avg Latency: " .. string.format("%.2f", latency.mean / 1000) .. "ms")
   io.write(", Max Latency: " .. string.format("%.2f", latency.max / 1000) .. "ms\n")
end