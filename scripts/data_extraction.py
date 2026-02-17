import re
from urllib.parse import urlparse
from scripts.contracts import STRUCTURE_EXEMPT_COURSES, CourseExecutionContext, RenderReport, TableRenderInfo
from scripts.patterns import (
    CO_SPLIT_PATTERN,
    JOURNAL_PATTERN,
    TEXTBOOKS_NUMBERED_LINE_PATTERN,
    UNIT_HEADING_PATTERN,
    UNIT_CO_MAP_PATTERN,
    THEORY_HEADER_PATTERN,
    HOURS_PATTERN,
    PRACTICAL_HEADER_PATTERN,
    XACT_HEADER_PATTERN,
    ACTIVITY_TITLE_PATTERN,
    DESCRIPTION_SUB_BULLET_PATTERN,
    PC_EXPERIMENT_CO_PATTERN,
    TABLE_ROW_PATTERN,
    TABLE_SEPARATOR_PATTERN,
    QUOTE_PAIRS, STANDARD_EXTRACT_PATTERN,
    URL_PATTERN, STANDARD_SENTRY_PATTERN, 
    STANDARD_PATTERN, JOURNAL_SENTRY_PATTERN
)
from scripts.utils import extract_bullet_items, get_column_count, strip_markdown_emphasis

def _type_dispatch(value, *, extract_as: str | None = None):
    if extract_as == "bullets" and isinstance(value, str):
        return extract_bullet_items(value)
    return value

def _extract_objectives_data(content: str, ctx: CourseExecutionContext):
   ctx.extracted_data["course_objectives"] = _type_dispatch(content, extract_as="bullets")

def _extract_outcomes_data(content: str, ctx: CourseExecutionContext):
    raw_items = extract_bullet_items(content)
    outcomes = []
    co_id = 1
    for item in raw_items:
        match = CO_SPLIT_PATTERN.match(item)
        if not match:
            # Grammar already filtered this; ignore defensively
            continue
        k_level = int(match.group(1))
        bloom = match.group(2)
        outcome_text = match.group(3).strip()
        outcomes.append({
            "id": co_id,
            "k_level": k_level,
            "bloom": bloom,
            "outcome": outcome_text
        })
        co_id += 1
    ctx.extracted_data["course_outcomes"] = outcomes

def _co_token_to_int(co: str) -> int:
    # Stage-4 already validated format
    return int(co[2:])

def _is_hours_bullet_theory_block(item: str) -> bool:
    return item.strip().lower().startswith("hours:")

def _split_topic(item: str) -> dict:
    """
    Splits a topic bullet into title and subtopics.
    Assumes grammar already validated.
    """
    title, rest = item.split(":", 1)

    subtopics = [
        s.strip()
        for s in rest.split(";")
        if s.strip()
    ]

    return {
        "title": title.strip(),
        "subtopics": subtopics
    }

def _extract_activity_items(block: str):
    """
    Extracts (title, description) pairs from a block.
    Assumes grammar already validated.
    """
    lines = block.splitlines()
    items = []
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        m = ACTIVITY_TITLE_PATTERN.match(line)
        if not m:
            i += 1
            continue

        title = m.group(1).strip()
        description = ""

        j = i + 1
        while j < len(lines):
            sub = lines[j].rstrip()

            d = DESCRIPTION_SUB_BULLET_PATTERN.match(sub)
            if d:
                description = d.group(1).strip()
                break

            if ACTIVITY_TITLE_PATTERN.match(sub) or sub.startswith("####"):
                break

            j += 1

        items.append({"title": title, "description": description})
        i = j + 1

    return items

def _extract_activity_block(unit_block: str, header_pattern: re.Pattern):
    """
    Extracts hours and activities for Practical / X-Activity blocks.
    Returns (hours, items)
    """
    match = header_pattern.search(unit_block)
    if not match:
        return 0, []

    start = match.end()
    next_section = re.search(r"^####\s+", unit_block[start:], re.MULTILINE)
    block = unit_block[start:start + next_section.start()] if next_section else unit_block[start:]

    h = HOURS_PATTERN.search(block)
    hours = int(h.group("hours")) if h else 0

    items = _extract_activity_items(block)
    return hours, items

