--[[
WRK script for plaintext energy testing - most reproducible response
]]--

-- Track statistics
local request_counter = 0
local responses = 0
local errors = 0
local plaintext_responses = 0

function request()
   -- Increment request counter
   request_counter = request_counter + 1
   
   -- Set Accept header for plain text response
   wrk.headers["Accept"] = "text/plain"
   
   -- Return formatted request
   return wrk.format("GET", "/plaintext")
end

function response(status, headers, body)
   -- Track responses
   responses = responses + 1
   
   -- Count errors
   if status >= 400 then
      errors = errors + 1
   else
      -- Verify response is the expected plaintext
      if body and body == "Hello, World!" then
         plaintext_responses = plaintext_responses + 1
      end
   end
end

function done(summary, latency, requests)
   -- Print summary stats
   io.write("Requests: " .. requests.total .. ", Responses: " .. responses)
   io.write(", Valid Plaintext: " .. plaintext_responses)
   io.write(", Errors: " .. errors)
   io.write(", Avg Latency: " .. string.format("%.2f", latency.mean / 1000) .. "ms")
   io.write(", Max Latency: " .. string.format("%.2f", latency.max / 1000) .. "ms\n")
end