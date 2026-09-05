# scripts/preview_workflow.py — Loopback-only allowlisted workflow preview.
# VERSION HISTORY
# v1.1.0 · 2026-09-02 · Allow live evidence-driven checklist asset.
# v1.0.0 · 2026-09-02 · Serves new workflow assets without exposing the archived application or credentials.
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {
    '/EP052_lean_implementation_workflow.html', '/EP052_lean_implementation_checklist.html',
    '/ARCHIVE_INDEX.md', '/lean_delivery/EP052_lean_scope_and_implementation_design.md',
    '/workflows/workflow.css', '/workflows/workflow.js', '/workflows/workflow-data.js', '/workflows/checklist.js',
    *{f'/workflows/EP052_l{i}_workflow.html' for i in range(1, 7)},
}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path == '/':
            self.path = '/EP052_lean_implementation_workflow.html'
        elif path not in ALLOWED:
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        path = unquote(urlsplit(self.path).path)
        if path not in ALLOWED and path != '/':
            self.send_error(404)
            return
        if path == '/':
            self.path = '/EP052_lean_implementation_workflow.html'
        super().do_HEAD()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()


if __name__ == '__main__':
    print('Workflow preview: http://127.0.0.1:8053', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8053), Handler).serve_forever()
