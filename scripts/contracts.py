# contracts.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional

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


@dataclass(frozen=True)
class MarkdownSection:
    level: int          # 0 for preamble, 1+ for headers
    title: str          # "__PREAMBLE__" or header text
    body: str           # raw content under this section

class ValidationError(Exception):
    def __init__(self, course_code: str, invariant_id: str, message: str):
        super().__init__(f"{course_code} [{invariant_id}]: {message}")

@dataclass(frozen=True)
class ValidationWarning:
    course_code: str
    code: str
    message: str

@dataclass(frozen=True)
class CourseMetadata:
    category: CourseCategory
    course_type: CourseType
    ltpxtotal_hours: int
    c: float
    l: int
    t: int
    p: int
    x: int
    prerequisite: Optional[str] = None
    corequisite: Optional[str] = None