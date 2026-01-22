from pathlib import Path
from markdown_it import MarkdownIt
import re
import sys
from typing import NoReturn
from fractions import Fraction


# -------------------------
# Errors
# -------------------------

class SyllabusError(Exception):
    pass


def error(msg: str, file: str) -> NoReturn:
    raise SyllabusError(f"{file}: {msg}")


# -------------------------
# Markdown parsing
# -------------------------

md = MarkdownIt("commonmark")


def parse_markdown(text):
    return md.parse(text)


# -------------------------
# Validators
# -------------------------

CO_RE = re.compile(r"^CO\d+\s*:")
# -------------------------
# Section heading regexes (with hours)
# -------------------------

THEORY_HDR_RE = re.compile(
    r"^Theory Content\s*\(\s*(\d+)\s*Hours\s*\)$",
    re.IGNORECASE
)

LAB_HDR_RE = re.compile(
    r"^Laboratory Experiments\s*\(\s*(\d+)\s*Hours\s*\)$",
    re.IGNORECASE
)

X_HDR_RE = re.compile(
    r"^X-Activity\s*\(\s*(\d+)\s*Hours\s*\)$",
    re.IGNORECASE
)
def get_next_inline_content(tokens, start_idx, limit_idx=None):
    """
    Safely finds the next 'inline' token content without assuming its position.
    """
    if limit_idx is None:
        limit_idx = len(tokens)
        
    for j in range(start_idx, limit_idx):
        if tokens[j].type == "inline":
            return tokens[j].content.strip(), j
    return None, start_idx

def parse_ltpxc(ltpxc: str, file: str) -> tuple[int, int, int, int, Fraction]:
    try:
        parts = ltpxc.split("-")
        if len(parts) != 5:
            raise ValueError

        L = int(parts[0])
        T = int(parts[1])
        P = int(parts[2])
        X = int(parts[3])
        C = Fraction(parts[4])   # exact credit

        return L, T, P, X, C

    except Exception:
        error(f"Invalid LTPXC format: '{ltpxc}'", file)


def validate_colon_bullet(text, file):
    # Must have at least one colon
    if ":" not in text:
        error(
            f"Invalid topic bullet (must contain at least one colon): '{text}'",
            file
        )

    if text.strip().endswith(":"):
        error(
            f"Trailing colon not allowed in topic bullet: '{text}'",
            file
        )

    # Split ONLY on the first colon
    topic, rest = text.split(":", 1)

    topic = topic.strip()
    rest = rest.strip()

    if not topic or not rest:
        error(
            f"Empty topic or sub-topic in bullet: '{text}'",
            file
        )

    # Store EVERYTHING after first colon as ONE sub-topic string
    subtopics = [rest]

    return topic, subtopics

def tex_safe(text: str) -> str:
    """Escapes standard LaTeX reserved characters."""
    # Order matters: escape backslash first, then others
    chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    # We use a regex to replace these characters
    return "".join(chars.get(c, c) for c in text)

def robust_tex_sanitize(line: str) -> str:
    """
    Partitions a line into math and non-math segments to 
    sanitize reserved characters outside of math mode.
    """
    if "$" not in line:
        return tex_safe(line)

    # Split the line by math blocks ($...$)
    # This regex captures the math blocks including the delimiters
    parts = re.split(r'(\$.*?\$)', line)
    
    sanitized_parts = []
    for part in parts:
        if part.startswith("$") and part.endswith("$"):
            # This is a math block, keep it as is
            sanitized_parts.append(part)
        else:
            # This is text outside math, escape reserved characters
            # Note: We manually avoid escaping '$' here because it's handled by split
            sanitized_parts.append(tex_safe(part))
            
    return "".join(sanitized_parts)

ALLOWED_ARTICULATION_VALUES = {"3", "2", "1", "-"}

def normalize_value(v, file):
    v = v.strip()
    if v not in ALLOWED_ARTICULATION_VALUES:
        error(
            f"Invalid articulation value '{v}'. Allowed: 3, 2, 1, -",
            file
        )
    return None if v == "-" else int(v)


