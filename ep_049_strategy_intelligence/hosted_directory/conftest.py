"""Test bootstrap for the EP049 strategy-intelligence package.

Version history:
- 1.0.0 (2026-09-04): Initial version. The intelligence implementation
  (app/intelligence/*, app/arena_provider.py) lives here, but it is served
  by EP051's FastAPI host (app/main.py, app/config.py, app/contracts.py,
  app/repository.py) - both directories' app/ packages are Python
  namespace packages (no __init__.py) that merge into one `app` import
  namespace when both are on sys.path, which is what this file sets up
  for pytest collection.
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_EP051_HOSTED_DIRECTORY = _HERE.parent.parent / "ep_051_strategy_directory" / "hosted_directory"

for _path in (str(_HERE), str(_EP051_HOSTED_DIRECTORY)):
    if _path not in sys.path:
        sys.path.insert(0, _path)
