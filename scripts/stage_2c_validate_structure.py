"""
STAGE 2c: Structural Validation
Verbatim: Enforces R2025 Section 4.5 (5-Unit Rule) and Project constraints.
"""
from typing import List
from scripts.contracts import ContentShape, ValidationError, StructuredSection
from scripts.patterns import UNIT_HEADER_PATTERN
from scripts.utils import find_sections_by_title_pattern

def validate_course_structure(
    course_code: str, 
    structured_sections: List[StructuredSection], 
    shape: ContentShape
):
    unit_sections = find_sections_by_title_pattern(structured_sections, UNIT_HEADER_PATTERN)
    # Rule 1: Project courses MUST NOT have Unit headers
    if shape == ContentShape.PROJECT:
        if len(unit_sections) > 0:
            raise ValidationError(
                course_code, 
                "STRUC-PROJ-UNITS", 
                "Project-based courses (R2025 Sec 4.4) must not be organized into Unit sections."
            )
        return # Exit early as 5-unit rule doesn't apply to projects

    # Rule 2: Academic/Skill courses MUST have exactly 5 units (R2025 Section 4.5)
    if len(unit_sections) != 5:
        raise ValidationError(
            course_code, 
            "STRUC-UNIT-COUNT", 
            f"Syllabus has {len(unit_sections)} units. R2025 requires exactly 5 units."
        )