--[[
Basic WRK script for standard benchmarking
]]--

-- Track statistics
requests = 0
responses = 0
errors = 0

function request()
   -- Increment request counter
   requests = requests + 1
   
   -- Use path from environment variable or default to "/"
   local path = wrk.path or "/"
   
   -- Return formatted request
   return wrk.format("GET", path)
end

function response(status, headers, body)
   -- Track responses
   responses = responses + 1
   
   -- Count errors
   if status >= 400 then
      errors = errors + 1
   end
end

function done(summary, latency, requests)
   -- Print summary stats
   io.write("Requests: " .. requests.total .. ", Responses: " .. responses)
   io.write(", Errors: " .. errors)
   io.write(", Avg Latency: " .. string.format("%.2f", latency.mean / 1000) .. "ms")
   io.write(", Max Latency: " .. string.format("%.2f", latency.max / 1000) .. "ms\n")
end