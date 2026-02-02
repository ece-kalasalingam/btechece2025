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
from typing import Dict, List
from contracts import ValidationError

# Updated to match "PO1=3" or "PSO1=2" or "SO=3" (SO typically doesn't have an index)
# Note: Added support for SO without a following digit.
MAP_RE = re.compile(r"\b(PO|PSO|SO)(\d*)\s*=\s*([123])\b", re.I)
CO_LINE_RE = re.compile(r"^\s*(CO\d+)\s*:\s*(.+)$", re.I)

# The return type is now a clean dict: e.g., {"PO1": 3, "SO": 3}
ArticulationMap = Dict[str, Dict[str, int]]

def extract_articulation_map(
    course_code: str,
    section_body: str,
    declared_cos: List[str],
) -> ArticulationMap:
    mapping: ArticulationMap = {}

    def _norm(line: str) -> str:
        return line.strip().lstrip("-* ").strip()

    valid_ids = {line.split(":")[0].strip().upper() for line in declared_cos}
    
    for line in section_body.splitlines():
        line = _norm(line)
        if not line:
            continue

        m = CO_LINE_RE.match(line)
        if not m:
            continue

        co_id = m.group(1).upper()
        rhs = m.group(2)

        # Validation: Is it a declared CO?
        if co_id not in valid_ids:
            raise ValidationError(
                course_code,
                "ART-CO-UNKNOWN",
                f"{co_id} is not declared in Course Outcomes"
            )

        # Validation: Prevent double entries for the same CO
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

        # Validation: Check for "Garbage" (unexpected text on the line)
        # We replace the matches and the separators (commas/spaces) to see if anything is left
        clean_rhs = MAP_RE.sub("", rhs).replace(",", "").strip()
        if clean_rhs:
            raise ValidationError(
                course_code,
                "ART-CO-GARBAGE",
                f"{co_id} articulation line contains invalid text: '{clean_rhs}'"
            )
        
        # Build the JSON-friendly dictionary
        # Format: "PO1": 3
        co_mappings = {}
        for kind, idx, level in entries:
            key = f"{kind.upper()}{idx}" if idx else kind.upper()
            co_mappings[key] = int(level)
            
        mapping[co_id] = co_mappings

    return mapping