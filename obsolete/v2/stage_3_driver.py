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
from typing import List


def run_stage_3(
    course_code: str,
    sections,
    declared_cos: List[str],
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
    #return {
        #"policy_version": POLICY_VERSION,
        #"articulation_map": articulation_map,
    #}
    course_outcomes = []
    
    for co_string in declared_cos:
        # Splitting "CO1: Explain..." into ID and Statement
        # Using maxsplit=1 to ensure we don't break the statement itself
        parts = co_string.split(":", 1)
        co_id = parts[0].strip()
        statement = parts[1].strip() if len(parts) > 1 else ""

        course_outcomes.append({
            "id": co_id,
            "statement": statement,
            #"bloom": infer_bloom_level(statement), # Optional helper
            "articulationmatrix": articulation_map.get(co_id, {})
        })
    return {
        "policy_version": POLICY_VERSION,
        "course_outcomes": course_outcomes,
    }
