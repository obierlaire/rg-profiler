--[[
WRK script for multiple database queries testing
]]--

-- Track statistics
requests = 0
responses = 0
errors = 0
valid_json = 0

function request()
   -- Increment request counter
   requests = requests + 1
   
   -- Set Accept header for JSON response
   wrk.headers["Accept"] = "application/json"
   
   -- Query parameters
   local query_count = os.getenv("QUERY_COUNT") or "20"
   
   -- Return formatted request
   return wrk.format("GET", "/queries?queries=" .. query_count)
end

function response(status, headers, body)
   -- Track responses
   responses = responses + 1
   
   -- Count errors
   if status >= 400 then
      errors = errors + 1
   else
      -- Validate JSON response is an array
      if body and body:find("%[") and body:find("%]") then
         valid_json = valid_json + 1
      end
   end
end

function done(summary, latency, requests)
   -- Print summary stats
   io.write("Requests: " .. requests.total .. ", Responses: " .. responses)
   io.write(", Valid responses: " .. valid_json)
   io.write(", Errors: " .. errors)
   io.write(", Avg Latency: " .. string.format("%.2f", latency.mean / 1000) .. "ms")
   io.write(", Max Latency: " .. string.format("%.2f", latency.max / 1000) .. "ms\n")
end