def read_programme_details(path: Path, file: str):
    if not path.exists():
        error(f"Programme details file not found: {path}", file)

    text = path.read_text(encoding="utf-8")
    tokens = parse_markdown(text)

    programme = {
        "NBA_PO": [],
        "PSO": [],
        "ABET_SO": []
    }

    i = 0
    current_section = None

    while i < len(tokens):
        t = tokens[i]

        # Detect section headers
        if t.type == "heading_open" and t.tag == "h2":
            # FIXED: Use the helper to safely retrieve the title regardless of formatting
            title, title_idx = get_next_inline_content(tokens, i + 1)
            
            if not title:
                i += 1
                continue

            if title == "NBA Programme Outcomes":
                current_section = "NBA_PO"
            elif title == "Programme Specific Outcomes":
                current_section = "PSO"
            elif title == "ABET Student Outcomes":
                current_section = "ABET_SO"
            else:
                current_section = None

            i = title_idx # Advance pointer to the content found
            continue

        # Collect bullet items
        if current_section and t.type == "list_item_open":
            content, content_idx = get_next_inline_content(tokens, i + 1)
            if content:
                programme[current_section].append(content)
                i = content_idx 
                continue

        i +=1

    # -------------------------
    # Validation (strict)
    # -------------------------

    def validate_sequence(items, prefix, section):
        numbers = []
        for item in items:
            m = re.match(rf"^{prefix}(\d+)\s*:", item)
            if not m:
                error(
                    f"{section}: Invalid outcome format: '{item}'",
                    file
                )
            numbers.append(int(m.group(1)))

        if numbers != list(range(1, len(numbers) + 1)):
            error(
                f"{section}: Invalid numbering sequence {numbers}",
                file
            )

    if programme["NBA_PO"]:
        validate_sequence(programme["NBA_PO"], "PO", "NBA Programme Outcomes")

    if programme["PSO"]:
        validate_sequence(programme["PSO"], "PSO", "Programme Specific Outcomes")

    if programme["ABET_SO"]:
        validate_sequence(programme["ABET_SO"], "SO", "ABET Student Outcomes")

    return programme


def extract_course_header(md_tokens, file) -> tuple[str, str, str, str | None]:
    title = None
    metadata_blob = []

    i = 0
    while i < len(md_tokens):
        t = md_tokens[i]
        
        # Stop early once header section ends (H2 starts)
        if t.type == "heading_open" and t.tag == "h2":
            break
            
        # Course title (H1) - Standardized Detection
        if t.type == "heading_open" and t.tag == "h1":
            content, next_idx = get_next_inline_content(md_tokens, i + 1)
            if content:
                title = content
                i = next_idx # Advance pointer
        
        # Metadata paragraphs
        if t.type == "paragraph_open":
            content, next_idx = get_next_inline_content(md_tokens, i + 1)
            if content:
                metadata_blob.append(content)
                i = next_idx # Advance pointer
        
        i += 1

    if not title:
        error("Missing course title (H1 heading)", file)
        
    full_text = "\n".join(metadata_blob)
    # -------------------------
    # Semantic key-based extraction
    # -------------------------
    code_match = re.search(
        r"Course\s*Code\s*:\s*([^\n]+)",
        full_text,
        re.IGNORECASE
    )
    if code_match is None:
        error("Missing Course Code", file)
    code = code_match.group(1).strip()

    prereq_match = re.search(
        r"Pre-?requisite\s*:\s*([^\n]+)",
        full_text,
        re.IGNORECASE
    )
    prerequisite = prereq_match.group(1).strip() if prereq_match else None

    ltpxc_match = re.search(
        r"L\s*-\s*T\s*-\s*P\s*-\s*X\s*-\s*C\s*:\s*"
        r"(\d+\s*-\s*\d+\s*-\s*\d+\s*-\s*\d+\s*-\s*\d+(?:\.\d+)?)",
        full_text,
        re.IGNORECASE
    )
    if ltpxc_match is None:
        error("Missing L-T-P-X-C information", file)

    # Normalize LTPXC (remove spaces)
    ltpxc = re.sub(r"\s*", "", ltpxc_match.group(1))

    return title, code, ltpxc, prerequisite

# -------------------------
# Semantic Model Builders
# -------------------------

