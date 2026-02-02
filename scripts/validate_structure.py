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
# NOTE:
# Title sentence count and description paragraph validation
# are enforced in Stage-2d (not here).

# validate_structure.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import re

from contracts import ValidationError, MarkdownSection, ValidationWarning, CourseMetadata
# ---------------------------
# Shared contracts
# ---------------------------

class ContentShape(Enum):
    ACADEMIC_THEORY = "academic_theory"
    ACADEMIC_INTEGRATED = "academic_integrated"
    SKILL_PRACTICE = "skill_practice"
    PROJECT = "project"


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

EXPERIMENT_TITLE_RE = re.compile(r"^\s*[\*\-]\s*(experiment|lab)\b[:\-]?\s*(?P<title>[^.]+)\.?\s*$",  re.I)
#X_ACTIVITY_TITLE_RE = re.compile(r"^\s*(x[\s\-]*activity)\b[:\-]?\s*(.+)$", re.I)
X_ACTIVITY_TITLE_RE = re.compile(r"^\s*[\*\-]\s*(x[\s\-]*activity)\b[:\-]?\s*(?P<title>.+?)$", re.I)


# ---------------------------
# Extractors
# ---------------------------

@dataclass
class ActivityBlock:
    title: str
    description: str

@dataclass
class UnitBlock:
    number: int
    title: str
    topics: List[str] = field(default_factory=list)
    experiments: List[ActivityBlock] = field(default_factory=list)
    x_activities: List[ActivityBlock] = field(default_factory=list)
    theory_hours: Optional[int] = None
    lab_hours: Optional[int] = None
    x_hours: Optional[int] = None
    mapped_cos: List[str] = field(default_factory=list)

    @property
    def total_hours(self) -> int:
        return int(self.theory_hours or 0) + int(self.lab_hours or 0) + int(self.x_hours or 0)


def extract_units(course_code:str, sections: List[MarkdownSection]) -> List[UnitBlock]:
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
                title=raw_title.strip(),
                topics=[],
                experiments=[],
                x_activities=[],
                theory_hours=None,
                lab_hours=None,
                x_hours=None,
            )

            #continue

        if not current:
            continue

        lines = sec.body.splitlines()
        i = 0
        while i < len(lines):
            s = lines[i].strip()

            if not s:
                i += 1
                continue

            # -------- Bulleted Experiment Block --------
            # Look for a line starting with a bullet followed by "Experiment"
            mexp = EXPERIMENT_TITLE_RE.search(s)
            if mexp:
                title = mexp.group("title").strip()
                desc_lines = []
                i += 1
                
                # Look for sub-bullets (indented with spaces)
                while i < len(lines):
                    sub_line = lines[i] # Don't strip yet, we need to check indentation
                    stripped_sub = sub_line.strip()
                    
                    # Stop if we hit an empty line or a new main-level bullet
                    if not stripped_sub or (sub_line.startswith((" ", "\t")) == False and stripped_sub.startswith(("*", "-"))):
                        break
                        
                    # It's a sub-bullet if it starts with indentation and a bullet marker
                    if re.match(r"^\s+[\*\-]\s+", sub_line):
                        desc_lines.append(re.sub(r"^\s*[\*\-]\s*", "", sub_line).strip())
                    
                    i += 1

                # 1. Check sub-bullet count (Your requirement: 1 to 4)
                if not (1 <= len(desc_lines) <= 4):
                    raise ValidationError(course_code, "STRUC-EXP-SUB-COUNT", 
                        f"Experiment '{title}' must have 1–4 sub-bullets (found {len(desc_lines)}) as description.")

                full_desc = " ".join(desc_lines)
                word_count = len(full_desc.split())

                # 2. Check total word count (Min 15)
                if word_count < 15:
                    raise ValidationError(course_code, "STRUC-EXP-DESC-SHORT", 
                        f"Experiment '{title}' description (sum of sub-bullets) must be at least 15 words.")

                current.experiments.append(ActivityBlock(title=title, description=full_desc))
                continue
            # -------- Bulleted X-Activity Block --------
            # Priority check: Catch X-Activity BEFORE general topics
            mxact = X_ACTIVITY_TITLE_RE.search(s)
            if mxact:
                title = mxact.group("title").strip()
                desc_lines = []
                i += 1
                
                # Look for sub-bullets (Must be indented)
                while i < len(lines):
                    sub_line_raw = lines[i]
                    sub_s = sub_line_raw.strip()
                    
                    if not sub_s: 
                        i += 1
                        continue
                    
                    # Break if the line is NOT indented (meaning it's a new main topic or hour)
                    if not (sub_line_raw.startswith(" ") or sub_line_raw.startswith("\t")):
                        break
                        
                    # Capture sub-bullet content from indented lines starting with - or *
                    if sub_s.startswith(("-", "*")):
                        desc_lines.append(sub_s.lstrip("-* ").strip())
                    
                    i += 1

                # Validation: 1 to 4 sub-bullets for X-Activity
                if not (1 <= len(desc_lines) <= 4):
                    raise ValidationError(course_code, "STRUC-XACT-SUB-COUNT", 
                        f"X-Activity '{title}' must have 1–4 sub-bullets as description.")

                full_desc = " ".join(desc_lines)
                
                # Validation: Min 15 words for the collective description
                if len(full_desc.split()) < 15:
                    raise ValidationError(course_code, "STRUC-XACT-DESC-SHORT", 
                        f"X-Activity '{title}' description must be at least 15 words.")

                current.x_activities.append(ActivityBlock(title=title, description=full_desc))
                continue # Claimed as X-Activity, skip topic check

            # -------- Topics --------
            if s.startswith(("-", "*")):
                t = s.lstrip("-* ").strip()
                if t:
                    current.topics.append(t)
                i += 1
                continue

            # -------- Hours --------
            mt = THEORY_HOURS_RE.search(s)
            if mt:
                current.theory_hours = int(mt.group(2))
                i += 1
                continue

            ml = LAB_HOURS_RE.search(s)
            if ml:
                current.lab_hours = int(ml.group(2))
                i += 1
                continue

            mx = X_HOURS_RE.search(s)
            if mx:
                current.x_hours = int(mx.group(2))
                i += 1
                continue
            i += 1

    if current:
        units.append(current)

    return units


