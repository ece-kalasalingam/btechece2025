"""
STAGE 2a: Metadata Extraction
Verbatim: Pulls Category, Type, LTPXC, and Prerequisites from the Preamble.
"""
import re
from typing import List
from scripts.contracts import CourseMetadata, CourseCategory, CourseType, PREAMBLE_TITLE, ValidationError, StructuredSection


# Patterns for R2025 metadata blocks
META_RE = {
    "category": re.compile(r"category\s*:\s*([A-Z]+)", re.I),
    "type": re.compile(r"type\s*:\s*([\w-]+)", re.I),
    "ltpxc": re.compile(r"([0-9])\s*-\s*([0-9])\s*-\s*([0-9])\s*-\s*([0-9])\s*-\s*([0-9.]+)", re.I),
    "prereq": re.compile(r"prerequisite\s*:\s*(.*)", re.I),
    "coreq": re.compile(r"corequisite\s*:\s*(.*)", re.I),
    # NEW: Pattern to find the Title if it's written in the preamble body
    "title": re.compile(r"course\s*title\s*:\s*(.*)", re.I) 
}

def extract_course_metadata(course_code: str, structured_sections: List[StructuredSection]) -> CourseMetadata:
    # 1. Locate Preamble
    preamble = next((s for s in structured_sections if s.section.title == PREAMBLE_TITLE), None)
    
    if not preamble or not preamble.section.body:
        raise ValidationError(course_code, "META-MISSING", "Preamble metadata block is empty or missing")

    body = preamble.section.body

    # 2. Extract matches
    cat_match = META_RE["category"].search(body)
    type_match = META_RE["type"].search(body)
    ltpxc_match = META_RE["ltpxc"].search(body)
    
    # NEW: Extract Course Title (or default to "Untitled Course")
    title_match = META_RE["title"].search(body)
    course_title = title_match.group(1).strip() if title_match else "Unknown Course"

    # 3. Explicit Guard (Silences Pylance "group is not attribute of None")
    if cat_match is None or type_match is None or ltpxc_match is None:
        raise ValidationError(course_code, "META-INCOMPLETE", "Missing Category, Type, or LTPXC in preamble")

    # 4. Optional Match handling
    pre_match = META_RE["prereq"].search(body)
    co_match = META_RE["coreq"].search(body)

    # 5. Return the object using correctly named local variables
    return CourseMetadata(
        category=CourseCategory(cat_match.group(1).upper()),
        course_type=CourseType(type_match.group(1).upper()),
        course_code=course_code,  # FIXED: Use the argument passed to function
        course_title=course_title, # FIXED: Use extracted course_title
        l=int(ltpxc_match.group(1)),
        t=int(ltpxc_match.group(2)),
        p=int(ltpxc_match.group(3)),
        x=int(ltpxc_match.group(4)),
        c=float(ltpxc_match.group(5)),
        prerequisite=pre_match.group(1).strip() if pre_match else None,
        corequisite=co_match.group(1).strip() if co_match else None
    )