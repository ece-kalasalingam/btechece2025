"""
STAGE 2a: Metadata Extraction
Verbatim: Pulls Category, Type, LTPXC, and Prerequisites from the Preamble.
"""
import re
from typing import List
from scripts.contracts import (
    CourseMetadata, 
    CourseCategory, 
    CourseType, 
    PREAMBLE_TITLE, 
    ValidationError, 
    StructuredSection
)

# Patterns for R2025 metadata blocks
META_RE = {
    "category": re.compile(r"category\s*:\s*([A-Z]+)", re.I),
    "type": re.compile(r"type\s*:\s*([\w-]+)", re.I),
    "ltpxc": re.compile(r"([0-9])\s*-\s*([0-9])\s*-\s*([0-9])\s*-\s*([0-9])\s*-\s*([0-9.]+)", re.I),
    "prereq": re.compile(r"prerequisite\s*:\s*(.*)", re.I),
    "coreq": re.compile(r"corequisite\s*:\s*(.*)", re.I),
    "title": re.compile(r"course\s*title\s*:\s*(.*)", re.I) 
}

def extract_course_metadata(course_code: str, structured_sections: List[StructuredSection]) -> CourseMetadata:
    """
    Identifies the preamble section and extracts the administrative 
    LTPXC and Course Categorization data.
    """
    # 1. Locate Preamble Section
    preamble = next(
        (s for s in structured_sections if s.section.title in ["__PREAMBLE__", "COURSE METADATA", PREAMBLE_TITLE]), 
        None
    )
    
    # Fallback if the standard title isn't found
    if not preamble or not preamble.section.body:
        preamble = next((s for s in structured_sections if "METADATA" in s.section.title.upper()), None)

    if not preamble or not preamble.section.body:
        raise ValidationError(course_code, "META-MISSING", "Preamble metadata block is empty or missing")

    body = preamble.section.body
    
    # 2. Extract matches
    cat_match = META_RE["category"].search(body)
    type_match = META_RE["type"].search(body)
    ltpxc_match = META_RE["ltpxc"].search(body)
    title_match = META_RE["title"].search(body)
    
    # 3. Explicit Guard: Ensures all mandatory fields are present
    # This narrowing tells Pylance that the .group() calls below are safe.
    if cat_match is None or type_match is None or ltpxc_match is None:
        raise ValidationError(course_code, "META-INCOMPLETE", "Missing Category, Type, or LTPXC in preamble")

    # 4. Extract strings from matches immediately after the guard
    raw_cat_str = cat_match.group(1).upper()
    raw_type_str = type_match.group(1).upper().replace("-", "_")
    course_title = title_match.group(1).strip() if title_match else "Unknown Course"

    # 5. Enum Casting with deterministic error handling
    try:
        category_val = CourseCategory(raw_cat_str)
    except ValueError:
        raise ValidationError(
            course_code, 
            "META-INVALID-CATEGORY", 
            f"'{raw_cat_str}' is not a valid R2025 Course Category."
        )

    try:
        type_val = CourseType(raw_type_str)
    except ValueError:
        raise ValidationError(
            course_code, 
            "META-INVALID-TYPE", 
            f"'{raw_type_str}' is not a valid R2025 Course Type."
        )

    # 6. Optional Match handling (Safe to use .group because we check presence)
    pre_match = META_RE["prereq"].search(body)
    co_match = META_RE["coreq"].search(body)

    # 7. Final Object Assembly
    # Since ltpxc_match was part of the Guard, .group(n) is safe here
    return CourseMetadata(
        category=category_val,
        course_type=type_val,
        course_code=course_code,
        course_title=course_title,
        l=int(ltpxc_match.group(1)),
        t=int(ltpxc_match.group(2)),
        p=int(ltpxc_match.group(3)),
        x=int(ltpxc_match.group(4)),
        c=float(ltpxc_match.group(5)),
        prerequisite=pre_match.group(1).strip() if pre_match else None,
        corequisite=co_match.group(1).strip() if co_match else None
    )