"""
=====================================================================
STAGE-1 : STRUCTURAL GATEKEEPER & TEXT PARTITIONING (KARE R2025)
=====================================================================

PURPOSE
-------
1. Identify the 'Zero Point' (Course Code) and strip preceding junk.
2. Capture the Course Title from the first line.
3. Identify R2025 section headers (Level 2 Markdown ##).
4. Slicing text into Header and Section blocks for Stage-2.
"""

import re
from typing import List, Dict
from scripts.contracts import DocumentStructure, CourseExecutionContext, COURSE_SECTION_SEQUENCE
from scripts.patterns import (
    COURSE_CODE_HEADER_PATTERN,
    SECTION_TITLE_MAP
)
from scripts.utils import get_clean_section_title

def validate_structure(raw_text: str, ctx: CourseExecutionContext):
    lines = raw_text.splitlines()
    
    # 1. Find Anchor (Course Code)
    start_idx = -1
    for i, line in enumerate(lines):
        if COURSE_CODE_HEADER_PATTERN.match(line.strip()):
            start_idx = i
            break
    
    if start_idx == -1:
        ctx.log("STAGE-1", "START-NOT-FOUND", "Anchor not found.", fatal=True)
        return

    relevant_lines = lines[start_idx:]
    
    # 2. Identify ALL Level-2 Headers as Boundaries
    # This ensures "Unit 1" stops the "Description" block even if not in sequence
    found_headers = []
    for i, line in enumerate(relevant_lines):
        if line.strip().startswith("##"):
            # Use a more aggressive cleaner that takes just the first part 
            # e.g., "## Unit 1: Fundamentals" -> "UNIT 1"
            raw_title = line.strip().lstrip('#').strip().upper()
            base_title = raw_title.split(':')[0].strip() # Get "UNIT 1"
            
            found_headers.append({
                "key": base_title.lower().replace(" ", "_"),
                "line_index": i,
                "raw_title": raw_title
            })

    # 3. Validate the Mandatory Sequence
    # We check if the keys we NEED exist in the keys we FOUND
    expected_keys = [SECTION_TITLE_MAP[item["title"]] for item in COURSE_SECTION_SEQUENCE]
    found_keys = [h['key'] for h in found_headers]
    
    for req_key in expected_keys:
        if req_key not in found_keys:
            ctx.log("STAGE-1", "MISSING-SECTION", f"Mandatory section '{req_key}' missing.", fatal=True)

    # 4. Partitioning (The Slicer)
    # This logic now correctly stops at ANY ## header
    first_header_line = found_headers[0]['line_index']
    header_raw = f"Course Title: {lines[0].lstrip('#').strip()}\n" + \
                 "\n".join(relevant_lines[:first_header_line]).strip()

    sections_content = {}
    for i in range(len(found_headers)):
        curr = found_headers[i]
        start = curr['line_index'] + 1
        # Stop at the very next ## header found
        end = found_headers[i+1]['line_index'] if i+1 < len(found_headers) else len(relevant_lines)
        
        content = "\n".join(relevant_lines[start:end]).strip()
        sections_content[curr['key']] = content

    ctx.structure = DocumentStructure(
        header_block_raw=header_raw,
        explicit_sections=sections_content,
        footer_block_raw=""
    )
    
    #if ctx.is_eligible:
        #print(f"✅ Stage 1: Structure & Partitioning complete for {ctx.course_code}")