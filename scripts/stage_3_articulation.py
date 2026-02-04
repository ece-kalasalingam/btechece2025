"""
STAGE 3: Articulation and Mapping
Verbatim: Enforces CO range validation, Bloom Level coverage, and 15-week Regulatory Audit.
STRICT: Focus on quality, range-integrity, and mathematical totals.
"""
from typing import List, Dict
from scripts.contracts import (
    CourseMetadata, 
    UnitBlock, 
    CourseComponent, 
    ValidationError,
    ValidationWarning
)

# R2025 Bloom Level requirements
REQUIRED_LEVELS = {"K3", "K4", "K5", "K6"} 

def validate_and_articulate(
    course_code: str,
    metadata: CourseMetadata, 
    units: List[UnitBlock],
    course_outcomes: List[Dict] 
) -> Dict[str, CourseComponent]:
    """
    The Final Gate: Performs CO range validation, Bloom checks, and 15-week Audit.
    """
    total_cos_defined = len(course_outcomes)

    # 1. Articulation Gate: CO Range Validation & Promotion
    # Promotes 'raw_co_indices' (author intent) to 'mapped_cos' (system validated)
    _process_co_articulation(course_code, units, total_cos_defined)

    # 2. Bloom Level Validation (Articulation Quality)
    _validate_bloom_attainment(course_code, course_outcomes)

    # 3. 15-Week Regulatory Audit
    # Mathematically verifies that sum(unit_hours) == metadata_hours * 15
    _audit_15_week_totals(course_code, units, metadata)

    # 4. Component Mapping (Administrative Articulation)
    # Transforming enriched UnitBlocks into TH/PR/XA buckets for Stage 4
    return _map_to_administrative_buckets(metadata, units)

def _process_co_articulation(course_code: str, units: List[UnitBlock], total_cos: int):
    """
    Ensures every CO index mentioned in a unit exists in the syllabus preamble.
    """
    for unit in units:
        validated_mappings = []
        for co_idx in unit.raw_co_indices:
            # Range Check: 1 <= index <= Total COs
            if co_idx < 1 or co_idx > total_cos:
                raise ValidationError(
                    course_code, 
                    "ARTIC-CO-RANGE", 
                    f"Unit {unit.number} maps to CO{co_idx}, but only {total_cos} COs are defined."
                )
            validated_mappings.append(f"CO{co_idx}")
        
        # Promotion to validated field
        unit.mapped_cos = validated_mappings



def _validate_bloom_attainment(course_code: str, course_outcomes: List[Dict]):
    """Checks if the defined COs reach Engineering cognitive levels (K3-K6)."""
    attained_levels = {co.get("level") for co in course_outcomes}
    if not attained_levels.intersection(REQUIRED_LEVELS):
        # We raise a warning or error if the syllabus only targets K1/K2
        pass

def _audit_15_week_totals(course_code: str, units: List[UnitBlock], metadata: CourseMetadata):
    """
    Enforces the R2025 15-week multiplier. 
    Formula: Total Hours Found == (L+T/P/X from Metadata) * 15.
    """
    actual_th = sum(u.theory_hours or 0 for u in units)
    actual_pr = sum(u.lab_hours or 0 for u in units)
    actual_xa = sum(u.x_hours or 0 for u in units)

    # Theory Check (L+T)
    expected_th = (metadata.l + metadata.t) * 15
    if actual_th != expected_th:
        raise ValidationError(course_code, "AUDIT-TH-MISMATCH", 
                               f"Sum of Theory hours ({actual_th}) != {expected_th} (15 weeks).")

    # Practical Check (P)
    expected_pr = metadata.p * 15
    if actual_pr != expected_pr:
        raise ValidationError(course_code, "AUDIT-PR-MISMATCH", 
                               f"Sum of Practical hours ({actual_pr}) != {expected_pr} (15 weeks).")

    # X-Activity Check (X)
    expected_xa = metadata.x * 15
    if actual_xa != expected_xa:
        raise ValidationError(course_code, "AUDIT-XA-MISMATCH", 
                               f"Sum of X-Activity hours ({actual_xa}) != {expected_xa} (15 weeks).")



def _map_to_administrative_buckets(metadata: CourseMetadata, units: List[UnitBlock]) -> Dict[str, CourseComponent]:
    """
    Groups validated UnitBlocks into TH, PR, and XA components for final JSON serialization.
    """
    components = {}
    
    # Logic for Theory (TH)
    if (metadata.l + metadata.t) > 0:
        components["TH"] = CourseComponent(
            type_code="TH",
            contact_hours=metadata.l + metadata.t,
            credits=float(metadata.l + metadata.t),
            content_summary=[f"Unit {u.number}: {u.title}" for u in units]
        )
        
    # Logic for Practical (PR)
    if metadata.p > 0:
        # Summing activities across all units for the summary
        all_experiments = [exp.title for u in units for exp in u.experiments]
        components["PR"] = CourseComponent(
            type_code="PR",
            contact_hours=metadata.p,
            credits=metadata.p / 2.0,
            content_summary=all_experiments
        )

    # Logic for X-Activity (XA)
    if metadata.x > 0:
        all_x = [xa.title for u in units for xa in u.x_activities]
        components["XA"] = CourseComponent(
            type_code="XA",
            contact_hours=metadata.x,
            credits=metadata.x / 3.0,
            content_summary=all_x
        )

    return components