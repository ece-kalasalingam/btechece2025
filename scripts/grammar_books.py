from scripts.contracts import CourseExecutionContext, BLOOM_K_MAP, STRUCTURE_EXEMPT_COURSES
from scripts.patterns import (
    FORBIDDEN_PHRASES,
    TEXTBOOKS_NUMBERED_LINE_PATTERN ,
    URL_PATTERN, ISBN_PATTERN,
    PAGE_PATTERN,
    BIBTEX_APA_PATTERN,
    QUOTE_PAIRS
)
import re
def validate_numbered_list_block(content: str, ctx, *, min_count=1, err_prefix="SECTION"):
    lines = [ln.rstrip() for ln in content.splitlines() if ln.strip()]
    numbered = []

    for ln in lines:
        if TEXTBOOKS_NUMBERED_LINE_PATTERN.match(ln):
            numbered.append(ln)
        else:
            ctx.log(
                "STAGE-4",
                f"{err_prefix}-NOT-NUMBERED-LIST",
                "Section must contain ONLY a numbered list. No free text allowed.",
                fatal=True
            )
            return None

    if len(numbered) < min_count:
        ctx.log(
            "STAGE-4",
            f"{err_prefix}-MIN-COUNT",
            f"Section must contain at least {min_count} entry.",
            fatal=True
        )
        return None

    # Enforce contiguous numbering 1..N
    expected = 1
    for ln in numbered:
        m = TEXTBOOKS_NUMBERED_LINE_PATTERN.match(ln)
        n = int(m.group("num")) if m else None
        if n != expected:
            ctx.log(
                "STAGE-4",
                f"{err_prefix}-NUMBERING-NOT-CONTIGUOUS",
                f"Numbering must be continuous starting at 1. Expected {expected} but found {n}.",
                fatal=True
            )
            return None
        expected += 1

    return numbered


# --------------------------------------------------
# Helper 2: Parse & validate print-style reference
# --------------------------------------------------
def parse_print_reference_entry(
    ln: str,
    ctx,
    *,
    err_prefix="SECTION",
    year_range_regex=None
):
    """
    Validates and parses:
    Authors, "Title", Source, YYYY.
    """

    m = re.match(r'^\s*(\d+)\.\s+(.*)$', ln)
    if not m:
        ctx.log("STAGE-4", f"{err_prefix}-BAD-LINE", ln, fatal=True)
        return None

    body = m.group(2).strip()

    # ---- find opening quote ----
    qpos = qchar = None
    for i, ch in enumerate(body):
        if ch in QUOTE_PAIRS:
            qpos, qchar = i, ch
            break

    if qpos is None:
        ctx.log("STAGE-4", f"{err_prefix}-TITLE-NOT-QUOTED", ln, fatal=True)
        return None

    # ---- authors ----
    pre = body[:qpos].rstrip()
    if not pre.endswith(","):
        ctx.log("STAGE-4", f"{err_prefix}-AUTHOR-TITLE-COMMA", ln, fatal=True)
        return None

    authors = pre[:-1].strip()
    if not authors:
        ctx.log("STAGE-4", f"{err_prefix}-AUTHORS-EMPTY", ln, fatal=True)
        return None
    if re.match(r'^\s*\d', authors):
        ctx.log("STAGE-4", f"{err_prefix}-AUTHORS-STARTS-DIGIT", ln, fatal=True)
        return None
    if not re.search(r'[A-Za-z]', authors):
        ctx.log("STAGE-4", f"{err_prefix}-AUTHORS-NO-ALPHA", ln, fatal=True)
        return None

    # ---- title ----
    if qchar is None:
        ctx.log("STAGE-4", f"{err_prefix}-QUOTE-CHAR-NOT-FOUND", ln, fatal=True)
        return None
    close_q = QUOTE_PAIRS[qchar]
    rest = body[qpos + 1:]
    end = rest.find(close_q)
    if end == -1:
        ctx.log("STAGE-4", f"{err_prefix}-UNTERMINATED-TITLE", ln, fatal=True)
        return None

    title = rest[:end].strip()
    after_title = rest[end + 1:].strip()

    if not title:
        ctx.log("STAGE-4", f"{err_prefix}-TITLE-EMPTY", ln, fatal=True)
        return None
    if not after_title.startswith(","):
        ctx.log("STAGE-4", f"{err_prefix}-COMMA-AFTER-TITLE", ln, fatal=True)
        return None

    # ---- year at end ----
    body_clean = body.strip()
    if not re.search(r',\s*\d{4}\.?\s*$', body_clean):
        ctx.log("STAGE-4", f"{err_prefix}-YEAR-NOT-AT-END", ln, fatal=True)
        return None

    if year_range_regex:
        if not re.search(rf',\s*({year_range_regex})\.?\s*$', body_clean):
            ctx.log("STAGE-4", f"{err_prefix}-YEAR-OUT-OF-RANGE", ln, fatal=True)
            return None

    # ---- forbidden patterns ----
    if (
        URL_PATTERN.search(ln)
        or ISBN_PATTERN.search(ln)
        or PAGE_PATTERN.search(ln)
        or BIBTEX_APA_PATTERN.search(ln)
    ):
        ctx.log("STAGE-4", f"{err_prefix}-FORBIDDEN-PATTERN", ln, fatal=True)
        return None

    return {
        "authors": authors,
        "title": title,
        "raw": ln
    }


