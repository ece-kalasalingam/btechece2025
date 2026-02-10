from scripts.contracts import CourseExecutionContext, BLOOM_K_MAP, STRUCTURE_EXEMPT_COURSES
from scripts.grammar_books import _validate_references_grammar, _validate_textbooks_grammar
from scripts.patterns import (
    BULLET_LINE_PATTERN, PARAGRAPH_BULLET_START_PATTERN, 
    CO_PATTERN, NUMBERED_LIST_PATTERN, 
    CO_INDEXED_BULLET_PATTERN
)
from scripts.grammar_syllabus import _validate_syllabus_theory_grammar, _validate_pc_experiments_only, _validate_exempted_syllabus_markdown

import re

from scripts.utils import strip_markdown_emphasis
RAW_SPECIALS = ['_', '%', '^', '#', '&', '~']
MD_HEADING_PATTERN = re.compile(r'^\s*#{1,6}\s+')




def _validate_description_grammar(content: str, ctx: CourseExecutionContext):
    """
    Grammar rules for Course Description:
    1. Must be substantial (at least 15 words).
    2. Must be prose (no bullet points at the start of the block).
    """
    text = content.strip()
    if not text:
        return # Basic empty check is handled in Stage 2

    # Rule 1: Length check
    words = text.split()
    if len(words) < 15:
        ctx.log(
            stage="STAGE-4",
            code="DESC-TOO-SHORT",
            msg="Course Description is too brief. It must be at least 15 words.",
            fatal=True
        )

    # Rule 2: Prose check (No bullets)
    # Check if the text starts with common markdown/text bullet symbols
    if PARAGRAPH_BULLET_START_PATTERN.match(text):
        ctx.log(
            stage="STAGE-4",
            code="DESC-NOT-PROSE",
            msg="Course Description must be written in prose paragraphs, not as a list.",
            fatal=False # Warnings for formatting issues
        )
def _validate_objectives_grammar(content: str, ctx: CourseExecutionContext):
    """
    Grammar rules for Course Objectives:

    """
    text = content.strip()
    if not text:
        return # Basic empty check is handled in Stage 2
    """
    Grammar rules for Course Objectives:
    - Ignore all content until first bullet
    - After first bullet, only bullets are allowed
    - If no bullet exists → fatal error
    """
    lines = content.splitlines()
    bullet_seen = False

    for line in lines:
        if not line.strip():
            continue

        if BULLET_LINE_PATTERN.match(line):
            bullet_seen = True
            continue

        if bullet_seen:
            ctx.log(
                stage="STAGE-4",
                code="OBJECTIVES-NOT-BULLETED",
                msg="Course Objectives must be written strictly as bullet points.",
                fatal=True
            )
            return
        # else: ignore non-bullet lines before first bullet

    if not bullet_seen:
        ctx.log(
            stage="STAGE-4",
            code="OBJECTIVES-MISSING-BULLETS",
            msg="Course Objectives section must contain at least one bullet point.",
            fatal=True
        )
def _validate_outcomes_grammar(content: str, ctx: CourseExecutionContext):
    lines = content.splitlines()

    in_bullet_block = False
    bullet_block_ended = False

    valid = []
    seen = set()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Ignore numbered lists completely
        if NUMBERED_LIST_PATTERN.match(line):
            ctx.log(
                    "STAGE-4",
                    "NUMBERED-LIST-BLOCKS",
                    "Course Outcomes must be written using bullet list.",
                    fatal=True
                )
            return

        # Bullet line
        if line.startswith("-"):
            if bullet_block_ended:
                ctx.log(
                    "STAGE-4",
                    "MULTIPLE-BULLET-BLOCKS",
                    "Course Outcomes must contain only ONE bullet list.",
                    fatal=True
                )
                return

            in_bullet_block = True

            # Blank bullet ignored
            if line == "-":
                ctx.log(
                    "STAGE-4",
                    "BLANK-BULLET-CO",
                    "Course Outcomes can not be empty bullet line.",
                    fatal=True
                )
                return

            # Reject disallowed prefixes (e.g., CO1:)
            if CO_INDEXED_BULLET_PATTERN.match(line):
                ctx.log(
                    "STAGE-4",
                    "BULLET-PREFIX IS WRONG",
                    f"Course Outcomes must start with K like K1, K2 and must not strt with CO like CO1, CO2, found as: {line}.",
                    fatal=True
                )
                return

            m = CO_PATTERN.match(line)
            if not m:
                ctx.log(
                    stage="STAGE-4",
                    code="INVALID-CO-FORMAT",
                    msg=f"Invalid Course Outcome format: {line}",
                    fatal=True
                )
                return

            k_level = int(m.group("k_level"))
            bloom = m.group("bloom")

            if bloom not in BLOOM_K_MAP[k_level]:
                ctx.log(
                    stage="STAGE-4",
                    code="INVALID-BLOOM-K-MAP",
                    msg=(
                        f"Invalid Bloom level mapping in Course Outcome: {line}. "
                        f"K{k_level} allows only {sorted(BLOOM_K_MAP[k_level])}, "
                        f"but found {bloom}."
                    ),
                    fatal=True
                )
                return

            normalized = line.lower()
            if normalized in seen:
                ctx.log(
                    "STAGE-4",
                    "CO-DUPLICATE",
                    f"Duplicate Course Outcome detected: {line}",
                    fatal=True
                )
                return

            seen.add(normalized)
            valid.append(line)
            continue

        # Non-bullet after bullet block ends the block
        if in_bullet_block:
            bullet_block_ended = True
            in_bullet_block = False
            continue

