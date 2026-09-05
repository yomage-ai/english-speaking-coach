#!/usr/bin/env python3
"""Serve only the learning journal and its linked Markdown records on loopback."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse
import re


def handler(root):
    root = root.resolve()
    class JournalHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            name = unquote(urlsplit(self.path).path).lstrip('/')
            if name in ('', 'dashboard.html'):
                name = 'dashboard.html'
                mime = 'text/html; charset=utf-8'
            elif re.fullmatch(r'Sessions/SES-\d{8}-\d{3}\.md', name):
                mime = 'text/plain; charset=utf-8'
            else:
                self.send_error(404); return
            path = (root / name).resolve()
            if root not in path.parents or not path.is_file():
                self.send_error(404); return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)
    return JournalHandler

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8895)
    args = parser.parse_args()
    ThreadingHTTPServer(('127.0.0.1', args.port), handler(args.root)).serve_forever()
