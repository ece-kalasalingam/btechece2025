# scripts/stage_3.py
import re
from typing import Any
from datetime import datetime
from scripts.paths import get_path
from scripts.utils import get_automated_version, get_git_metadata
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

def normalize_bos_date(raw_text: str) -> str:
    current_year = str(datetime.now().year)
    # Year logic: prefix '20' if 2 digits
    four_digit = re.search(r"\b(\d{4})\b", raw_text)
    two_digit = re.search(r"\b(\d{2})\b", raw_text)
    year = four_digit.group(1) if four_digit else (f"20{two_digit.group(1)}" if two_digit else current_year)
    
    # Month logic
    month_part = "".join(re.findall(r"[a-zA-Z]", raw_text)).lower()
    month_map = MONTH_MAP
    standard_month = month_map.get(month_part, month_part.capitalize()[:3] + "." if len(month_part) >=3 else "Jan.")
    return f"{standard_month}/{year}"

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
    git_ver, git_date = get_git_metadata(file_path)
    
    footer_dict["document_version"] = git_ver
    footer_dict["document_date"] = git_date

    # RULE: Automatic Versioning (Git Count + Timestamp)
    file_path = get_path(COURSES_DIR) / f"{ctx.course_code}.md"
    footer_dict["document_version"] = get_automated_version(file_path)
    ctx.log("STAGE-3", "AUTO-VER", f"Assigned version: {footer_dict['document_version']}", fatal=False)

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