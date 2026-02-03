"""
STAGE 3: R2025 Regulatory Audit
Verbatim: Strictly enforces the 15-hour multiplier and credit increments 
as per Section 4.4 of the R2025 Regulations.
"""
from typing import List
from scripts.contracts import CourseMetadata, LiftedUnit, ValidationError

def validate_r2025_quantum_alignment(
    course_code: str, 
    metadata: CourseMetadata, 
    units: List[LiftedUnit]
):
    """
    Performs the mathematical audit of the syllabus content against 
    the administrative LTPXC metadata.
    """

    # --- 1. Credit Increment Check ---
    # R2025 Constraint: Credits must be 0.5, 1.0, 1.5, etc.
    if (metadata.c * 2) != int(metadata.c * 2):
        raise ValidationError(
            course_code, 
            "REG-CREDIT-STEP", 
            f"Credit {metadata.c} is invalid. R2025 requires 0.5 increments."
        )

    # --- 2. Aggregate Unit-Level Hours ---
    total_th_hrs = sum(u.theory_hours for u in units)
    total_pr_hrs = sum(u.lab_hours for u in units)
    total_xa_hrs = sum(u.x_hours for u in units)

    # --- 3. Theory Audit (L + T) ---
    # Rule: 1 credit = 1 hour/week = 15 hours/semester
    expected_th = 15 * (metadata.l + metadata.t)
    if total_th_hrs != expected_th:
        raise ValidationError(
            course_code, 
            "REG-TH-QUANTUM", 
            f"Theory Mismatch: Units provide {total_th_hrs}h, but LTPXC requires {expected_th}h (15 * {metadata.l + metadata.t})"
        )

    # --- 4. Practical Audit (P) ---
    # Rule: 1 credit = 2 hours/week = 30 hours/semester (which is 15 * P)
    expected_pr = 15 * metadata.p
    if total_pr_hrs != expected_pr:
        raise ValidationError(
            course_code, 
            "REG-PR-QUANTUM", 
            f"Practical Mismatch: Units provide {total_pr_hrs}h, but LTPXC requires {expected_pr}h (15 * {metadata.p})"
        )

    # --- 5. X-Activity Audit (X) ---
    # Rule: 1 credit = 3 hours/week = 45 hours/semester (which is 15 * X)
    expected_xa = 15 * metadata.x
    if total_xa_hrs != expected_xa:
        raise ValidationError(
            course_code, 
            "REG-XA-QUANTUM", 
            f"X-Activity Mismatch: Units provide {total_xa_hrs}h, but LTPXC requires {expected_xa}h (15 * {metadata.x})"
        )

    # --- 6. Total Quantum Audit ---
    total_syllabus_hours = total_th_hrs + total_pr_hrs + total_xa_hrs
    expected_total_hours = 15 * metadata.c
    
    if abs(total_syllabus_hours - expected_total_hours) > 0.01:
        raise ValidationError(
            course_code, 
            "REG-TOTAL-QUANTUM", 
            f"Total Quantum Mismatch: Syllabus has {total_syllabus_hours}h, expected {expected_total_hours}h"
        )

    print(f"✅ Regulatory Audit Passed for {course_code}: {total_syllabus_hours} total hours align with {metadata.c} credits.")