"""Voice_backend — API gateway. Owns FastAPI, uploads, jobs, status; NO ML inference."""

# Make the repo-root `shared` package importable regardless of cwd.
import pathlib as _pathlib
import sys as _sys

_root = _pathlib.Path(__file__).resolve().parents[2]
if str(_root) not in _sys.path:
    _sys.path.insert(0, str(_root))

__version__ = "2.0.0"
