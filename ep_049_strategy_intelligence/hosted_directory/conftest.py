"""Test bootstrap for the EP049 strategy-intelligence package.

Version history:
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
_EP051_HOSTED_DIRECTORY = _HERE.parent.parent / "ep_051_strategy_directory" / "hosted_directory"

for _path in (str(_EP051_HOSTED_DIRECTORY), str(_HERE)):
    if _path in sys.path:
        sys.path.remove(_path)
    sys.path.insert(0, _path)
# _HERE goes in last, so it ends up first on sys.path - this repo's own
# app/main.py must win module resolution for its own test suite, with
# EP051's app/ package only supplying app.config/app.contracts/app.repository
# (which EP049's app/main.py imports directly) plus whatever else this
# repo's own app/ package does not itself provide.
