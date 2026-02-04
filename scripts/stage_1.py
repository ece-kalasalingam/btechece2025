import re
from typing import List, Dict, Optional
from scripts.contracts import DocumentStructure, CourseExecutionContext
from scripts.patterns import COURSE_SECTION_SEQUENCE, SECTION_TITLE_MAP
from scripts.utils import get_clean_section_title

def validate_structure(raw_text: str, ctx: CourseExecutionContext):
    """
    STAGE-1: Structural Gatekeeper.
    1. Detects mandatory R2025 section headers.
    2. Enforces strict verbatim sequence.
    3. Partitions text into Header, Explicit Sections, and Footer zones.
    """
    lines = raw_text.splitlines()
    
    # 1. Identify all Section Header lines and their positions
    found_headers = []
    for i, line in enumerate(lines):
        canonical_key = get_clean_section_title(line)
        if canonical_key:
            found_headers.append({
                "key": canonical_key,
                "line_index": i,
                "raw_title": line.strip()
            })

    # 2. FATAL CHECK: Exact Sequence Enforcement
    # We compare the list of found keys against the registry in patterns.py
    found_keys = [h['key'] for h in found_headers]
    
    if found_keys != COURSE_SECTION_SEQUENCE:
        # Check for missing vs out-of-order
        missing = [s for s in COURSE_SECTION_SEQUENCE if s.lower().replace(" ", "_") not in found_keys]
        error_msg = f"Sequence mismatch. Found: {len(found_keys)}/10 sections."
        if missing:
            error_msg += f" Missing: {missing}"
        else:
            error_msg += " Order is incorrect."
            
        ctx.log("STAGE-1", "SEC-SEQUENCE-FAIL", error_msg, fatal=True)
        return

    # 3. Partitioning the Zones
    # A. Header Zone: Everything before the first mandatory heading
    first_idx = found_headers[0]['line_index']
    header_raw = "\n".join(lines[:first_idx]).strip()

    # B. Explicit Sections: Content between headings
    sections_content = {}
    for i in range(len(found_headers)):
        current_h = found_headers[i]
        start_line = current_h['line_index'] + 1
        
        # If there's a next header, that's our boundary
        if i + 1 < len(found_headers):
            end_line = found_headers[i+1]['line_index']
        else:
            # For the last section (RUBRICS), content goes until 
            # we hit the Footer marker or end of file
            end_line = len(lines)
            
        content = "\n".join(lines[start_line:end_line]).strip()
        sections_content[current_h['key']] = content

    # C. Footer Zone: 
    # Logic: If 'RUBRICS' content contains a footer marker (like "---" or "Author:"),
    # we would split it here. For now, we assume the footer follows the last section.
    # (Refine this if you have a specific footer marker in your .md files)
    footer_raw = "" 

    # 4. Attach to Context
    ctx.structure = DocumentStructure(
        header_block_raw=header_raw,
        explicit_sections=sections_content,
        footer_block_raw=footer_raw
    )