from scripts.contracts import CourseExecutionContext
from scripts.patterns import (
    FORBIDDEN_PHRASES,
    STANDARD_PATTERN,
    TEXTBOOKS_NUMBERED_LINE_PATTERN,
    URL_PATTERN, ISBN_PATTERN,
    PAGE_PATTERN, URL_SENTRY_PATTERN,
    BIBTEX_APA_PATTERN,
    QUOTE_PAIRS, STANDARD_SENTRY_PATTERN, JOURNAL_SENTRY_PATTERN
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
                f"NOT-NUMBERED-LIST",
                f"{err_prefix} must contain ONLY a numbered list. No free text allowed.",
                fatal=True
            )
            return None

    if len(numbered) < min_count:
        ctx.log(
            "STAGE-4",
            f"MIN-COUNT",
            f"{err_prefix} must contain at least {min_count} entries.",
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
                f"NUMBERING-NOT-CONTIGUOUS",
                f"Numbering must be continuous starting at 1. Expected {expected} but found {n} in {err_prefix}.",
                fatal=True
            )
            return None
        expected += 1

    return numbered

def validate_print_reference_entry(
    ln: str,
    ctx,
    err_prefix="SECTION",
    year_range_regex=None
):
    """
    Validates and parses:
    Authors, "Title", Source, YYYY.
    """

    m = TEXTBOOKS_NUMBERED_LINE_PATTERN.match(ln)
    if not m:
        ctx.log("STAGE-4", f"{err_prefix}-BAD-LINE", ln, fatal=True)
        return None

    body = m.group("content").strip()

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
    # ---- 4. Edition (Gatekeeper: Look for 'Edition' followed by a comma) ----
    # Expecting: ", 2nd Edition, Publisher..."
    remaining_info = after_title[1:].strip() 
    edition_match = re.search(r'^(.+?\bEdition)\s*(,)', remaining_info, re.I)
    
    if not edition_match:
        ctx.log("STAGE-4", f"{err_prefix}-EDITION-FORMAT-ERROR", ln, fatal=True)
        return None
    
    edition = edition_match.group(1).strip()
    # The part after the edition's comma
    post_edition = remaining_info[edition_match.end():].strip()

    # ---- 5. Publisher & Year (Gatekeeper: Split from the right) ----
    # Using rsplit ensures the very last item is the year
    if ',' not in post_edition:
        ctx.log("STAGE-4", f"{err_prefix}-PUBLISHER-OR-YEAR-MISSING", ln, fatal=True)
        return None

    publisher_part, year_part = post_edition.rsplit(',', 1)
    publisher = publisher_part.strip()
    year = year_part.strip().rstrip('.')

    # Final Year Check
    if not re.match(r'^\d{4}$', year):
        ctx.log("STAGE-4", f"{err_prefix}-INVALID-YEAR-FORMAT", ln, fatal=True)
        return None

    if year_range_regex:
        # Directly match the 4-digit year against your range pattern
        if not re.match(rf'^({year_range_regex})$', year):
            ctx.log("STAGE-4", f"{err_prefix}-YEAR-OUT-OF-RANGE", 
                    f"Year {year} is out of allowed range ({year_range_regex})", fatal=True)
            return None

    # ---- forbidden patterns ----
    if URL_PATTERN.search(ln):
        ctx.log("STAGE-4", "TEXTBOOKS-URL-NOT-ALLOWED", "URLs are not allowed in Textbooks.", fatal=True)
        return None
    if ISBN_PATTERN.search(ln):
        ctx.log("STAGE-4", "TEXTBOOKS-ISBN-NOT-ALLOWED", "ISBN is not allowed in Textbooks.", fatal=True)
        return None
    if PAGE_PATTERN.search(ln):
        ctx.log("STAGE-4", "TEXTBOOKS-PAGES-NOT-ALLOWED", "Page numbers are not allowed in Textbooks.", fatal=True)
        return None
    if BIBTEX_APA_PATTERN.search(ln):
        ctx.log("STAGE-4", "TEXTBOOKS-BIBTEX-APA-NOT-ALLOWED", "BibTeX/APA clutter not allowed.", fatal=True)
        return None

    return {
        "authors": authors,
        "title": title,
        "edition": edition,
        "publisher": publisher,
        "year": year
    }