def build_course(md_tokens, file, title, code, ltpxc, prerequisite, programme_details):
    course = {
        "title": title,
        "code": code,
        "ltpxc": ltpxc,
        "prerequisite": prerequisite,
        "objectives": [],
        "outcomes": [],
        "units": []
    }
    course["articulation"] = {}

    i = 0
    while i < len(md_tokens):
        t = md_tokens[i]
        
        if t.type == "heading_open":
            # Use the helper to get the title regardless of token padding
            section_title, title_idx = get_next_inline_content(md_tokens, i + 1)
            
            if section_title == "Course Objectives":
                i = parse_simple_list(md_tokens, title_idx + 1, course["objectives"], file)
                continue

            if section_title == "Course Outcomes":
                i = parse_outcomes(md_tokens, title_idx + 1, course["outcomes"], file)
                continue

            if section_title.startswith("Unit"):
                unit_data, next_idx = parse_unit(md_tokens, i, file)
                course["units"].append(unit_data)
                i = next_idx
                continue
        i += 1

    if not course["title"] or not course["code"]:
        error("Missing course title or course code", file)
    
    if not course["outcomes"]:
        error("Course Outcomes must be defined before articulation matrices", file)
    expected_cos = [f"CO{i+1}" for i in range(len(course["outcomes"]))]
    i = 0
    while i < len(md_tokens):
        t = md_tokens[i]
        if t.type == "heading_open":
            # Standardized detection for articulation headers
            section_title, title_idx = get_next_inline_content(md_tokens, i + 1)
            
            if not section_title:
                i += 1
                continue

            section_title = section_title.replace("–", "-")
            
            if section_title.startswith("CO-"):
                if not course["outcomes"]:
                    error(f"Articulation matrix '{section_title}' appears before Course Outcomes", file)

                # Determine which mapping to parse
                if section_title == "CO-NBA Programme Outcomes Mapping":
                    expected_cols = [f"PO{j+1}" for j in range(len(programme_details["NBA_PO"]))]
                    mapping, next_idx = parse_articulation_table(md_tokens, title_idx + 1, expected_cols, expected_cos, file)
                    course["articulation"]["NBA_PO"] = mapping
                    i = next_idx
                    continue

                if section_title == "CO-Programme Specific Outcomes Mapping":
                    expected_cols = [f"PSO{j+1}" for j in range(len(programme_details["PSO"]))]
                    mapping, next_idx = parse_articulation_table(md_tokens, title_idx + 1, expected_cols, expected_cos, file)
                    course["articulation"]["PSO"] = mapping
                    i = next_idx
                    continue

                if section_title == "CO-ABET Student Outcomes Mapping":
                    expected_cols = [f"SO{j+1}" for j in range(len(programme_details["ABET_SO"]))]
                    mapping, next_idx = parse_articulation_table(md_tokens, title_idx + 1, expected_cols, expected_cos, file)
                    course["articulation"]["ABET_SO"] = mapping
                    i = next_idx
                    continue
        i += 1

    # -------------------------
    # Presence validation
    # -------------------------
    L, T, P, X, C = parse_ltpxc(course["ltpxc"], file)
    expected_order = []
    if (L + T) > 0:
        expected_order.append("theory")
    if P > 0:
        expected_order.append("lab")
    if X > 0:
        expected_order.append("x")

    for u in course["units"]:
        actual = u["section_order"]
        expected = [s for s in expected_order if u[s] is not None]

        if actual != expected:
            error(
                f"Unit {u['number']} section order invalid. "
                f"Expected {expected}, found {actual}",
                file
            )

    total_theory = 0
    total_lab = 0
    total_x = 0

    for u in course["units"]:
        if u["theory"] is not None:
            total_theory += u["theory"]["hours"]
        if u["lab"] is not None:
            total_lab += u["lab"]["hours"]
        if u["x"] is not None:
            total_x += u["x"]["hours"]
        # ---- Theory presence ----
    
    if (L + T) > 0:
        if total_theory == 0:
            error(
                f"Theory Content required (L+T={L+T}) but not found in any unit",
                file
            )
    else:
        if total_theory > 0:
            error("Theory Content found but L+T = 0", file)

    # ---- Lab presence ----
    if P > 0:
        if total_lab == 0:
            error(
                f"Laboratory Experiments required (P={P}) but not found",
                file
            )
    else:
        if total_lab > 0:
            error("Laboratory Experiments found but P = 0", file)

    # ---- X-Activity presence ----
    if X > 0:
        if total_x == 0:
            error(
                f"X-Activity required (X={X}) but not found",
                file
            )
    else:
        if total_x > 0:
            error("X-Activity found but X = 0", file)

    # Number of units check
    if len(course["units"]) != 5:
        error(
            f"Invalid number of units: expected 5, found {len(course['units'])}",
            file
        )
    # Unit numbering continuity (DSL v1.1)
    expected_numbers = list(range(1, 6))
    found_numbers = [u["number"] for u in course["units"]]

    if found_numbers != expected_numbers:
        error(
            f"Invalid unit numbering: expected units {expected_numbers}, "
            f"but found {found_numbers}",
            file
        )
    # -------------------------
    # Per-unit component consistency (Policy rule)
    # -------------------------
    for u in course["units"]:
        if (L + T) > 0 and u["theory"] is None:
            error(
                f"Unit {u['number']} missing Theory Content (L+T > 0)",
                file
            )

        if P > 0 and u["lab"] is None:
            error(
                f"Unit {u['number']} missing Laboratory Experiments (P > 0)",
                file
            )

        if X > 0 and u["x"] is None:
            error(
                f"Unit {u['number']} missing X-Activity (X > 0)",
                file
            )
        # -------------------------
        # Empty Unit Validation (DSL v1.0)
        # -------------------------
        total_topics = 0

        # Count only LTPXC-allowed sections
        if (L + T) > 0 and u["theory"] is not None:
            total_topics += len(u["theory"]["topics"])

        if P > 0 and u["lab"] is not None:
            total_topics += len(u["lab"]["experiments"])

        if X > 0 and u["x"] is not None:
            total_topics += len(u["x"]["components"])

        if total_topics == 0:
            error(
                f"Unit {u['number']} is empty: no topics found in any LTPXC-allowed section",
                file
            )
    
    # -------------------------
    # Hours Consistency Check
    # -------------------------    
    expected_theory = 15 * (L + T)
    expected_lab = 15 * P
    expected_x = 15 * X

    if total_theory != expected_theory:
        error(
            f"Theory hours mismatch: expected {expected_theory}, found {total_theory}",
            file
        )

    if total_lab != expected_lab:
        error(
            f"Laboratory hours mismatch: expected {expected_lab}, found {total_lab}",
            file
        )

    if total_x != expected_x:
        error(
            f"X-Activity hours mismatch: expected {expected_x}, found {total_x}",
            file
        )
    
    # -------------------------
    # Credit Consistency Check (Exact, LTPXC)
    # -------------------------

    # Convert everything to exact rational numbers
    L_f = Fraction(L, 1)
    T_f = Fraction(T, 1)
    P_f = Fraction(P, 1)
    X_f = Fraction(X, 1)

    computed_C = L_f + T_f + (P_f / 2) + (X_f / 3)

    if computed_C != C:
        error(
            f"Credit mismatch: expected C = {C}, "
            f"but L+T+(P/2)+(X/3) = {computed_C}",
            file
        )
    # -------------------------
    # Articulation existence check (course-level)
    # -------------------------
    #required = {"NBA_PO", "PSO", "ABET_SO"}
    required = set()
    if programme_details["NBA_PO"]:
        required.add("NBA_PO")
    if programme_details["PSO"]:
        required.add("PSO")
    if programme_details["ABET_SO"]:
        required.add("ABET_SO")
    missing = required - set(course["articulation"])

    if missing:
        error(
            f"Missing articulation matrix/matrices: {sorted(missing)}",
            file
        )

    return course

