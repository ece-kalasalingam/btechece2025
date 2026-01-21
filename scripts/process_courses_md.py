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

def parse_ltpxc(ltpxc: str, file: str) -> tuple[int, int, int, int, int]:
    try:
        L, T, P, X, C = map(int, ltpxc.split("-"))
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

def tex_safe(text):
    """Escapes common LaTeX special characters."""
    if not text:
        return ""
    
    # Define mappings for characters that crash LaTeX
    # Note: We do NOT escape $ here because you use it for Math mode
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
    }
    
    for char, safe_version in replacements.items():
        text = text.replace(char, safe_version)
    return text

def extract_course_header(md_tokens, file) -> tuple[str, str, str, str | None]:
    title = None
    code = None
    ltpxc = None
    prerequisite = None
    metadata_blob = []

    for i, t in enumerate(md_tokens):
        # Course title (H1)
        if t.type == "heading_open" and t.tag == "h1":
            title = md_tokens[i + 1].content.strip()
        # Metadata
        if t.type == "paragraph_open":
            metadata_blob.append(md_tokens[i + 1].content)
        # Stop early once header section ends
        if t.type == "heading_open" and t.tag == "h2":
            break

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
        r"L\s*-\s*T\s*-\s*P\s*-\s*X\s*-\s*C\s*:\s*(\d+\s*-\s*\d+\s*-\s*\d+\s*-\s*\d+\s*-\s*\d+)",
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

def build_course(md_tokens, file, title, code, ltpxc, prerequisite):
    course = {
        "title": title,
        "code": code,
        "ltpxc": ltpxc,
        "prerequisite": prerequisite,
        "objectives": [],
        "outcomes": [],
        "units": []
    }

    i = 0
    while i < len(md_tokens):
        t = md_tokens[i]
        # Objectives
        if t.type == "heading_open" and md_tokens[i + 1].content == "Course Objectives":
            i = parse_simple_list(md_tokens, i + 2, course["objectives"], file)

        # Outcomes
        if t.type == "heading_open" and md_tokens[i + 1].content == "Course Outcomes":
            i = parse_outcomes(md_tokens, i + 2, course["outcomes"], file)

        # Units
        if t.type == "heading_open" and md_tokens[i + 1].content.startswith("Unit"):
            unit_data, next_idx = parse_unit(md_tokens, i, file)
            course["units"].append(unit_data)
            i = next_idx
            continue

        i += 1

    if not course["title"] or not course["code"]:
        error("Missing course title or course code", file)

    # -------------------------
    # Presence validation
    # -------------------------
    L, T, P, X, C = parse_ltpxc(course["ltpxc"], file)

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

    # Parse declared C exactly (e.g., "4.25" → Fraction(17,4))
    try:
        C_f = Fraction(C)
    except Exception:
        error(f"Invalid credit value C = {C}", file)

    if computed_C != C_f:
        error(
            f"Credit mismatch: expected C = {C_f}, "
            f"but L+T+(P/2)+(X/3) = {computed_C}",
            file
        )

    return course


def parse_simple_list(tokens, start, target, file):
    i = start
    while i < len(tokens) and tokens[i].type != "heading_open":
        if tokens[i].type == "list_item_open":
            text = tokens[i + 2].content.strip()
            target.append(text)
        i += 1
    return i


def parse_outcomes(tokens, start, target, file):
    i = start
    while i < len(tokens) and tokens[i].type != "heading_open":
        if tokens[i].type == "list_item_open":
            text = tokens[i + 2].content.strip()
            if not CO_RE.match(text):
                error(f"Invalid course outcome format: '{text}'", file)
            target.append(text)
        i += 1
    return i


