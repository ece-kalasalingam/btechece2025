"""
=====================================================================
STAGE-3b : ARTICULATION DATA EXTRACTION (KARE R2025)
=====================================================================

PURPOSE
-------
Extract CO–PO / CO–PSO / CO–SO articulation mappings
from the articulation section into structured data.

INPUTS
------
- Parsed Markdown sections
- Declared Course Outcomes (COs)

OUTPUT
------
- In-memory articulation map:
  CO → [(PO|PSO|SO, index, level)]

NON-GOALS
---------
- No validation of index ranges
- No validation of required coverage
- No accreditation judgement

DESIGN PRINCIPLES
-----------------
- Single-pass extraction
- Lightweight regex only
- Deterministic output

=====================================================================
"""

import re
from typing import Dict, List, Tuple
from contracts import ValidationError

CO_LINE_RE = re.compile(r"^\s*(CO\d+)\s*:\s*(.+)$", re.I)
MAP_RE = re.compile(r"\b(PO|PSO|SO)(\d+)\s*\(\s*([123])\s*\)", re.I)

ArticulationMap = Dict[str, List[Tuple[str, int, int]]]

def extract_articulation_map(
    course_code: str,
    section_body: str,
    declared_cos: set[str],
) -> ArticulationMap:

    mapping: ArticulationMap = {}

    def _norm(line: str) -> str:
        return line.strip().lstrip("-* ").strip()

    for line in section_body.splitlines():
        line = _norm(line)
        if not line:
            continue

        m = CO_LINE_RE.match(line)
        if not m:
            continue

        co_id = m.group(1).upper()
        rhs = m.group(2)

        if co_id not in declared_cos:
            raise ValidationError(
                course_code,
                "ART-CO-UNKNOWN",
                f"{co_id} is not declared in Course Outcomes"
            )

        if co_id in mapping:
            raise ValidationError(
                course_code,
                "ART-CO-DUPLICATE",
                f"Multiple articulation entries for {co_id}"
            )

        entries = MAP_RE.findall(rhs)
        if not entries:
            raise ValidationError(
                course_code,
                "ART-CO-EMPTY",
                f"{co_id} has no valid PO/PSO/SO mappings"
            )
        if MAP_RE.sub("", rhs).strip():
            raise ValidationError(
                course_code,
                "ART-CO-GARBAGE",
                f"{co_id} articulation line contains text outside valid PO/PSO/SO mappings"
            )
        
        mapping[co_id] = [
            (kind.upper(), int(idx), int(level))
            for kind, idx, level in entries
        ]

    return mapping