import sys
import os
import json
import re
import traceback
import threading

from urllib.parse import parse_qs

# Add current directory to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

init_error = None
try:
    import main
    import database
    import crawler
except Exception as e:
    init_error = traceback.format_exc()


def application(environ, start_response):
    """
    High-performance native WSGI application for Phusion Passenger / LiteSpeed.
    Bypasses a2wsgi thread pools to eliminate concurrency deadlocks on shared hosting.
    """
    cors_headers = [
        ('Content-Type', 'application/json; charset=utf-8'),
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS'),
        ('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With'),
    ]

    # If top-level initialization failed (e.g. missing pip packages or db issues)
    if init_error:
        start_response('500 Internal Server Error', cors_headers)
        error_payload = {
            "error": "Backend Application Failed to Initialize",
            "details": init_error,
            "solution": "In cPanel 'Setup Python App', make sure to click 'Run Pip Install' or install dependencies from requirements.txt, then click 'Restart'."
        }
        return [json.dumps(error_payload, indent=2).encode('utf-8')]

    method = environ.get('REQUEST_METHOD', 'GET').upper()
    path = environ.get('PATH_INFO', '/')


    # 1. Handle CORS Preflight
    if method == 'OPTIONS':
        start_response('204 No Content', cors_headers)
        return [b'']

    # 2. Normalize path (strip /api prefix so /api/stories and /stories both work)
    norm_path = re.sub(r'^/api', '', path).rstrip('/')
    if not norm_path:
        norm_path = '/'

    db = database.SessionLocal()
    try:
        # GET / or GET /api
        if norm_path == '/' and method == 'GET':
            res = main.root()
            start_response('200 OK', cors_headers)
            return [json.dumps(res).encode('utf-8')]

        # GET /topics or GET /api/topics
        if norm_path == '/topics' and method == 'GET':
            res = main.get_topics(db)
            start_response('200 OK', cors_headers)
            return [json.dumps(res).encode('utf-8')]

        # GET /stories or GET /api/stories
        if norm_path == '/stories' and method == 'GET':
            qs = parse_qs(environ.get('QUERY_STRING', ''))
            topic = qs.get('topic', [None])[0]
            lang = qs.get('lang', [None])[0]
            search = qs.get('search', [None])[0]
            skip = int(qs.get('skip', [0])[0] or 0)
            limit = int(qs.get('limit', [50])[0] or 50)
            res = main.get_stories(topic=topic, lang=lang, search=search, skip=skip, limit=limit, db=db)
            start_response('200 OK', cors_headers)
            return [json.dumps(res).encode('utf-8')]

        # GET /stories/<id> or GET /api/stories/<id>
        m_story = re.match(r'^/stories/(\d+)$', norm_path)
        if m_story and method == 'GET':
            story_id = int(m_story.group(1))
            res = main.get_story_detail(story_id, db)
            start_response('200 OK', cors_headers)
            return [json.dumps(res).encode('utf-8')]

        # GET /stats or GET /api/stats
        if norm_path == '/stats' and method == 'GET':
            res = main.get_stats(db)
            start_response('200 OK', cors_headers)
            return [json.dumps(res).encode('utf-8')]

        # GET /sources or GET /api/sources
        if norm_path == '/sources' and method == 'GET':
            sources = main.get_sources(db)
            res = [
                {
                    'id': s.id,
                    'name': s.name,
                    'domain': s.domain,
                    'rss_url': s.rss_url,
                    'default_bias': s.default_bias,
                    'language': s.language,
                    'is_active': s.is_active
                }
                for s in sources
            ]
            start_response('200 OK', cors_headers)
            return [json.dumps(res).encode('utf-8')]

        # POST /sources or POST /api/sources
        if norm_path == '/sources' and method == 'POST':
            try:
                content_length = int(environ.get('CONTENT_LENGTH', 0))
                body = environ['wsgi.input'].read(content_length).decode('utf-8')
                data = json.loads(body)
                source_create = main.SourceCreate(**data)
                created = main.create_source(source_create, db)
                res = {
                    'id': created.id,
                    'name': created.name,
                    'domain': created.domain,
                    'rss_url': created.rss_url,
                    'default_bias': created.default_bias,
                    'language': created.language,
                    'is_active': created.is_active
                }
                start_response('200 OK', cors_headers)
                return [json.dumps(res).encode('utf-8')]
            except Exception as e:
                start_response('400 Bad Request', cors_headers)
                return [json.dumps({'detail': str(e)}).encode('utf-8')]

        # DELETE /sources/<id>
        m_del = re.match(r'^/sources/(\d+)$', norm_path)
        if m_del and method == 'DELETE':
            source_id = int(m_del.group(1))
            res = main.delete_source(source_id, db)
            start_response('200 OK', cors_headers)
            return [json.dumps(res).encode('utf-8')]

        # POST /crawl or POST /api/crawl
        if norm_path == '/crawl' and method == 'POST':
            t = threading.Thread(target=crawler.crawl_rss)
            t.daemon = True
            t.start()
            start_response('200 OK', cors_headers)
            return [json.dumps({'message': 'Crawler pipeline triggered successfully in background.'}).encode('utf-8')]

        # 404 Not Found
        start_response('404 Not Found', cors_headers)
        return [json.dumps({'detail': f'Not Found: {path}'}).encode('utf-8')]

    except Exception as e:
        error_trace = traceback.format_exc()
        start_response('500 Internal Server Error', cors_headers)
        return [json.dumps({'detail': str(e), 'trace': error_trace}).encode('utf-8')]

    finally:
        db.close()