"""
def parse_simple_list(tokens, start, target, file):
    i = start
    while i < len(tokens) and tokens[i].type != "heading_open":
        if tokens[i].type == "list_item_open":
            text = tokens[i + 2].content.strip()
            target.append(text)
        i += 1
    return i
"""
def parse_simple_list(tokens, start, target, file):
    i = start
    # Stop if we hit a new heading or the end of the tokens
    while i < len(tokens) and tokens[i].type != "heading_open":
        if tokens[i].type == "list_item_open":
            # Find the next 'inline' token before the next 'list_item_close'
            content, next_idx = get_next_inline_content(tokens, i + 1)
            if content:
                target.append(content)
                i = next_idx # Advance to where we found the content
        i += 1
    return i

def parse_outcomes(tokens, start, target, file):
    i = start
    while i < len(tokens) and tokens[i].type != "heading_open":
        if tokens[i].type == "list_item_open":
            # Safely find the next 'inline' token content
            content, next_idx = get_next_inline_content(tokens, i + 1)
            if content:
                if not CO_RE.match(content):
                    error(f"Invalid course outcome format: '{content}'", file)
                target.append(content)
                i = next_idx  # Advance the pointer to the content we found
        i += 1
    return i

def parse_articulation_table(tokens, start_idx, expected_columns, expected_cos, file):
    """
    Robustly parses a Markdown table into a mapping dictionary using content-seeking.
    """
    i = start_idx

    if i >= len(tokens) or tokens[i].type != "table_open":
        error("Expected articulation table", file)

    i += 1  # Move past table_open

    # -------------------------
    # 1. Parse Header Row
    # -------------------------
    headers = []
    # Seek the end of the table head
    while i < len(tokens) and tokens[i].type != "thead_close":
        if tokens[i].type == "th_open":
            # Use helper to find text regardless of formatting (bold, etc.)
            content, next_idx = get_next_inline_content(tokens, i + 1)
            if content:
                headers.append(content)
                i = next_idx
        i += 1

    if not headers:
        error("Articulation table has no headers", file)

    if headers[0] != "CO":
        error("First articulation column must be 'CO'", file)

    if headers[1:] != expected_columns:
        error(
            f"Articulation columns mismatch.\n"
            f"Expected: {expected_columns}\n"
            f"Found: {headers[1:]}",
            file
        )

    # -------------------------
    # 2. Parse Body Rows
    # -------------------------
    # Seek the table body
    while i < len(tokens) and tokens[i].type != "tbody_open":
        i += 1
    
    if i < len(tokens):
        i += 1 # Move past tbody_open

    mapping = {}
    seen_cos = set()

    while i < len(tokens) and tokens[i].type != "tbody_close":
        if tokens[i].type == "tr_open":
            cells = []
            # Parse individual cells in the row
            while i < len(tokens) and tokens[i].type != "tr_close":
                if tokens[i].type == "td_open":
                    content, next_idx = get_next_inline_content(tokens, i + 1)
                    # Allow empty cells for "-" values
                    cells.append(content if content else "")
                    if content:
                        i = next_idx
                i += 1
            
            # Process the row content
            if cells:
                co = cells[0]
                if co not in expected_cos:
                    error(f"Unexpected CO in articulation table: {co}", file)

                if co in seen_cos:
                    error(f"Duplicate CO row in articulation table: {co}", file)

                if len(cells[1:]) != len(expected_columns):
                    error(
                        f"Incorrect column count for {co} in articulation table. "
                        f"Expected {len(expected_columns)}, found {len(cells[1:])}",
                        file
                    )

                mapping[co] = {}
                for col, val in zip(expected_columns, cells[1:]):
                    mapping[co][col] = normalize_value(val, file)

                seen_cos.add(co)
        i += 1

    # Final pointer advancement
    while i < len(tokens) and tokens[i].type != "table_close":
        i += 1
    i += 1 # Move past table_close

    # -------------------------
    # 3. Validation
    # -------------------------
    if set(expected_cos) != seen_cos:
        error(
            f"Missing CO rows in articulation table.\n"
            f"Expected: {expected_cos}\n"
            f"Found: {sorted(seen_cos)}",
            file
        )

    return mapping, i

