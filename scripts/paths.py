from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=1)
def get_project_root() -> Path:
    """
    Optimized for GitHub Actions: 
    Calculates root relative to this file's location.
    Works without any external .project-root file.
    """
    # __file__ is scripts/paths.py, .parent is scripts/, .parent.parent is root
    return Path(__file__).resolve().parent.parent
PROJECT_ROOT = get_project_root()
def get_path(*parts, ensure_within_root=True):
    path = PROJECT_ROOT.joinpath(*parts).resolve()

    if ensure_within_root:
        if not str(path).startswith(str(PROJECT_ROOT.resolve())):
            raise ValueError(f"Path escapes project root: {path}")

    return path
