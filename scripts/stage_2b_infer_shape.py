"""
STAGE 2b: Shape Inference
Verbatim: Mapping Category + Type to ContentShape. No title heuristics allowed.
"""
from dataclasses import dataclass
from scripts.contracts import CourseCategory, CourseType, ContentShape, ValidationError

@dataclass(frozen=True)
class InferenceInput:
    course_code: str
    category: CourseCategory
    course_type: CourseType

def infer_content_shape(input_data: InferenceInput) -> ContentShape:
    c_type = input_data.course_type
    
    # Deterministic Mapping
    if c_type == CourseType.TC:
        return ContentShape.ACADEMIC_THEORY
    elif c_type in {CourseType.IC_T, CourseType.IC_P}:
        return ContentShape.ACADEMIC_INTEGRATED
    elif c_type in {CourseType.PC, CourseType.SC}:
        return ContentShape.SKILL_PRACTICE
    elif c_type == CourseType.PROJ:
        return ContentShape.PROJECT
    
    raise ValidationError(input_data.course_code, "SHAPE-UNKNOWN", f"No shape mapping for {c_type}")