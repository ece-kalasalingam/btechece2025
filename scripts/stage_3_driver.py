"""
=====================================================================
STAGE-3 : ARTICULATION & MAPPING VALIDATION DRIVER (KARE R2025)
=====================================================================

PURPOSE
-------
Coordinate Stage-3 articulation validation by invoking:
- Structural checks
- Articulation extraction
- Accreditation rule enforcement

INPUTS
------
- ContentShape (from Stage-2a)
- Parsed sections (from Stage-1)
- Units (from Stage-2b)
- Declared COs (from Stage-2d)

NON-GOALS
---------
- No parsing
- No rendering
- No data mutation beyond Stage-3 scope

DESIGN PRINCIPLES
-----------------
- Sequential, deterministic execution
- Single failure terminates Stage-3
- No cross-stage leakage

=====================================================================
"""


from validate_articulation_structure import find_articulation_section
from extract_articulation import extract_articulation_map
from validate_articulation_rules import validate_articulation_rules
from contracts import POLICY_VERSION

def run_stage_3(
    course_code: str,
    sections,
    declared_cos: set[str],
):
    articulation_section = find_articulation_section(course_code, sections)

    articulation_map = extract_articulation_map(
        course_code,
        articulation_section.body,
        declared_cos,
    )

    validate_articulation_rules(
        course_code,
        declared_cos,
        articulation_map,
    )

    #return articulation_map
    return {
        "policy_version": POLICY_VERSION,
        "articulation_map": articulation_map,
    }