def validate_url_only_reference(ln: str, ctx, *, err_prefix):
    m = re.match(r'^\s*\d+\.\s*(https?://\S+)\s*$', ln)
    if not m:
        ctx.log("STAGE-4", f"{err_prefix}-INVALID-URL",
                f"URL-only reference must contain ONLY a URL: {ln}", fatal=True)
        return None
    return m.group(1)
def _validate_references_grammar(content: str, ctx):
    numbered_lines = validate_numbered_list_block(
        content, ctx, err_prefix="REFERENCES"
    )
    if not numbered_lines:
        return

    for ln in numbered_lines:
        body = ln.split(".", 1)[1].strip()

        if body.startswith("http://") or body.startswith("https://"):
            validate_url_only_reference(ln, ctx, err_prefix="REFERENCES")
        else:
            parse_print_reference_entry(
                ln, ctx,
                err_prefix="REFERENCES",
                year_range_regex=None   # references can be older
            )


def _validate_textbooks_grammar(content: str, ctx: CourseExecutionContext):
    text = (content or "").strip()
    if not text:
        return

    # ---------- Optionality policy ----------
    course_type = ctx.metadata.get("course_type") if ctx and ctx.metadata else None
    TEXTBOOKS_OPTIONAL_TYPES = {"PC"}

    compact = re.sub(r'\s+', ' ', text).strip().lower()
    if course_type in TEXTBOOKS_OPTIONAL_TYPES and compact in {"1. not applicable.", "1. na."}:
        return

    if course_type not in TEXTBOOKS_OPTIONAL_TYPES:
        if "not applicable" in compact or re.search(r'\bna\.\b|\bna\b', compact):
            ctx.log("STAGE-4", "TEXTBOOKS-NA-NOT-ALLOWED",
                    "Textbooks cannot be 'Not Applicable' for this course type.",
                    fatal=True)
            return

    # ---------- Block-level forbidden scans ----------
    lower_all = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lower_all:
            ctx.log("STAGE-4", "TEXTBOOKS-FORBIDDEN-PHRASE",
                    f"Forbidden content in Textbooks section: '{phrase}'.",
                    fatal=True)
            return

    if URL_PATTERN.search(text):
        ctx.log("STAGE-4", "TEXTBOOKS-URL-NOT-ALLOWED", "URLs are not allowed in Textbooks.", fatal=True)
        return
    if ISBN_PATTERN.search(text):
        ctx.log("STAGE-4", "TEXTBOOKS-ISBN-NOT-ALLOWED", "ISBN is not allowed in Textbooks.", fatal=True)
        return
    if PAGE_PATTERN.search(text):
        ctx.log("STAGE-4", "TEXTBOOKS-PAGES-NOT-ALLOWED", "Page numbers are not allowed in Textbooks.", fatal=True)
        return
    if BIBTEX_APA_PATTERN.search(text):
        ctx.log("STAGE-4", "TEXTBOOKS-BIBTEX-APA-NOT-ALLOWED", "BibTeX/APA clutter not allowed.", fatal=True)
        return

    # ---------- Numbered list validation ----------
    numbered_lines = validate_numbered_list_block(
        content, ctx,
        min_count=1,
        err_prefix="TEXTBOOKS"
    )
    if not numbered_lines:
        return

    # ---------- Per-entry validation ----------
    for ln in numbered_lines:
        parse_print_reference_entry(
            ln,
            ctx,
            err_prefix="TEXTBOOKS",
            year_range_regex="201[5-9]|202[0-6]"
        )
