"""
Views implementation for Django RG Profiler endpoints
"""
import json
import os
import random
import re
import time
from datetime import datetime, timedelta

from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.contrib.sessions.models import Session
from django.conf import settings

from server.core.models import World, Fortune, User, ComplexData


def json_endpoint(request):
    """Simple JSON serialization test"""
    return JsonResponse({
        'message': 'Hello, World!',
        'timestamp': datetime.now().isoformat(),
        'framework': 'django'
    })


def plaintext_endpoint(request):
    """Simple plaintext response test"""
    return HttpResponse('Hello, World!', content_type='text/plain')


def db_endpoint(request):
    """Single database query test"""
    world_id = random.randint(1, 10000)
    
    try:
        # Use Django ORM to query the database
        world = World.objects.get(id=world_id)
        
        # Convert to dict for serialization
        result = {
            'id': world.id,
            'randomnumber': world.randomnumber
        }
        
        return JsonResponse(result)
    except World.DoesNotExist:
        return JsonResponse({'error': 'World not found'}, status=404)


def queries_endpoint(request):
    """Multiple database queries test"""
    try:
        queries = int(request.GET.get('queries', 1))
    except ValueError:
        queries = 1
        
    # Sanitize input
    queries = max(1, min(queries, 500))
    
    worlds = []
    for _ in range(queries):
        world_id = random.randint(1, 10000)
        try:
            world = World.objects.get(id=world_id)
            worlds.append({
                'id': world.id,
                'randomnumber': world.randomnumber
            })
        except World.DoesNotExist:
            pass
    
    return JsonResponse(worlds, safe=False)


def complex_routing_endpoint(request, id, name, param1, param2):
    """Complex URL routing and parameter parsing test"""
    return JsonResponse({
        'id': id,
        'name': name,
        'param1': param1,
        'param2': param2,
        'parsed': {
            'id_as_int': int(id) if id.isdigit() else None,
            'name_length': len(name),
            'params_hash': hash(param1 + param2)
        },
        'timestamp': datetime.now().isoformat()
    })


def middleware_endpoint(request):
    """Middleware chain overhead test"""
    # The middleware processing times are tracked by custom middleware
    middleware_chain = getattr(request, 'middleware_chain', [])
    
    # Add final endpoint timestamp
    middleware_chain.append({
        'name': 'endpoint',
        'timestamp': time.time()
    })
    
    # Calculate time spent in each middleware
    times = []
    for i in range(1, len(middleware_chain)):
        prev = middleware_chain[i-1]
        curr = middleware_chain[i]
        times.append({
            'from': prev['name'],
            'to': curr['name'],
            'time_ms': (curr['timestamp'] - prev['timestamp']) * 1000
        })
    
    return JsonResponse({
        'middleware_chain': [m['name'] for m in middleware_chain],
        'times': times,
        'total_middleware_time_ms': (time.time() - middleware_chain[0]['timestamp']) * 1000
    })


def template_simple_endpoint(request):
    """Simple template rendering test"""
    return render(
        request,
        'simple.html',
        {
            'title': 'Simple Template',
            'message': 'Hello, World!',
            'timestamp': datetime.now().isoformat()
        }
    )


def template_complex_endpoint(request):
    """Complex template rendering test with fortunes database"""
    # Get fortunes from the database
    fortunes = list(Fortune.objects.all().values())
    
    # Add an additional fortune
    fortunes.append({
        'id': 0,
        'message': 'Additional fortune added at request time.'
    })
    
    # Sort fortunes by message
    fortunes = sorted(fortunes, key=lambda x: x['message'])
    
    return render(
        request,
        'complex.html',
        {
            'title': 'Fortunes',
            'fortunes': fortunes
        }
    )


@csrf_exempt
def session_write_endpoint(request):
    """Session creation and storage test"""
    # Create a session with various data types
    request.session['user_id'] = random.randint(1, 1000)
    request.session['username'] = f"user_{random.randint(1000, 9999)}"
    request.session['is_authenticated'] = True
    request.session['login_time'] = datetime.now().isoformat()
    request.session['preferences'] = {
        'theme': random.choice(['light', 'dark', 'system']),
        'language': random.choice(['en', 'fr', 'es', 'de', 'ja']),
        'notifications': random.choice([True, False])
    }
    
    return JsonResponse({
        'session_created': True,
        'session_id': request.session.session_key,
        'data': {
            'user_id': request.session['user_id'],
            'username': request.session['username'],
            'is_authenticated': request.session['is_authenticated'],
            'login_time': request.session['login_time']
        }
    })


