from typing import Dict
from pathlib import Path
from scripts.paths import get_path
from scripts.utils import normalize_line_endings, validate_course_code
from scripts.contracts import COURSES_DIR, INDEX_FILE
from typing import List
from scripts.docx_ingestion import convert_docx_to_normalized_markdown

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

        file_path_md = courses_path / f"{code}.md"
        file_path_docx = courses_path / f"{code}.docx"

        if file_path_md.exists():
            raw_text = file_path_md.read_text(encoding="utf-8")
            yield code, raw_text, None
            continue

        if file_path_docx.exists():
            try:
                raw_text = convert_docx_to_normalized_markdown(code, file_path_docx)
                raw_text = ingest(raw_text)
                yield code, raw_text, None
            except Exception as e:
                yield code, None, f"DOCX parse failed for {file_path_docx}: {e}"
            continue

        yield code, None, f"Missing course file: {file_path_md} or {file_path_docx}"