def _extract_pc_experiments(block: str, ctx: CourseExecutionContext):
    """
    Extracts PC experiments with auto-incremented EXP IDs.
    Grammar already validated in Stage-4.
    """
    if ctx is None or ctx.metadata is None:
        return
    lines = block.splitlines()
    experiments = {}
    i = 0
    exp_index = 1

    while i < len(lines):
        line = lines[i].rstrip()
        m = ACTIVITY_TITLE_PATTERN.match(line)
        if not m:
            i += 1
            continue

        title = m.group(1).strip()
        practical_hours = 0
        cos = []
        description = ""

        j = i + 1
        while j < len(lines):
            sub = lines[j].rstrip()

            if ACTIVITY_TITLE_PATTERN.match(sub) or sub.startswith("####"):
                break

            h = HOURS_PATTERN.match(sub)
            if h:
                practical_hours = int(h.group("hours"))

            c = PC_EXPERIMENT_CO_PATTERN.match(sub)
            if c:
                raw = [x.strip().upper() for x in c.group(1).split(",")]
                cos = [_co_token_to_int(x) for x in raw]

            d = DESCRIPTION_SUB_BULLET_PATTERN.match(sub)
            if d:
                description = d.group(1).strip()

            j += 1

        exp_id = f"EXP{exp_index:02d}"
        experiments[exp_id] = {
            "title": title,
            "practical_hours": practical_hours,
            "cos": cos,
            "description": description,
        }
        exp_index += 1
        i = j

    return experiments

def stage_5_extract_render_data(content: str, ctx: CourseExecutionContext):
    """
    STAGE-5: Render-Safety & Data Extraction
    Assumes Stage-4 grammar has already passed.
    """

    lines = content.splitlines()

    render_data = {
        "math_unbalanced_lines": [],
        "latex_special_char_lines": [],
        "long_line_risk": [],
        "tables": [],
    }

    # ---------- 1. Math balance check ----------
    for idx, line in enumerate(lines, start=1):
        if line.count("$") % 2 != 0:
            render_data["math_unbalanced_lines"].append((idx, line))
            ctx.log(
                "STAGE-5",
                "UNBALANCED-MATH",
                f"Unbalanced $ detected at line {idx}",
                fatal=False,
            )

    # ---------- 2. LaTeX special character scan ----------
    LATEX_SPECIALS = ["%", "_", "&", "#", "{", "}"]

    for idx, line in enumerate(lines, start=1):
        found = [c for c in LATEX_SPECIALS if c in line]
        if found:
            render_data["latex_special_char_lines"].append((idx, found, line))
            ctx.log(
                "STAGE-5",
                "LATEX-SPECIAL-CHAR",
                f"Line {idx} contains LaTeX special chars {found}",
                fatal=False,
            )

    # ---------- 3. Table extraction ----------
    i = 0
    while i < len(lines):
        line = lines[i]

        if (
            TABLE_ROW_PATTERN.match(line)
            and i + 1 < len(lines)
            and TABLE_SEPARATOR_PATTERN.match(lines[i + 1])
        ):
            col_count = get_column_count(line)
            row_count = 0

            j = i + 2
            while j < len(lines) and TABLE_ROW_PATTERN.match(lines[j]):
                row_count += 1
                j += 1

            render_data["tables"].append({
                "start_line": i + 1,
                "columns": col_count,
                "rows": row_count,
            })

            i = j
            continue

        i += 1

    # ---------- 4. Overfull hbox risk ----------
    MAX_SAFE_LENGTH = 90  # conservative for LaTeX

    for idx, line in enumerate(lines, start=1):
        if len(line) > MAX_SAFE_LENGTH:
            render_data["long_line_risk"].append((idx, line))
            ctx.log(
                "STAGE-5",
                "OVERFULL-RISK",
                f"Long unbreakable line at {idx} ({len(line)} chars)",
                fatal=False,
            )

    # ---------- 5. Store extracted data ----------
    
    ctx.render_report = RenderReport(
        math_unbalanced_lines=render_data["math_unbalanced_lines"],
        latex_special_char_lines=render_data["latex_special_char_lines"],
        long_line_risk=render_data["long_line_risk"],
        tables=[ TableRenderInfo(**t) for t in render_data["tables"] ]

    )



