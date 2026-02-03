"""
SHARED DATA CONTRACTS
Common types and enums used across all pipeline stages.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Any, Dict

# ---------------------------------------------------------------------
# 1. Base Structure (Stage 1)
# ---------------------------------------------------------------------

class BlockType(Enum):
    """Structural classification of content chunks."""
    BULLET = auto()
    PARAGRAPH = auto()

    
@dataclass(frozen=True)
class MarkdownBlock:
    type: BlockType
    content: str

@dataclass(frozen=True)
class MarkdownSection:
    """Raw structural output from Stage 1 parsing."""
    level: int
    title: str
    body: str

@dataclass(frozen=True)
class StructuredSection:
    section: MarkdownSection
    blocks: List[MarkdownBlock]
# ---------------------------------------------------------------------
# 2. Metadata & Domain Types
# ---------------------------------------------------------------------

class CourseCategory(Enum):
    FCM = "FCM"  # Foundation Core
    PCM = "PCM"  # Programme Core
    SEM = "SEM"  # Skill Enhancement
    # Add other categories as per R2025

class CourseType(Enum):
    TC = "TC"      # Theory Course
    PC = "PC"      # Practical Course
    IC_T = "IC-T"  # Integrated Course (Theory weighted)
    IC_P = "IC-P"  # Integrated Course (Practical weighted)
    SC = "SC"      # Skill Course
    PROJ = "PROJ"  # Project

class ContentShape(Enum):
    """The semantic hinge determined in Stage 2."""
    ACADEMIC_THEORY = "academic_theory"
    ACADEMIC_INTEGRATED = "academic_integrated"
    SKILL_PRACTICE = "skill_practice"
    PROJECT = "project"

@dataclass(frozen=True)
class CourseMetadata:
    """The 'Administrative DNA' of the course."""
    course_code: str
    course_title: str
    category: CourseCategory
    course_type: CourseType
    l: int
    t: int
    p: int
    x: int
    c: float
    prerequisite: Optional[str] = None
    corequisite: Optional[str] = None

# ---------------------------------------------------------------------
# 3. Validation & Reporting
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationError(Exception):
    """Fatal structural or regulation violation."""
    course_code: str
    code: str
    message: str

@dataclass(frozen=True)
class ValidationWarning:
    """Non-fatal guideline deviation."""
    course_code: str
    code: str
    message: str

# ---------------------------------------------------------------------
# 4. Pipeline Constants
# ---------------------------------------------------------------------

PREAMBLE_TITLE = "PREAMBLE"
POLICY_VERSION = "R2025-1.0"

# ---------------------------------------------------------------------
# 5. Lifted Academic Objects (New additions)
# ---------------------------------------------------------------------



@dataclass(frozen=True)
class CourseComponent:
    """The final articulated output for a specific mode (TH, PR, or XA)."""
    type_code: str  # 'TH', 'PR', 'XA'
    contact_hours: int
    credits: float
    content_summary: List[str]

@dataclass(frozen=True)
class AssessmentComponent:
    name: str          # e.g., "Sessional Exam 1", "Assignment", "Lab Rubric"
    weightage: int     # e.g., 20 (for 20%)

@dataclass
class AssessmentStrategy:
    course_type_code: str  # TC, PC, IC, SC
    cia_weight: int        # Total CIA %
    ese_weight: int        # Total ESE %
    components: List[AssessmentComponent] = field(default_factory=list)

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