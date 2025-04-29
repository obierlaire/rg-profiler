--[[
WRK script for header parsing testing - measures header processing performance
]]--

-- Track statistics
requests = 0
responses = 0
errors = 0
valid_responses = 0

function request()
   -- Increment request counter
   requests = requests + 1
   
   -- Set many custom headers to test header parsing
   wrk.headers["Accept"] = "application/json"
   wrk.headers["X-Custom-Header-1"] = "value1"
   wrk.headers["X-Custom-Header-2"] = "value2"
   wrk.headers["X-Custom-Header-3"] = "value3"
   wrk.headers["X-Custom-Header-4"] = "value4"
   wrk.headers["X-Custom-Header-5"] = "value5"
   wrk.headers["X-Custom-Header-6"] = "value6"
   wrk.headers["X-Custom-Header-7"] = "value7"
   wrk.headers["X-Custom-Header-8"] = "value8"
   wrk.headers["X-Custom-Header-9"] = "value9"
   wrk.headers["X-Custom-Header-10"] = "value10"
   wrk.headers["X-Device-Type"] = "mobile"
   wrk.headers["X-User-Agent"] = "WRK-Benchmark"
   wrk.headers["X-Requested-With"] = "XMLHttpRequest"
   wrk.headers["X-Forwarded-For"] = "10.0.0.1"
   wrk.headers["X-Forwarded-Proto"] = "https"
   
   -- Return formatted request
   return wrk.format("GET", "/header-parsing")
end

function response(status, headers, body)
   -- Track responses
   responses = responses + 1
   
   -- Count errors
   if status >= 400 then
      errors = errors + 1
   else
      -- Check if the response includes header info
      if body and body:find("headers") then
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