# -------------------------
# Main extractor
# -------------------------

def _extract_syllabus_data(content: str, ctx: CourseExecutionContext):
    if ctx is None or ctx.metadata is None:
        return
    syllabus = ctx.extracted_data.setdefault("syllabus", {})
    course_type = ctx.metadata.get("course_type")
    units = syllabus.setdefault("units", [])
    pc_experiments = syllabus.setdefault("pc_experiments", [])
    raw_content = syllabus.setdefault("raw_content", [])

    # --------------------------------------------------
    # IC-T / IC-P / TC
    # --------------------------------------------------
    if (
        course_type in {"IC-T", "IC-P", "TC"}
        and ctx.course_code not in STRUCTURE_EXEMPT_COURSES
    ):
        syllabus["course_display_type"] = "UNITIZED-TABLE" 
        matches = list(UNIT_HEADING_PATTERN.finditer(content))

        for i, m in enumerate(matches):
            unit_no = int(m.group("number"))
            unit_title = (m.group("title") or m.group("title2") or "").strip()

            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            unit_block = content[start:end]

            # COs
            co_match = UNIT_CO_MAP_PATTERN.search(unit_block)
            if co_match is None:
                return 
            raw_cos = [c.strip().upper() for c in co_match.group(1).split(",")]
            unit_cos_raw = [_co_token_to_int(c) for c in raw_cos]

            # Theory
            theory_match = THEORY_HEADER_PATTERN.search(unit_block)
            if theory_match is None:
                return 
            theory_block = unit_block[theory_match.end():]

            h = HOURS_PATTERN.search(theory_block)
            theory_hours = int(h.group("hours")) if h else 0

            raw_items = extract_bullet_items(theory_block)
            topics = [
                _split_topic(item)
                for item in raw_items
                if not _is_hours_bullet_theory_block(item)
            ]


            # Practical / X-Activity
            practical_hours, experiments = _extract_activity_block(
                unit_block, PRACTICAL_HEADER_PATTERN
            )
            x_activity_hours, x_activities = _extract_activity_block(
                unit_block, XACT_HEADER_PATTERN
            )

            units.append({
                "unit_number": unit_no,
                "unit_title": unit_title,
                "cos": unit_cos_raw,
                "theory_hours": theory_hours,
                "practical_hours": practical_hours,
                "x_activity_hours": x_activity_hours,
                "topics": topics,
                "experiments": experiments,
                "x_activities": x_activities,
                "unit_hours": theory_hours + practical_hours + x_activity_hours
            })

        return

    # --------------------------------------------------
    # PC (Practical Course)
    # --------------------------------------------------
    if (
        course_type == "PC"
        and ctx.course_code not in STRUCTURE_EXEMPT_COURSES
    ):
        syllabus["course_display_type"] = "LABORATORY-TABLE"

        exp_match = PRACTICAL_HEADER_PATTERN.search(content)
        if exp_match is None:
            return

        start = exp_match.end()
        next_section = re.search(r"^####\s+", content[start:], re.MULTILINE)
        block = content[start:start + next_section.start()] if next_section else content[start:]

        experiments = _extract_pc_experiments(block, ctx)
        if experiments is None:
            return
        total_hours = sum(exp["practical_hours"] for exp in experiments.values())

        #syllabus["experiments"] = experiments
        #syllabus["total_practical_hours"] = total_hours
        
        pc_experiments.extend(experiments.values())
        return

    # --------------------------------------------------
    # Exempted courses
    # --------------------------------------------------
    syllabus["course_display_type"] = "RAW"
    raw_content.append({"content": content})

def _extract_textbooks_data(content: str, ctx):
    """
    Extract structured textbook data.
    Assumes grammar validation has already passed.
    """
    textbooks = []

    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    
    for ln in lines:
        data = _extract_single_textbook_data(ln, ctx)
        if data:
            textbooks.append(data)
            
    ctx.extracted_data["textbooks"] = textbooks

