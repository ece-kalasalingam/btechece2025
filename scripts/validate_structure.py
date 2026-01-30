"""
=====================================================================
STAGE-2b : STRUCTURAL VALIDATION ENGINE (KARE R2025)
=====================================================================

PURPOSE
-------
Validate syllabus STRUCTURE after content-shape inference.

INPUTS
------
- Inferred ContentShape (from Stage-2a)
- Parsed syllabus sections (structure only)
- L-T-P-X derived total hours

NON-GOALS
---------
- No semantic inference
- No NBA / ABET / CO validation
- No appendix processing
- No hour inference from counts

DESIGN PRINCIPLES
-----------------
- Fail-fast on first violated invariant
- X-activity is a first-class hour block
- No recovery, no defaults, no guessing
- Validators are shape-specific and exclusive

REGULATION BASIS
----------------
KARE B.Tech Regulations R2025

=====================================================================
"""
# validate_structure.py

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
import re


# ---------------------------
# Shared contracts
# ---------------------------

class ContentShape(Enum):
    ACADEMIC_THEORY = "academic_theory"
    ACADEMIC_INTEGRATED = "academic_integrated"
    SKILL_PRACTICE = "skill_practice"
    PROJECT = "project"


@dataclass(frozen=True)
class MarkdownSection:
    title: str
    body: str


class ValidationError(Exception):
    def __init__(self, course_code: str, invariant_id: str, message: str):
        super().__init__(f"{course_code} [{invariant_id}]: {message}")


# ---------------------------
# Regex + Normalization
# ---------------------------

UNIT_HEADER_RE = re.compile(
    r"""
    \bunit
    \s*[-:]?\s*
    (?P<num>[1-9]\d*)
    \s*[-:–]?\s*
    (?P<title>.*)?
    """,
    re.IGNORECASE | re.VERBOSE,
)

THEORY_HOURS_RE = re.compile(r"(theory\s*hours?|lecture\s*hours?)\s*[:\-]?\s*(\d+)", re.I)
LAB_HOURS_RE    = re.compile(r"(lab\s*hours?|practical\s*hours?)\s*[:\-]?\s*(\d+)", re.I)
X_HOURS_RE      = re.compile(r"(x\s*hours?|activity\s*hours?)\s*[:\-]?\s*(\d+)", re.I)

TOTAL_HOURS_RE  = re.compile(r"(total\s*hours?)\s*[:\-]?\s*(\d+)", re.I)

CAPSTONE_KEYWORDS = (
    "project",
    "capstone",
    "major project",
    "minor project",
    "final year project",
)


def normalize_unit_title(raw: str) -> str:
    if not raw:
        return ""
    t = raw.strip()
    t = t.replace("&", "and")
    t = re.sub(r"^introduction\s+(to|of)\s+(.+)$", r"Basics of \2", t, flags=re.I)
    t = t.title()
    return t


# ---------------------------
# Extractors
# ---------------------------

@dataclass
class UnitBlock:
    number: int
    title: str
    topics: List[str]
    experiments: List[str]
    theory_hours: Optional[int]
    lab_hours: Optional[int]
    x_hours: Optional[int]

    @property
    def total_hours(self) -> int:
        return int(self.theory_hours or 0) + int(self.lab_hours or 0) + int(self.x_hours or 0)


def extract_units(sections: List[MarkdownSection]) -> List[UnitBlock]:
    units: List[UnitBlock] = []
    current: Optional[UnitBlock] = None

    for sec in sections:
        m = UNIT_HEADER_RE.search(sec.title)
        if m:
            if current:
                units.append(current)

            raw_title = (m.group("title") or "").strip()
            current = UnitBlock(
                number=int(m.group("num")),
                title=normalize_unit_title(raw_title),
                topics=[],
                experiments=[],
                theory_hours=None,
                lab_hours=None,
                x_hours=None,
            )
            continue

        if not current:
            continue

        for line in sec.body.splitlines():
            s = line.strip()
            if not s:
                continue

            if s.startswith(("-", "*")):
                current.topics.append(s.lstrip("-* ").strip())
                continue

            mt = THEORY_HOURS_RE.search(s)
            if mt:
                current.theory_hours = int(mt.group(2))
                continue

            ml = LAB_HOURS_RE.search(s)
            if ml:
                current.lab_hours = int(ml.group(2))
                continue

            mx = X_HOURS_RE.search(s)
            if mx:
                current.x_hours = int(mx.group(2))
                continue

            if re.search(r"\b(experiment|lab)\b", s, re.I):
                current.experiments.append(s)
                continue

    if current:
        units.append(current)

    return units


