from pathlib import Path
from functools import lru_cache

PROJECT_MARKER = ".project-root"

@lru_cache(maxsize=1)
def get_project_root() -> Path:
    start = Path(__file__).resolve().parent
    for parent in [start] + list(start.parents):
        if (parent / PROJECT_MARKER).is_file():
            return parent
    raise FileNotFoundError(f"Project root marker '{PROJECT_MARKER}' not found.")

def get_path(name: str, create: bool = False) -> Path:
    root = get_project_root()
    path = root / name
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path