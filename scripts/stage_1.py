"""
=====================================================================
STAGE-1 : STRUCTURAL PARSER & TEXT PARTITIONING (FORMAT-AGNOSTIC)
=====================================================================

RESPONSIBILITY
--------------
1. Locate COURSE CODE anchor
2. Extract course title from preamble (H1)
3. Detect ALL section headings generically (## ...)
4. Slice raw text into:
   - header_block_raw
   - explicit_sections (ALL sections, no filtering)
   - footer_block_raw
5. Set ctx.structure exactly once

NO VALIDATION. NO POLICY. NO SEMANTICS.
"""

import re
from scripts.contracts import DocumentStructure, CourseExecutionContext
from scripts.patterns import COURSE_CODE_HEADER_PATTERN, H1_PATTERN

SECTION_HEADING_PATTERN = re.compile(r"^##\s+(.*)$")


def canonicalize_heading(title: str) -> str:
    return (
        title.strip()
        .lower()
        .replace("&", "and")
        .replace("-", " ")
        .replace("  ", " ")
        .replace(" ", "_")
    )


def extract_course_title_from_preamble(preamble_lines: list[str]) -> str:
    for line in preamble_lines:
        match = H1_PATTERN.match(line.strip())
        if match:
            return match.group(1).strip()
    return ""  # tolerate bad authoring; validate later


def run_structure_parse(raw_text: str, ctx: CourseExecutionContext) -> None:
    lines = raw_text.splitlines()

    # -------------------------------------------------
    # 1. Find COURSE CODE anchor
    # -------------------------------------------------
    anchor_idx = -1
    for i, line in enumerate(lines):
        if COURSE_CODE_HEADER_PATTERN.match(line.strip()):
            anchor_idx = i
            break

    if anchor_idx == -1:
        ctx.log(
            "STAGE-1",
            "COURSE-CODE-NOT-FOUND",
            "COURSE CODE anchor missing.",
            fatal=True
        )
        return

    preamble_lines = lines[:anchor_idx]
    relevant_lines = lines[anchor_idx:]

    # -------------------------------------------------
    # 2. Extract course title (no validation)
    # -------------------------------------------------
    course_title = extract_course_title_from_preamble(preamble_lines)

    # -------------------------------------------------
    # 3. Extract footer (---)
    # -------------------------------------------------
    footer_raw = ""
    for i in range(len(relevant_lines) - 1, -1, -1):
        if relevant_lines[i].strip() == "---":
            footer_raw = "\n".join(relevant_lines[i + 1:]).strip()
            relevant_lines = relevant_lines[:i]
            break

    # -------------------------------------------------
    # 4. Detect ALL section headings
    # -------------------------------------------------
    headers = []
    for idx, line in enumerate(relevant_lines):
        m = SECTION_HEADING_PATTERN.match(line.strip())
        if m:
            title = m.group(1)
            headers.append({
                "key": canonicalize_heading(title),
                "line_index": idx,
                "raw_title": title
            })

    if not headers:
        ctx.log(
            "STAGE-1",
            "NO-SECTIONS",
            "No section headings (## ...) found after COURSE CODE.",
            fatal=True
        )
        return

    # -------------------------------------------------
    # 5. Build header block
    # -------------------------------------------------
    first_section_line = headers[0]["line_index"]
    header_block_raw = (
        f"Course Title: {course_title}\n"
        + "\n".join(relevant_lines[:first_section_line]).strip()
    )

    # -------------------------------------------------
    # 6. Slice ALL sections
    # -------------------------------------------------
    sections_content = {}
    for i, h in enumerate(headers):
        start = h["line_index"] + 1
        end = headers[i + 1]["line_index"] if i + 1 < len(headers) else len(relevant_lines)
        content = "\n".join(relevant_lines[start:end]).strip()
        sections_content[h["key"]] = content

    # -------------------------------------------------
    # 7. Freeze structure
    # -------------------------------------------------
    ctx.structure = DocumentStructure(
        header_block_raw=header_block_raw,
        explicit_sections=sections_content,
        footer_block_raw=footer_raw
    )