from typing import Dict, List, Tuple
from scripts.paths import get_path
from scripts.utils import normalize_line_endings

# Constants for the file system
COURSES_DIR = "courses_md"
INDEX_FILE = "index.md"

def load_all_courses() -> Dict[str, str]:
    """
    1. Finds the index.md file.
    2. Reads the list of course codes (e.g., - CS101).
    3. Loads the corresponding .md files from the courses_md/ folder.
    4. Returns a dictionary: { "CS101": "raw text..." }
    """
    courses_path = get_path(COURSES_DIR)
    index_path = courses_path / INDEX_FILE
    
    if not index_path.exists():
        raise FileNotFoundError(f"Critical Error: {INDEX_FILE} not found in {courses_path}")

    course_order = []
    # Read index.md to get the processing order
    with open(index_path, "r", encoding="utf-8") as f:
        for line in f:
            clean_line = line.strip()
            if clean_line.startswith("- "):
                # Extracts 'CS101' from '- CS101'
                code = clean_line[2:].strip()
                if code:
                    course_order.append(code)

    raw_data: Dict[str, str] = {}
    
    # Load each file in the order specified by the index
    for code in course_order:
        file_path = courses_path / f"{code}.md"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Normalize text immediately upon ingestion
                raw_data[code] = ingest(content)
        else:
            # We don't crash here; we just skip and let the Driver handle the missing data
            print(f"⚠️ Warning: File {code}.md listed in index but not found in folder.")

    return raw_data

def ingest(raw_text: str) -> str:
    """
    Pure text preparation. 
    Standardizes line endings for cross-platform (Windows/Linux/GitHub) compatibility.
    """
    return normalize_line_endings(raw_text)