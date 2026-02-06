# scripts/stage_3.py
import re
from typing import Any
from datetime import datetime
from scripts.paths import get_path
from scripts.utils import get_git_metadata
from scripts.contracts import CourseExecutionContext, COURSES_DIR, MONTH_MAP
from scripts.patterns import (
    META_PATTERNS, 
    PREREQ_PATTERN, 
    COREQ_PATTERN,
    COURSE_TITLE_PATTERN,
    COURSE_CODE_HEADER_PATTERN,
    FOOTER_PATTERNS
)

def _extract_optional_field(key: str, pattern: Any, text: str, ctx: CourseExecutionContext):
    if ctx.metadata is None: ctx.metadata = {}
    match = pattern.search(text)
    if match:
        val = match.group(1).strip()
        if val.upper() not in ["NONE", "NIL", "N.A", "NA", ""]:
            ctx.metadata[key] = val

# FIND: normalize_bos_date(raw_text: str)
# REPLACE WITH:
def normalize_bos_date(date_str: str) -> str:
    """Targeted normalization for the date component only."""
    if not date_str or date_str.upper() in ["N/A", "NONE"]:
        return "N/A"
    
    # Split "Jan/25" or "January/2025"
    parts = date_str.split('/')
    if len(parts) != 2:
        return date_str # Fallback if format is weird
    
    month_part = parts[0].strip().lower().replace(".", "")
    year_part = parts[1].strip()
    
    # Use MONTH_MAP from contracts.py
    normalized_month = MONTH_MAP.get(month_part, month_part.capitalize())
    
    # Normalize Year (2-digit to 4-digit)
    if len(year_part) == 2:
        normalized_year = f"20{year_part}"
    else:
        normalized_year = year_part
        
    return f"{normalized_month} {normalized_year}"

def run_footer_extraction(ctx: CourseExecutionContext):
    if ctx.metadata is None: ctx.metadata = {}
    """Extracts structured governance data from the footer block."""
    footer_raw = ctx.metadata.get("footer_block_raw", "")
    footer_dict = {}

    # Extract based on Footer Patterns
    for key, pattern in FOOTER_PATTERNS.items():
        match = pattern.search(footer_raw)
        if match:
            val = match.group(1).strip()
            if val:
                # Handle numeric Course Level
                if key == "course_level":
                    try:
                        footer_dict[key] = int(val) if val.isdigit() else 1
                    except ValueError:
                        ctx.log("STAGE-3", "LVL-CONV-ERR", f"Level '{val}' is not a number.")
                elif key == "bos_date":
                    footer_dict[key] = normalize_bos_date(val)
                else:
                    footer_dict[key] = val

    # RULE: Default "Course Author" if empty
    if not footer_dict.get("course_author"):
        footer_dict["course_author"] = "Department Curriculum Committee"

    file_path = get_path(COURSES_DIR) / f"{ctx.course_code}.md"
    git_ver, git_date, git_hash = get_git_metadata(file_path)
    
    footer_dict["document_version"] = git_ver
    footer_dict["document_date"] = git_date
    footer_dict["document_git_hash"] = git_hash

    # Store for Stage 4 assembly
    ctx.metadata["footer_governance"] = footer_dict

def run_metadata_extraction(ctx: CourseExecutionContext):
    if ctx.structure is None or not ctx.is_eligible:
        return
    if ctx.metadata is None: ctx.metadata = {}

    header_text = ctx.structure.header_block_raw

    # Extract Course Code
    title_match = COURSE_CODE_HEADER_PATTERN.search(header_text)
    ctx.course_code = title_match.group(1).strip() if title_match else "UNTITLED"

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
    # --- 2. Footer Extraction (Governance) ---
    run_footer_extraction(ctx)