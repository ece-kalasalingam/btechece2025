"""
STAGE 2f: Regulation & Course-Type Legality
Verbatim: Enforces Section 4.5 policy math and Course-Type vs. Content-Type constraints.
"""
from typing import List
from scripts.contracts import (
    CourseMetadata, 
    CourseType, 
    ContentShape, 
    ValidationWarning, 
    ValidationError, 
    UnitBlock
)
from scripts.stage_2c2_semantic_lift import UnitParseContext

def enrich_and_legalize(
    course_code: str, 
    units: List[UnitBlock], 
    contexts: List[UnitParseContext], 
    metadata: CourseMetadata
):
    """
    Step 1: Regulatory Enrichment.
    Casts transient strings to integers and enforces immediate legality rules.
    """
    for i, unit in enumerate(units):
        ctx = contexts[i]
        
        # 1. Cast transient strings to semantic integers
        unit.theory_hours = int(ctx.raw_theory_str)
        unit.lab_hours = int(ctx.raw_lab_str)
        unit.x_hours = int(ctx.raw_x_str)

        # 2. Semantic Legality Check (Course Type vs Content Type)
        # Rule: Theory Courses (TC) must NOT have Lab Hours or Experiments
        if metadata.course_type == CourseType.TC:
            if unit.lab_hours > 0:
                raise ValidationError(
                    course_code, "LEGAL-TC-LAB-HOURS", 
                    f"Unit {unit.number}: Theory Course (TC) cannot have Practical Hours."
                )
            if unit.experiments:
                raise ValidationError(
                    course_code, "LEGAL-TC-EXPERIMENTS", 
                    f"Unit {unit.number}: Theory Course (TC) cannot contain experiments."
                )

        # Rule: Practical Courses (PC) must NOT have Theory Hours or Topics
        elif metadata.course_type == CourseType.PC:
            if unit.theory_hours > 0:
                raise ValidationError(
                    course_code, "LEGAL-PC-THEORY-HOURS", 
                    f"Unit {unit.number}: Practical Course (PC) cannot have Theory Hours."
                )
            if unit.topics:
                raise ValidationError(
                    course_code, "LEGAL-PC-TOPICS", 
                    f"Unit {unit.number}: Practical Course (PC) cannot contain theory topics."
                )

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
    warnings: List[ValidationWarning]
):
    """
    Phase B: Complex policy math and Cross-Gate Alignment.
    Ensures Metadata (Administrative) aligns with Shape (Pedagogical).
    """
    
    # 1. R2025 Credit Math Verification (L + T + P/2 + X/3)
    calculated_c = metadata.l + metadata.t + (metadata.p / 2) + (metadata.x / 3)
    
    if abs(calculated_c - metadata.c) > 0.01:
        warnings.append(ValidationWarning(
            course_code, "CR-MISMATCH", 
            f"Regulatory math ({calculated_c}) does not match claimed credits ({metadata.c})"
        ))

    # 2. Integrated Course Integrity Check
    if metadata.course_type in [CourseType.IC_T, CourseType.IC_P]:
        if metadata.l == 0 or metadata.p == 0:
            raise ValidationError(
                course_code, "IC-INCOMPLETE", 
                "Integrated courses must have both Theory (L) and Practical (P) hours."
            )

    # 3. SHAPE ALIGNMENT (Sealing the Stage Leak)
    # Verifies if the inferred structural shape matches the metadata course type
    _check_shape_alignment(course_code, metadata, shape, warnings)

def _check_shape_alignment(course_code: str, metadata: CourseMetadata, shape: ContentShape, warnings: List[ValidationWarning]):
    """
    Internal helper to cross-verify shape and metadata using 
    Contract-defined ContentShape Enums.
    """
    
    # 1. Conflict: Structure is Skill/Practice only, but Metadata says Theory (TC)
    if shape == ContentShape.SKILL_PRACTICE and metadata.course_type == CourseType.TC:
        raise ValidationError(
            course_code, "SHAPE-TYPE-MISMATCH",
            "Metadata claims Theory Course (TC), but Syllabus structure is Skill/Practice-only."
        )

    # 2. Conflict: Structure is Academic Theory only, but Metadata says Practical (PC)
    if shape == ContentShape.ACADEMIC_THEORY and metadata.course_type == CourseType.PC:
        raise ValidationError(
            course_code, "SHAPE-TYPE-MISMATCH",
            "Metadata claims Practical Course (PC), but Syllabus structure is Theory-only."
        )

    # 3. Warning: Structure is Integrated, but Metadata is marked as a single-mode course
    if shape == ContentShape.ACADEMIC_INTEGRATED and metadata.course_type in [CourseType.TC, CourseType.PC]:
        warnings.append(ValidationWarning(
            course_code, "SHAPE-INTEGRATION-WARN",
            f"Syllabus structure is Integrated, but Metadata lists it as {metadata.course_type.value}."
        ))