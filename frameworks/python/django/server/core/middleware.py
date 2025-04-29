"""
Custom middleware for the Django version of RG Profiler
"""
import time


class ResponseTimeMiddleware:
    """Middleware to measure response time"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Set start time
        request.start_time = time.time()
        
        # Initialize middleware chain with this middleware
        request.middleware_chain = [{
            'name': 'response_time',
            'timestamp': request.start_time
        }]
        
        # Process request
        response = self.get_response(request)
        
        # Add response time header
        response_time = time.time() - request.start_time
        response['X-Response-Time'] = str(response_time)
        
        return response


class CustomSecurityMiddleware:
    """Middleware for security checks"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Register this middleware's execution in the chain
        if hasattr(request, 'middleware_chain'):
            request.middleware_chain.append({
                'name': 'security',
                'timestamp': time.time()
            })
        
        # Example security check (in a real app, this would be more robust)
        user_agent = request.headers.get('User-Agent', '').lower()
        if 'vulnerability-scanner' in user_agent:
            # For profiling purposes, we just log but don't block
            pass
        
        return self.get_response(request)


class RateLimitMiddleware:
    """Middleware for rate limiting simulation"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_counts = {}
    
    def __call__(self, request):
        # Register this middleware's execution in the chain
        if hasattr(request, 'middleware_chain'):
            request.middleware_chain.append({
                'name': 'rate_limit',
                'timestamp': time.time()
            })
        
        # Get client IP (simplified)
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        
        # Simulate rate limiting check (no actual limiting for profiling)
        current_time = int(time.time())
        time_window = current_time - (current_time % 60)  # 1-minute window
        
        # Initialize or update request count
        if (ip, time_window) not in self.request_counts:
            self.request_counts[(ip, time_window)] = 1
        else:
            self.request_counts[(ip, time_window)] += 1
        
        # Clean up old entries (just to prevent memory leaks)
        self.request_counts = {k: v for k, v in self.request_counts.items() 
                              if k[1] >= time_window - 300}  # Keep last 5 minutes
        
        return self.get_response(request)
