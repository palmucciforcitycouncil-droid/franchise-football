import http.server, socketserver, sys
PORT=8000
try:
    with socketserver.TCPServer(('', PORT), http.server.SimpleHTTPRequestHandler) as httpd:
        print(f'PROBE OK: http.server running on http://127.0.0.1:{PORT}', flush=True)
        httpd.serve_forever()
except Exception as e:
    print('PROBE FAIL:', e, file=sys.stderr)
    sys.exit(1)
