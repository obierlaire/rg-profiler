--[[
WRK script for JSON energy testing - maximizes reproducibility
Tests either completely with or without sessions to demonstrate optimization impacts
]]--

-- Track statistics
local request_counter = 0
local responses = 0
local errors = 0
local valid_json = 0
local session_used = 0
local session_skipped = 0

-- Configuration
local use_session = false  -- IMPORTANT: Session mode toggle
                          -- Set to TRUE to test WITH session initialization (baseline)
                          -- Set to FALSE to test WITHOUT session (optimized path)

-- NOTE: Each test run should use either all session requests or all non-session requests
-- for the most accurate energy measurements and clear performance comparison.
-- Run the test twice (once with each setting) to compare the difference.

function request()
   -- Increment request counter
   request_counter = request_counter + 1
   
   -- Set Accept header for JSON response
   wrk.headers["Accept"] = "application/json"
   
   -- Determine URL based on the session mode (deterministic for entire test)
   local url = "/json"
   if use_session then
      url = "/json?use_session=1"
      session_used = session_used + 1
      
      -- Add a cookie header to simulate a session cookie
      -- This makes the test more realistic for session usage
      wrk.headers["Cookie"] = "session=mock-session-id-for-testing"
   else
      session_skipped = session_skipped + 1
   end
   
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
   io.write("SESSION MODE: " .. (use_session and "WITH SESSION (baseline)" or "WITHOUT SESSION (optimized)") .. "\n")
   io.write("======================================================\n")
   io.write("Requests: " .. requests.total .. ", Responses: " .. responses)
   io.write(", Valid JSON: " .. valid_json)
   io.write(", Errors: " .. errors .. "\n")
   
   -- Session statistics
   if use_session then
      io.write("Session requests: " .. session_used .. " (100%)\n")
   else
      io.write("Non-session requests: " .. session_skipped .. " (100%)\n")
   end
   
   -- Performance statistics
   io.write("Avg Latency: " .. string.format("%.2f", latency.mean / 1000) .. "ms")
   io.write(", Max Latency: " .. string.format("%.2f", latency.max / 1000) .. "ms\n")
   io.write("Requests/sec: " .. string.format("%.2f", requests.rate) .. "\n")
end