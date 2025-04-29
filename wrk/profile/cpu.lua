--[[
WRK script for CPU-intensive testing - measures computational performance
]]--

-- Track statistics
requests = 0
responses = 0
errors = 0
valid_responses = 0

function request()
   -- Increment request counter
   requests = requests + 1
   
   -- Set complexity parameter (1-10, varying with each request)
   local complexity = requests % 10 + 1
   
   -- Set Accept header for JSON response
   wrk.headers["Accept"] = "application/json"
   
   -- Return formatted request with complexity parameter
   return wrk.format("GET", "/cpu-intensive?complexity=" .. complexity)
end

function response(status, headers, body)
   -- Track responses
   responses = responses + 1
   
   -- Count errors
   if status >= 400 then
      errors = errors + 1
   else
      -- Check for valid response
      if body and body:find("result") then
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