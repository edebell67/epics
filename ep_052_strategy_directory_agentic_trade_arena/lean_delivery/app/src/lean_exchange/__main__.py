# VERSION HISTORY v1.0.0 · 2026-09-02 · Loopback API launcher; no scheduled agent activity.
import os
import uvicorn

if __name__ == '__main__':
    uvicorn.run('lean_exchange.api:create_app', factory=True, host='127.0.0.1',
                port=int(os.environ.get('EP052_PORT', '8054')))
