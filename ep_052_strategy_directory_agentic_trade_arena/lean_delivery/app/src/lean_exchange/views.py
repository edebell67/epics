# VERSION HISTORY v1.1.0 · 2026-09-02 · Serve a read-only API-driven Arena alongside the private owner workspace.
# v1.0.0 · 2026-09-02 · Allowlisted owner workspace files with a self-only content security policy.
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

ROOT = Path(__file__).resolve().parent / 'web'
HEADERS = {'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
           'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer'}


def router():
    routes = APIRouter()

    @routes.get('/', include_in_schema=False)
    def index():
        return RedirectResponse('/owner')

    @routes.get('/owner', include_in_schema=False)
    def owner():
        return FileResponse(ROOT / 'owner.html', headers=HEADERS)

    @routes.get('/arena', include_in_schema=False)
    def arena():
        return FileResponse(ROOT / 'arena.html', headers=HEADERS)

    @routes.get('/assets/{name}', include_in_schema=False)
    def assets(name: str):
        if name not in ('owner.css', 'owner.js', 'arena.css', 'arena.js'):
            raise HTTPException(404, 'Asset not found')
        return FileResponse(ROOT / name, headers=HEADERS)

    return routes