#def extract_project_block(sections: List[MarkdownSection]) -> List[MarkdownSection]:
 #   return [s for s in sections if "project" in s.title.lower()]

def extract_project_description(sections: List[MarkdownSection]) -> Optional[MarkdownSection]:
    """
    Match ONLY the 'Project Description' section.
    Word-boundary, case-insensitive.
    """
    for s in sections:
        title = s.title.lower()
        if re.search(r"\bproject\s+description\b", title):
            return s
    return None

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
    expected_sequence = list(range(1, len(units) + 1))
    
    if numbers != expected_sequence:
        # If they are out of order OR a number is missing, this triggers
        raise ValidationError(
            course_code,
            f"{invariant_prefix}-UNIT-SEQUENCE",
            f"Units must be continuous starting from 1. Expected {expected_sequence}, found {numbers}"
        )

# ---------------------------
# Validators
# ---------------------------

def validate_course(
    course_code: str,
    inferred_shape: ContentShape,
    sections: List[MarkdownSection],
    meta: CourseMetadata,
    warnings: List[ValidationWarning],
) -> None:
    if inferred_shape == ContentShape.ACADEMIC_THEORY:
        validate_academic_theory(course_code, sections, meta)
    elif inferred_shape == ContentShape.ACADEMIC_INTEGRATED:
        validate_academic_integrated(course_code, sections, meta, warnings)
    elif inferred_shape == ContentShape.SKILL_PRACTICE:
        validate_skill_practice(course_code, sections, meta)
    elif inferred_shape == ContentShape.PROJECT:
        validate_project(course_code, sections, meta)
    else:
        raise ValidationError(course_code, "SHAPE-UNKNOWN", f"Unsupported content shape {inferred_shape}")


