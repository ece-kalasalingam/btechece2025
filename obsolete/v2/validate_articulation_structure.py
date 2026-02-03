"""
=====================================================================
STAGE-3a : ARTICULATION SECTION STRUCTURAL VALIDATION (KARE R2025)
=====================================================================

PURPOSE
-------
Validate the existence and structural presence of the
Articulation section.

SCOPE
-----
- Section heading existence
- Section uniqueness
- Basic line presence per declared CO

NON-GOALS
---------
- No validation of PO / PSO / SO indices
- No validation of articulation values
- No coverage or traceability checks
- No accreditation strength logic

DESIGN PRINCIPLES
-----------------
- Fail-fast
- Structure only, not meaning
- No inference, no recovery

REGULATION BASIS
----------------
KARE B.Tech Regulations R2025

=====================================================================
"""


from typing import List
import re
from validate_structure import MarkdownSection, ValidationError

ARTICULATION_HEADING_RE = re.compile(
    r"^\s*articulation\s+matrix\b",
    re.I
)

def find_articulation_section(
    course_code: str,
    sections: List[MarkdownSection]
) -> MarkdownSection:
    matches = [
        s for s in sections
        if ARTICULATION_HEADING_RE.search(s.title)
    ]

    if not matches:
        raise ValidationError(
            course_code,
            "ART-SECTION-MISSING",
            "Articulation section is missing"
        )

    if len(matches) > 1:
        raise ValidationError(
            course_code,
            "ART-SECTION-DUPLICATE",
            "Multiple Articulation sections found"
        )

    section = matches[0]
    
    def _norm(line: str) -> str:
        return line.strip().lstrip("-* ").strip().upper()

    if not any(
        _norm(line).startswith("CO")
        for line in section.body.splitlines()
    ):

        raise ValidationError(
            course_code,
            "ART-SECTION-EMPTY",
            "Articulation Matrix section contains no CO mappings"
        )

    return section