def session_read_endpoint(request):
    """Session retrieval test"""
    if 'user_id' not in request.session:
        return JsonResponse({'error': 'No session found'}, status=404)
    
    return JsonResponse({
        'session_found': True,
        'session_id': request.session.session_key,
        'data': {
            'user_id': request.session['user_id'],
            'username': request.session['username'],
            'is_authenticated': request.session['is_authenticated'],
            'login_time': request.session['login_time'],
            'preferences': request.session['preferences']
        }
    })


def error_handling_endpoint(request):
    """Error handling and exception processing test"""
    error_type = request.GET.get('type', 'none')
    
    try:
        if error_type == 'division':
            # Trigger division by zero
            result = 1 / 0
        elif error_type == 'key':
            # Trigger key error
            d = {}
            result = d['nonexistent']
        elif error_type == 'type':
            # Trigger type error
            result = 'string' + 42
        elif error_type == 'database':
            # Trigger database error
            with connection.cursor() as cursor:
                cursor.execute('SELECT * FROM nonexistent_table')
        elif error_type == 'custom':
            # Custom exception
            class CustomError(Exception):
                pass
            raise CustomError("This is a custom error")
        else:
            # No error
            return JsonResponse({
                'message': 'No error triggered',
                'error_type': error_type
            })
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error occurred: {str(e)}")
        
        return JsonResponse({
            'error': str(e),
            'error_type': error_type,
            'error_class': e.__class__.__name__,
            'handled': True
        }, status=500)


def header_parsing_endpoint(request):
    """Header parsing test"""
    headers = {}
    for key, value in request.headers.items():
        headers[key] = value
    
    return JsonResponse({
        'headers': headers,
        'headers_count': len(headers),
        'user_agent': request.headers.get('User-Agent', 'Unknown'),
        'accept': request.headers.get('Accept', 'Unknown'),
        'custom_headers': {
            k: v for k, v in headers.items() if k.startswith('X-')
        }
    })


def regex_heavy_endpoint(request):
    """Regular expression intensive test"""
    # Get test string from query param or use default
    test_string = request.GET.get('text', """
        This is a test string with email addresses like test@example.com
        and phone numbers like (123) 456-7890 or URLs like https://example.com
        and dates like 2023-05-30 or IP addresses like 192.168.1.1
        and code snippets like `print("hello")` or JSON like {"key": "value"}
    """)
    
    # Apply a series of regular expressions
    results = {}
    
    # 1. Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    results['emails'] = re.findall(email_pattern, test_string)
    
    # 2. Phone numbers
    phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    results['phones'] = re.findall(phone_pattern, test_string)
    
    # 3. URLs
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    results['urls'] = re.findall(url_pattern, test_string)
    
    # 4. Dates
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    results['dates'] = re.findall(date_pattern, test_string)
    
    # 5. IP addresses
    ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
    results['ips'] = re.findall(ip_pattern, test_string)
    
    # 6. Code snippets
    code_pattern = r'`([^`]+)`'
    results['code_snippets'] = re.findall(code_pattern, test_string)
    
    # 7. JSON-like patterns
    json_pattern = r'{[^}]+}'
    results['json_patterns'] = re.findall(json_pattern, test_string)
    
    # Complex pattern replacement
    transformed = re.sub(
        r'(\b\w+\b)', 
        lambda m: m.group(1).upper() if len(m.group(1)) > 4 else m.group(1),
        test_string
    )
    
    return JsonResponse({
        'original': test_string,
        'results': results,
        'transformed': transformed,
        'match_count': sum(len(v) for v in results.values())
    })


