"""
URL Configuration for the Django implementation in the RG Profiler framework
"""
from django.urls import path, re_path

from server import views  # Updated import path

urlpatterns = [
    # 1. JSON Serialization
    path('json', views.json_endpoint, name='json'),
    
    # 2. Plaintext
    path('plaintext', views.plaintext_endpoint, name='plaintext'),
    
    # 3. Single Database Query
    path('db', views.db_endpoint, name='db'),
    
    # 4. Multiple Database Queries
    path('queries', views.queries_endpoint, name='queries'),
    
    # 5. Complex Routing
    path('complex-routing/<str:id>/<str:name>/<str:param1>/<str:param2>', 
         views.complex_routing_endpoint, name='complex_routing'),
    
    # 6. Middleware and Advanced Middleware Tests
    path('middleware', views.middleware_endpoint, name='middleware'),
    path('middleware-advanced', views.middleware_advanced_endpoint, name='middleware_advanced'),
    
    # 7. Simple Template
    path('template-simple', views.template_simple_endpoint, name='template_simple'),
    
    # 8. Complex Template
    path('template-complex', views.template_complex_endpoint, name='template_complex'),
    
    # 9. Session Write
    path('session-write', views.session_write_endpoint, name='session_write'),
    
    # 10. Session Read
    path('session-read', views.session_read_endpoint, name='session_read'),
    
    # 11. Error Handling
    path('error-handling', views.error_handling_endpoint, name='error_handling'),
    path('errors', views.error_handling_endpoint, name='errors'),  # Alias for the same endpoint
    
    # 12. Header Parsing
    path('header-parsing', views.header_parsing_endpoint, name='header_parsing'),
    
    # 13. Regex Heavy
    path('regex-heavy', views.regex_heavy_endpoint, name='regex_heavy'),
    
    # 14. Serialization
    path('serialization', views.serialization_endpoint, name='serialization'),
    
    # 15. Deserialization
    path('deserialization', views.deserialization_endpoint, name='deserialization'),
    
    # 16. CPU Intensive
    path('cpu-intensive', views.cpu_intensive_endpoint, name='cpu_intensive'),
    
    # 17. Memory Heavy
    path('memory-heavy', views.memory_heavy_endpoint, name='memory_heavy'),
    
    # 18. Mixed Workload
    path('mixed-workload', views.mixed_workload_endpoint, name='mixed_workload'),
    
    # 19. I/O Operations
    path('io-ops', views.io_ops_endpoint, name='io_ops'),
    
    # 20. Database Connection Pool
    path('database-connection-pool', views.database_connection_pool_endpoint, name='database_connection_pool'),
    
    # 21. CPU State Transition
    path('cpu-state-transition', views.cpu_state_transition_endpoint, name='cpu_state_transition'),
    
    # 22. Streaming responses
    path('streaming', views.streaming_endpoint, name='streaming'),
    path('streaming/non-streaming', views.non_streaming_endpoint, name='non_streaming'),
    
    # 23. Shutdown Endpoint
    path('shutdown', views.shutdown_endpoint, name='shutdown'),
    
    # Additional regex route for regex_heavy testing
    re_path(r'^regex-route/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[\w-]+)/$',
            views.regex_route_endpoint, name='regex_route'),
    
    # Advanced routing tests
    path('routing', views.routing_endpoint, name='routing'),
    path('routing/<path:path>', views.routing_endpoint, name='routing_with_path'),
]