def parse_unit(tokens, idx, file):
    # -------------------------
    # Parse Unit H2 heading
    # -------------------------
    header, content_idx = get_next_inline_content(tokens, idx + 1)
    if not header:
        error("Unit heading has no content", file)
    
    unit_re = re.compile(
        r"^Unit\s+(\d+):\s+(.*)$"
    )

    m = unit_re.match(header)
    if m is None:
        error(
            "Invalid unit heading format.\n"
            "Expected: Unit <number>: <title>\n"
            f"Found: '{header}'",
            file
        )
    unit = {
        "number": int(m.group(1)),
        "title": m.group(2).strip(),
        "theory": None,
        "lab": None,
        "x": None
    }
    # 1. Skip everything until the Unit H2 heading actually closes
    i = content_idx
    while i < len(tokens) and tokens[i].type != "heading_close":
        i += 1
    
    # 2. Look for the FIRST H3 heading, skipping any noise (newlines, spaces, etc.)
    # This replaces your old 'i += 1' and 'if tokens[i].type != "heading_open"' block
    while i < len(tokens):
        # If we find an H3, we are ready to start the section parser
        if tokens[i].type == "heading_open" and tokens[i].tag == "h3":
            break 
            
        # If we hit another H2 before finding an H3, the unit is empty
        if tokens[i].type == "heading_open" and tokens[i].tag == "h2":
            error(f"Unit {unit['number']} has no H3 sections (Theory/Lab/X-Activity)", file)
        
        i += 1
    #i=idx
    seen_sections = []
    while i < len(tokens) and tokens[i].type != "heading_close":
        i += 1
        if i >= len(tokens):
            error(f"Unit {unit['number']}: Heading '{header}' is unterminated (missing closing # tags or newline)", file)

    i += 1  # move past heading_close
    # Only H3 headings allowed inside a Unit at first
    if tokens[i].type != "heading_open" or tokens[i].tag != "h3":
        found = tokens[i].tag if hasattr(tokens[i], "tag") else tokens[i].type
        error(
            f"Unit {unit['number']}: Unexpected content. \n"
            f"Existing is a {found} \n"
            f"Expected a section heading (H3).",
            file
        )

    # -------------------------
    # Parse H3 sections inside unit
    # -------------------------
    while i < len(tokens):

        if tokens[i].type == "heading_open" and tokens[i].tag == "h2":
            break

        # Seek the title of the H3 section
        section_title, title_idx = get_next_inline_content(tokens, i + 1)
        if not section_title:
            i += 1
            continue

        # Use the found section_title for regex matching
        m_theory = THEORY_HDR_RE.match(section_title)
        m_lab = LAB_HDR_RE.match(section_title)
        m_x = X_HDR_RE.match(section_title)
        
        # Move i to the end of the heading to begin parsing content
        i = title_idx
        while i < len(tokens) and tokens[i].type != "heading_close":
            i += 1
        i += 1 # move past heading_close

        # -------------------------
        # Theory Content section
        # -------------------------
        if m_theory:
            seen_sections.append("theory")
            if "theory" in seen_sections[:-1]:
                error(
                    f"Unit {unit['number']}: Theory Content section repeated or out of order",
                    file
                )

            if unit["theory"] is not None:
                error(
                    f"Unit {unit['number']}: Duplicate Theory Content section",
                    file
                )

            unit["theory"] = {
                "hours": int(m_theory.group(1)),
                "topics": []
            }
            while i < len(tokens) and tokens[i].type != "heading_close":
                i += 1
                if i >= len(tokens):
                    error(f"Unit {unit['number']}: Section '{section_title}' is unterminated (missing closing # tags or newline)", file)

            i += 1  # move past heading_close
            # -------------------------
            # Expect bullet list
            # -------------------------
            if i >= len(tokens) or tokens[i].type != "bullet_list_open":
                error(
                    f"Unit {unit['number']}: Theory Content must be a bullet list",
                    file
                )

            i += 1  # enter bullet list

            # -------------------------
            # Parse theory topics
            # -------------------------
            while i < len(tokens):
                t = tokens[i]

                # 1. If we hit the end of the list, we are done with this section
                if t.type == "bullet_list_close":
                    i += 1
                    break

                # 2. Skip "noise" tokens that markdown-it generates inside lists
                if t.type in ["list_item_close", "paragraph_open", "paragraph_close"]:
                    i += 1
                    continue

                # 3. Process the actual content of a bullet
                if t.type == "list_item_open":
                    # Look ahead for the 'inline' token which contains the text
                    content_idx = i
                    while content_idx < len(tokens) and tokens[content_idx].type != "inline":
                        content_idx += 1
                    
                    if content_idx < len(tokens):
                        text = tokens[content_idx].content.strip()
                        topic, details = validate_colon_bullet(text, file)
                        unit["theory"]["topics"].append((topic, details))
                    
                    # Move i to the content_idx to continue processing
                    i = content_idx + 1
                    continue

                # 4. If it's anything else that isn't handled above, trigger your error
                error(
                    f"Unit {unit['number']}: Invalid content inside Theory Content.\n"
                    f"Found unexpected token type: {t.type}",
                    file
                )
            if not unit["theory"]["topics"]:
                error(
                    f"Unit {unit['number']}: Theory Content has no topics",
                    file
                )

            continue
        # -------------------------
        # Laboratory Experiments section
        # -------------------------
        if m_lab:
            seen_sections.append("lab")
            if "lab" in seen_sections[:-1]:
                error(f"Unit {unit['number']}: Laboratory Experiments section repeated or out of order", file)
            if unit["lab"] is not None:
                error(f"Unit {unit['number']}: Duplicate Laboratory Experiments section", file)

            unit["lab"] = {
                "hours": int(m_lab.group(1)),
                "experiments": []
            }

            # Move past H3 heading robustly using the helper
            _, i = get_next_inline_content(tokens, i) 
            while i < len(tokens) and tokens[i].type != "heading_close":
                i += 1
            i += 1  # past heading_close

            # -------------------------
            # Parse H4 experiment blocks
            # -------------------------
            while i < len(tokens):
                # Stop if next H3 (Theory / X-Activity) or H2 (next Unit) starts
                if tokens[i].type == "heading_open" and tokens[i].tag in ("h3", "h2"):
                    break

                # Skip non-semantic noise between experiments
                if tokens[i].type in ("softbreak", "hardbreak", "paragraph_open", "paragraph_close"):
                    i += 1
                    continue

                # Robustly find experiment title (H4)
                if tokens[i].type == "heading_open" and tokens[i].tag == "h4":
                    exp_title, title_idx = get_next_inline_content(tokens, i + 1)
                    if not exp_title:
                        error(f"Unit {unit['number']}: Malformed H4 experiment heading", file)
                    
                    # Move past H4 heading
                    i = title_idx
                    while i < len(tokens) and tokens[i].type != "heading_close":
                        i += 1
                    i += 1  # past heading_close

                    # -------------------------
                    # Collect experiment description
                    # -------------------------
                    description = []
                    while i < len(tokens):
                        # Stop if any new heading starts
                        if tokens[i].type == "heading_open":
                            break
                        
                        # Use the helper to seek the next piece of actual text
                        content, next_idx = get_next_inline_content(tokens, i)
                        
                        if content:
                            # Detect if this content is inside a bullet list to add a prefix
                            is_list_item = False
                            # Look back slightly to see if we are inside a list item
                            check_idx = i
                            while check_idx < next_idx:
                                if tokens[check_idx].type == "list_item_open":
                                    is_list_item = True
                                    break
                                check_idx += 1
                            
                            prefix = "- " if is_list_item else ""
                            description.append(f"{prefix}{content}")
                            i = next_idx # Advance past the found content
                        else:
                            i += 1

                    if not description:
                        error(f"Unit {unit['number']}: Experiment '{exp_title}' has no description", file)

                    unit["lab"]["experiments"].append({
                        "title": exp_title,
                        "description": description
                    })
                    continue
                
                # If we encounter something that isn't a heading or noise, skip it or handle it
                i += 1

            if not unit["lab"]["experiments"]:
                error(f"Unit {unit['number']}: Laboratory Experiments section has no experiments", file)

            continue
        # -------------------------
        # X-Activity section
        # -------------------------
        if m_x:
            seen_sections.append("x")
            if "x" in seen_sections[:-1]:
                error(f"Unit {unit['number']}: X-Activity section repeated or out of order", file)
            if unit["x"] is not None:
                error(f"Unit {unit['number']}: Duplicate X-Activity section", file)

            unit["x"] = {
                "hours": int(m_x.group(1)),
                "components": []
            }

            # Move past H3 heading safely using the helper
            _, i = get_next_inline_content(tokens, i)
            while i < len(tokens) and tokens[i].type != "heading_close":
                i += 1
            i += 1  # past heading_close

            # -------------------------
            # Parse H4 component blocks
            # -------------------------
            while i < len(tokens):
                if tokens[i].type == "heading_open" and tokens[i].tag in ("h3", "h2"):
                    break

                if tokens[i].type in ("softbreak", "hardbreak", "paragraph_open", "paragraph_close"):
                    i += 1
                    continue

                if tokens[i].type == "heading_open" and tokens[i].tag == "h4":
                    comp_title, title_idx = get_next_inline_content(tokens, i + 1)
                    if not comp_title:
                        error(f"Unit {unit['number']}: Malformed H4 component heading", file)
                    
                    i = title_idx
                    while i < len(tokens) and tokens[i].type != "heading_close":
                        i += 1
                    i += 1  # past heading_close

                    description = []
                    while i < len(tokens):
                        if tokens[i].type == "heading_open":
                            break
                        
                        content, next_idx = get_next_inline_content(tokens, i)
                        if content:
                            is_list_item = False
                            check_idx = i
                            while check_idx < next_idx:
                                if tokens[check_idx].type == "list_item_open":
                                    is_list_item = True
                                    break
                                check_idx += 1
                            
                            prefix = "- " if is_list_item else ""
                            description.append(f"{prefix}{content}")
                            i = next_idx 
                        else:
                            i += 1

                    if not description:
                        error(f"Unit {unit['number']}: X-Activity component '{comp_title}' has no description", file)

                    # --- FIXED: Added missing append call ---
                    unit["x"]["components"].append({
                        "title": comp_title,
                        "description": description
                    })
                    # ----------------------------------------
                    continue
                
                i += 1

            if not unit["x"]["components"]:
                error(f"Unit {unit['number']}: X-Activity section has no components", file)

            continue
        # -------------------------
        # Unknown section
        # -------------------------
        error(
            f"Unit {unit['number']}: Invalid section heading '{section_title}'",
            file
        )
    unit["section_order"] = seen_sections
   
    return unit, i

