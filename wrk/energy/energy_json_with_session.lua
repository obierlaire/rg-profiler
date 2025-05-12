--[[
WRK script for JSON energy testing - WITH SESSION version 
Tests session initialization to compare against optimized path
]]--

-- Track statistics
local request_counter = 0
local responses = 0
local errors = 0
local valid_json = 0
local session_used = 0

-- This script ALWAYS uses sessions (baseline performance)
local use_session = true  

function request()
   -- Increment request counter
   request_counter = request_counter + 1
   
   -- Set Accept header for JSON response
   wrk.headers["Accept"] = "application/json"
   
   -- Always use sessions in this script
   local url = "/json?use_session=1"
   session_used = session_used + 1
   
   -- Add a cookie header to simulate a session cookie
   wrk.headers["Cookie"] = "session=mock-session-id-for-testing"
   
   return wrk.format("GET", url)
end

function response(status, headers, body)
   -- Track responses
   responses = responses + 1
   
   -- Count errors
   if status >= 400 then
      errors = errors + 1
   else
      -- Validate JSON response
      if body and body:find("{") then
         -- Simple check if it at least starts with a brace
         valid_json = valid_json + 1
      end
   end
end

function done(summary, latency, requests)
   -- Print summary stats with clear session mode information
   io.write("======================================================\n")
   io.write("SESSION MODE: WITH SESSION (baseline)\n")
   io.write("======================================================\n")
   io.write("Requests: " .. requests.total .. ", Responses: " .. responses)
   io.write(", Valid JSON: " .. valid_json)
   io.write(", Errors: " .. errors .. "\n")
   
   -- Session statistics
   io.write("Session requests: " .. session_used .. " (100%)\n")
   
   -- Performance statistics
   io.write("Avg Latency: " .. string.format("%.2f", latency.mean / 1000) .. "ms")
   io.write(", Max Latency: " .. string.format("%.2f", latency.max / 1000) .. "ms\n")
   io.write("Requests/sec: " .. summary.requests / summary.duration .. "\n")
end