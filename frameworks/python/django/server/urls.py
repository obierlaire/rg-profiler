"""
URL Configuration for the Django implementation in the RG Profiler framework
"""
from django.urls import path, re_path

from server.core import views

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
    
    # 6. Middleware Test
    path('middleware', views.middleware_endpoint, name='middleware'),
    
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
    
    # 18. Shutdown Endpoint
    path('shutdown', views.shutdown_endpoint, name='shutdown'),
    
    # Additional regex route for regex_heavy testing
    re_path(r'^regex-route/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/(?P<slug>[\w-]+)/$',
            views.regex_route_endpoint, name='regex_route'),
]
