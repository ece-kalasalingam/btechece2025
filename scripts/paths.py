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

def get_path(name: str, create: bool = False) -> Path:
    root = get_project_root()
    path = root / name
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path