# -------------------------
# LaTeX Emission (Semantic Only)
# -------------------------
def emit_articulation_block(title, columns, mapping):
    out = []
    out.append(f"\\BeginArticulation{{{title}}}{{{len(columns)}}}")

    header = "CO & " + " & ".join(columns)
    out.append(f"\\ArticulationHeader{{{header}}}")

    for co in sorted(mapping.keys(), key=lambda x: int(x[2:])):
        row = mapping[co]
        values = []
        for col in columns:
            v = row[col]
            values.append("-" if v is None else str(v))
        out.append(
            "\\ArticulationRow{" +
            f"{co} & " + " & ".join(values) +
            "}"
        )

    out.append("\\EndArticulation")
    return out

def emit_latex(courses, programme_details):
    out = []
    for c in courses:
        
        out.append(f"\\BeginCourse{{{c['code']}}}{{{c['title']}}}{{{c['ltpxc']}}}{{{c['prerequisite'] if c['prerequisite'] else 'None'  }}}")

        out.append("\\CourseObjectives{")
        for o in c["objectives"]:
            out.append(f"  \\COBItem{{{tex_safe(o)}}}")
        out.append("}")

        out.append("\\CourseOutcomes{")
        for o in c["outcomes"]:
            out.append(f"  \\COItem{{{tex_safe(o)}}}")
        out.append("}")
        # -------------------------
        # Articulation Matrices
        # -------------------------
        po_cols = [f"PO{i+1}" for i in range(len(programme_details["NBA_PO"]))]
        pso_cols = [f"PSO{i+1}" for i in range(len(programme_details["PSO"]))]
        so_cols = [f"SO{i+1}" for i in range(len(programme_details["ABET_SO"]))]
        if "NBA_PO" in c["articulation"]:            
            out.extend(
                emit_articulation_block(
                    "CO-NBA Programme Outcomes Mapping",
                    po_cols,
                    c["articulation"]["NBA_PO"]
                )
            )

        if "PSO" in c["articulation"]:
            out.extend(
                emit_articulation_block(
                    "CO-Programme Specific Outcomes Mapping",
                    pso_cols,
                    c["articulation"]["PSO"]
                )
            )

        if "ABET_SO" in c["articulation"]:
            out.extend(
                emit_articulation_block(
                    "CO-ABET Student Outcomes Mapping",
                    so_cols,
                    c["articulation"]["ABET_SO"]
                )
            )

        # -------------------------
        # Units
        # -------------------------
        for u in c["units"]:
            # Sanitize unit title
            safe_title = tex_safe(u['title'])
            out.append(f"\\BeginUnit{{{u['number']}}}{{{safe_title}}}")

            # -------- Theory --------
            if u["theory"] is not None:
                out.append(f"\\BeginTheory{{{u['theory']['hours']}}}")
                for topic, subs in u["theory"]["topics"]:
                    # Sanitize topic and sub-details
                    safe_topic = tex_safe(topic)
                    safe_subs = [tex_safe(s) for s in subs]
                    joined = "; ".join(safe_subs)
                    out.append(f"  \\TheoryTopic{{{safe_topic}}}{{{joined}}}")
                out.append("\\EndTheory")

            # -------- Laboratory --------
            if u["lab"] is not None:
                out.append(f"\\BeginLab{{{u['lab']['hours']}}}")
                for exp in u["lab"]["experiments"]:
                    safe_exp_title = tex_safe(exp['title'])
                    out.append(f"  \\LabExperiment{{{safe_exp_title}}}")
                    for line in exp["description"]:
                        # If the line contains '$', it's math; don't sanitize it
                        # Otherwise, make it safe
                        safe_line = robust_tex_sanitize(line)
                        out.append(f"    \\LabDesc{{{safe_line}}}")
                    out.append("  \\EndLabExperiment")
                out.append("\\EndLab")

            # -------- X-Activity (Apply same logic) --------
            if u["x"] is not None:
                out.append(f"\\BeginXActivity{{{u['x']['hours']}}}")
                for comp in u["x"]["components"]:
                    safe_comp_title = tex_safe(comp['title'])
                    out.append(f"  \\XComponent{{{safe_comp_title}}}")
                    for line in comp["description"]:
                        safe_line = robust_tex_sanitize(line)
                        out.append(f"    \\XDesc{{{safe_line}}}")
                    out.append("  \\EndXComponent")
                out.append("\\EndXActivity")

            out.append("\\EndUnit")

        out.append("\\EndCourse")

    return "\n".join(out)