def validate_academic_theory(course_code: str, sections: List[MarkdownSection], meta:CourseMetadata) -> None:
    units = extract_units(course_code, sections)

    if len(units) != 5:
        raise ValidationError(course_code, "AT-UNIT-COUNT", f"Expected exactly 5 units, found {len(units)}")

    _check_unit_sequence(course_code, units, "AT")

    total_hours = 0

    for u in units:
        unit_label = f"Unit {u.number}" + (f" ({u.title})" if u.title else "")

        if u.experiments or u.x_activities:
            raise ValidationError(
                course_code,
                "AT-ACTIVITY-FORBIDDEN",
                f"{unit_label}: experiments or X-activities are not allowed in Academic-Theory courses",
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

    if total_hours != meta.ltpxtotal_hours:
        raise ValidationError(
            course_code,
            "AT-HOUR-MISMATCH",
            f"Declared hours {total_hours} ≠ expected {meta.ltpxtotal_hours}",
        )

# NOTE:
# u.experiments and u.x_activities are lists of ActivityBlock (not strings)
# Structural validators only count presence, not content.

def validate_academic_integrated(course_code: str, sections: List[MarkdownSection], meta:CourseMetadata, warnings) -> None:
    units = extract_units(course_code,sections)

    if len(units) != 5:
        raise ValidationError(course_code, "AI-UNIT-COUNT", f"Expected exactly 5 units, found {len(units)}")
    
    _check_unit_sequence(course_code, units, "AI")

    total_hours = 0
    total_theory_hours = 0
    total_lab_hours = 0
    total_x_hours = 0

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
        
        if u.x_hours and not u.x_activities:
            raise ValidationError(
                course_code,
                "AI-X-ACTIVITY-MISSING",
                f"{unit_label}: X-hours declared but no X-activity block provided",
            )

        total_hours += u.total_hours
        total_theory_hours += u.theory_hours or 0
        total_lab_hours += u.lab_hours or 0
        total_x_hours += u.x_hours or 0

    if total_hours != meta.ltpxtotal_hours:
        raise ValidationError(
            course_code,
            "AI-HOUR-MISMATCH",
            f"Declared hours {total_hours} ≠ expected {meta.ltpxtotal_hours}",
        )
    if total_theory_hours != (15 * (meta.L + meta.T)):
        warnings.append(
           ValidationWarning(
            course_code,
            "AI-THEORY-HOUR-WARN",
            f"Total theory hours {total_theory_hours} differs from expected {15 * (meta.L + meta.T)} (15 × (L + T))",
            )
        )
        
    if total_lab_hours != (15 * meta.P):
        warnings.append(
           ValidationWarning(
            course_code,
            "AI-PRACTICAL-HOUR-WARN",
            f"Total practical hours {total_lab_hours} differs from expected {15 * meta.P} (15 × P)",
            )
        )
    if total_x_hours != (15 * meta.X):
        warnings.append(
            ValidationWarning(
            course_code,
            "AI-X-HOUR-WARN",
            f"Total x-activity hours {total_x_hours} differs from expected {15 * meta.X} (15 × X)",
            )
        )
        

def validate_skill_practice(course_code: str, sections: List[MarkdownSection], meta:CourseMetadata) -> None:
    units = extract_units(course_code, sections)

    if units:
        _check_unit_sequence(course_code, units, "SP")

    total_hours = 0
    has_activity = False

    for u in units:
        if u.theory_hours:
            raise ValidationError(course_code, "SP-THEORY-FORBIDDEN", "Theory hours not allowed in Skill-Practice courses")

        if u.experiments or u.x_activities or u.lab_hours or u.x_hours:
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

    if total_hours != meta.ltpxtotal_hours:
        raise ValidationError(
            course_code,
            "SP-HOUR-MISMATCH",
            f"Declared hours {total_hours} ≠ expected {meta.ltpxtotal_hours}",
        )


def validate_project(course_code: str, sections: List[MarkdownSection], meta:CourseMetadata) -> None:
    units = extract_units(course_code, sections)
    if units:
        raise ValidationError(course_code, "PR-UNIT-FORBIDDEN", "Units are not allowed in Project courses")

    project_desc = extract_project_description(sections)

    if not project_desc:
        raise ValidationError(
            course_code,
            "PR-DESCRIPTION-MISSING",
            "Project Description section is missing"
        )

    hours = extract_project_total_hours(project_desc)

    if hours is None:
        raise ValidationError(course_code, "PR-HOUR-MISSING", "Project total hours not declared")

    if hours == 0:
        raise ValidationError(course_code, "PR-HOUR-ZERO", "Project total hours cannot be zero")

    if hours != meta.ltpxtotal_hours:
        raise ValidationError(
            course_code,
            "PR-HOUR-MISMATCH",
            f"Declared hours {hours} ≠ expected {meta.ltpxtotal_hours}",
        )