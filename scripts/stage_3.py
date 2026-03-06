# scripts/stage_3.py
from typing import Any
from scripts.paths import get_path
from scripts.utils import get_git_metadata, validate_course_code
from scripts.contracts import CourseExecutionContext, COURSES_DIR
from scripts.patterns import (
    META_PATTERNS, 
    PREREQ_PATTERN, 
    COREQ_PATTERN,
    COURSE_TITLE_PATTERN,
    COURSE_CODE_HEADER_PATTERN,
    FOOTER_PATTERNS
)

def _extract_optional_field(key: str, pattern: Any, text: str, ctx: CourseExecutionContext):
    if ctx.metadata is None: ctx.metadata = {}
    match = pattern.search(text)
    if match:
        val = match.group(1).strip()
        if val.upper() not in ["NONE", "NIL", "N.A", "NA", ""]:
            ctx.metadata[key] = val

def run_footer_extraction(ctx: CourseExecutionContext):
    if ctx.structure is None or not ctx.is_eligible:
        return
    if ctx.metadata is None: ctx.metadata = {}
    """Extracts structured governance data from the footer block."""
    footer_raw = ctx.structure.footer_block_raw

    # Extract based on Footer Patterns
    for key, pattern in FOOTER_PATTERNS.items():
        match = pattern.search(footer_raw)
        if match:
            val = match.group(1).strip()
            if not val:
                return
            if val.startswith("-"):
                ctx.log("STAGE-3", "FOOTER-INVALID", f"Footer field '{key}' has an invalid value starting with '-'.", fatal=True)
                return  # Stop processing footer if any field is invalid
            if val:
                ctx.metadata[key] = val

    validate_course_code(ctx.course_code)
    courses_root = get_path(COURSES_DIR)
    file_path_md = courses_root / f"{ctx.course_code}.md"
    file_path_docx = courses_root / f"{ctx.course_code}.docx"

    # Prefer whichever source file actually exists in courses_md.
    if file_path_docx.exists():
        source_file_path = file_path_docx
    elif file_path_md.exists():
        source_file_path = file_path_md
    else:
        # Keep metadata extraction resilient for transient or generated inputs.
        source_file_path = file_path_docx

    git_ver, git_date, git_hash = get_git_metadata(source_file_path)
    
    ctx.metadata["document_version"] = git_ver
    ctx.metadata["document_date"] = git_date
    ctx.metadata["document_git_hash"] = git_hash
    ctx.structure.footer_block_raw = None

def run_metadata_extraction(ctx: CourseExecutionContext):
    if ctx.structure is None or not ctx.is_eligible:
        return
    if ctx.metadata is None: ctx.metadata = {}

    header_text = ctx.structure.header_block_raw

    # Extract Course Code
    title_match = COURSE_CODE_HEADER_PATTERN.search(header_text)
    declared_course_code = title_match.group(1) if title_match else "UNTITLED"
    if declared_course_code != ctx.course_code:
        ctx.log(
            "STAGE-3",
            "COURSE-CODE-MISMATCH",
            f"Declared CourseCode '{declared_course_code}' does not match index/file code '{ctx.course_code}'.",
            fatal=True
        )

    # Extract Title (Key aligned with Stage 4)
    title_match = COURSE_TITLE_PATTERN.search(header_text)
    ctx.metadata["course_title"] = title_match.group(1).strip() if title_match else "UNTITLED"
    
    # Extract Category & Type
    for field in ["category", "type"]:
        pattern = META_PATTERNS.get(field)
        if pattern:
            match = pattern.search(header_text)
            if match:
                ctx.metadata[f"course_{field}"] = match.group(1).upper().strip()

    # Extract LTPXC
    ltpxc_pattern = META_PATTERNS.get("ltpxc")
    if ltpxc_pattern:
        match = ltpxc_pattern.search(header_text)
        if match:
            try:
                ctx.metadata.update({
                    "l": int(match.group(1)), "t": int(match.group(2)),
                    "p": int(match.group(3)), "x": int(match.group(4)),
                    "c": float(match.group(5))
                })
                ctx.structure.header_block_raw = None
            except (ValueError, IndexError):
                ctx.log("STAGE-3", "LTPXC-CONV-ERR", "Numeric conversion failed.")

    _extract_optional_field("prerequisite", PREREQ_PATTERN, header_text, ctx)
    _extract_optional_field("corequisite", COREQ_PATTERN, header_text, ctx)
    # --- 2. Footer Extraction (Governance) ---
    run_footer_extraction(ctx)