def _validate_syllabus_grammar(content: str, ctx: CourseExecutionContext):
    if ctx is None:
        return
    course_type = ctx.metadata["course_type"] if ctx and ctx.metadata else None
    # Grammar1: Check Grammar for IC-T, IC-P, TC courses
    if (
        course_type in {"IC-T", "IC-P", "TC"}
            # and ctx.course_category not in UNIT_STRUCTURE_EXEMPT_CATEGORIES - we may add it later if needed
        and ctx.course_code not in STRUCTURE_EXEMPT_COURSES
        ):
        _validate_syllabus_theory_grammar (content, ctx)
    
    # Grammar2: Check Grammar for PC courses
    elif (
        course_type in {"PC"}
        and ctx.course_code not in STRUCTURE_EXEMPT_COURSES
        ):
        _validate_pc_experiments_only (content, ctx)
    else :
        _validate_exempted_syllabus_markdown(content, ctx)

    

# Map of canonical keys to their specific grammar functions.
# Other sections will be added to this map one by one later.
_GRAMMAR_REGISTRY = {
    "course_description": _validate_description_grammar,
    "course_objectives": _validate_objectives_grammar,
    "course_outcomes": _validate_outcomes_grammar,
    "syllabus": _validate_syllabus_grammar,
    "textbooks": _validate_textbooks_grammar,
    "references": _validate_references_grammar 
}

def split_math_zones(text: str):
    """
    Splits text into [(segment, in_math)] preserving order.
    Math is delimited by $...$.
    """
    parts = re.split(r'(\$.*?\$)', text)
    for part in parts:
        if part.startswith('$') and part.endswith('$'):
            yield part, True
        else:
            yield part, False
def warn_unbalanced_dollar(section, text, ctx):
    count = text.count('$') - text.count(r'\$')
    if count % 2 != 0:
        ctx.log(
            stage="STAGE-4",
            code="UNBALANCED-MATH",
            msg=f"Unbalanced '$' detected in section '{section}'.",
            fatal=False
        )
def warn_raw_specials(section, text, ctx):
    for segment, in_math in split_math_zones(text):
        if in_math:
            continue
        for ch in RAW_SPECIALS:
            if re.search(rf'(?<!\\){re.escape(ch)}', segment):
                ctx.log(
                    stage="STAGE-4",
                    code=f"RAW-{ch}",
                    msg=(
                        f"Character '{ch}' found outside math mode in section "
                        f"'{section}'. Use '$...$' or escape it."
                    ),
                    fatal=False
                )
def warn_latex_macros(section, text, ctx):
    for segment, in_math in split_math_zones(text):
        if in_math:
            continue
        for match in re.finditer(r'\\[a-zA-Z]+', segment):
            ctx.log(
                stage="STAGE-4",
                code="LATEX-MACRO-OUTSIDE-MATH",
                msg=(
                    f"LaTeX macro '{match.group()}' used outside math mode "
                    f"in section '{section}'."
                ),
                fatal=False
            )
def warn_corrupted_math(section, text, ctx):
    if re.search(r'\$\s*(\[\]){2,}\s*\$', text):
        ctx.log(
            stage="STAGE-4",
            code="CORRUPTED-MATH",
            msg=(
                f"Suspicious math content like '$[][]$' detected in section "
                f"'{section}'. Possible escaped or stale content."
            ),
                fatal=False
        )
def warn_long_tokens(section, text, ctx, limit=25):
    for word in re.findall(r'\b\S+\b', text):
        if len(word) >= limit and not '-' in word:
            ctx.log(
                stage="STAGE-4",
                code="LONG-UNBREAKABLE-TOKEN",
                msg=(
                    f"Long word '{word}' in section '{section}' may cause "
                    f"overfull lines."
                ),
                fatal=False
            )
def warn_long_inline_math(section, text, ctx, limit=30):
    for match in re.findall(r'\$(.*?)\$', text):
        if len(match) > limit:
            ctx.log(
                stage="STAGE-4",
                code="LONG-INLINE-MATH",
                msg=(
                    f"Long inline math '${match}$' in section '{section}' may "
                    f"cause overfull boxes. Consider display math or rephrasing."
                ),
                fatal=False
            )
def warn_dense_math_lines(section, text, ctx):
    lines = text.splitlines()
    for line in lines:
        if line.count('$') >= 4 and len(line) > 80:
            ctx.log(
                stage="STAGE-4",
                code="DENSE-MATH-LINE",
                msg=(
                    f"Line with multiple inline math expressions in section "
                    f"'{section}' may cause layout issues."
                ),
                fatal=False
            )
def warn_urls(section, text, ctx):
    if re.search(r'https?://\S+', text):
        ctx.log(
            stage="STAGE-4",
            code="LONG-URL",
            msg=(
                f"URL detected in section '{section}'. URLs often cause "
                f"overfull boxes."
            ),
            fatal=False
        )


def check_section_grammar(key: str, content: str, ctx: CourseExecutionContext):
    """
    Dispatches content to the appropriate logic based on the section key.
    """
    handler = _GRAMMAR_REGISTRY.get(key)
    if handler:
        handler(strip_markdown_emphasis(content), ctx)
    # --- LaTeX hygiene warnings ---
    filtered_lines = []
    for line in content.splitlines():
        if MD_HEADING_PATTERN.match(line):
            continue
        filtered_lines.append(line)

    filtered_content = "\n".join(filtered_lines)
    warn_unbalanced_dollar(key, filtered_content, ctx)
    warn_raw_specials(key, filtered_content, ctx)
    warn_latex_macros(key, filtered_content, ctx)
    warn_corrupted_math(key, filtered_content, ctx)
    # --- typography risk (may cause layout warnings) ---
    #warn_long_tokens(key, content, ctx)
    #warn_long_inline_math(key, content, ctx)
    #warn_dense_math_lines(key, content, ctx)
        