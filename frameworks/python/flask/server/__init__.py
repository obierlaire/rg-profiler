"""
Flask implementation for RG Profiler
"""
import json
import os
import random
import re
import time
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, jsonify, request, render_template, session, g

# Database imports
import psycopg2
import psycopg2.extras
import pymysql
import pymysql.cursors
from pymongo import MongoClient


def create_app(db_type, db_host, db_port, db_user, db_pass, db_name):
    """Create Flask application instance with all profiling endpoints"""
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = 'rg-profiler-secret-key'
    app.config['DB_TYPE'] = db_type
    app.config['DB_HOST'] = db_host
    app.config['DB_PORT'] = db_port
    app.config['DB_USER'] = db_user
    app.config['DB_PASS'] = db_pass
    app.config['DB_NAME'] = db_name
    
    # Session configuration
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
    
    # Setup database connection
    @app.before_request
    def before_request():
        """Setup database connection before each request if needed"""
        # Skip DB setup for endpoints that don't need it
        if request.path in ['/json', '/plaintext', '/complex-routing', 
                            '/middleware', '/header-parsing', '/regex-heavy',
                            '/cpu-intensive', '/memory-heavy', '/shutdown']:
            return
        
        # Create DB connection based on type
        if app.config['DB_TYPE'] == 'postgres':
            g.conn = psycopg2.connect(
                host=app.config['DB_HOST'],
                port=app.config['DB_PORT'],
                user=app.config['DB_USER'],
                password=app.config['DB_PASS'],
                database=app.config['DB_NAME']
            )
            g.cursor = g.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        elif app.config['DB_TYPE'] == 'mysql':
            g.conn = pymysql.connect(
                host=app.config['DB_HOST'],
                port=int(app.config['DB_PORT']),
                user=app.config['DB_USER'],
                password=app.config['DB_PASS'],
                database=app.config['DB_NAME'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            g.cursor = g.conn.cursor()
            
        elif app.config['DB_TYPE'] == 'mongodb':
            g.conn = MongoClient(
                host=app.config['DB_HOST'],
                port=int(app.config['DB_PORT']),
                username=app.config['DB_USER'],
                password=app.config['DB_PASS']
            )
            g.db = g.conn[app.config['DB_NAME']]
    
    @app.teardown_request
    def teardown_request(exception):
        """Close database connection after each request"""
        conn = getattr(g, 'conn', None)
        if conn is not None:
            conn.close()
    
    # Define middleware stack
    @app.before_request
    def middleware_logger():
        """Middleware: Request logger"""
        g.start_time = time.time()
        g.middleware_chain = [{'name': 'logger', 'timestamp': g.start_time}]
    
    @app.before_request
    def middleware_security():
        """Middleware: Security checks"""
        g.middleware_chain.append({
            'name': 'security',
            'timestamp': time.time()
        })
    
    @app.before_request
    def middleware_rate_limit():
        """Middleware: Rate limiting"""
        g.middleware_chain.append({
            'name': 'rate_limit',
            'timestamp': time.time()
        })
    
    @app.after_request
    def middleware_response_time(response):
        """Middleware: Calculate response time"""
        response_time = time.time() - g.start_time
        response.headers['X-Response-Time'] = str(response_time)
        return response
    
    # 1. JSON Serialization
    @app.route('/json', methods=['GET'])
    def json_endpoint():
        """Simple JSON serialization test"""
        return jsonify({
            'message': 'Hello, World!',
            'timestamp': datetime.now().isoformat(),
            'framework': 'flask'
        })
    
    # 2. Plaintext
    @app.route('/plaintext', methods=['GET'])
    def plaintext_endpoint():
        """Simple plaintext response test"""
        return 'Hello, World!', 200, {'Content-Type': 'text/plain'}
    
    # 3. Single Database Query
    @app.route('/db', methods=['GET'])
    def db_endpoint():
        """Single database query test"""
        world_id = random.randint(1, 10000)
        
        if app.config['DB_TYPE'] == 'postgres' or app.config['DB_TYPE'] == 'mysql':
            g.cursor.execute('SELECT * FROM world WHERE id = %s', (world_id,))
            world = g.cursor.fetchone()
            
        elif app.config['DB_TYPE'] == 'mongodb':
            world = g.db.world.find_one({'id': world_id})
            if world:
                # Convert ObjectId to string for JSON serialization
                world['_id'] = str(world['_id'])
                
        return jsonify(world)
    
    # 4. Multiple Database Queries
    @app.route('/queries', methods=['GET'])
    def queries_endpoint():
        """Multiple database queries test"""
        try:
            queries = int(request.args.get('queries', 1))
        except ValueError:
            queries = 1
            
        # Sanitize input
        queries = max(1, min(queries, 500))
        
        worlds = []
        for i in range(queries):
            world_id = random.randint(1, 10000)
            
            if app.config['DB_TYPE'] == 'postgres' or app.config['DB_TYPE'] == 'mysql':
                g.cursor.execute('SELECT * FROM world WHERE id = %s', (world_id,))
                world = g.cursor.fetchone()
                worlds.append(dict(world))
                
            elif app.config['DB_TYPE'] == 'mongodb':
                world = g.db.world.find_one({'id': world_id})
                if world:
                    # Convert ObjectId to string for JSON serialization
                    world['_id'] = str(world['_id'])
                    worlds.append(world)
        
        return jsonify(worlds)
    
    # 5. Complex Routing
    @app.route('/complex-routing/<id>/<name>/<param1>/<param2>', methods=['GET'])
    def complex_routing_endpoint(id, name, param1, param2):
        """Complex URL routing and parameter parsing test"""
        return jsonify({
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
    
    # 6. Middleware Test
    @app.route('/middleware', methods=['GET'])
    def middleware_endpoint():
        """Middleware chain overhead test"""
        # Add final middleware timestamp
        g.middleware_chain.append({
            'name': 'endpoint',
            'timestamp': time.time()
        })
        
        # Calculate time spent in each middleware
        times = []
        for i in range(1, len(g.middleware_chain)):
            prev = g.middleware_chain[i-1]
            curr = g.middleware_chain[i]
            times.append({
                'from': prev['name'],
                'to': curr['name'],
                'time_ms': (curr['timestamp'] - prev['timestamp']) * 1000
            })
        
        return jsonify({
            'middleware_chain': [m['name'] for m in g.middleware_chain],
            'times': times,
            'total_middleware_time_ms': (time.time() - g.start_time) * 1000
        })
    
    # 7. Simple Template
    @app.route('/template-simple', methods=['GET'])
    def template_simple_endpoint():
        """Simple template rendering test"""
        return render_template(
            'simple.html',
            title='Simple Template',
            message='Hello, World!',
            timestamp=datetime.now().isoformat()
        )
    
    # 8. Complex Template
    @app.route('/template-complex', methods=['GET'])
    def template_complex_endpoint():
        """Complex template rendering test with fortunes database"""
        if app.config['DB_TYPE'] == 'postgres' or app.config['DB_TYPE'] == 'mysql':
            g.cursor.execute('SELECT * FROM fortune')
            fortunes = g.cursor.fetchall()
            
        elif app.config['DB_TYPE'] == 'mongodb':
            fortunes = list(g.db.fortune.find())
            # Convert ObjectId to string for template rendering
            for fortune in fortunes:
                fortune['_id'] = str(fortune['_id'])
        
        # Add an additional fortune
        fortunes.append({
            'id': 0,
            'message': 'Additional fortune added at request time.'
        })
        
        # Sort fortunes by message
        fortunes = sorted(fortunes, key=lambda x: x['message'])
        
        return render_template(
            'complex.html',
            title='Fortunes',
            fortunes=fortunes
        )
    
    # 9. Session Write
    @app.route('/session-write', methods=['GET'])
    def session_write_endpoint():
        """Session creation and storage test"""
        # Create a session with various data types
        session['user_id'] = random.randint(1, 1000)
        session['username'] = f"user_{random.randint(1000, 9999)}"
        session['is_authenticated'] = True
        session['login_time'] = datetime.now().isoformat()
        session['preferences'] = {
            'theme': random.choice(['light', 'dark', 'system']),
            'language': random.choice(['en', 'fr', 'es', 'de', 'ja']),
            'notifications': random.choice([True, False])
        }
        
        return jsonify({
            'session_created': True,
            'session_id': session.sid if hasattr(session, 'sid') else None,
            'data': {
                'user_id': session['user_id'],
                'username': session['username'],
                'is_authenticated': session['is_authenticated'],
                'login_time': session['login_time']
            }
        })
    
    # 10. Session Read
    @app.route('/session-read', methods=['GET'])
    def session_read_endpoint():
        """Session retrieval test"""
        if 'user_id' not in session:
            return jsonify({'error': 'No session found'}), 404
        
        return jsonify({
            'session_found': True,
            'session_id': session.sid if hasattr(session, 'sid') else None,
            'data': {
                'user_id': session['user_id'],
                'username': session['username'],
                'is_authenticated': session['is_authenticated'],
                'login_time': session['login_time'],
                'preferences': session['preferences']
            }
        })
    
    # 11. Error Handling
    @app.route('/error-handling', methods=['GET'])
    def error_handling_endpoint():
        """Error handling and exception processing test"""
        error_type = request.args.get('type', 'none')
        
        try:
            if error_type == 'division':
                # Trigger division by zero
                1 / 0
            elif error_type == 'key':
                # Trigger key error
                d = {}
                d['nonexistent']
            elif error_type == 'type':
                # Trigger type error
                'string' + 42
            elif error_type == 'database':
                # Trigger database error
                if app.config['DB_TYPE'] == 'postgres' or app.config['DB_TYPE'] == 'mysql':
                    g.cursor.execute('SELECT * FROM nonexistent_table')
                else:
                    g.db.nonexistent_collection.find_one()
            elif error_type == 'custom':
                # Custom exception
                class CustomError(Exception):
                    pass
                raise CustomError("This is a custom error")
            else:
                # No error
                return jsonify({
                    'message': 'No error triggered',
                    'error_type': error_type
                })
        
        except Exception as e:
            app.logger.error(f"Error occurred: {str(e)}")
            return jsonify({
                'error': str(e),
                'error_type': error_type,
                'error_class': e.__class__.__name__,
                'handled': True
            }), 500
    
    # 12. Header Parsing
    @app.route('/header-parsing', methods=['GET'])
    def header_parsing_endpoint():
        """Header parsing test"""
        headers = {}
        for key, value in request.headers.items():
            headers[key] = value
        
        return jsonify({
            'headers': headers,
            'headers_count': len(headers),
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'accept': request.headers.get('Accept', 'Unknown'),
            'custom_headers': {
                k: v for k, v in headers.items() if k.startswith('X-')
            }
        })
    
    # 13. Regex Heavy
    @app.route('/regex-heavy', methods=['GET'])
    def regex_heavy_endpoint():
        """Regular expression intensive test"""
        # Get test string from query param or use default
        test_string = request.args.get('text', """
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
        
        return jsonify({
            'original': test_string,
            'results': results,
            'transformed': transformed,
            'match_count': sum(len(v) for v in results.values())
        })
    
    # 14. Serialization
    @app.route('/serialization', methods=['GET'])
    def serialization_endpoint():
        """Complex object serialization test"""
        if app.config['DB_TYPE'] == 'postgres' or app.config['DB_TYPE'] == 'mysql':
            g.cursor.execute('SELECT * FROM complex_data')
            items = g.cursor.fetchall()
            
        elif app.config['DB_TYPE'] == 'mongodb':
            items = list(g.db.complex_data.find())
            # Convert ObjectId to string for JSON serialization
            for item in items:
                item['_id'] = str(item['_id'])
        
        # Add additional metadata
        for item in items:
            if isinstance(item, dict):
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
            'items': items,
            'metadata': {
                'count': len(items),
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
                    'total': len(items),
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
        
        return jsonify(response)
    
    # 15. Deserialization
    @app.route('/deserialization', methods=['POST'])
    def deserialization_endpoint():
        """Complex object deserialization test"""
        try:
            # Parse JSON data
            data = request.get_json()
            
            # Validate structure
            if not data:
                return jsonify({
                    'error': 'No JSON data provided'
                }), 400
                
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
            
            return jsonify(processed)
            
        except Exception as e:
            return jsonify({
                'error': 'Error processing JSON data',
                'message': str(e)
            }), 400
    
    # 16. CPU Intensive
    @app.route('/cpu-intensive', methods=['GET'])
    def cpu_intensive_endpoint():
        """Compute-heavy operation to test CPU efficiency"""
        # Get complexity parameter (1-10)
        try:
            complexity = min(10, max(1, int(request.args.get('complexity', '5'))))
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
        
        return jsonify({
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
    
    # 17. Memory Heavy
    @app.route('/memory-heavy', methods=['GET'])
    def memory_heavy_endpoint():
        """Memory-intensive operation to test memory allocation performance"""
        # Get memory size parameter (1-10)
        try:
            size = min(10, max(1, int(request.args.get('size', '5'))))
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
        
        return jsonify({
            'memory': memory_stats,
            'meta': {
                'size_parameter': size,
                'base_size': base_size,
                'duration_seconds': duration
            }
        })
    
    # Return the app
    return app
