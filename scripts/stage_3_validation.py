"""
STAGE 3: Articulation & Regulatory Audit
Verbatim: Enforces CO range validation and the 15-week academic multiplier.
"""
from typing import List
from scripts.contracts import UnitBlock, ValidationError, CourseMetadata

def validate_stage_3(
    course_code: str, 
    units: List[UnitBlock], 
    metadata: CourseMetadata, 
    total_cos_defined: int
):
    """
    The Final Gate: Validates CO mappings and performs the 15-week audit.
    """
    
    # 1. Articulation Gate (CO Range Validation)
    _process_articulation(course_code, units, total_cos_defined)
    
    # 2. 15-Week Regulatory Audit
    _audit_total_contact_hours(course_code, units, metadata)

def _process_articulation(course_code: str, units: List[UnitBlock], total_cos: int):
    """
    Promotes author-intent (raw_co_indices) to system-validated data (mapped_cos).
    """
    for unit in units:
        if not unit.raw_co_indices:
            # Note: Hard error here if your policy mandates every unit must have a CO
            continue
            
        validated_mappings = []
        for co_idx in unit.raw_co_indices:
            # Rule: Index must be > 0 and <= total number of COs defined in syllabus
            if co_idx < 1 or co_idx > total_cos:
                raise ValidationError(
                    course_code, 
                    "ARTIC-CO-RANGE", 
                    f"Unit {unit.number} maps to CO{co_idx}, but only {total_cos} COs are defined."
                )
            
            # Promotion: Convert integer intent to formal system string
            validated_mappings.append(f"CO{co_idx}")
        
        # Update the UnitBlock field
        unit.mapped_cos = validated_mappings



def _audit_total_contact_hours(course_code: str, units: List[UnitBlock], metadata: CourseMetadata):
    """
    R2025 Multiplier Audit: Total Hours = (Unit Hours Sum) * 15 weeks.
    Checks if the unit breakdown matches the claimed Preamble metadata.
    """
    # Sum up hours across all units
    total_theory = sum(u.theory_hours or 0 for u in units)
    total_lab = sum(u.lab_hours or 0 for u in units)
    total_x = sum(u.x_hours or 0 for u in units)
    
    # Audit Theory (L + T)
    # Metadata L and T are usually weekly values; total should be weekly * 15
    expected_theory_total = (metadata.l + metadata.t) * 15
    actual_theory_total = total_theory # Already summed from units
    
    if actual_theory_total != expected_theory_total:
        raise ValidationError(
            course_code,
            "AUDIT-THEORY-MISMATCH",
            f"Total Theory/Tutorial hours ({actual_theory_total}) does not match "
            f"15-week requirement ({expected_theory_total} hours)."
        )

    # Audit Practical (P)
    expected_lab_total = metadata.p * 15
    if total_lab != expected_lab_total:
        raise ValidationError(
            course_code,
            "AUDIT-LAB-MISMATCH",
            f"Total Practical hours ({total_lab}) does not match 15-week requirement ({expected_lab_total})."
        )

    # Audit X-Activity (X)
    expected_x_total = metadata.x * 15
    if total_x != expected_x_total:
        raise ValidationError(
            course_code,
            "AUDIT-X-MISMATCH",
            f"Total X-Activity hours ({total_x}) does not match 15-week requirement ({expected_x_total})."
        )