"""
STAGE 2f: Regulation Policies
Verbatim: Phase A (Basic) and Phase B (Late Policy/Math).
"""
# FIX: Import List from typing
from typing import List
from scripts.contracts import CourseMetadata, ContentShape, ValidationWarning, ValidationError

def validate_basic_metadata(course_code: str, metadata: CourseMetadata):
    """Phase A: Fail-fast on malformed data types or negative values."""
    if any(val < 0 for val in [metadata.l, metadata.t, metadata.p, metadata.x]):
        raise ValidationError(course_code, "NEG-HOURS", "Contact hours cannot be negative")
    
    if metadata.c <= 0:
        raise ValidationError(course_code, "ZERO-CREDIT", "Course must have positive credit value")

def validate_regulation_policies(
    course_code: str, 
    metadata: CourseMetadata, 
    shape: ContentShape, 
    warnings: List[ValidationWarning] # List is now defined
):
    """Phase B: Complex policy math and shape-aware warnings."""
    
    # 1. R2025 Credit Math: L + T + P/2 + X/3
    calculated_c = metadata.l + metadata.t + (metadata.p / 2) + (metadata.x / 3)
    
    if abs(calculated_c - metadata.c) > 0.01:
        warnings.append(ValidationWarning(
            course_code, "CR-MISMATCH", 
            f"Regulatory math ({calculated_c}) does not match claimed credits ({metadata.c})"
        ))

    # 2. Shape-Aware Policy
    if shape == ContentShape.ACADEMIC_THEORY and metadata.p > 0:
        warnings.append(ValidationWarning(
            course_code, "THEORY-P-WARN", 
            "Theory course (TC) contains Practical hours"
        ))