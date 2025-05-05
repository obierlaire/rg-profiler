"""
Flask implementation for RG Profiler
"""
import json
import os
import random
import re
import time
import io
import csv
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, jsonify, request, render_template, session, g, Response, stream_with_context, abort, make_response

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
                            '/middleware', '/middleware-advanced', '/header-parsing', '/regex-heavy',
                            '/cpu-intensive', '/memory-heavy', '/shutdown', '/streaming', '/errors',
                            '/routing', '/io-ops', '/mixed-workload']:
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
        
        # Simple security check example
        if request.path == '/middleware-advanced' and request.args.get('skip_security') != 'true':
            # Simulate security check processing
            time.sleep(0.005)  # 5ms penalty
    
    @app.before_request
    def middleware_rate_limit():
        """Middleware: Rate limiting"""
        g.middleware_chain.append({
            'name': 'rate_limit',
            'timestamp': time.time()
        })
        
        # Simple rate limiting example
        if request.path == '/middleware-advanced' and request.args.get('simulate_rate_limit') == 'true':
            # Simulate rate limit processing
            time.sleep(0.01)  # 10ms penalty
    
    @app.before_request
    def middleware_request_transformation():
        """Middleware: Request transformation"""
        if hasattr(g, 'middleware_chain'):
            g.middleware_chain.append({
                'name': 'request_transform',
                'timestamp': time.time()
            })
            
        if request.path == '/middleware-advanced':
            # Store original request data for manipulation
            g.original_headers = {k: v for k, v in request.headers.items()}
            g.original_args = request.args.copy()
            
            # Add custom attribute to the request context
            g.transformed_request = True
            
            # Simulate processing time for transformation
            if request.args.get('transform_heavy') == 'true':
                time.sleep(0.015)  # 15ms for heavy transformation
    
    @app.after_request
    def middleware_response_transformation(response):
        """Middleware: Response transformation"""
        if hasattr(g, 'middleware_chain'):
            # Add timing point
            g.middleware_chain.append({
                'name': 'response_transform',
                'timestamp': time.time()
            })
            
        if request.path == '/middleware-advanced' and request.args.get('transform_response') == 'true':
            # Add headers to indicate response was transformed
            response.headers['X-Response-Transformed'] = 'true'
            
            # Simulate response transformation processing time
            time.sleep(0.008)  # 8ms penalty
            
        return response
    
    @app.after_request
    def middleware_response_time(response):
        """Middleware: Calculate response time"""
        if hasattr(g, 'start_time'):
            response_time = time.time() - g.start_time
            response.headers['X-Response-Time'] = str(response_time)
            
            # Add final timing point
            if hasattr(g, 'middleware_chain'):
                g.middleware_chain.append({
                    'name': 'response_time',
                    'timestamp': time.time()
                })
                
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
    
    # 5. Original Complex Routing
    @app.route('/complex-routing/<id>/<name>/<param1>/<param2>', methods=['GET'])
    def complex_routing_endpoint(id, n, param1, param2):
        """Original complex URL routing and parameter parsing test"""
        return jsonify({
            'id': id,
            'name': n,
            'param1': param1,
            'param2': param2,
            'parsed': {
                'id_as_int': int(id) if id.isdigit() else None,
                'name_length': len(n),
                'params_hash': hash(param1 + param2)
            },
            'timestamp': datetime.now().isoformat()
        })
    
    # 5B. Enhanced Complex Routing with Deterministic Patterns
    @app.route('/routing', methods=['GET'])
    @app.route('/routing/<path:path>', methods=['GET'])
    def routing_advanced_endpoint(path=None):
        """Advanced routing test with path parameters and query strings"""
        # Get all query parameters
        args = dict(request.args)
        
        # Parse the path
        segments = []
        params = {}
        
        if path:
            # Split by '/' and analyze each segment
            parts = path.split('/')
            for i, part in enumerate(parts):
                segments.append({
                    'index': i,
                    'value': part,
                    'type': 'numeric' if part.isdigit() else 'string'
                })
                
                # Extract parameters from path segments
                if i == 0 and part.isdigit():
                    params['id'] = int(part)
                elif i == 1:
                    params['resource'] = part
                elif i >= 2 and i % 2 == 0 and i + 1 < len(parts):
                    # Every even-indexed segment followed by another segment
                    # is treated as a key-value pair
                    params[part] = parts[i + 1]
        
        # Get processing flags
        complexity = int(request.args.get('complexity', '1'))
        delay = float(request.args.get('delay', '0'))
        
        # Cap values for safety
        complexity = min(max(1, complexity), 5)
        delay = min(max(0, delay), 0.1)
        
        # Optional processing delay
        if delay > 0:
            time.sleep(delay)
        
        # Perform route parsing and type conversions
        result = {
            'path': path,
            'segments': segments,
            'params': params,
            'query_args': args,
            'method': request.method,
            'timestamp': datetime.now().isoformat(),
        }
        
        # Add simulated route matching complexity
        if complexity > 1:
            parsed_results = []
            
            # Generate dummy route matching attempts
            for i in range(complexity):
                parsed_results.append({
                    'pattern': f'/routing/{i}/<param>/<type:path>',
                    'matched': i == 0 and path and path.startswith(str(i)),
                    'weight': complexity - i,
                    'processing_order': i + 1
                })
            
            result['route_analysis'] = {
                'patterns_checked': complexity,
                'matching_pattern': f'/routing/{path}' if path else '/routing',
                'parsed_results': parsed_results
            }
        
        # Add URL parameter type conversion examples
        if path and segments:
            conversions = {}
            
            for segment in segments:
                if segment['type'] == 'numeric':
                    val = segment['value']
                    conversions[f"{val}_int"] = int(val)
                    conversions[f"{val}_float"] = float(val)
                elif segment['value'].lower() in ('true', 'false'):
                    conversions[f"{segment['value']}_bool"] = segment['value'].lower() == 'true'
                elif segment['value'].count('-') == 2 and len(segment['value']) >= 8:
                    # Attempt date parsing for YYYY-MM-DD format
                    try:
                        parts = segment['value'].split('-')
                        if len(parts) == 3 and all(p.isdigit() for p in parts):
                            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                            if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                                conversions[f"{segment['value']}_date"] = segment['value']
                    except:
                        pass
            
            if conversions:
                result['type_conversions'] = conversions
        
        return jsonify(result)
    
    # 6. Basic Middleware Test
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
        
    # 6B. Advanced Middleware Test
    @app.route('/middleware-advanced', methods=['GET'])
    def middleware_advanced_endpoint():
        """Advanced middleware test with configurable behaviors"""
        # Add endpoint timestamp
        g.middleware_chain.append({
            'name': 'endpoint',
            'timestamp': time.time()
        })
        
        # Get middleware configuration from query parameters
        config = {
            'skip_security': request.args.get('skip_security') == 'true',
            'simulate_rate_limit': request.args.get('simulate_rate_limit') == 'true',
            'transform_heavy': request.args.get('transform_heavy') == 'true',
            'transform_response': request.args.get('transform_response') == 'true',
            'add_headers': request.args.get('add_headers', '').split(',') if request.args.get('add_headers') else [],
            'sleep_time': float(request.args.get('sleep_time', 0)),
        }
        
        # Optional endpoint processing time
        if config['sleep_time'] > 0:
            time.sleep(min(config['sleep_time'], 0.1))  # Cap at 100ms for safety
            
        # Build middleware analysis
        times = []
        for i in range(1, len(g.middleware_chain)):
            prev = g.middleware_chain[i-1]
            curr = g.middleware_chain[i]
            times.append({
                'from': prev['name'],
                'to': curr['name'],
                'time_ms': (curr['timestamp'] - prev['timestamp']) * 1000
            })
            
        # Create response with detailed middleware metrics
        response_data = {
            'middleware_chain': [m['name'] for m in g.middleware_chain],
            'times': times,
            'total_middleware_time_ms': (time.time() - g.start_time) * 1000,
            'config': config,
            'request_was_transformed': hasattr(g, 'transformed_request'),
            'original_headers': getattr(g, 'original_headers', {}),
            'original_args': dict(getattr(g, 'original_args', {})),
            'timestamp': datetime.now().isoformat()
        }
        
        # Prepare response
        response = jsonify(response_data)
        
        # Add custom headers if requested
        for header in config['add_headers']:
            if header:
                response.headers[f'X-Custom-{header}'] = 'test-value'
                
        return response
    
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
    
    # Streaming Response Tests
    @app.route('/streaming', methods=['GET'])
    def streaming_endpoint():
        """Test for streaming response performance and energy usage"""
        # Get parameters
        size = int(request.args.get('size', 1000))  # Data size in KB
        chunk_size = int(request.args.get('chunk_size', 64))  # Chunk size in KB
        delay = float(request.args.get('delay', 0))  # Delay between chunks in seconds
        streaming_mode = request.args.get('mode', 'json')  # Mode: json, csv, plaintext
        
        # Cap sizes for safety
        size = min(max(1, size), 10000)  # 1KB to 10MB
        chunk_size = min(max(1, chunk_size), 1024)  # 1KB to 1MB
        delay = min(max(0, delay), 0.1)  # 0 to 100ms
        
        # Convert KB to bytes
        size_bytes = size * 1024
        chunk_bytes = chunk_size * 1024
        
        # Calculate number of chunks
        chunks = (size_bytes + chunk_bytes - 1) // chunk_bytes  # Ceiling division
        
        if streaming_mode == 'json':
            # JSON streaming
            def generate_json():
                # Start with array open bracket
                yield '[\n'
                
                for i in range(chunks):
                    # Generate a chunk of JSON data
                    chunk_items = []
                    items_per_chunk = max(1, chunk_bytes // 100)  # Approximate size per item
                    
                    for j in range(items_per_chunk):
                        idx = i * items_per_chunk + j
                        item = {
                            'id': idx,
                            'value': random.random(),
                            'name': f'item_{idx}',
                            'timestamp': datetime.now().isoformat(),
                            'data': ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(20))
                        }
                        chunk_items.append(json.dumps(item))
                    
                    # Join items with commas
                    chunk_data = ',\n'.join(chunk_items)
                    
                    # Add comma for all but the last chunk
                    if i < chunks - 1:
                        chunk_data += ','
                    
                    yield chunk_data + '\n'
                    
                    # Add optional delay between chunks
                    if delay > 0:
                        time.sleep(delay)
                
                # Close the array
                yield ']\n'
            
            # Return streaming response with the right content type
            return Response(
                stream_with_context(generate_json()),
                content_type='application/json'
            )
            
        elif streaming_mode == 'csv':
            # CSV streaming
            def generate_csv():
                # Generate CSV header
                yield 'id,value,name,timestamp,data\n'
                
                total_rows = size_bytes // 100  # Approximate size per row
                rows_per_chunk = max(1, chunk_bytes // 100)
                
                for i in range(0, total_rows, rows_per_chunk):
                    # Create StringIO buffer for CSV writer
                    output = io.StringIO()
                    writer = csv.writer(output)
                    
                    # Generate rows for this chunk
                    for j in range(rows_per_chunk):
                        if i + j >= total_rows:
                            break
                            
                        row_id = i + j
                        row = [
                            row_id,
                            random.random(),
                            f'item_{row_id}',
                            datetime.now().isoformat(),
                            ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(20))
                        ]
                        writer.writerow(row)
                    
                    # Get the chunk data and reset the buffer
                    chunk_data = output.getvalue()
                    output.close()
                    
                    yield chunk_data
                    
                    # Add optional delay between chunks
                    if delay > 0:
                        time.sleep(delay)
            
            # Return streaming response with the right content type
            return Response(
                stream_with_context(generate_csv()),
                content_type='text/csv'
            )
            
        else:  # plaintext
            # Plaintext streaming
            def generate_plaintext():
                lines_per_chunk = max(1, chunk_bytes // 80)  # Approximate 80 chars per line
                total_lines = size_bytes // 80
                
                for i in range(0, total_lines, lines_per_chunk):
                    chunk_lines = []
                    
                    for j in range(lines_per_chunk):
                        if i + j >= total_lines:
                            break
                            
                        line_id = i + j
                        # Generate a line with ID, timestamp and random data
                        line = f"Line {line_id}: {datetime.now().isoformat()} - "
                        # Fill the rest with random characters to reach ~80 chars
                        line += ''.join(random.choice('abcdefghijklmnopqrstuvwxyz ') 
                                       for _ in range(80 - len(line)))
                        chunk_lines.append(line)
                    
                    # Join lines with newlines
                    chunk_data = '\n'.join(chunk_lines) + '\n'
                    
                    yield chunk_data
                    
                    # Add optional delay between chunks
                    if delay > 0:
                        time.sleep(delay)
            
            # Return streaming response with the right content type
            return Response(
                stream_with_context(generate_plaintext()),
                content_type='text/plain'
            )
    
    # Non-streaming comparison endpoint
    @app.route('/streaming/non-streaming', methods=['GET'])
    def non_streaming_endpoint():
        """Non-streaming version of the streaming endpoint for comparison"""
        # Get parameters
        size = int(request.args.get('size', 1000))  # Data size in KB
        response_mode = request.args.get('mode', 'json')  # Mode: json, csv, plaintext
        
        # Cap size for safety
        size = min(max(1, size), 10000)  # 1KB to 10MB
        
        # Convert KB to bytes
        size_bytes = size * 1024
        
        if response_mode == 'json':
            # Generate full JSON data
            items = []
            items_count = size_bytes // 100  # Approximate size per item
            
            for i in range(items_count):
                item = {
                    'id': i,
                    'value': random.random(),
                    'name': f'item_{i}',
                    'timestamp': datetime.now().isoformat(),
                    'data': ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(20))
                }
                items.append(item)
            
            return jsonify(items)
            
        elif response_mode == 'csv':
            # Generate full CSV data
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['id', 'value', 'name', 'timestamp', 'data'])
            
            # Write rows
            rows_count = size_bytes // 100  # Approximate size per row
            for i in range(rows_count):
                row = [
                    i,
                    random.random(),
                    f'item_{i}',
                    datetime.now().isoformat(),
                    ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(20))
                ]
                writer.writerow(row)
            
            # Get the data and reset the buffer
            csv_data = output.getvalue()
            output.close()
            
            return Response(csv_data, content_type='text/csv')
            
        else:  # plaintext
            # Generate full plaintext data
            lines = []
            lines_count = size_bytes // 80  # Approximate 80 chars per line
            
            for i in range(lines_count):
                # Generate a line with ID, timestamp and random data
                line = f"Line {i}: {datetime.now().isoformat()} - "
                # Fill the rest with random characters to reach ~80 chars
                line += ''.join(random.choice('abcdefghijklmnopqrstuvwxyz ') 
                               for _ in range(80 - len(line)))
                lines.append(line)
            
            return Response('\n'.join(lines), content_type='text/plain')
    
    # 11. Enhanced Error Handling
    @app.route('/errors', methods=['GET', 'POST', 'PUT', 'DELETE'])
    def errors_endpoint():
        """Enhanced error handling and exception processing test"""
        error_type = request.args.get('type', 'none')
        status_code = int(request.args.get('code', 500))
        recovery_time = float(request.args.get('recovery', 0)) # Time in ms to simulate recovery operations
        
        # Cap recovery time for safety
        recovery_time = min(max(0, recovery_time), 100) / 1000  # Convert to seconds, max 100ms
        
        # Start timing for performance monitoring
        start_time = time.time()
        
        try:
            # Handle HTTP status code errors first
            if error_type == 'http':
                if 400 <= status_code < 600:
                    # HTTP error response
                    # Simulate recovery steps
                    if recovery_time > 0:
                        time.sleep(recovery_time)
                        
                    abort(status_code)
                else:
                    return jsonify({
                        'error': 'Invalid HTTP status code',
                        'valid_range': '400-599'
                    }), 400
            
            # Programming errors
            elif error_type == 'division':
                # Trigger division by zero
                result = 1 / 0
                return jsonify({'result': result})  # Never reached
                
            elif error_type == 'key':
                # Trigger key error
                d = {}
                value = d['nonexistent']
                return jsonify({'value': value})  # Never reached
                
            elif error_type == 'type':
                # Trigger type error
                result = 'string' + 42
                return jsonify({'result': result})  # Never reached
                
            elif error_type == 'database':
                # Trigger database error
                if app.config['DB_TYPE'] == 'postgres' or app.config['DB_TYPE'] == 'mysql':
                    g.cursor.execute('SELECT * FROM nonexistent_table')
                else:
                    g.db.nonexistent_collection.find_one()
                return jsonify({'result': 'Query executed'})  # Never reached
                
            elif error_type == 'memory':
                # Memory error simulation (without actually causing OOM)
                # Just allocate a reasonably large object then fail
                large_list = [0] * 10000000  # 10 million integers
                # Simulate failure
                raise MemoryError("Simulated memory error")
                
            elif error_type == 'timeout':
                # Timeout simulation
                time.sleep(0.5)  # Sleep for 500ms
                raise TimeoutError("Simulated timeout error")
                
            elif error_type == 'io':
                # I/O error simulation
                try:
                    with open('/nonexistent/file.txt', 'r') as f:
                        content = f.read()
                    return jsonify({'content': content})  # Never reached
                except IOError as e:
                    raise e
                    
            elif error_type == 'custom':
                # Custom application exception
                class ApplicationError(Exception):
                    def __init__(self, message, code, details=None):
                        self.message = message
                        self.code = code
                        self.details = details or {}
                        super().__init__(self.message)
                
                raise ApplicationError(
                    message="This is a custom application error",
                    code="APP_ERROR_001",
                    details={"request_id": "test-123", "timestamp": datetime.now().isoformat()}
                )
            
            elif error_type == 'validation':
                # Input validation error
                errors = []
                
                # Validate parameters
                params = request.args.get('params', 'name,age,email').split(',')
                for param in params:
                    if param == 'name' and len(request.args.get('name', '')) < 3:
                        errors.append({'field': 'name', 'message': 'Name must be at least 3 characters'})
                    elif param == 'age' and not request.args.get('age', '').isdigit():
                        errors.append({'field': 'age', 'message': 'Age must be a number'})
                    elif param == 'email' and '@' not in request.args.get('email', ''):
                        errors.append({'field': 'email', 'message': 'Invalid email format'})
                
                if errors:
                    # Simulate validation processing time
                    if recovery_time > 0:
                        time.sleep(recovery_time)
                    
                    return jsonify({
                        'errors': errors,
                        'valid': False,
                        'error_type': 'validation',
                        'params_received': dict(request.args)
                    }), 400
                
                return jsonify({
                    'message': 'Validation successful',
                    'params': dict(request.args)
                })
            
            else:
                # No error - success response
                return jsonify({
                    'message': 'No error triggered',
                    'error_type': error_type,
                    'timestamp': datetime.now().isoformat()
                })
        
        except Exception as e:
            # Record error handling time
            error_time = time.time()
            
            # Log the error
            app.logger.error(f"Error occurred: {str(e)}")
            
            # Simulate recovery operations
            if recovery_time > 0:
                time.sleep(recovery_time)
                
            # Calculate total handling time
            handling_time = (time.time() - error_time) * 1000  # Convert to ms
            total_time = (time.time() - start_time) * 1000     # Convert to ms
            
            # Return detailed error response with timing information
            return jsonify({
                'error': str(e),
                'error_type': error_type,
                'error_class': e.__class__.__name__,
                'handled': True,
                'timing': {
                    'error_handling_ms': handling_time,
                    'total_request_ms': total_time
                },
                'request_info': {
                    'method': request.method,
                    'path': request.path,
                    'args': dict(request.args),
                    'headers': {k: v for k, v in request.headers.items()}
                }
            }), status_code if 400 <= status_code < 600 else 500
    
    # Register HTTP error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            'error': 'Not Found',
            'code': 404,
            'message': 'The requested resource does not exist',
            'path': request.path,
            'timestamp': datetime.now().isoformat()
        }), 404
    
    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({
            'error': 'Bad Request',
            'code': 400,
            'message': 'The server cannot process the request',
            'path': request.path,
            'timestamp': datetime.now().isoformat()
        }), 400
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            'error': 'Internal Server Error',
            'code': 500,
            'message': 'The server encountered an unexpected condition',
            'path': request.path,
            'timestamp': datetime.now().isoformat()
        }), 500
    
    # Preserving original error handling endpoint for backward compatibility
    @app.route('/error-handling', methods=['GET'])
    def error_handling_endpoint():
        """Original error handling and exception processing test (kept for compatibility)"""
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
    
    # 18. I/O Operations Test
    @app.route('/io-ops', methods=['GET'])
    def io_ops_endpoint():
        """Test various I/O operations and their energy/performance impact"""
        # Get I/O configuration parameters
        operation = request.args.get('op', 'read')  # read, write, append, combined
        buffer_size = int(request.args.get('buffer', 8192))  # Buffer size in bytes
        file_size = int(request.args.get('size', 1024))  # File size in KB
        iterations = int(request.args.get('iterations', 1))  # Number of operations
        sync_mode = request.args.get('sync', 'buffered')  # buffered, sync, fsync, fdatasync
        
        # Validate and cap parameters for safety
        buffer_size = min(max(1024, buffer_size), 1024 * 1024)  # 1KB to 1MB
        file_size = min(max(1, file_size), 10 * 1024)  # 1KB to 10MB
        iterations = min(max(1, iterations), 10)  # 1 to 10
        
        # Create test directory if it doesn't exist
        test_dir = '/tmp/flask-io-test'
        os.makedirs(test_dir, exist_ok=True)
        
        # Generate a unique filename for this test
        test_file = os.path.join(test_dir, f'test-{int(time.time())}.dat')
        
        # Start timing
        start_time = time.time()
        results = {
            'operation': operation,
            'buffer_size': buffer_size,
            'file_size': file_size,
            'iterations': iterations,
            'sync_mode': sync_mode,
            'file': test_file,
            'timing': {}
        }
        
        try:
            # Prepare data for write operations
            data = b'x' * buffer_size
            
            # Execute the requested operation
            if operation == 'read' or operation == 'combined':
                # First create a file to read
                write_start = time.time()
                
                with open(test_file, 'wb') as f:
                    # Write the file in chunks
                    bytes_to_write = file_size * 1024
                    while bytes_to_write > 0:
                        chunk_size = min(buffer_size, bytes_to_write)
                        f.write(data[:chunk_size])
                        bytes_to_write -= chunk_size
                
                results['timing']['file_creation'] = (time.time() - write_start) * 1000  # ms
                
                # Now perform read operations
                read_start = time.time()
                bytes_read = 0
                
                for i in range(iterations):
                    with open(test_file, 'rb') as f:
                        # Set appropriate flags based on sync mode
                        if sync_mode == 'sync':
                            os.fdatasync(f.fileno()) if hasattr(os, 'fdatasync') else os.fsync(f.fileno())
                        
                        # Read the file in chunks
                        while True:
                            chunk = f.read(buffer_size)
                            if not chunk:
                                break
                            bytes_read += len(chunk)
                
                results['timing']['read'] = (time.time() - read_start) * 1000  # ms
                results['bytes_read'] = bytes_read
            
            if operation == 'write' or operation == 'combined':
                # Perform write operations
                write_start = time.time()
                bytes_written = 0
                
                for i in range(iterations):
                    with open(test_file, 'wb') as f:
                        # Set appropriate flags based on sync mode
                        if sync_mode == 'sync':
                            # Set the file to be opened in sync mode if possible
                            pass
                        
                        # Write the file in chunks
                        bytes_to_write = file_size * 1024
                        while bytes_to_write > 0:
                            chunk_size = min(buffer_size, bytes_to_write)
                            f.write(data[:chunk_size])
                            bytes_written += chunk_size
                            bytes_to_write -= chunk_size
                            
                            # Perform syncs after each write if requested
                            if sync_mode == 'fsync':
                                os.fsync(f.fileno())
                            elif sync_mode == 'fdatasync':
                                os.fdatasync(f.fileno()) if hasattr(os, 'fdatasync') else os.fsync(f.fileno())
                
                results['timing']['write'] = (time.time() - write_start) * 1000  # ms
                results['bytes_written'] = bytes_written
            
            if operation == 'append':
                # Perform append operations
                append_start = time.time()
                bytes_appended = 0
                
                # First create the initial file
                with open(test_file, 'wb') as f:
                    f.write(b'Initial data\n')
                
                # Now perform the append operations
                for i in range(iterations):
                    with open(test_file, 'ab') as f:
                        # Set appropriate flags based on sync mode
                        if sync_mode == 'sync':
                            # Set the file to be opened in sync mode if possible
                            pass
                        
                        # Append data in chunks
                        bytes_to_append = (file_size * 1024) // iterations
                        while bytes_to_append > 0:
                            chunk_size = min(buffer_size, bytes_to_append)
                            f.write(data[:chunk_size])
                            bytes_appended += chunk_size
                            bytes_to_append -= chunk_size
                            
                            # Perform syncs after each append if requested
                            if sync_mode == 'fsync':
                                os.fsync(f.fileno())
                            elif sync_mode == 'fdatasync':
                                os.fdatasync(f.fileno()) if hasattr(os, 'fdatasync') else os.fsync(f.fileno())
                
                results['timing']['append'] = (time.time() - append_start) * 1000  # ms
                results['bytes_appended'] = bytes_appended
            
            # Record final file stats
            if os.path.exists(test_file):
                file_stats = os.stat(test_file)
                results['file_stats'] = {
                    'size': file_stats.st_size,
                    'mode': file_stats.st_mode,
                    'created': file_stats.st_ctime,
                    'modified': file_stats.st_mtime,
                    'accessed': file_stats.st_atime
                }
        
        except Exception as e:
            results['error'] = {
                'message': str(e),
                'type': type(e).__name__
            }
        
        finally:
            # Clean up the test file
            if os.path.exists(test_file):
                try:
                    os.unlink(test_file)
                    results['cleanup'] = 'success'
                except:
                    results['cleanup'] = 'failed'
        
        # Record total time
        results['timing']['total'] = (time.time() - start_time) * 1000  # ms
        
        return jsonify(results)
    
    # 19. Mixed Workload
    @app.route('/mixed-workload', methods=['GET'])
    def mixed_workload_endpoint():
        """Combined workload test simulating real-world usage patterns"""
        # Get workload parameters
        pattern = request.args.get('pattern', 'balanced')  # balanced, cpu-heavy, io-heavy, memory-heavy
        intensity = int(request.args.get('intensity', '1'))  # 1-5 scale
        fixed_seed = request.args.get('fixed_seed', 'true') == 'true'  # Use fixed seed for reproducibility
        
        # Cap intensity for safety
        intensity = min(max(1, intensity), 5)
        
        # Set random seed for reproducibility if requested
        if fixed_seed:
            random.seed(42)  # Fixed seed for reproducible results
        
        # Start timing
        start_time = time.time()
        
        # Define workload composition based on pattern
        workloads = {
            'balanced': {
                'json': 0.2,
                'cpu': 0.2,
                'memory': 0.2,
                'routing': 0.2,
                'string': 0.2
            },
            'cpu-heavy': {
                'json': 0.1,
                'cpu': 0.6,
                'memory': 0.1,
                'routing': 0.1,
                'string': 0.1
            },
            'memory-heavy': {
                'json': 0.1,
                'cpu': 0.1,
                'memory': 0.6,
                'routing': 0.1,
                'string': 0.1
            },
            'io-heavy': {
                'json': 0.3,
                'cpu': 0.1,
                'memory': 0.1,
                'routing': 0.1,
                'string': 0.4
            }
        }
        
        # Get the workload distribution or use balanced as default
        distribution = workloads.get(pattern, workloads['balanced'])
        
        # Results collection
        results = {
            'pattern': pattern,
            'intensity': intensity,
            'fixed_seed': fixed_seed,
            'tasks': [],
            'timing': {}
        }
        
        # 1. JSON processing workload
        if distribution['json'] > 0:
            json_work_start = time.time()
            
            # Generate and process JSON data
            items = []
            item_count = int(100 * intensity * distribution['json'])
            
            for i in range(item_count):
                item = {
                    'id': i,
                    'name': f'item_{i}',
                    'value': random.random(),
                    'tags': [f'tag_{j}' for j in range(random.randint(1, 5))],
                    'active': random.choice([True, False]),
                    'created': datetime.now().isoformat()
                }
                
                # Process the item
                item['calculated'] = {
                    'name_length': len(item['name']),
                    'tag_count': len(item['tags']),
                    'value_category': 'high' if item['value'] > 0.5 else 'low'
                }
                
                items.append(item)
            
            # Add to results
            results['timing']['json'] = (time.time() - json_work_start) * 1000  # ms
            results['tasks'].append({
                'type': 'json',
                'items_processed': item_count,
                'sample': items[:2] if items else []
            })
        
        # 2. CPU workload
        if distribution['cpu'] > 0:
            cpu_work_start = time.time()
            
            # Fibonacci - adjust work based on intensity
            fib_n = 25 + (intensity * 2)
            
            # Memoized implementation to prevent excessive CPU usage
            memo = {}
            def fibonacci(n):
                if n in memo:
                    return memo[n]
                if n <= 2:
                    return 1
                memo[n] = fibonacci(n-1) + fibonacci(n-2)
                return memo[n]
            
            fib_result = fibonacci(fib_n)
            
            # Prime number calculation
            prime_count = 0
            prime_limit = 1000 * intensity * distribution['cpu']
            
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
            
            for i in range(int(prime_limit)):
                if is_prime(i):
                    prime_count += 1
            
            # Add to results
            results['timing']['cpu'] = (time.time() - cpu_work_start) * 1000  # ms
            results['tasks'].append({
                'type': 'cpu',
                'fibonacci_n': fib_n,
                'fibonacci_result': fib_result,
                'prime_count': prime_count,
                'prime_limit': prime_limit
            })
        
        # 3. Memory workload
        if distribution['memory'] > 0:
            memory_work_start = time.time()
            
            # Adjust memory usage based on intensity and distribution
            memory_size = int(10000 * intensity * distribution['memory'])
            
            # Create memory structures
            arrays = []
            for i in range(5):
                arrays.append([random.random() for _ in range(memory_size // 5)])
            
            # Dictionary with calculation results
            memory_results = {}
            for i in range(min(100, memory_size // 100)):
                # Perform some calculations on the arrays
                memory_results[f'calc_{i}'] = sum(a[i % len(a)] for a in arrays if i < len(a))
            
            # Add to results
            results['timing']['memory'] = (time.time() - memory_work_start) * 1000  # ms
            results['tasks'].append({
                'type': 'memory',
                'array_count': len(arrays),
                'array_size': memory_size // 5,
                'calculation_count': len(memory_results),
                'sample_results': {k: memory_results[k] for k in list(memory_results.keys())[:3]} if memory_results else {}
            })
        
        # 4. Routing simulation
        if distribution['routing'] > 0:
            routing_work_start = time.time()
            
            # Simulate route matching and parameter extraction
            routes = [
                '/api/users/<id>',
                '/api/products/<id>/reviews',
                '/api/orders/<id>/items/<item_id>',
                '/api/categories/<slug>',
                '/api/search/<query>'
            ]
            
            route_matches = []
            route_count = int(10 * intensity * distribution['routing'])
            
            for i in range(route_count):
                route_template = random.choice(routes)
                
                # Create an actual URL by replacing template parts
                actual_url = route_template
                if '<id>' in actual_url:
                    actual_url = actual_url.replace('<id>', str(random.randint(1, 1000)))
                if '<item_id>' in actual_url:
                    actual_url = actual_url.replace('<item_id>', str(random.randint(1, 100)))
                if '<slug>' in actual_url:
                    slugs = ['electronics', 'clothing', 'books', 'toys', 'home']
                    actual_url = actual_url.replace('<slug>', random.choice(slugs))
                if '<query>' in actual_url:
                    queries = ['laptop', 'phone', 'headphones', 'camera', 'watch']
                    actual_url = actual_url.replace('<query>', random.choice(queries))
                
                # Simulate route matching
                matched_route = None
                for route in routes:
                    # Simple pattern matching simulation
                    if len(route.split('/')) == len(actual_url.split('/')):
                        matched_route = route
                        break
                
                route_matches.append({
                    'url': actual_url,
                    'matched_template': matched_route,
                    'params': {p.split('/')[2]: p.split('/')[3] for p in [actual_url] if len(p.split('/')) > 3}
                })
            
            # Add to results
            results['timing']['routing'] = (time.time() - routing_work_start) * 1000  # ms
            results['tasks'].append({
                'type': 'routing',
                'routes_processed': route_count,
                'sample_matches': route_matches[:3] if route_matches else []
            })
        
        # 5. String processing
        if distribution['string'] > 0:
            string_work_start = time.time()
            
            # Generate and process text
            text_blocks = []
            block_count = int(5 * intensity * distribution['string'])
            
            for i in range(block_count):
                # Generate some text
                words = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 
                         'elit', 'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore',
                         'et', 'dolore', 'magna', 'aliqua']
                
                text_length = random.randint(50, 200)
                text = ' '.join(random.choice(words) for _ in range(text_length))
                
                # Process the text
                word_count = len(text.split())
                char_count = len(text)
                unique_words = len(set(text.lower().split()))
                
                # Add some pattern matching
                word_freq = {}
                for word in text.lower().split():
                    word_freq[word] = word_freq.get(word, 0) + 1
                
                # Get most common words
                most_common = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
                
                text_blocks.append({
                    'sample': text[:100] + '...' if len(text) > 100 else text,
                    'stats': {
                        'word_count': word_count,
                        'char_count': char_count,
                        'unique_words': unique_words,
                        'most_common': most_common
                    }
                })
            
            # Add to results
            results['timing']['string'] = (time.time() - string_work_start) * 1000  # ms
            results['tasks'].append({
                'type': 'string',
                'blocks_processed': block_count,
                'sample_blocks': text_blocks[:2] if text_blocks else []
            })
        
        # Add overall timing
        results['timing']['total'] = (time.time() - start_time) * 1000  # ms
        
        # Reset random seed if it was fixed
        if fixed_seed:
            random.seed(None)  # Reset to system time or other source of randomness
        
        return jsonify(results)
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
