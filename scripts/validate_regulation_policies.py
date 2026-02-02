"""
Stage-2e: Regulation Policy Validation (R2025)

Purpose:
- Enforce numeric and rule-based constraints defined by university regulations
- Operates ONLY on already-validated metadata
- Must NOT parse markdown
- Must NOT infer content
- Must NOT perform accreditation or articulation logic

Current rules implemented (R2025 §4.4):
- Credit computation and validation from L-T-P-X-C

Future rules may include:
- Category credit limits
- Semester credit load constraints
- VAC / Project credit caps
"""

from typing import NamedTuple
from contracts import ValidationError, ValidationWarning


class LTPXCTuple(NamedTuple):
    L: int
    T: int
    P: int
    X: int
    C: float


# ---------------------------------------------------------
# Public entry point for Stage-2e
# ---------------------------------------------------------

def validate_regulation_policies(course_code: str, meta, warnings):
    """
    Entry point for all regulation-bound validations.
    Called only AFTER Stage-2d (semantic blocks) validation.
    """

    _validate_credit_policy(course_code, meta)

    _warn_course_type_component_mismatch(course_code, meta, warnings)

    # Future regulation checks go here:
    # _validate_category_credit_limits(course_code, ...)
    # _validate_semester_load(course_code, ...)
    # _validate_vac_constraints(course_code, ...)


# ---------------------------------------------------------
# R2025 Credit Policy Validation
# ---------------------------------------------------------

def _validate_credit_policy(course_code: str, meta):
    """
    Enforces R2025 §4.4 credit rules:

    Credits are computed as:
        C_expected = L + T + (P / 2) + (X / 3)

    Constraints:
    - X must be a multiple of 3
    - Computed credits must equal declared credits
    """

    L, T, P, X, C_declared = meta.l, meta.t, meta.p, meta.x, meta.c

    # X-Activity hours rule
    if X % 3 != 0:
        raise ValidationError(
            course_code,
            "CR-X-INVALID",
            "X-Activity hours (X) must be in multiples of 3 as per R2025 §4.4"
        )

    # Compute expected credits
    C_expected = L + T + (P / 2) + (X / 3)

    # Credit mismatch
    if C_expected != C_declared:
        raise ValidationError(
            course_code,
            "CR-MISMATCH",
            f"Declared credits ({C_declared}) do not match "
            f"computed credits ({C_expected}) as per R2025 §4.4"
        )
def _warn_course_type_component_mismatch(course_code, metadata, warnings):
    T = metadata.t
    P = metadata.p
    ct = metadata.course_type.name

    if ct == "TC" and P > 0:
        warnings.append(
            ValidationWarning(
                course_code,
                "WARN-TC-P",
                "Theory Course (TC) has Practical hours (P > 0). "
                "This is allowed but discouraged as per course-type conventions."
            )
        )

    if ct == "PC" and T > 0:
        warnings.append(
            ValidationWarning(
                course_code,
                "WARN-PC-T",
                "Practical Course (PC) has Tutorial hours (T > 0). "
                "This is allowed but discouraged as per course-type conventions."
            )
        )