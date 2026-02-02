"""
=====================================================================
STAGE-3c : ARTICULATION RULE & COVERAGE VALIDATION (KARE R2025)
=====================================================================

PURPOSE
-------
Validate accreditation rules for CO–PO / CO–PSO / CO–SO
articulation mappings.

VALIDATIONS
-----------
- Every CO must have an articulation entry
- Each CO must map to:
  - ≥ 1 PO
  - ≥ 1 PSO
  - ≥ 1 SO
- Valid PO / PSO / SO index ranges
- Valid articulation strength values {1,2,3}

NON-GOALS
---------
- No attainment computation
- No NBA / ABET threshold enforcement
- No presentation or matrix rendering

DESIGN PRINCIPLES
-----------------
- Fail-fast on first violation
- Deterministic and auditable
- No heuristics or inference

REGULATION BASIS
----------------
KARE B.Tech Regulations R2025
NBA / ABET articulation requirements

=====================================================================
"""

from validate_structure import ValidationError

from articulation_policy import (
    MAX_PO,
    MAX_PSO,
    MAX_SO,
    ALLOWED_LEVELS
)

def validate_articulation_rules(
    course_code: str,
    declared_cos: set[str],
    articulation_map: dict,
) -> None:

    # ---- Every CO must be present ----
    missing = declared_cos - articulation_map.keys()
    if missing:
        raise ValidationError(
            course_code,
            "ART-CO-NOT-MAPPED",
            f"COs missing articulation: {sorted(missing)}"
        )

    # ---- Validate each CO entry ----
    for co, entries in articulation_map.items():
        kinds = set()

        for kind, idx, level in entries:
            kinds.add(kind)

            if level not in ALLOWED_LEVELS:
                raise ValidationError(
                    course_code,
                    "ART-LEVEL-INVALID",
                    f"{co}: invalid articulation level {level}"
                )

            if kind == "PO" and not (1 <= idx <= MAX_PO):
                raise ValidationError(
                    course_code,
                    "ART-PO-RANGE",
                    f"{co}: PO{idx} out of range (1–{MAX_PO})"
                )

            if kind == "PSO" and not (1 <= idx <= MAX_PSO):
                raise ValidationError(
                    course_code,
                    "ART-PSO-RANGE",
                    f"{co}: PSO{idx} out of range (1–{MAX_PSO})"
                )

            if kind == "SO" and not (1 <= idx <= MAX_SO):
                raise ValidationError(
                    course_code,
                    "ART-SO-RANGE",
                    f"{co}: SO{idx} out of range (1–{MAX_SO})"
                )

        # ---- Mandatory triple coverage ----
        if "PO" not in kinds:
            raise ValidationError(course_code, "ART-CO-PO-MISSING", f"{co} has no PO mapping")
        if "PSO" not in kinds:
            raise ValidationError(course_code, "ART-CO-PSO-MISSING", f"{co} has no PSO mapping")
        if "SO" not in kinds:
            raise ValidationError(course_code, "ART-CO-SO-MISSING", f"{co} has no SO mapping")