def serialization_endpoint(request):
    """Complex object serialization test"""
    # Get complex data from the database
    complex_data = list(ComplexData.objects.all().values())
    
    # Add additional metadata
    for item in complex_data:
        item['processed'] = True
        item['score'] = random.random()
        item['labels'] = [f"label_{i}" for i in range(random.randint(1, 5))]
        item['related'] = [{
            'id': random.randint(1, 100),
            'name': f"related_item_{random.randint(1, 100)}",
            'similarity': random.random()
        } for _ in range(random.randint(1, 3))]
    
    # Create a complex nested structure
    response = {
        'items': complex_data,
        'metadata': {
            'count': len(complex_data),
            'timestamp': datetime.now().isoformat(),
            'processing': {
                'duration_ms': random.randint(10, 100),
                'status': 'complete',
                'steps': [
                    {'name': 'fetch', 'duration_ms': random.randint(5, 50)},
                    {'name': 'transform', 'duration_ms': random.randint(5, 50)},
                    {'name': 'enrich', 'duration_ms': random.randint(5, 50)}
                ]
            },
            'pagination': {
                'total': len(complex_data),
                'page': 1,
                'per_page': 10,
                'pages': 1
            }
        },
        'settings': {
            'sort': 'name',
            'direction': 'asc',
            'filters': {
                'tags': [],
                'date_range': {
                    'start': None,
                    'end': None
                }
            },
            'display': {
                'columns': ['name', 'data', 'tags', 'created_at'],
                'theme': 'default'
            }
        }
    }
    
    return JsonResponse(response)


@csrf_exempt
def deserialization_endpoint(request):
    """Complex object deserialization test"""
    try:
        # Parse JSON data
        data = json.loads(request.body)
        
        # Validate structure
        if not data:
            return JsonResponse({
                'error': 'No JSON data provided'
            }, status=400)
            
        # Process the data
        processed = {
            'received': {
                'item_count': len(data.get('items', [])),
                'keys': list(data.keys()),
                'nested_keys': {k: list(v.keys()) if isinstance(v, dict) else None for k, v in data.items()},
                'types': {k: type(v).__name__ for k, v in data.items()}
            },
            'validation': {
                'valid': True,
                'errors': []
            },
            'transformed': {
                'uppercase_keys': {k.upper(): v for k, v in data.items() if isinstance(v, (str, int, float, bool))},
                'item_names': [item.get('name') for item in data.get('items', []) if isinstance(item, dict)],
                'tag_counts': {}
            }
        }
        
        # Count tags
        for item in data.get('items', []):
            if isinstance(item, dict) and 'tags' in item and isinstance(item['tags'], list):
                for tag in item['tags']:
                    if tag in processed['transformed']['tag_counts']:
                        processed['transformed']['tag_counts'][tag] += 1
                    else:
                        processed['transformed']['tag_counts'][tag] = 1
        
        return JsonResponse(processed)
        
    except Exception as e:
        return JsonResponse({
            'error': 'Error processing JSON data',
            'message': str(e)
        }, status=400)


