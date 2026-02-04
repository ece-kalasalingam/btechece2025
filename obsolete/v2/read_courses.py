"""
PIPELINE STAGE: 0 → 1.5  (Ingestion + Structural Parsing + Serialization)

Purpose:
- Load course Markdown files listed in courses_md/index.md
- Preserve deterministic order


ARCHITECTURAL CONSTRAINTS:
- This module MUST NOT parse Markdown structure
- This module MUST NOT interpret syllabus semantics
- This module MUST NOT perform validation of academic rules
- This module MUST NOT generate LaTeX layout or presentation
- MUST NOT interpret syllabus semantics
- MUST NOT validate academic rules
- MUST NOT assign meaning to headers
- MUST NOT generate LaTeX layout


"""

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple
import json
from obsolete2.paths import get_path

COURSES_DIRNAME = "courses_md"
OUTPUTS_DIRNAME = "outputs"
INDEX_FILENAME = "index.md"
REPORT_FILENAME = "error_report.json"
MASTER_TEX_FILENAME = "course_data.tex"

from contracts import MarkdownSection

def split_markdown_sections(md_text: str) -> list[MarkdownSection]:
    sections: list[MarkdownSection] = []

    # Initialize PREAMBLE
    current_level: int = 0
    current_title: str = "__PREAMBLE__"
    current_body: list[str] = []

    in_code_block: bool = False
    code_fence: str | None = None   # exact fence string, e.g. ``` or ```` or ~~~

    lines = md_text.splitlines()

    for line in lines:
        stripped = line.lstrip()

        # --------------------------------------------------
        # Detect start/end of fenced code blocks
        # --------------------------------------------------
        if stripped.startswith("```") or stripped.startswith("~~~"):
            # capture full fence run (all same chars)
            fence_char = stripped[0]
            i = 0
            while i < len(stripped) and stripped[i] == fence_char:
                i += 1
            fence = stripped[:i]

            if not in_code_block:
                in_code_block = True
                code_fence = fence
            elif fence == code_fence:
                in_code_block = False
                code_fence = None

            current_body.append(line)
            continue

        # --------------------------------------------------
        # Header detection (ONLY if not inside code block)
        # --------------------------------------------------
        if not in_code_block and stripped.startswith("#"):
            i = 0
            while i < len(stripped) and stripped[i] == "#":
                i += 1

            # Valid Markdown header rules:
            # 1. One or more '#'
            # 2. Followed by a space
            # 3. Non-empty title text
            if (
                i > 0
                and i < len(stripped)
                and stripped[i] == " "
                and stripped[i + 1 :].strip() != ""
            ):
                # Flush current section
                sections.append(
                    MarkdownSection(
                        level=current_level,
                        title=current_title,
                        body="\n".join(current_body).strip()
                    )
                )

                # Start new section
                current_level = i
                current_title = stripped[i + 1 :].strip()
                current_body = []
                continue

        # --------------------------------------------------
        # Normal content
        # --------------------------------------------------
        current_body.append(line)

    # Flush final section
    sections.append(
        MarkdownSection(
            level=current_level,
            title=current_title,
            body="\n".join(current_body).strip()
        )
    )

    # --------------------------------------------------
    # Filter out empty PREAMBLE if it has no body
    # --------------------------------------------------
    if (
        sections
        and sections[0].title == "__PREAMBLE__"
        and sections[0].body == ""
    ):
        sections = sections[1:]

    return sections


@dataclass
class CourseError:
    course_code: str
    stage: str
    message: str

def read_course_index(index_path: Path) -> List[str]:
    course_codes: List[str] = []
    seen: set[str] = set()

    with index_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if line.startswith("- "):
                code = line[2:].strip()
                if not code:
                    raise ValueError(f"Empty course code at {index_path}:{lineno}")
                if code in seen:
                    raise ValueError(f"Duplicate course code '{code}' at {index_path}:{lineno}")
                seen.add(code)
                course_codes.append(code)

    if not course_codes:
        raise ValueError(f"No course codes found in {index_path}")

    return course_codes


def load_courses() -> Tuple[Dict[str, str], List[CourseError], int]:
    courses_dir = get_path(COURSES_DIRNAME)
    index_path = courses_dir / INDEX_FILENAME

    course_codes = read_course_index(index_path)

    loaded: Dict[str, str] = {}
    errors: List[CourseError] = []

    for code in course_codes:
        course_file = courses_dir / f"{code}.md"
        try:
            loaded[code] = course_file.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(
                CourseError(
                    course_code=code,
                    stage="load",
                    message=str(e),
                )
            )

    return loaded, errors, len(course_codes)

def write_report(
    output_dir: Path,
    total_listed: int | None,
    loaded_count: int | None,
    errors: list[CourseError],
    status: str,
) -> Path:
    report = {
        "summary": {
            "status": status,          # OK | PARTIAL | FATAL
            "total_courses_listed": total_listed,
            "courses_loaded": loaded_count,
            "courses_skipped": len(errors),
        },
        "errors": [
            {
                "course_code": e.course_code,
                "stage": e.stage,
                "message": e.message,
            }
            for e in errors
        ],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / REPORT_FILENAME
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )
    return report_path