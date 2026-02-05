from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum, auto
# File system constants
COURSES_DIR = "courses_md"
INDEX_FILE = "index.md"
OUTPUT_DIR = "output_generated"
OUTPUT_JSON_FILE = "master_data.json"
OUTPUT_SYLL_DIR = "syllabus_files"
TEMPLATES_DIR = "templates"
MAIN_LATEX_TEMPLATE_FILE = "syllabus_body.tex.j2"
DESTINATION_DIR = "final_pdfs"
VIEW_CONFIG = {
    "a4": "base_a4.tex.j2",
    "a5": "base_a5.tex.j2"
}

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

# Section Sequence
COURSE_SECTION_SEQUENCE = [
    {"title": "COURSE DESCRIPTION", "mandatory": True},
]

MANDATORY_METADATA = {
    "Course Category": "category",
    "Course Type": "type",
    "L-T-P-X-C": "ltpxc"
}

class ViolationLevel(Enum):
    WARNING = auto()
    FATAL = auto()

@dataclass(frozen=True)
class Violation:
    stage: str
    code: str
    message: str
    level: ViolationLevel = ViolationLevel.FATAL

@dataclass
class DocumentStructure:
    header_block_raw: str
    explicit_sections: Dict[str, str] # Keyed by canonical section name
    footer_block_raw: str

@dataclass
class CourseExecutionContext:
    course_code: str
    source_index: int = 0
    is_eligible: bool = True  # Flips to False on any FATAL violation
    
    # Structural components
    violations: List[Violation] = field(default_factory=list)
    structure: Optional[Any] = None # Will be DocumentStructure
    metadata: Optional[Dict[str, Any]] = None 
    extracted_data: Dict[str, Any] = field(default_factory=dict)

    # Stage-4 Product: The Canonical Object
    course: Optional[Any] = None # Will be CanonicalCourse

    def log(self, stage: str, code: str, msg: str, fatal: bool = True):
        level = ViolationLevel.FATAL if fatal else ViolationLevel.WARNING
        self.violations.append(Violation(stage, code, msg, level))
        if fatal:
            self.is_eligible = False

@dataclass
class CourseMeta:
    """The administrative identity of the course."""
    course_title: str 
    course_category: str
    course_type: str
    l: int
    t: int
    p: int
    x: int
    c: float
    prerequisite: Optional[str] = None
    corequisite: Optional[str] = None

@dataclass
class CanonicalCourse:
    """The 'Big Object' representing the entire course."""
    course_code: str
    course_meta: CourseMeta  # Grouped metadata
    description: str
    units: List[Dict] = field(default_factory=list)
    outcomes: List[Dict] = field(default_factory=list)
    # Sections as raw strings for final pass-through
    articulation: Optional[str] = None
    assessment: Optional[str] = None
    rubrics: Optional[str] = None
@dataclass
class MasterExportData:
    """
    The final structure for Stage 7 export.
    Groups results into success, warning, and error buckets.
    """
    success: List[Dict] = field(default_factory=list)
    warning: List[Dict] = field(default_factory=list)
    error: List[Dict] = field(default_factory=list)