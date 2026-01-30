"""
=====================================================================
STAGE-2c : CONTENT BLOCK GRAMMAR VALIDATION (KARE R2025)
=====================================================================

PURPOSE
-------
Validate grammar and minimal structural completeness of
content blocks inside units and activities.

This stage operates AFTER:
- Stage-2a (content shape inference)
- Stage-2b (structural validation)

INPUTS
------
- Parsed syllabus sections
- Extracted UnitBlocks (from Stage-2b extractors)

NON-GOALS
---------
- No content shape inference
- No hour validation
- No pedagogical quality checks
- No NBA / ABET / CO validation
- No deduplication or normalization

DESIGN PRINCIPLES
-----------------
- Grammar-level validation only
- No semantic interpretation
- Fail-fast on first violation
- Shape-agnostic unless explicitly stated

REGULATION BASIS
----------------
KARE B.Tech Regulations R2025

=====================================================================
"""
from typing import List
from dataclasses import dataclass

from validate_structure import (
    UnitBlock,
    MarkdownSection,
    ValidationError,
)
# Topic Grammar
TG_PREFIX = "TG"

# Experiment Grammar
EXP_PREFIX = "EXP"

# X-Activity Grammar
XG_PREFIX = "XG"
def validate_content_blocks(
    course_code: str,
    sections: List[MarkdownSection],
    units: List[UnitBlock],
) -> None:
    """
    Dispatch content-block grammar validators.
    """
    validate_topic_grammar(course_code, units)
    validate_experiment_blocks(course_code, units)
    validate_x_activity_blocks(course_code, units)

def validate_topic_grammar(course_code: str, units: List[UnitBlock]) -> None:
    for u in units:
        for idx, topic in enumerate(u.topics, start=1):
            if ":" not in topic:
                raise ValidationError(
                    course_code,
                    f"{TG_PREFIX}-COLON-MISSING",
                    f"Unit {u.number}: Topic {idx} must contain ':' separating title and sub-topics"
                )

def validate_experiment_blocks(course_code: str, units: List[UnitBlock]) -> None:
    for u in units:
        for idx, exp in enumerate(u.experiments, start=1):
            if not exp.strip():
                raise ValidationError(
                    course_code,
                    f"{EXP_PREFIX}-TITLE-MISSING",
                    f"Unit {u.number}: Experiment {idx} title missing"
                )

            # Description presence check is deferred to section-level parsing
            # Placeholder invariant for future extension
def validate_x_activity_blocks(course_code: str, units: List[UnitBlock]) -> None:
    for u in units:
        if u.x_hours:
            if not u.experiments:
                raise ValidationError(
                    course_code,
                    f"{XG_PREFIX}-ACTIVITY-MISSING",
                    f"Unit {u.number}: X-activity hours declared but no activity description provided"
                )