from typing import Dict
from pathlib import Path
from scripts.paths import get_path
from scripts.utils import normalize_line_endings, validate_course_code
from scripts.contracts import COURSES_DIR, INDEX_FILE
from typing import List

def ingest(raw_text: str) -> str:
    """
    Pure text preparation. 
    Standardizes line endings for cross-platform (Windows/Linux/GitHub) compatibility.
    """
    return normalize_line_endings(raw_text)

def parse_index(index_path: Path) -> List[str]:
    """
    Parses index.md and returns a list of course codes.
    Ignores blank lines and comments.
    """
    if not index_path.exists():
        raise FileNotFoundError(f"Index file not found at {index_path}")

    course_codes = []
    with index_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            if line.startswith(("-", "*", "+")):
                line = line[1:].strip()
            course_codes.append(line)

    return course_codes

def iter_courses():
    """
    Yields (course_code, raw_text) one at a time.
    """
    courses_path = get_path(COURSES_DIR)
    index_path = courses_path / INDEX_FILE

    course_codes = parse_index(index_path)
    course_codes = sorted(course_codes)

    for code in course_codes:
        try:
            validate_course_code(code)
        except ValueError as e:
            yield code, None, str(e)
            continue

        file_path = courses_path / f"{code}.md"
        if not file_path.exists():
            yield code, None, f"Missing course file: {file_path}"
            continue

        raw_text = file_path.read_text(encoding="utf-8")
        yield code, raw_text, None
