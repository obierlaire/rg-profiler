--[[
WRK script for complex template rendering testing
]]--

-- Track statistics
requests = 0
responses = 0
errors = 0
html_responses = 0

function request()
   -- Increment request counter
   requests = requests + 1
   
   -- Set Accept header for HTML response
   wrk.headers["Accept"] = "text/html"
   
   -- Return formatted request
   return wrk.format("GET", "/template-complex")
end

function response(status, headers, body)
   -- Track responses
   responses = responses + 1
   
   -- Count errors
   if status >= 400 then
      errors = errors + 1
   else
      -- Check if response is HTML
      if body and (body:find("<!DOCTYPE") or body:find("<html") or body:find("<body")) then
         html_responses = html_responses + 1
      end
   end
end

function done(summary, latency, requests)
   -- Print summary stats
   io.write("Requests: " .. requests.total .. ", Responses: " .. responses)
   io.write(", HTML responses: " .. html_responses)
   io.write(", Errors: " .. errors)
   io.write(", Avg Latency: " .. string.format("%.2f", latency.mean / 1000) .. "ms")
   io.write(", Max Latency: " .. string.format("%.2f", latency.max / 1000) .. "ms\n")
end