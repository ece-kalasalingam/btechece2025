"""
=====================================================================
STAGE-2 : STRUCTURAL & FORMAT VALIDATION GATE
=====================================================================

RESPONSIBILITY
--------------
1. Validate mandatory header metadata
2. Validate course title correctness
3. Validate mandatory section presence
4. Validate optional metadata formats
5. Validate footer governance

NO PARSING. NO EXTRACTION.
"""

from scripts.contracts import (
    CourseExecutionContext,
    COURSE_SECTION_SEQUENCE,
    MANDATORY_METADATA,
    DocumentStructure,
    CourseCategory,
    CourseType,
    SECTION_OPTIONAL_POLICY
)
from scripts.utils import get_section_key
from scripts.patterns import (
    META_PATTERNS,
    PREREQ_PATTERN,
    COREQ_PATTERN,
    FOOTER_PATTERNS,
)

def is_section_optional(section_key: str, ctx: CourseExecutionContext) -> bool:
    meta = ctx.structure.header_meta_raw if ctx.structure else None
    if not meta:
        return False  # fail-safe
    course_code = meta.get("course_code", "").upper().strip()
    course_type = meta.get("type")
    category = meta.get("category")
    policy = SECTION_OPTIONAL_POLICY.get(section_key)
    
    if not policy:
        return False

    # Exact course-code match
    if course_code and course_code in policy.get("course_codes", set()):
        return True

    # Course type rule
    if course_type and course_type in policy.get("course_types", set()):
        return True

    # Course category rule
    if category and category in policy.get("course_categories", set()):
        return True

    return False

# ------------------------------------------------------------------
# STAGE-2A : HEADER METADATA FORMAT
# ------------------------------------------------------------------

def validate_header_format(ctx: CourseExecutionContext, header_text: str) -> None:
    VALID_CATEGORY_CODES = {e.code for e in CourseCategory}
    for label, pattern_key in MANDATORY_METADATA.items():
        pattern = META_PATTERNS.get(pattern_key)
        match = pattern.search(header_text) if pattern else None

        if not match:
            ctx.log(
                "STAGE-2A",
                f"MISSING-{pattern_key.upper()}",
                f"Required header field '{label}' missing.",
                fatal=True,
            )
            continue

        value = match.group(1).strip()

        if pattern_key == "category" and value not in VALID_CATEGORY_CODES:
            ctx.log("STAGE-2A", "INVALID-CATEGORY", f"Invalid category '{value}'.", fatal=True)

        if pattern_key == "type" and value not in [e.value for e in CourseType]:
            ctx.log("STAGE-2A", "INVALID-TYPE", f"Invalid course type '{value}'.", fatal=True)


# ------------------------------------------------------------------
# STAGE-2B : COURSE TITLE VALIDATION
# ------------------------------------------------------------------

def validate_course_title(ctx: CourseExecutionContext, header_text: str) -> None:
    for line in header_text.splitlines():
        if line.lower().startswith("course title:"):
            title = line.split(":", 1)[1].strip()
            if not title or title.lower().startswith("course code"):
                ctx.log(
                    "STAGE-2B",
                    "INVALID-COURSE-TITLE",
                    "Course title must be a meaningful H1 heading before COURSE CODE.",
                    fatal=True
                )
            return

    ctx.log(
        "STAGE-2B",
        "COURSE-TITLE-MISSING",
        "Course title not found in header.",
        fatal=True
    )


# ------------------------------------------------------------------
# STAGE-2C : MANDATORY SECTION PRESENCE
# ------------------------------------------------------------------

def validate_section_presence(ctx: CourseExecutionContext, sections: dict) -> None:
    for item in COURSE_SECTION_SEQUENCE:
        title = item["title"]
        base_mandatory = item["mandatory"]
        key = get_section_key(title)

        content = sections.get(key, "").strip()
        mandatory = base_mandatory
        if base_mandatory and is_section_optional(key, ctx):
            mandatory = False
        if not content and mandatory:
            ctx.log(
                "STAGE-2C",
                f"SECTION-MISSING-{key.upper()}",
                f"Section '{title}' is missing or empty.",
                fatal=mandatory,
            )
    # Reject unknown sections
    allowed_keys = {
        item["title"].lower().replace(" ", "_")
        for item in COURSE_SECTION_SEQUENCE
    }

    for key in sections.keys():
        if key not in allowed_keys:
            ctx.log(
                "STAGE-2C",
                "UNKNOWN-SECTION",
                f"Unknown section found: '{key}'. Only predefined sections are allowed.",
                fatal=True,
            )


# ------------------------------------------------------------------
# STAGE-2D : OPTIONAL METADATA FORMAT
# ------------------------------------------------------------------

def validate_optional_metadata(ctx: CourseExecutionContext, header_text: str) -> None:
    checks = {
        "Prerequisite": PREREQ_PATTERN,
        "Corequisite": COREQ_PATTERN,
    }

    for label, pattern in checks.items():
        if label.upper() in header_text.upper() and not pattern.search(header_text):
            ctx.log(
                "STAGE-2D",
                f"BAD-FORMAT-{label.upper()}",
                f"Invalid format for {label}.",
                fatal=False,
            )


# ------------------------------------------------------------------
# STAGE-2E : FOOTER GOVERNANCE FORMAT
# ------------------------------------------------------------------

def validate_footer(ctx: CourseExecutionContext, footer_text: str) -> None:
    if not footer_text or len(footer_text.strip()) < 10:
        ctx.log(
            "STAGE-2E",
            "FOOTER-MISSING",
            "Governance footer missing.",
            fatal=True
        )
        return

    for key, pattern in FOOTER_PATTERNS.items():
        if not pattern.search(footer_text):
            ctx.log(
                "STAGE-2E",
                f"INVALID-{key.upper()}",
                f"Footer field '{key}' missing or invalid.",
                fatal=True
            )


# ------------------------------------------------------------------
# STAGE-2 ORCHESTRATOR
# ------------------------------------------------------------------

def run_format_gate(ctx: CourseExecutionContext) -> None:
    if not ctx.is_eligible:
        return

    if ctx.structure is None:
        ctx.log(
            "STAGE-2",
            "STRUCTURE-MISSING",
            "Stage-2 invoked before Stage-1.",
            fatal=True,
        )
        return

    structure: DocumentStructure = ctx.structure

    validate_header_format(ctx, structure.header_block_raw)
    validate_course_title(ctx, structure.header_block_raw)
    validate_section_presence(ctx, structure.explicit_sections)
    validate_footer(ctx, structure.footer_block_raw)
    validate_optional_metadata(ctx, structure.header_block_raw)