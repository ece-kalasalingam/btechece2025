"""
Path Resolution Utilities

Purpose:
- Provide deterministic, project-root–anchored path resolution
- Enforce strict separation between required inputs and creatable outputs

Design Constraints:
- Project root is resolved via an explicit marker file
- Input paths MUST exist (fail-fast)
- Output paths are created ONLY when explicitly requested (create=True)
- No implicit environment-based or relative-path inference is allowed

Intent:
- Prevent silent misconfiguration
- Preserve auditability and reproducibility across environments
  (local runs, CI, GitHub Actions)
"""

from pathlib import Path
from functools import lru_cache

PROJECT_MARKER = ".project-root"
@lru_cache(maxsize=1)
def get_project_root() -> Path:
    """
    Resolve project root by walking upward from this file's location
    until a project marker file is found.

    This works reliably for:
    - GitHub Actions
    - Local clones
    - Codespaces
    """
    start = Path(__file__).resolve().parent

    for parent in [start] + list(start.parents):
        if (parent / PROJECT_MARKER).is_file():
            return parent

    raise FileNotFoundError(
        "Project root not found (expected '.project-root' marker file)"
    )

def get_path(name: str, *, create: bool = False) -> Path:
    """
    Resolve a named project directory (e.g., courses, outputs, templates).

    Fails fast if directory does not exist or is not a directory.
    """
    root = get_project_root()
    path = root / name

    if create:
        path.mkdir(parents=True, exist_ok=True)
    
    if not path.exists():
        raise FileNotFoundError(f"Required path not found: {path}")

    if not path.is_dir():
        raise NotADirectoryError(f"Expected directory, found file: {path}")

    return path