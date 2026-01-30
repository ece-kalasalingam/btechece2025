"""
=====================================================================
STAGE-2a : CONTENT SHAPE INFERENCE ENGINE (KARE R2025)
=====================================================================

PURPOSE
-------
This module performs SEMANTIC inference of syllabus Content Shape
based strictly on:

    1. Course Category   (authoritative)
    2. Course Type       (authoritative)
    3. Course Title      (override detection ONLY)

OUTPUT
------
Exactly ONE ContentShape per course.

This is the semantic hinge of the syllabus compiler.
All downstream validation depends on this being correct.

---------------------------------------------------------------------
ABSOLUTE RULES
---------------------------------------------------------------------
1. Exactly ONE content shape must be inferred
2. Override rules are evaluated BEFORE policy lookup
3. Policy table is IMMUTABLE
4. Missing or ambiguous inference is FATAL
5. No inference from LTPXC or syllabus body
6. No structural validation here

---------------------------------------------------------------------
CONTENT SHAPES
---------------------------------------------------------------------
- academic_theory
- academic_integrated
- skill_practice
- project

---------------------------------------------------------------------
NON-GOALS (DO NOT ADD)
---------------------------------------------------------------------
- Unit / topic / experiment validation
- Hour accounting
- NBA / ABET checks
- Assessment validation

=====================================================================
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Tuple


# =====================================================================
# POLICY VERSION
# =====================================================================

POLICY_VERSION = "R2025_v1.0"


# =====================================================================
# ENUMERATIONS (STABLE VALUES — NO auto())
# =====================================================================

class CourseCategory(Enum):
    FCM = "FCM"   # Foundation Course Mandatory
    FCE = "FCE"   # Foundation Course Elective
    PCM = "PCM"   # Program Course Mandatory (includes Capstone)
    PCE = "PCE"   # Program Course Elective
    SEM = "SEM"   # Skill Enhancement Mandatory (Internship)
    SEE = "SEE"   # Skill Enhancement Elective
    MDM = "MDM"   # Multidisciplinary Mandatory (EXSEL)
    MDE = "MDE"   # Multidisciplinary Elective


class CourseType(Enum):
    TC = "TC"       # Theory Course
    PC = "PC"       # Practical Course
    IC_T = "IC-T"   # Integrated Course – Theory dominant
    IC_P = "IC-P"   # Integrated Course – Practical dominant
    SC = "SC"       # Skill Course


class ContentShape(Enum):
    ACADEMIC_THEORY = "academic_theory"
    ACADEMIC_INTEGRATED = "academic_integrated"
    SKILL_PRACTICE = "skill_practice"
    PROJECT = "project"


# =====================================================================
# CAPSTONE KEYWORDS (ROBUST TITLE DETECTION)
# =====================================================================

CAPSTONE_KEYWORDS = (
    "project",
    "capstone",
    "major project",
    "minor project",
    "final year project",
)


# =====================================================================
# IMMUTABLE POLICY TABLE (NORMAL CASES ONLY)
# =====================================================================

CONTENT_SHAPE_POLICY: dict[Tuple[CourseCategory, CourseType], ContentShape] = {

    # Foundation Courses
    (CourseCategory.FCM, CourseType.TC):   ContentShape.ACADEMIC_THEORY,
    (CourseCategory.FCM, CourseType.PC):   ContentShape.ACADEMIC_INTEGRATED,
    (CourseCategory.FCM, CourseType.IC_T): ContentShape.ACADEMIC_INTEGRATED,
    (CourseCategory.FCM, CourseType.IC_P): ContentShape.ACADEMIC_INTEGRATED,

    (CourseCategory.FCE, CourseType.TC):   ContentShape.ACADEMIC_THEORY,
    (CourseCategory.FCE, CourseType.PC):   ContentShape.ACADEMIC_INTEGRATED,
    (CourseCategory.FCE, CourseType.IC_T): ContentShape.ACADEMIC_INTEGRATED,
    (CourseCategory.FCE, CourseType.IC_P): ContentShape.ACADEMIC_INTEGRATED,

    # Program Courses (NON-PROJECT)
    (CourseCategory.PCM, CourseType.TC):   ContentShape.ACADEMIC_THEORY,
    (CourseCategory.PCM, CourseType.PC):   ContentShape.ACADEMIC_INTEGRATED,
    (CourseCategory.PCM, CourseType.IC_T): ContentShape.ACADEMIC_INTEGRATED,
    (CourseCategory.PCM, CourseType.IC_P): ContentShape.ACADEMIC_INTEGRATED,

    # Program Electives
    (CourseCategory.PCE, CourseType.TC):   ContentShape.ACADEMIC_THEORY,
    (CourseCategory.PCE, CourseType.PC):   ContentShape.ACADEMIC_INTEGRATED,
    (CourseCategory.PCE, CourseType.IC_T): ContentShape.ACADEMIC_INTEGRATED,
    (CourseCategory.PCE, CourseType.IC_P): ContentShape.ACADEMIC_INTEGRATED,

    # Skill Enhancement Elective
    (CourseCategory.SEE, CourseType.SC):   ContentShape.SKILL_PRACTICE,

    # Multidisciplinary Elective
    (CourseCategory.MDE, CourseType.TC):   ContentShape.ACADEMIC_THEORY,
    (CourseCategory.MDE, CourseType.PC):   ContentShape.ACADEMIC_INTEGRATED,
    (CourseCategory.MDE, CourseType.IC_T): ContentShape.ACADEMIC_INTEGRATED,
    (CourseCategory.MDE, CourseType.IC_P): ContentShape.ACADEMIC_INTEGRATED,
}


# =====================================================================
# GUARD ASSERTION — FORBIDDEN POLICY CATEGORIES
# =====================================================================

FORBIDDEN_POLICY_CATEGORIES = {
    CourseCategory.MDM,   # EXSEL
    CourseCategory.SEM,   # Internship
}

assert not any(
    cat in FORBIDDEN_POLICY_CATEGORIES
    for (cat, _) in CONTENT_SHAPE_POLICY.keys()
), (
    "MDM (EXSEL) and SEM (Internship) must NOT appear in "
    "CONTENT_SHAPE_POLICY; they are override-only categories."
)


# =====================================================================
# OVERRIDE RULES (ORDER MATTERS)
# =====================================================================

@dataclass(frozen=True)
class OverrideRule:
    name: str
    predicate: Callable[[CourseCategory, CourseType, str], bool]
    shape: ContentShape


OVERRIDE_RULES: List[OverrideRule] = [

    # Capstone Project (PCM)
    OverrideRule(
        name="Capstone Project (PCM)",
        predicate=lambda cat, ctype, title:
            cat == CourseCategory.PCM
            and ctype == CourseType.PC
            and any(k in title.lower() for k in CAPSTONE_KEYWORDS),
        shape=ContentShape.PROJECT,
    ),

    # EXSEL
    OverrideRule(
        name="EXSEL (MDM)",
        predicate=lambda cat, ctype, title:
            cat == CourseCategory.MDM,
        shape=ContentShape.PROJECT,
    ),

    # SEM Internship
    OverrideRule(
        name="SEM Internship",
        predicate=lambda cat, ctype, title:
            cat == CourseCategory.SEM and ctype == CourseType.PC,
        shape=ContentShape.PROJECT,
    ),
]


# =====================================================================
# INFERENCE DATA CONTRACTS
# =====================================================================

@dataclass(frozen=True)
class InferenceInput:
    course_code: str
    course_title: str
    category: CourseCategory
    course_type: CourseType


@dataclass(frozen=True)
class InferenceResult:
    course_code: str
    inferred_shape: ContentShape
    rule_source: str
    policy_version: str
    trace: List[str]


class InferenceError(Exception):
    pass


# =====================================================================
# CORE INFERENCE ENGINE
# =====================================================================

def infer_content_shape(inp: InferenceInput) -> InferenceResult:
    """
    Infer exactly ONE ContentShape for the given course.

    Evaluation order:
        1. Override rules (explicit semantic intent)
        2. Policy table lookup (normal cases)

    Any ambiguity or missing mapping is fatal.
    """
    # -------------------------------
    # GUARD: ENUM SANITY CHECK
    # -------------------------------
    if not isinstance(inp.category, CourseCategory):
        raise InferenceError(
            f"{inp.course_code}: unknown CourseCategory {inp.category}"
        )

    if not isinstance(inp.course_type, CourseType):
        raise InferenceError(
            f"{inp.course_code}: unknown CourseType {inp.course_type}"
        )

    trace: List[str] = []

    # -------------------------------
    # STEP 1: OVERRIDES
    # -------------------------------
    matched: List[OverrideRule] = []

    for rule in OVERRIDE_RULES:
        if rule.predicate(inp.category, inp.course_type, inp.course_title):
            matched.append(rule)
            trace.append(f"override matched: {rule.name}")

    if len(matched) > 1:
        raise InferenceError(
            f"{inp.course_code}: multiple override rules matched "
            f"{[r.name for r in matched]}"
        )

    if len(matched) == 1:
        rule = matched[0]
        trace.append(f"content shape set by override → {rule.shape.value}")
        return InferenceResult(
            course_code=inp.course_code,
            inferred_shape=rule.shape,
            rule_source=f"override:{rule.name}",
            policy_version=POLICY_VERSION,
            trace=trace,
        )

    # -------------------------------
    # STEP 2: POLICY LOOKUP
    # -------------------------------
    key = (inp.category, inp.course_type)
    trace.append(f"policy lookup: ({inp.category.value}, {inp.course_type.value})")

    if key not in CONTENT_SHAPE_POLICY:
        raise InferenceError(
            f"{inp.course_code}: no content shape mapping for "
            f"({inp.category.value}, {inp.course_type.value})"
        )

    shape = CONTENT_SHAPE_POLICY[key]
    trace.append(f"content shape set by policy → {shape.value}")

    return InferenceResult(
        course_code=inp.course_code,
        inferred_shape=shape,
        rule_source="policy",
        policy_version=POLICY_VERSION,
        trace=trace,
    )


# =====================================================================
# END OF FILE
# =====================================================================