def parse_unit(tokens, idx, file):
    # -------------------------
    # Parse Unit H2 heading
    # -------------------------
    header = tokens[idx + 1].content.strip()
    
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
    i=idx
    seen_sections = []
    while i < len(tokens) and tokens[i].type != "heading_close":
        i += 1
        if i >= len(tokens):
            error(
                f"Unit {unit['number']}: Unterminated heading",
                file
            )

    i += 1  # move past heading_close
    # Only H3 headings allowed inside a Unit at first
    if tokens[i].type != "heading_open" or tokens[i].tag != "h3":
        found = tokens[i].tag if hasattr(tokens[i], "tag") else tokens[i].type
        error(
            f"Unit {unit['number']}: Unexpected content. \n"
            f"Existing is a {found} at \n"
            f'{tokens[i + 1].content.strip()} \n'
            f"Expected a section heading (H3).",
            file
        )

    # -------------------------
    # Parse H3 sections inside unit
    # -------------------------
    while i < len(tokens):

        # Stop when next Unit starts
        if tokens[i].type == "heading_open" and tokens[i].tag == "h2":
            break

        section_title = tokens[i + 1].content.strip()

        # -------------------------
        # Theory Content section
        # -------------------------
        m_theory = THEORY_HDR_RE.match(section_title)
        if m_theory:
            seen_sections.append("theory")
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
                    error(
                        f"Unit {unit['number']}: Unterminated heading",
                        file
                    )

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
        m_lab = LAB_HDR_RE.match(section_title)
        if m_lab:
            seen_sections.append("lab")
            if unit["lab"] is not None:
                error(f"Unit {unit['number']}: Duplicate Laboratory Experiments section", file)

            unit["lab"] = {
                "hours": int(m_lab.group(1)),
                "experiments": []
            }

            # Move past H3 heading (robust)
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
                if tokens[i].type in ("softbreak", "hardbreak"):
                    i += 1
                    continue

                # Expect experiment title (H4)
                if tokens[i].type != "heading_open" or tokens[i].tag != "h4":
                    error(f"Unit {unit['number']}: Laboratory Experiments must contain H4 experiment headings", file)

                if i + 1 >= len(tokens) or tokens[i + 1].type != "inline":
                    error(f"Unit {unit['number']}: Malformed H4 experiment heading", file)
                
                exp_title = tokens[i + 1].content.strip()

                # Move past H4 heading (robust)
                while i < len(tokens) and tokens[i].type != "heading_close":
                    i += 1
                i += 1  # past heading_close

                # -------------------------
                # Collect experiment description
                # -------------------------
                description = []
                while i < len(tokens):
                    # Stop if a new heading starts
                    if tokens[i].type == "heading_open":
                        break

                    # Skip breaks and closers
                    if tokens[i].type in ("paragraph_close", "softbreak", "hardbreak", "list_item_open", "list_item_close", "bullet_list_close"):
                        i += 1
                        continue

                    # Paragraph content
                    if tokens[i].type == "paragraph_open":
                        i += 1
                        while i < len(tokens) and tokens[i].type != "inline":
                            i += 1
                        if i < len(tokens):
                            description.append(tokens[i].content.strip())
                        while i < len(tokens) and tokens[i].type != "paragraph_close":
                            i += 1
                        i += 1 # past paragraph_close
                        continue

                    # Bullet list inside description
                    if tokens[i].type == "bullet_list_open":
                        i += 1
                        while i < len(tokens) and tokens[i].type != "bullet_list_close":
                            if tokens[i].type == "inline":
                                description.append(f"- {tokens[i].content.strip()}")
                            i += 1
                        i += 1  # past bullet_list_close
                        continue

                    # If none of the above matched, it's an error
                    error(f"Unit {unit['number']}: Invalid content inside Laboratory Experiment description", file)

                if not description:
                    error(f"Unit {unit['number']}: Experiment '{exp_title}' has no description", file)

                unit["lab"]["experiments"].append({
                    "title": exp_title,
                    "description": description
                })

            if not unit["lab"]["experiments"]:
                error(f"Unit {unit['number']}: Laboratory Experiments section has no experiments", file)

            continue
        
        # -------------------------
        # X-Activity section
        # -------------------------
        m_x = X_HDR_RE.match(section_title)
        if m_x:
            seen_sections.append("x")
            if unit["x"] is not None:
                error(
                    f"Unit {unit['number']}: Duplicate X-Activity section",
                    file
                )

            unit["x"] = {
                "hours": int(m_x.group(1)),
                "components": []
            }

            # Move past H3 heading (robust)
            while i < len(tokens) and tokens[i].type != "heading_close":
                i += 1
            i += 1  # past heading_close

            # -------------------------
            # Parse H4 component blocks
            # -------------------------
            while i < len(tokens):

                # Stop if next H3 or next Unit starts
                if tokens[i].type == "heading_open" and tokens[i].tag in ("h3", "h2"):
                    break

                # Skip non-semantic noise
                if tokens[i].type in ("softbreak", "hardbreak"):
                    i += 1
                    continue

                # Expect component title (H4)
                if tokens[i].type != "heading_open" or tokens[i].tag != "h4":
                    error(
                        f"Unit {unit['number']}: X-Activity must contain H4 component headings",
                        file
                    )

                if i + 1 >= len(tokens) or tokens[i + 1].type != "inline":
                    error(
                        f"Unit {unit['number']}: Malformed H4 component heading",
                        file
                    )

                comp_title = tokens[i + 1].content.strip()

                # Move past H4 heading
                while i < len(tokens) and tokens[i].type != "heading_close":
                    i += 1
                i += 1  # past heading_close

                # -------------------------
                # Collect component description
                # -------------------------
                description = []

                while i < len(tokens):

                    # Stop if a new heading starts
                    if tokens[i].type == "heading_open":
                        break

                    # Skip noise
                    if tokens[i].type in (
                        "paragraph_close",
                        "softbreak",
                        "hardbreak",
                        "list_item_open",
                        "list_item_close",
                    ):
                        i += 1
                        continue

                    # Paragraph content
                    if tokens[i].type == "paragraph_open":
                        i += 1
                        while i < len(tokens) and tokens[i].type != "inline":
                            i += 1
                        if i < len(tokens):
                            description.append(tokens[i].content.strip())
                        while i < len(tokens) and tokens[i].type != "paragraph_close":
                            i += 1
                        i += 1
                        continue

                    # Bullet list inside component description
                    if tokens[i].type == "bullet_list_open":
                        i += 1
                        while i < len(tokens) and tokens[i].type != "bullet_list_close":
                            if tokens[i].type == "inline":
                                description.append(f"- {tokens[i].content.strip()}")
                            i += 1
                        i += 1
                        continue

                    error(
                        f"Unit {unit['number']}: Invalid content inside X-Activity component description",
                        file
                    )

                if not description:
                    error(
                        f"Unit {unit['number']}: X-Activity component '{comp_title}' has no description",
                        file
                    )

                unit["x"]["components"].append({
                    "title": comp_title,
                    "description": description
                })

            if not unit["x"]["components"]:
                error(
                    f"Unit {unit['number']}: X-Activity section has no components",
                    file
                )

            continue

        # -------------------------
        # Unknown section
        # -------------------------
        error(
            f"Unit {unit['number']}: Invalid section heading '{section_title}'",
            file
        )
    # -------------------------
    # Section order validation (Policy rule)
    # -------------------------
    expected_order = []

    # NOTE: Order is fixed; inclusion depends on LTPXC
    if True:
        expected_order = ["theory", "lab", "x"]

    # Filter expected order based on what exists in this unit
    expected_order = [
        s for s in expected_order
        if unit[s] is not None
    ]

    if seen_sections != expected_order:
        error(
            f"Unit {unit['number']} section order invalid. "
            f"Expected {expected_order}, found {seen_sections}",
            file
        )

    return unit, i