def validate_url_reference(ln, ctx, *, err_prefix="SECTION"):
    # Gatekeeper: Must be a numbered list
    m = TEXTBOOKS_NUMBERED_LINE_PATTERN.match(ln)
    if not m:
        ctx.log("STAGE-4", f"{err_prefix}-URL-NOT-NUMBERED", ln, fatal=True)
        return False
     # Gatekeeper: Block forbidden sources
    if any(phrase in m.group("content").lower() for phrase in FORBIDDEN_PHRASES):
        ctx.log("STAGE-4", f"{err_prefix}-URL-FORBIDDEN-SOURCE", ln, fatal=True)
        return False
    # Does it have a URL?
    if not URL_PATTERN.search(m.group("content")):
        return False # Not a URL line, try next
    return True # It's a valid URL line

def validate_standard_reference(ln, ctx, *, err_prefix="SECTION"):
    # Gatekeeper: Strict Regex Validation
    # (Org Code, "Quoted Title", 4-digit Year)
    # 1. Sentry Check: Does this even look like a standard?
    if not STANDARD_SENTRY_PATTERN.search(ln):
        return False 

    # 2. Gatekeeper Check: Is the grammar perfect?
    if not STANDARD_PATTERN.match(ln):
        # If the sentry passed but the gatekeeper failed, the user made a typo
        ctx.log("STAGE-4", f"{err_prefix}-STANDARD-FORMAT-INVALID", ln, fatal=True)
    
    return True

def validate_journal_reference(ln, ctx, *, err_prefix="SECTION"):
    # Sentry check
    if not JOURNAL_SENTRY_PATTERN.search(ln):
        return False

    # Gatekeeper: Check for comma after title and year at end
    # Note: Using the logic from your earlier parse_print_reference_entry
    if not re.search(r',\s*\d{4}\.?\s*$', ln):
        ctx.log("STAGE-4", f"{err_prefix}-JOURNAL-YEAR-MISSING", ln, fatal=True)
        return False
    if not re.search(r'["”]\s*,\s*', ln):
        ctx.log("STAGE-4", f"{err_prefix}-JOURNAL-COMMA-AFTER-TITLE", ln, fatal=True)
        return False

    return True

def _validate_references_grammar(content: str, ctx):
    numbered_lines = validate_numbered_list_block(
        content, ctx, err_prefix="REFERENCES"
    )
    if not numbered_lines:
        return

    for ln in numbered_lines:
        # 1. URL Gatekeeper (Check first as it's the most distinct)
        if URL_SENTRY_PATTERN.search(ln):
            validate_url_reference(ln, ctx, err_prefix="REFERENCES")
            continue # Move to next line in the for-loop

        # 2. Standard Gatekeeper (Check for Org Codes like ISO/IEEE)
        if STANDARD_SENTRY_PATTERN.search(ln):
            validate_standard_reference(ln, ctx, err_prefix="REFERENCES")
            continue

        # 3. Journal Gatekeeper (Check for Vol/Issue/pp)
        if JOURNAL_SENTRY_PATTERN.search(ln):
            validate_journal_reference(ln, ctx, err_prefix="REFERENCES")
            continue

        # 4. Fallback: Textbook Gatekeeper
        # If it's none of the above, it MUST follow the book format.
        # If this fails, it triggers the fatal error inside the function.
        validate_print_reference_entry(
            ln, ctx,
            err_prefix="REFERENCES",
            year_range_regex=None
        )

def _validate_textbooks_grammar(content: str, ctx: CourseExecutionContext):
    text = (content or "").strip()
    if not text:
        return
    # ---------- Block-level forbidden scans ----------
    lower_all = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lower_all:
            ctx.log("STAGE-4", "TEXTBOOKS-FORBIDDEN-PHRASE",
                    f"Forbidden content in Textbooks section: '{phrase}'.",
                    fatal=True)
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
        validate_print_reference_entry(
            ln,
            ctx,
            err_prefix="TEXTBOOKS",
            year_range_regex="201[5-9]|202[0-6]"
        )