def _extract_single_textbook_data(content: str, ctx: CourseExecutionContext):
    m = TEXTBOOKS_NUMBERED_LINE_PATTERN.match(content)
    if not m:
            # Grammar should have caught this earlier
            ctx.log(
                "STAGE-5",
                "TEXTBOOKS-EXTRACT-FAILED",
                f"Unable to extract textbook entry: {content}",
                fatal=True
            )
            return []
    body = m.group("content").strip()
    
    try:
        # 1. Author and Title
        # We find the first quote index
        qpos = next(i for i, ch in enumerate(body) if ch in QUOTE_PAIRS)
        authors = body[:qpos].rstrip(", ").strip()
        
        close_q = QUOTE_PAIRS[body[qpos]]
        end = body.find(close_q, qpos + 1)
        title = body[qpos + 1:end].strip()
        
        # 2. Edition, Publisher, Year
        # body[end+1:] is ", 2nd Edition, Wiley, 2020."
        after = body[end + 1:].strip(", .")
        parts = [p.strip() for p in after.split(",")]
        
        return {
            "authors": authors,
            "title": title,
            "edition": parts[0] if len(parts) > 0 else "N/A",
            "publisher": parts[1] if len(parts) > 1 else "N/A",
            "year": parts[-1] # Usually the last element
        }
    except Exception as e:
        ctx.log(
            "STAGE-5",
            "TEXTBOOKS-EXTRACT-FAILED",
            f"Error parsing textbook entry: {content} | Exception: {str(e)}",
            fatal=True
        )
        return None

def _extract_references_data(content: str, ctx: CourseExecutionContext):
    references = []
    lines = content.splitlines()
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        # Check Sentry to route extraction
        url_match = URL_PATTERN.search(ln)
        if url_match:
            references.append({
                "format_type": "URL",
                "url": url_match.group(1).strip(),
                "raw": ln
            })
            continue
        
        if STANDARD_SENTRY_PATTERN.search(ln):
            # Using the Standard Gatekeeper Regex we defined earlier
            m = STANDARD_EXTRACT_PATTERN.match(ln)
            if m:
                references.append({
                    "format_type": "STANDARD",
                    "code": m.group("code").strip() if "code" in m.groupdict() else "UNKNOWN",
                    "title": m.group("title").strip() if "title" in m.groupdict() else "UNKNOWN",
                    "year": m.group("year").strip() if "year" in m.groupdict() else "UNKNOWN"
                })
                continue
        if JOURNAL_SENTRY_PATTERN.search(ln):
            m = JOURNAL_PATTERN.match(ln)
            if m:
                references.append({
                    "format_type": "JOURNAL",
                    "authors": m.group("authors").strip(),
                    "title": m.group("title").strip(),
                    "journal": m.group("journal").strip(),  # Was 'edition'
                    "metadata": m.group("metadata").strip(), # Was 'publisher'
                    "year": m.group("year").strip()
                })
                continue        
        
        base_data = _extract_single_textbook_data(ln, ctx)
        
        # Guard: Only unpack if base_data is a dictionary
        if isinstance(base_data, dict):
            is_journal = bool(JOURNAL_SENTRY_PATTERN.search(ln))
            references.append({
                **base_data, 
                "format_type": "JOURNAL" if is_journal else "BOOK"
            })
        else:
            ctx.log("STAGE-5", "REF-EXTRACT-FAIL", f"Failed to parse: {ln}", fatal=False)

    ctx.extracted_data["references"] = references

# Map of canonical keys to their specific extraction functions.
# Other sections will be added to this map one by one later.
_EXTRACTION_REGISTRY = {
    "course_objectives": _extract_objectives_data,
    "course_outcomes": _extract_outcomes_data,
    "syllabus": _extract_syllabus_data,
    "textbooks": _extract_textbooks_data,
    "references": _extract_references_data,
}

def extract_section_data(section_key: str, content: str, ctx: CourseExecutionContext):
    """
    Dispatches content to the appropriate section extraction of data based on the section key.
    Only sections with registered extraction handlers will be processed.
    """
    handler = _EXTRACTION_REGISTRY.get(section_key)
    if handler:
        #handler(content, ctx)
        handler(strip_markdown_emphasis(content), ctx)