def extract_project_block(sections: List[MarkdownSection]) -> List[MarkdownSection]:
    return [s for s in sections if "project" in s.title.lower()]


def extract_project_total_hours(project_section: MarkdownSection) -> Optional[int]:
    for line in project_section.body.splitlines():
        m = TOTAL_HOURS_RE.search(line.strip())
        if m:
            return int(m.group(2))
    return None

def _check_unit_sequence(course_code: str, units: List[UnitBlock], invariant_prefix: str):
    numbers = [u.number for u in units]

    if len(set(numbers)) != len(numbers):
        raise ValidationError(
            course_code,
            f"{invariant_prefix}-UNIT-DUPLICATE",
            "Duplicate unit numbers detected"
        )

    if numbers != sorted(numbers):
        raise ValidationError(
            course_code,
            f"{invariant_prefix}-UNIT-ORDER",
            "Units must be in increasing numerical order"
        )

# ---------------------------
# Validators
# ---------------------------

def validate_course(
    course_code: str,
    inferred_shape: ContentShape,
    sections: List[MarkdownSection],
    ltpxtotal_hours: int,
) -> None:
    if inferred_shape == ContentShape.ACADEMIC_THEORY:
        validate_academic_theory(course_code, sections, ltpxtotal_hours)
    elif inferred_shape == ContentShape.ACADEMIC_INTEGRATED:
        validate_academic_integrated(course_code, sections, ltpxtotal_hours)
    elif inferred_shape == ContentShape.SKILL_PRACTICE:
        validate_skill_practice(course_code, sections, ltpxtotal_hours)
    elif inferred_shape == ContentShape.PROJECT:
        validate_project(course_code, sections, ltpxtotal_hours)
    else:
        raise ValidationError(course_code, "SHAPE-UNKNOWN", f"Unsupported content shape {inferred_shape}")


def validate_academic_theory(course_code: str, sections: List[MarkdownSection], ltpxtotal_hours: int) -> None:
    units = extract_units(sections)

    if len(units) != 5:
        raise ValidationError(course_code, "AT-UNIT-COUNT", f"Expected exactly 5 units, found {len(units)}")

    _check_unit_sequence(course_code, units, "AT")

    total_hours = 0

    for u in units:
        unit_label = f"Unit {u.number}" + (f" ({u.title})" if u.title else "")

        if u.experiments:
            raise ValidationError(
                course_code,
                "AT-EXPERIMENT-FORBIDDEN",
                f"{unit_label}: experiments are not allowed in Academic-Theory courses",
            )

        if u.lab_hours or u.x_hours:
            raise ValidationError(
                course_code,
                "AT-NON-THEORY-HOURS-FORBIDDEN",
                f"{unit_label}: lab/x hours are not allowed in Academic-Theory courses",
            )

        if not (4 <= len(u.topics) <= 8):
            raise ValidationError(
                course_code,
                "AT-TOPIC-CARDINALITY",
                f"{unit_label}: topics must be between 4 and 8 (found {len(u.topics)})",
            )

        if u.theory_hours is None:
            raise ValidationError(course_code, "AT-THEORY-HOUR-MISSING", f"{unit_label}: theory hours not declared")

        if u.theory_hours == 0:
            raise ValidationError(course_code, "AT-THEORY-HOUR-ZERO", f"{unit_label}: theory hours cannot be zero")

        total_hours += u.total_hours

    if total_hours != ltpxtotal_hours:
        raise ValidationError(
            course_code,
            "AT-HOUR-MISMATCH",
            f"Declared hours {total_hours} ≠ expected {ltpxtotal_hours}",
        )


