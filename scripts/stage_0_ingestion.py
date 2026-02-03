"""
PIPELINE STAGE: 0 (Ingestion)

Purpose:
- Load course Markdown files listed in courses_md/index.md
- Preserve deterministic order
- Emit raw text for downstream parsing

ARCHITECTURAL CONSTRAINTS:
- This module MUST NOT parse Markdown structure (No splitting sections)
- This module MUST NOT interpret syllabus semantics
- This module MUST NOT perform validation of academic rules
- This module MUST NOT generate LaTeX layout or presentation
"""

import json
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple
from paths import get_path

# Constants
COURSES_DIRNAME = "courses_md"
OUTPUTS_DIRNAME = "outputs"
INDEX_FILENAME = "index.md"
REPORT_FILENAME = "ingestion_report.json"

@dataclass
class IngestionError:
    course_code: str
    message: str

def read_course_index(index_path: Path) -> List[str]:
    """Reads the index file to determine the order of processing."""
    course_codes: List[str] = []
    seen: set[str] = set()

    if not index_path.exists():
        raise FileNotFoundError(f"Index file missing: {index_path}")

    with index_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if line.startswith("- "):
                code = line[2:].strip()
                if not code:
                    continue
                if code in seen:
                    raise ValueError(f"Duplicate course code '{code}' at {index_path}:{lineno}")
                seen.add(code)
                course_codes.append(code)

    if not course_codes:
        raise ValueError(f"No course codes found in {index_path}")

    return course_codes

def run_ingestion() -> Tuple[Dict[str, str], List[IngestionError], int]:
    """
    Primary entry point: Loads all course files.
    Returns: (Map of Code -> RawText, List of Errors, Total Count)
    """
    courses_dir = get_path(COURSES_DIRNAME)
    index_path = courses_dir / INDEX_FILENAME

    course_codes = read_course_index(index_path)
    
    loaded_content: Dict[str, str] = {}
    errors: List[IngestionError] = []

    for code in course_codes:
        course_file = courses_dir / f"{code}.md"
        try:
            if not course_file.exists():
                raise FileNotFoundError(f"File {code}.md not found in {COURSES_DIRNAME}")
            
            loaded_content[code] = course_file.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(IngestionError(course_code=code, message=str(e)))

    return loaded_content, errors, len(course_codes)

def write_ingestion_report(
    output_dir: Path,
    total_listed: int,
    loaded: Dict[str, str],
    errors: List[IngestionError]
) -> Path:
    """Writes an audit trail for the ingestion phase."""
    report = {
        "stage": "0_ingestion",
        "summary": {
            "total_listed": total_listed,
            "successfully_loaded": len(loaded),
            "failed_loads": len(errors),
            "status": "OK" if not errors else "PARTIAL_FAILURE"
        },
        "errors": [
            {"course_code": e.course_code, "message": e.message} 
            for e in errors
        ]
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / REPORT_FILENAME
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path