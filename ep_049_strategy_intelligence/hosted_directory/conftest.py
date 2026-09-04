"""Test bootstrap for the EP049 strategy-intelligence package.

Version history:
- 2.0.0 (2026-09-04): EP049 no longer needs EP051's filesystem path at all.
  app/config.py, app/contracts.py and app/repository.py are now vendored
  copies living directly under this repo's own app/ (see their version
  histories) instead of being merged in from EP051's app/ package via
  sys.path - required so EP049 can deploy standalone on its own Render
  rootDir. This file now only needs to put this directory's own hosted_directory
  on sys.path, same as any single-package pytest setup.
- 1.1.0 (2026-09-04): EP049 now has its own standalone app/main.py (no
  longer served by EP051's FastAPI host) - fixed the sys.path insertion
  order, which previously left EP051's directory ahead of EP049's own,
  so `app.main` (and `app.config`/`app.contracts`/`app.repository`, which
  EP049's app/main.py imports directly from EP051's data layer) resolved
  to the wrong file when both packages' app/ trees were on sys.path together.
- 1.0.0 (2026-09-04): Initial version. The intelligence implementation
  (app/intelligence/*, app/arena_provider.py) lives here; both directories'
  app/ packages are Python namespace packages (no __init__.py) that merge
  into one `app` import namespace when both are on sys.path, which is what
  this file sets up for pytest collection.
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
