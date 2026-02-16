from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum, auto
# File system constants
COURSES_DIR = "courses_md"
INDEX_FILE = "index.md"
TEMP_OUTPUT_DIR = "temporary_files"
ACADEMIC_JSON_FILE = "syllabus_data.json"
REPORT_JSON_FILE = "execution_report.json"
OUTPUT_SYLL_DIR = "temp_logs"
TEMPLATES_DIR = "templates"
JINJA_TEMPLATES_DIR = "jinja"
DOCX_TEMPLATES_DIR = "docx"
DESTINATION_DIR = "syllabus_books"
CHECKPOINTS_DIR = "checkpoints"
CO_MIN_COUNT = 3
CO_MAX_COUNT = 6
DASHBOARD_DIR = "dashboard"
DASHBOARD_JSON_FILE = "dashboard_data.json"


MONTH_MAP = {
        "jan": "Jan.", "january": "Jan.", "feb": "Feb.", "february": "Feb.",
        "mar": "Mar.", "march": "Mar.", "apr": "Apr.", "april": "Apr.",
        "may": "May.", "jun": "Jun.", "june": "Jun.", "jul": "Jul.", "july": "Jul.",
        "aug": "Aug.", "august": "Aug.", "sep": "Sep.", "sept": "Sep.", "september": "Sep.",
        "oct": "Oct.", "october": "Oct.", "nov": "Nov.", "november": "Nov.", "dec": "Dec.", "december": "Dec."
    }
BLOOM_K_MAP = {
    1: {"RE", "UN"},
    2: {"AP", "AN"},
    3: {"EV", "CR"},
}

BLOOM_EXPANSION = {
    "RE": "Remember",
    "UN": "Understand",
    "AP": "Apply",
    "AN": "Analyze",
    "EV": "Evaluate",
    "CR": "Create",
}


# View Configurations
VIEW_CONFIG = {
    "a4": {"template": "base.tex.j2", "ext": "pdf"},
    "a5": {"template": "base.tex.j2", "ext": "pdf"},
    "courses-list": {"ext": "xlsx"},
    "co-bloom": {"ext": "docx"}
}
EXTENSION_GUARDS = {
    "pdf": {
        "modules": ["subprocess"], 
        "tools": ["pdflatex"]
    },
    "xlsx": {
        "modules": ["pandas", "openpyxl"], 
        "tools": [] # No external tool needed, uses python libraries
    },
    "docx": {
        "modules": ["docx"], 
        "tools": ["pandoc"] # Assuming pandoc is used via subprocess or a library
    }
}

STRUCTURE_EXEMPT_COURSES = {"ECE002"}

class CourseCategory(Enum):
    FCM = ("FCM", "Foundation Courses Mandatory")
    PCM = ("PCM", "Programme Core Mandatory")
    SEM = ("SEM", "Skill Enhancement Module")

    def __init__(self, code, full_name):
        self._code = code
        self._full_name = full_name

    @property
    def code(self):
        return self._code

    @property
    def full_name(self):
        return self._full_name
    
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
    {"title": "COURSE OBJECTIVES", "mandatory": True},
    {"title": "COURSE OUTCOMES", "mandatory": True},
    {"title": "SYLLABUS", "mandatory": True},
    {"title": "TEXTBOOKS", "mandatory": True},
    {"title": "REFERENCES", "mandatory": True},
]
SECTION_OPTIONAL_POLICY = {
    "textbooks": {
        "course_codes": {
        },
        "course_types": {"PC"},
        "course_categories": {"SEM"},
    }
}

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
    header_meta_raw: dict | None = None
@dataclass
class TableRenderInfo:
    start_line: int
    columns: int
    rows: int


@dataclass
class RenderReport:
    math_unbalanced_lines: List[Tuple[int, str]] = field(default_factory=list)
    latex_special_char_lines: List[Tuple[int, List[str], str]] = field(default_factory=list)
    long_line_risk: List[Tuple[int, str]] = field(default_factory=list)
    tables: List[TableRenderInfo] = field(default_factory=list)
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
    render_report: Optional[RenderReport] = None

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
    course_author: str = "Department Curriculum Committee"
    bos_date: str = "N/A"
    course_revision: str = "1.0"
    course_level: Optional[int] = None
    document_version: str = "1.0"
    document_date: str = "N/A"
    document_git_hash: str = "N/A"

@dataclass
class SyllabusBlock:
    course_display_type: str 
    units: List[Dict] = field(default_factory=list)
    pc_experiments: List[Dict] = field(default_factory=list)
    raw_content: List[Dict] = field(default_factory=list)    

@dataclass
class CanonicalCourse:
    """The 'Big Object' representing the entire course."""
    course_code: str
    course_meta: CourseMeta  # Grouped metadata
    syllabus: SyllabusBlock
    description: str
    objectives: List[str] = field(default_factory=list)
    outcomes: List[Dict] = field(default_factory=list)
    textbooks: List[Dict] = field(default_factory=list)
    references: List[Dict] = field(default_factory=list)
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
    courses: Dict[str, List[Dict]] = field(default_factory=dict)
    warning: List[Dict] = field(default_factory=list)
    error: List[Dict] = field(default_factory=list)


@dataclass
class CourseReportRecord:
    course_code: str
    course_title: Optional[str]
    course_category: Optional[str]
    is_eligible: bool
    violations: List[Violation]