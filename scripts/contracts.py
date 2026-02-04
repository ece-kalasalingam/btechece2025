from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum, auto

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
    source_index: int
    violations: List[Violation] = field(default_factory=list)
    is_eligible: bool = True  # Flips to False on any FATAL violation
    
    # Storage for artifacts produced by stages
    structure: Optional[DocumentStructure] = None
    metadata: Optional[Any] = None 
    extracted_data: Dict[str, Any] = field(default_factory=dict)

    def log(self, stage: str, code: str, msg: str, fatal: bool = True):
        level = ViolationLevel.FATAL if fatal else ViolationLevel.WARNING
        self.violations.append(Violation(stage, code, msg, level))
        if fatal:
            self.is_eligible = False