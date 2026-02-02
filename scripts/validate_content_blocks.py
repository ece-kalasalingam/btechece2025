"""
=====================================================================
STAGE-2c : CONTENT BLOCK GRAMMAR VALIDATION (KARE R2025)
=====================================================================

PURPOSE
-------
Validate grammar-level correctness of topics, experiments,
and X-activities AFTER structural validation.

SCOPE
-----
- Topic title + sub-topic separator
- Experiment / X-activity title + description presence
- Sentence / paragraph form checks (lightweight)

NON-GOALS
---------
- No semantic checks
- No hour checks
- No standards / constraints interpretation
- No NBA / ABET / CO validation

=====================================================================
"""

from typing import List
import re

from validate_structure import (
    UnitBlock,
    ActivityBlock,
    ValidationError,
)

# ---------------------------
# Invariant prefixes
# ---------------------------

TG_PREFIX  = "TG"   # Topic Grammar
EXP_PREFIX = "EXP"  # Experiment Grammar
XG_PREFIX  = "XG"   # X-Activity Grammar


# ---------------------------
# Dispatch
# ---------------------------

def validate_content_blocks(course_code, units):
    validate_topic_grammar(course_code, units)
    validate_experiment_grammar(course_code, units)
    validate_x_activity_grammar(course_code, units)


# ---------------------------
# Topic Grammar
# ---------------------------
# Topic grammar is STRICT by regulation:
# title : sub-topics (colon is mandatory)

def validate_topic_grammar(course_code: str, units: List[UnitBlock]) -> None:
    for u in units:
        for idx, topic in enumerate(u.topics, start=1):
            if not topic.strip():
                raise ValidationError(
                    course_code,
                    f"{TG_PREFIX}-EMPTY",
                    f"Unit {u.number}: Topic {idx} is empty"
                )

            if ":" not in topic: #mandatory
                raise ValidationError(
                    course_code,
                    f"{TG_PREFIX}-COLON-MISSING",
                    f"Unit {u.number}: Topic {idx} must contain ':' separating title and sub-topics"
                )

            head, tail = topic.split(":", 1)
            if not head.strip() or not tail.strip():
                raise ValidationError(
                    course_code,
                    f"{TG_PREFIX}-INCOMPLETE",
                    f"Unit {u.number}: Topic {idx} must have content on both sides of ':'"
                )


# ---------------------------
# Experiment Grammar
# ---------------------------

def validate_experiment_grammar(course_code: str, units: List[UnitBlock]) -> None:
    for u in units:
        for idx, exp in enumerate(u.experiments, start=1):
            _validate_activity_block(
                course_code,
                exp,
                f"{EXP_PREFIX}",
                f"Unit {u.number}: Experiment {idx}",
            )


# ---------------------------
# X-Activity Grammar
# ---------------------------

def validate_x_activity_grammar(course_code: str, units: List[UnitBlock]) -> None:
    for u in units:
        for idx, act in enumerate(u.x_activities, start=1):
            _validate_activity_block(
                course_code,
                act,
                f"{XG_PREFIX}",
                f"Unit {u.number}: X-Activity {idx}",
            )


# ---------------------------
# Shared Activity Grammar
# ---------------------------

def _validate_activity_block(
    course_code: str,
    block: ActivityBlock,
    prefix: str,
    label: str,
) -> None:
    # ---- Title checks ----
    if not block.title.strip():
        raise ValidationError(
            course_code,
            f"{prefix}-TITLE-MISSING",
            f"{label}: title is missing"
        )

    if _count_sentences(block.title) != 1:
        raise ValidationError(
            course_code,
            f"{prefix}-TITLE-SENTENCE-COUNT",
            f"{label}: title must be exactly one sentence"
        )

    # ---- Description checks ----
    if not block.description.strip():
        raise ValidationError(
            course_code,
            f"{prefix}-DESCRIPTION-MISSING",
            f"{label}: description paragraph is missing"
        )

    if _count_sentences(block.description) < 1:
        raise ValidationError(
            course_code,
            f"{prefix}-DESCRIPTION-NOT-PARAGRAPH",
            f"{label}: description must be a paragraph (one or more sentences)"
        )
def _count_sentences(text: str) -> int:
    """
    Heuristic sentence counter.
    Not linguistically exact by design.
    """
    return len([s for s in re.split(r"[.!?]+", text) if s.strip()])