def cpu_intensive_endpoint(request):
    """Compute-heavy operation to test CPU efficiency"""
    # Get complexity parameter (1-10)
    try:
        complexity = min(10, max(1, int(request.GET.get('complexity', '5'))))
    except ValueError:
        complexity = 5
    
    # Scale number of operations based on complexity
    operations = 10000 * complexity
    
    # Fibonacci calculation (recursive with memoization)
    memo = {}
    def fibonacci(n):
        if n in memo:
            return memo[n]
        if n <= 2:
            return 1
        memo[n] = fibonacci(n-1) + fibonacci(n-2)
        return memo[n]
    
    # Prime number calculation
    def is_prime(n):
        if n <= 1:
            return False
        if n <= 3:
            return True
        if n % 2 == 0 or n % 3 == 0:
            return False
        i = 5
        while i * i <= n:
            if n % i == 0 or n % (i + 2) == 0:
                return False
            i += 6
        return True
    
    # Matrix multiplication
    def matrix_multiply(a, b):
        rows_a = len(a)
        cols_a = len(a[0])
        cols_b = len(b[0])
        result = [[0 for _ in range(cols_b)] for _ in range(rows_a)]
        for i in range(rows_a):
            for j in range(cols_b):
                for k in range(cols_a):
                    result[i][j] += a[i][k] * b[k][j]
        return result
    
    # Quick sort implementation
    def quick_sort(arr):
        if len(arr) <= 1:
            return arr
        pivot = arr[len(arr) // 2]
        left = [x for x in arr if x < pivot]
        middle = [x for x in arr if x == pivot]
        right = [x for x in arr if x > pivot]
        return quick_sort(left) + middle + quick_sort(right)
    
    # Perform CPU-intensive calculations
    start_time = time.time()
    
    # 1. Calculate Fibonacci numbers
    fib_result = fibonacci(20 + complexity)
    
    # 2. Find prime numbers
    primes = []
    for i in range(1000 * complexity):
        if is_prime(i):
            primes.append(i)
    
    # 3. Matrix operations
    size = 3 + complexity // 2
    matrix_a = [[random.random() for _ in range(size)] for _ in range(size)]
    matrix_b = [[random.random() for _ in range(size)] for _ in range(size)]
    matrix_result = matrix_multiply(matrix_a, matrix_b)
    
    # 4. Sorting
    random_list = [random.randint(1, 10000) for _ in range(1000 * complexity)]
    sorted_list = quick_sort(random_list)
    
    # 5. String operations
    text = "The quick brown fox jumps over the lazy dog" * (100 * complexity)
    words = text.split()
    word_freq = {}
    for word in words:
        if word in word_freq:
            word_freq[word] += 1
        else:
            word_freq[word] = 1
    
    duration = time.time() - start_time
    
    return JsonResponse({
        'result': {
            'fibonacci': fib_result,
            'prime_count': len(primes),
            'matrix_size': size,
            'sorted_list_length': len(sorted_list),
            'unique_words': len(word_freq),
            'top_words': sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        },
        'meta': {
            'complexity': complexity,
            'operations': operations,
            'duration_seconds': duration
        }
    })


def memory_heavy_endpoint(request):
    """Memory-intensive operation to test memory allocation performance"""
    # Get memory size parameter (1-10)
    try:
        size = min(10, max(1, int(request.GET.get('size', '5'))))
    except ValueError:
        size = 5
    
    # Scale memory usage based on size parameter
    base_size = 10000 * size
    
    # Perform memory-intensive operations
    start_time = time.time()
    
    # 1. Large list creation
    large_list = list(range(base_size))
    
    # 2. Dictionary with many entries
    large_dict = {f"key_{i}": f"value_{i}" for i in range(base_size // 10)}
    
    # 3. Nested data structures
    nested_structures = []
    for i in range(size * 10):
        nested_structures.append({
            'id': i,
            'data': {
                'values': [random.random() for _ in range(100)],
                'text': 'x' * (100 * size),
                'nested': {
                    'level1': {
                        'level2': {
                            'level3': [0] * (10 * size)
                        }
                    }
                }
            }
        })
    
    # 4. String manipulations
    strings = []
    for i in range(size * 50):
        strings.append('x' * 1000)
    joined_string = ''.join(strings[:10])
    
    # 5. Object duplication
    duplicate_objects = []
    template = {
        'name': 'test',
        'value': random.random(),
        'data': [random.randint(1, 100) for _ in range(100)],
        'timestamp': time.time(),
        'text': 'x' * 100
    }
    for i in range(base_size // 10):
        duplicate_objects.append(template.copy())
    
    duration = time.time() - start_time
    
    # Calculate memory stats (simplified approximation)
    memory_stats = {
        'large_list_size': len(large_list),
        'large_dict_size': len(large_dict),
        'nested_structures': len(nested_structures),
        'string_count': len(strings),
        'duplicate_objects': len(duplicate_objects),
        'approx_mb': (
            len(large_list) * 8 +                      # 64-bit integers
            len(large_dict) * 100 +                    # keys and values
            len(nested_structures) * 1000 * size +     # nested structures
            sum(len(s) for s in strings[:100]) +       # strings
            len(duplicate_objects) * 500               # duplicate objects
        ) / (1024 * 1024)  # Convert to MB
    }
    
    # Clean up to release memory
    del large_list
    del large_dict
    del nested_structures
    del strings
    del duplicate_objects
    
    return JsonResponse({
        'memory': memory_stats,
        'meta': {
            'size_parameter': size,
            'base_size': base_size,
            'duration_seconds': duration
        }
    })


def regex_route_endpoint(request, year, month, day, slug):
    """Special regex route handler for testing complex URL patterns"""
    return JsonResponse({
        'type': 'regex_route',
        'date': f"{year}-{month}-{day}",
        'slug': slug,
        'url': request.build_absolute_uri()
    })


def shutdown_endpoint(request):
    """Special endpoint for graceful termination"""
    response = JsonResponse({
        'status': 'shutting_down',
        'timestamp': datetime.now().isoformat()
    })
    
    # Schedule a shutdown after response is sent
    import threading
    def shutdown_server():
        import time
        import os
        import signal
        
        # Short delay to ensure response is sent
        time.sleep(0.5)
        
        # Send termination signal
        os.kill(os.getpid(), signal.SIGTERM)
    
    threading.Thread(target=shutdown_server).start()
    
    return response
