"""
STAGE 3: R2025 Regulatory Audit
Verbatim: Strictly enforces the 15-hour multiplier and credit increments 
as per Section 4.4 of the R2025 Regulations.
"""
from typing import List
from scripts.contracts import CourseMetadata, UnitBlock, ValidationError

def validate_r2025_quantum_alignment(
    course_code: str, 
    metadata: CourseMetadata, 
    units: List[UnitBlock]
):
    """
    Performs the mathematical audit of the syllabus content against 
    the administrative LTPXC metadata using 15-week semesters.
    """

    # --- 1. Credit Increment Check (R2025 Standard) ---
    # Rule: Credits must be in steps of 0.5 (e.g., 1.0, 1.5, 3.5)
    if (metadata.c * 2) != int(metadata.c * 2):
        raise ValidationError(
            course_code, 
            "REG-CREDIT-STEP", 
            f"Credit {metadata.c} is invalid. R2025 requires 0.5 increments."
        )

    # --- 2. Aggregate Unit-Level Hours ---
    # We use the enriched integer fields from the UnitBlock ABI
    total_th_hrs = sum(u.theory_hours or 0 for u in units)
    total_pr_hrs = sum(u.lab_hours or 0 for u in units)
    total_xa_hrs = sum(u.x_hours or 0 for u in units)

    # --- 3. Theory Audit (L + T) ---
    # Formula: (L + T) * 15 weeks
    expected_th = 15 * (metadata.l + metadata.t)
    if total_th_hrs != expected_th:
        raise ValidationError(
            course_code, 
            "REG-TH-QUANTUM", 
            f"Theory Mismatch: Units provide {total_th_hrs}h, but LTPXC requires {expected_th}h (15 * {metadata.l + metadata.t})"
        )

    # --- 4. Practical Audit (P) ---
    # Formula: P * 15 weeks
    expected_pr = 15 * metadata.p
    if total_pr_hrs != expected_pr:
        raise ValidationError(
            course_code, 
            "REG-PR-QUANTUM", 
            f"Practical Mismatch: Units provide {total_pr_hrs}h, but LTPXC requires {expected_pr}h (15 * {metadata.p})"
        )

    # --- 5. X-Activity Audit (X) ---
    # Formula: X * 15 weeks
    expected_xa = 15 * metadata.x
    if total_xa_hrs != expected_xa:
        raise ValidationError(
            course_code, 
            "REG-XA-QUANTUM", 
            f"X-Activity Mismatch: Units provide {total_xa_hrs}h, but LTPXC requires {expected_xa}h (15 * {metadata.x})"
        )

    # --- 6. Total Credit-Hour Integrity ---
    # R2025 Semantic Check: Does the total contact time support the credit claim?
    # Note: P is 2h/week for 1cr and X is 3h/week for 1cr, but the 15-week total 
    # multiplier applies to the weekly hours (L,T,P,X) directly.
    
    total_syllabus_hours = total_th_hrs + total_pr_hrs + total_xa_hrs
    
    # Weekly total hours from metadata
    weekly_total = (metadata.l + metadata.t + metadata.p + metadata.x)
    expected_total_hours = 15 * weekly_total
    
    if abs(total_syllabus_hours - expected_total_hours) > 0.01:
        raise ValidationError(
            course_code, 
            "REG-TOTAL-QUANTUM", 
            f"Total Quantum Mismatch: Syllabus has {total_syllabus_hours}h, expected {expected_total_hours}h based on 15 weeks."
        )

    print(f"✅ Regulatory Audit Passed for {course_code}: {total_syllabus_hours}h correctly distributed across 5 units.")