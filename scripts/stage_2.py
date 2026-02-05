from scripts.contracts import (
    CourseExecutionContext,
    COURSE_SECTION_SEQUENCE,
    MANDATORY_METADATA,
    DocumentStructure,
    CourseCategory,
    CourseType
)
from scripts.utils import get_section_key
from scripts.patterns import (
    META_PATTERNS,
    PREREQ_PATTERN,
    COREQ_PATTERN,
    FOOTER_PATTERNS,
)

# ------------------------------------------------------------------
# STAGE-2A : HEADER METADATA FORMAT
# ------------------------------------------------------------------

def validate_header_format(ctx: CourseExecutionContext, header_text: str) -> None:
    """
    Checks for mandatory identity markers and validates Enum values.
    """
    for label, pattern_key in MANDATORY_METADATA.items():
        pattern = META_PATTERNS.get(pattern_key)
        match = pattern.search(header_text) if pattern else None

        if not match:
            ctx.log("STAGE-2A", f"MISSING-{pattern_key.upper()}", 
                    f"Required header field '{label}' is missing.", fatal=True)
            continue

        # --- NEW VALUE VALIDATION ---
        value = match.group(1).strip()

        if pattern_key == "category":
            if value not in [e.value for e in CourseCategory]:
                ctx.log("STAGE-2A", "INVALID-CATEGORY", 
                        f"'{value}' is not a valid R2025 Category.", fatal=True)

        elif pattern_key == "type":
            if value not in [e.value for e in CourseType]:
                ctx.log("STAGE-2A", "INVALID-TYPE", 
                        f"'{value}' is not a valid R2025 Course Type.", fatal=True)

# ------------------------------------------------------------------
# STAGE-2B : SECTION PRESENCE GATE
# ------------------------------------------------------------------

def validate_section_gate(ctx: CourseExecutionContext, sections: dict) -> None:
    """
    Accepts sections dict directly.
    """
    for item in COURSE_SECTION_SEQUENCE:
        title = item["title"]
        is_mandatory = item["mandatory"]
        key = get_section_key(title)

        content = sections.get(key, "").strip()

        if not content:
            ctx.log(
                stage="STAGE-2B",
                code=f"EMPTY-{key.upper()}",
                msg=f"Section '{title}' has no content.",
                fatal=is_mandatory,
            )


# ------------------------------------------------------------------
# STAGE-2C : OPTIONAL METADATA FORMAT
# ------------------------------------------------------------------

def validate_optional_metadata(ctx: CourseExecutionContext, header_text: str) -> None:
    """
    Validates formatting for Prerequisite/Corequisite.
    """
    checks = {
        "Prerequisite": PREREQ_PATTERN,
        "Corequisite": COREQ_PATTERN,
    }

    for label, pattern in checks.items():
        if label.upper() in header_text.upper():
            if not pattern.search(header_text):
                ctx.log(
                    stage="STAGE-2C",
                    code=f"BAD-FORMAT-{label.upper()}",
                    msg=f"Found '{label}' label, but the value format is invalid.",
                    fatal=False,
                )
# ------------------------------------------------------------------
# STAGE-2D : FOOTER METADATA FORMAT
# ------------------------------------------------------------------

def validate_footer_gate(ctx: CourseExecutionContext, footer_text: str) -> None:
    """
    Checks if the footer block exists and contains valid governance data.
    """
    if not footer_text or len(footer_text.strip()) < 10:
        ctx.log("STAGE-2", "FOOTER-MISSING", 
                "The Governance Footer (separated by '---') is missing.", fatal=True)
        return

    bos_pattern = FOOTER_PATTERNS.get("bos_date")
    if bos_pattern and not bos_pattern.search(footer_text):
        ctx.log("STAGE-2", "INVALID-BOS-DATE", 
                "BoS Approval Date format is unrecognized. Use 'Month/Year' (e.g., Mar/25 or January/2026)", 
                fatal=True)
        
    # Check for Course Level (must be a number)
    level_pattern = FOOTER_PATTERNS.get("course_level")
    if level_pattern and not level_pattern.search(footer_text):
        ctx.log("STAGE-2", "INVALID-LEVEL", 
                "Course Level is missing or not a valid number.", fatal=True)
        
    # Check for Course Revision (must be a number, can have decimals)
    revision_pattern = FOOTER_PATTERNS.get("course_revision")
    print(f"DEBUG: Footer Text:\n{footer_text}\n")   
    if revision_pattern and not revision_pattern.search(footer_text):
        ctx.log("STAGE-2", "INVALID-REVISION", 
                "Course Revision is missing or not in the standard format X.X.", fatal=True)
# ------------------------------------------------------------------
# STAGE-2 ORCHESTRATOR
# ------------------------------------------------------------------

def run_format_gate(ctx: CourseExecutionContext) -> None:
    """
    Orchestrates Stage-2 validations with explicit Type Narrowing.
    """
    if not ctx.is_eligible:
        return

    # 1. THE TYPE GUARD:
    # If this passes, Pylance knows ctx.structure is DocumentStructure, not None.
    if ctx.structure is None:
        ctx.log(
            stage="STAGE-2",
            code="STRUCTURE-MISSING",
            msg="Internal pipeline error: Stage-2 invoked without parsed structure.",
            fatal=True,
        )
        return

    # 2. LOCAL BINDING: 
    # Helps static analyzers track the object state locally
    structure: DocumentStructure = ctx.structure 

    # 3. EXPLICIT PASSING:
    # Passing the strings/dicts directly prevents the sub-functions from
    # needing to check if ctx.structure is None again.
    validate_header_format(ctx, structure.header_block_raw)
    validate_section_gate(ctx, structure.explicit_sections)
    validate_footer_gate(ctx, structure.footer_block_raw)
    validate_optional_metadata(ctx, structure.header_block_raw)

    #if ctx.is_eligible:
        #print(f"✅ Stage 2: Format & Policy Gate passed for {ctx.course_code}")