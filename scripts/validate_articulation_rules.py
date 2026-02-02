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
from typing import List, Dict
import re

from articulation_policy import (
    MAX_PO,
    MAX_PSO,
    MAX_SO,
    ALLOWED_LEVELS
)

def validate_articulation_rules(
    course_code: str,
    declared_cos: List[str],
    articulation_map: Dict[str, Dict[str, int]],
) -> None:

    # ---- 1. Every declared CO must be present in the mapping ----
    valid_ids = {line.split(":")[0].strip().upper() for line in declared_cos}
    missing = valid_ids - articulation_map.keys()
    if missing:
        raise ValidationError(
            course_code,
            "ART-CO-NOT-MAPPED",
            f"COs missing articulation: {sorted(missing)}"
        )

    # ---- 2. Validate each CO's internal mapping data ----
    for co_id, matrix in articulation_map.items():
        found_kinds = set()

        for key, level in matrix.items():
            # Use regex to split "PO1" into "PO" and "1"
            match = re.match(r"([A-Z]+)(\d*)", key.upper())
            if not match:
                continue
            
            kind = match.group(1)
            idx_str = match.group(2)
            idx = int(idx_str) if idx_str else None
            
            found_kinds.add(kind)

            # Validate Level (1, 2, or 3)
            if level not in ALLOWED_LEVELS:
                raise ValidationError(
                    course_code,
                    "ART-LEVEL-INVALID",
                    f"{co_id}: {key} has invalid articulation level {level}"
                )

            # Validate PO Range
            if kind == "PO":
                if idx is None or not (1 <= idx <= MAX_PO):
                    raise ValidationError(
                        course_code,
                        "ART-PO-RANGE",
                        f"{co_id}: PO{idx_str} out of range (1 - {MAX_PO})"
                    )

            # Validate PSO Range
            elif kind == "PSO":
                if idx is None or not (1 <= idx <= MAX_PSO):
                    raise ValidationError(
                        course_code,
                        "ART-PSO-RANGE",
                        f"{co_id}: PSO{idx_str} out of range (1 - {MAX_PSO})"
                    )

            # Validate SO Range
            elif kind == "SO":
                if idx is None or not (1 <= idx <= MAX_SO):
                    raise ValidationError(
                        course_code,
                        "ART-SO-RANGE",
                        f"{co_id}: SO{idx_str} out of range (1 - {MAX_SO})"
                    )

        # ---- 3. Mandatory Coverage Check (PO, PSO, and SO must all exist) ----
        if "PO" not in found_kinds:
            raise ValidationError(course_code, "ART-CO-PO-MISSING", f"{co_id} has no PO mapping")
        if "PSO" not in found_kinds:
            raise ValidationError(course_code, "ART-CO-PSO-MISSING", f"{co_id} has no PSO mapping")
        if "SO" not in found_kinds:
            raise ValidationError(course_code, "ART-CO-SO-MISSING", f"{co_id} has no SO mapping")