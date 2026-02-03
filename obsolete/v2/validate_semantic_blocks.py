"""
=====================================================================
STAGE-2d : SEMANTIC BLOCK PRESENCE & SHAPE VALIDATION (KARE R2025)
=====================================================================

PURPOSE
-------
Validate presence and structural shape of mandatory
semantic blocks AFTER Stage-2a, Stage-2b, and Stage-2c.

INPUTS
------
- Inferred ContentShape (from Stage-2a)
- Parsed syllabus sections (structure only)
- Extracted UnitBlocks (from Stage-2b)

NON-GOALS
---------
- No semantic interpretation of content
- No Bloom-level correctness checks
- No NBA / ABET / CO articulation validation
- No pedagogy or quality judgement
- No hour inference or reconciliation

DESIGN PRINCIPLES
-----------------
- Fail-fast on first violated invariant
- Presence and shape only (not meaning)
- No cross-stage responsibility leakage
- Deterministic and auditable validation

REGULATION BASIS
----------------
KARE B.Tech Regulations R2025

=====================================================================
"""

from typing import List, Optional
import re

from validate_structure import (
    ContentShape,
    MarkdownSection,
    UnitBlock,
    ValidationError,
)

# ------------------------------------------------------------------
# Invariant prefixes
# ------------------------------------------------------------------

SB_PREFIX  = "SB"     # Semantic Block
COB_PREFIX = "COB"    # Course Outcome Block
TB_PREFIX  = "TB"     # Textbook Block
RE_PREFIX  = "RE"     # Reference Block
ASB_PREFIX = "ASB"    # Assessment Scheme Block
PRB_PREFIX = "PRB"    # Project Block


# ------------------------------------------------------------------
# Regex patterns (shape only)
# ------------------------------------------------------------------

CO_ID_RE = re.compile(r"\bCO\d+\b", re.I)
BULLET_RE = re.compile(r"^\s*[-*]\s+.+")


# ------------------------------------------------------------------
# Dispatcher
# ------------------------------------------------------------------

def validate_semantic_blocks(
    course_code: str,
    content_shape: ContentShape,
    sections: List[MarkdownSection],
    units: List[UnitBlock],
) -> None:
    validate_course_objectives(course_code, sections)
    validate_course_outcomes(course_code, sections)
    validate_textbooks(course_code, sections)
    validate_references(course_code, sections)

    if content_shape == ContentShape.PROJECT:
        validate_project_blocks(course_code, sections)
    else:
        validate_assessment_scheme(course_code, sections)


# ------------------------------------------------------------------
# Course Objectives
# ------------------------------------------------------------------

def validate_course_objectives(course_code: str, sections: List[MarkdownSection]) -> None:
    sec = _find_section(sections, ("course objectives", "objectives"))
    if not sec:
        raise ValidationError(
            course_code,
            f"{SB_PREFIX}-OBJECTIVES-MISSING",
            "Course Objectives section is missing"
        )

    bullets = _extract_bullets(sec.body)
    if len(bullets) < 3:
        raise ValidationError(
            course_code,
            f"{SB_PREFIX}-OBJECTIVES-COUNT",
            "Course Objectives must contain at least 3 bullet points"
        )


# ------------------------------------------------------------------
# Course Outcomes (COs)
# ------------------------------------------------------------------

def validate_course_outcomes(course_code: str, sections: list) -> None:
    sec = _find_section(sections, ("course outcomes",))
    if not sec:
        raise ValidationError(course_code, "COB-MISSING", "Course Outcomes section missing")

    bullets = _extract_bullets(sec.body)
    
    if not bullets:
        raise ValidationError(course_code, "COB-NO-BULLETS", "Outcomes must be listed as bullet points")

    for line in bullets:
        clean_line = line.strip().lstrip('-*+').strip() #line.strip().upper()
        # Check if the line starts with 'CO' (e.g., CO1, CO 1, Course Outcome)
        if clean_line.startswith("CO"):
            raise ValidationError(
                course_code, 
                "COB-LABEL-FOUND", 
                f"Remove 'CO' prefix from outcome: '{line[:15]}...'. "
                "No manual mentioning of CO1, CO2 and so on."
            )

    # KARE R2025: 3 to 7 outcomes required
    if not (3 <= len(bullets) <= 7):
        raise ValidationError(
            course_code, 
            "COB-COUNT", 
            f"Found {len(bullets)} outcomes, but R2025 requires 3-7"
        )