# -------------------------
# Main
# -------------------------

def main():
    # 1. Initialize error collection
    all_errors = []

    # --- Load Programme Details ---
    try:
        programme_details = read_programme_details(
            Path("programme_details.md"), 
            "programme_details.md"
        )
        
        # Mandatory section checks
        for section, key in [("NBA Programme Outcomes", "NBA_PO"), 
                             ("Programme Specific Outcomes", "PSO"), 
                             ("ABET Student Outcomes", "ABET_SO")]:
            if not programme_details[key]:
                all_errors.append(f"programme_details.md: {section} section is mandatory")
    except SyllabusError as e:
        all_errors.append(str(e))
        # If programme details fail, we can't map COs, so we must stop
        print("\n".join(all_errors))
        sys.exit(1)

    # --- Process Course Files ---
    input_dir = Path("courses_md")
    courses = []

    if not input_dir.exists():
        print(f"Error: Directory '{input_dir}' not found.")
        sys.exit(1)

    for md_file in input_dir.glob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
            tokens = parse_markdown(text)
            
            # Extract header and build course
            title, code, ltpxc, prereq = extract_course_header(tokens, md_file.name)
            course_data = build_course(
                tokens, md_file.name, title, code, ltpxc, prereq, programme_details
            )
            
            # Only add to list if successful
            courses.append(course_data)
            
        except SyllabusError as e:
            # Capture error and move to next file
            all_errors.append(str(e))
        except Exception as e:
            # Capture unexpected crashes to prevent loop breakage
            all_errors.append(f"{md_file.name}: Unexpected error: {str(e)}")

    # --- Final Report and Emission ---
    if all_errors:
        print("\n" + "="*30)
        print(f"ERRORS FOUND ({len(all_errors)}):")
        for err in all_errors:
            print(f"- {err}")
        print("="*30 + "\n")

    if courses:
        output = Path("generated/body_md.tex")
        output.parent.mkdir(exist_ok=True)
        
        print(f"Generating LaTeX for {len(courses)} successful courses...")
        output.write_text(emit_latex(courses, programme_details), encoding="utf-8")
    else:
        print("No valid courses found to generate LaTeX.")

    # Exit with error code if any errors were collected
    if all_errors:
        sys.exit(1)

if __name__ == "__main__":
    main()