# -------------------------
# LaTeX Emission (Semantic Only)
# -------------------------

def emit_latex(courses):
    out = []
    for c in courses:
        
        out.append(f"\\BeginCourse{{{c['code']}}}{{{c['title']}}}{{{c['ltpxc']}}}{{{c['prerequisite'] if c['prerequisite'] else 'None'  }}}")

        out.append("\\CourseObjectives{")
        for o in c["objectives"]:
            out.append(f"  \\COItem{{{o}}}")
        out.append("}")

        out.append("\\CourseOutcomes{")
        for o in c["outcomes"]:
            out.append(f"  \\COItem{{{o}}}")
        out.append("}")

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
                        safe_line = line if "$" in line else tex_safe(line)
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
                        safe_line = line if "$" in line else tex_safe(line)
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
    input_dir = Path("courses_md")
    output = Path("generated/body_md.tex")

    courses = []

    for md_file in input_dir.glob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
            tokens = parse_markdown(text)
            title, code, ltpc, prerequisite = extract_course_header(tokens, md_file.name, )
            course = build_course(tokens, md_file.name, title, code, ltpc, prerequisite)
            courses.append(course)
        except SyllabusError as e:
            print(f"\nERROR:\n{e}")
            sys.exit(1)
    output.parent.mkdir(exist_ok=True)
    output.write_text(emit_latex(courses), encoding="utf-8")
    print("Semantic LaTeX generated:", output)


if __name__ == "__main__":
    main()