# ------------------------------------------------------------------
# Textbooks
# ------------------------------------------------------------------

def validate_textbooks(course_code: str, sections: List[MarkdownSection]) -> None:
    sec = _find_section(sections, ("textbook", "textbooks"))
    if not sec:
        raise ValidationError(
            course_code,
            f"{TB_PREFIX}-MISSING",
            "Textbooks section is missing"
        )

    entries = [
        line.strip()
        for line in sec.body.splitlines()
        if line.strip()
    ]

    if not entries:
        raise ValidationError(
            course_code,
            f"{TB_PREFIX}-EMPTY",
            "At least one textbook entry is required"
        )

    # NOTE:
    # Citation format, edition, ISBN, and author validation
    # are intentionally NOT enforced at Stage-2d.
# ------------------------------------------------------------------
# Textbooks
# ------------------------------------------------------------------

def validate_references(course_code: str, sections: List[MarkdownSection]) -> None:
    sec = _find_section(sections, ("reference", "references"))
    if not sec:
        raise ValidationError(
            course_code,
            f"{RE_PREFIX}-MISSING",
            "References section is missing"
        )

    entries = [
        line.strip()
        for line in sec.body.splitlines()
        if line.strip()
    ]

    if not entries:
        raise ValidationError(
            course_code,
            f"{RE_PREFIX}-EMPTY",
            "At least one reference entry is required"
        )

    # NOTE:
    # Format and  validation
    # are intentionally NOT enforced at Stage-2d.

# ------------------------------------------------------------------
# Assessment Scheme (Non-Project Courses)
# ------------------------------------------------------------------

def validate_assessment_scheme(course_code: str, sections: List[MarkdownSection]) -> None:
    sec = _find_section(sections, ("assessment",))
    if not sec:
        raise ValidationError(
            course_code,
            f"{ASB_PREFIX}-MISSING",
            "Assessment scheme section is missing"
        )

    if not sec.body.strip():
        raise ValidationError(
            course_code,
            f"{ASB_PREFIX}-EMPTY",
            "Assessment scheme section must not be empty"
        )


    # NOTE:
    # Weightage correctness, percentage totals, and rubric quality
    # are NOT validated at Stage-2d.


# ------------------------------------------------------------------
# Project / Internship Courses
# ------------------------------------------------------------------

def validate_project_blocks(course_code: str, sections: List[MarkdownSection]) -> None:
    required_blocks = [
        ("project description", "PRB-DESCRIPTION-MISSING"),
        ("objectives", "PRB-OBJECTIVES-MISSING"),
        ("deliverables", "PRB-DELIVERABLES-MISSING"),
        ("assessment", "PRB-ASSESSMENT-MISSING"),
    ]

    for key, code in required_blocks:
        if not _find_section(sections, (key,)):
            raise ValidationError(
                course_code,
                code,
                f"Project block '{key}' is missing"
            )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _find_section(
    sections: List[MarkdownSection],
    keys: tuple[str, ...],
) -> Optional[MarkdownSection]:
    """
    Word-boundary, case-insensitive section matcher.
    Prevents accidental substring matches.
    """
    for sec in sections:
        title = sec.title.lower()
        for key in keys:
            if re.search(rf"\b{re.escape(key)}\b", title):
                return sec
    return None


def _extract_bullets(text: str) -> List[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if BULLET_RE.match(line)
    ]
def extract_declared_cos(
    course_code: str,
    sections: List[MarkdownSection],
) -> List[str]:
    """
    Extract declared the Course Outcomes section.

    Structure-only extraction. No semantic interpretation.
    """

    sec = _find_section(sections, ("course outcomes",))
    if not sec:
        raise ValidationError(
            course_code,
            "COB-MISSING",
            "Course Outcomes section is missing"
        )

    bullets = _extract_bullets(sec.body)
    if not bullets:
        raise ValidationError(
            course_code,
            "COB-NO-BULLETS",
            "Course Outcomes must be listed as bullet points"
        )
    for line in bullets:
        clean_line = line.strip().lstrip('-*+').strip() #line.strip().upper()
    return [ 
        f"CO{i+1}: {line.strip().lstrip('-*+').strip()}" 
        for i, line in enumerate(bullets) if line.strip()
    ]