def validate_academic_integrated(course_code: str, sections: List[MarkdownSection], ltpxtotal_hours: int) -> None:
    units = extract_units(sections)

    if len(units) != 5:
        raise ValidationError(course_code, "AI-UNIT-COUNT", f"Expected exactly 5 units, found {len(units)}")
    
    _check_unit_sequence(course_code, units, "AI")

    total_hours = 0

    for u in units:
        unit_label = f"Unit {u.number}" + (f" ({u.title})" if u.title else "")

        if not u.experiments:
            raise ValidationError(course_code, "AI-EXPERIMENT-MISSING", f"{unit_label}: at least one experiment required")

        if not (1 <= len(u.experiments) <= 4):
            raise ValidationError(course_code, "AI-EXPERIMENT-COUNT", f"{unit_label}: experiments must be 1–4")

        if u.topics and not (4 <= len(u.topics) <= 8):
            raise ValidationError(course_code, "AI-TOPIC-CARDINALITY", f"{unit_label}: topics must be 4–8 if present")

        if u.theory_hours is None and u.lab_hours is None and u.x_hours is None:
            raise ValidationError(course_code, "AI-HOUR-BLOCK-MISSING", f"{unit_label}: no theory/lab/x hours declared")

        if u.theory_hours == 0:
            raise ValidationError(course_code, "AI-THEORY-HOUR-ZERO", f"{unit_label}: theory hours cannot be zero")

        if u.lab_hours == 0:
            raise ValidationError(course_code, "AI-LAB-HOUR-ZERO", f"{unit_label}: lab hours cannot be zero")

        if u.x_hours == 0:
            raise ValidationError(course_code, "AI-X-HOUR-ZERO", f"{unit_label}: x hours cannot be zero")

        total_hours += u.total_hours

    if total_hours != ltpxtotal_hours:
        raise ValidationError(
            course_code,
            "AI-HOUR-MISMATCH",
            f"Declared hours {total_hours} ≠ expected {ltpxtotal_hours}",
        )


def validate_skill_practice(course_code: str, sections: List[MarkdownSection], ltpxtotal_hours: int) -> None:
    units = extract_units(sections)

    if units:
        _check_unit_sequence(course_code, units, "SP")

    total_hours = 0
    has_activity = False

    for u in units:
        if u.theory_hours:
            raise ValidationError(course_code, "SP-THEORY-FORBIDDEN", "Theory hours not allowed in Skill-Practice courses")

        if u.experiments or u.lab_hours or u.x_hours:
            has_activity = True

        if u.lab_hours is None and u.x_hours is None:
            raise ValidationError(course_code, "SP-PRACTICE-HOUR-MISSING", "Practice hours (lab/x) must be declared for all modules")

        if u.lab_hours == 0:
            raise ValidationError(course_code, "SP-LAB-HOUR-ZERO", "Lab hours cannot be zero")

        if u.x_hours == 0:
            raise ValidationError(course_code, "SP-X-HOUR-ZERO", "X hours cannot be zero")

        total_hours += u.total_hours

    if not has_activity:
        raise ValidationError(course_code, "SP-ACTIVITY-MISSING", "At least one activity/experiment (lab/x) is mandatory")

    if total_hours != ltpxtotal_hours:
        raise ValidationError(
            course_code,
            "SP-HOUR-MISMATCH",
            f"Declared hours {total_hours} ≠ expected {ltpxtotal_hours}",
        )


def validate_project(course_code: str, sections: List[MarkdownSection], ltpxtotal_hours: int) -> None:
    units = extract_units(sections)
    if units:
        raise ValidationError(course_code, "PR-UNIT-FORBIDDEN", "Units are not allowed in Project courses")

    project_blocks = extract_project_block(sections)
    if len(project_blocks) != 1:
        raise ValidationError(
            course_code,
            "PR-DESCRIPTION-COUNT",
            f"Expected exactly 1 project description block, found {len(project_blocks)}",
        )

    hours = extract_project_total_hours(project_blocks[0])
    if hours is None:
        raise ValidationError(course_code, "PR-HOUR-MISSING", "Project total hours not declared")

    if hours == 0:
        raise ValidationError(course_code, "PR-HOUR-ZERO", "Project total hours cannot be zero")

    if hours != ltpxtotal_hours:
        raise ValidationError(
            course_code,
            "PR-HOUR-MISMATCH",
            f"Declared hours {hours} ≠ expected {ltpxtotal_hours}",
        )