# scripts/stage_3.py
from typing import Any, Dict
from scripts.contracts import CourseExecutionContext
from scripts.patterns import (
    META_PATTERNS, 
    PREREQ_PATTERN, 
    COREQ_PATTERN,
    COURSE_TITLE_PATTERN
)

def _extract_optional_field(key: str, pattern: Any, text: str, ctx: CourseExecutionContext):
    if ctx.metadata is None: ctx.metadata = {}
    match = pattern.search(text)
    if match:
        val = match.group(1).strip()
        if val.upper() not in ["NONE", "NIL", "N.A", "NA", ""]:
            ctx.metadata[key] = val

def run_metadata_extraction(ctx: CourseExecutionContext):
    if ctx.structure is None or not ctx.is_eligible:
        return
    if ctx.metadata is None: ctx.metadata = {}

    header_text = ctx.structure.header_block_raw

    # Extract Title (Key aligned with Stage 4)
    title_match = COURSE_TITLE_PATTERN.search(header_text)
    ctx.metadata["course_title"] = title_match.group(1).strip() if title_match else "UNTITLED"
    
    # Extract Category & Type
    for field in ["category", "type"]:
        pattern = META_PATTERNS.get(field)
        if pattern:
            match = pattern.search(header_text)
            if match:
                ctx.metadata[f"course_{field}"] = match.group(1).upper().strip()

    # Extract LTPXC
    ltpxc_pattern = META_PATTERNS.get("ltpxc")
    if ltpxc_pattern:
        match = ltpxc_pattern.search(header_text)
        if match:
            try:
                ctx.metadata.update({
                    "l": int(match.group(1)), "t": int(match.group(2)),
                    "p": int(match.group(3)), "x": int(match.group(4)),
                    "c": float(match.group(5))
                })
            except (ValueError, IndexError):
                ctx.log("STAGE-3", "LTPXC-CONV-ERR", "Numeric conversion failed.")

    _extract_optional_field("prerequisite", PREREQ_PATTERN, header_text, ctx)
    _extract_optional_field("corequisite", COREQ_PATTERN, header_text, ctx)