
from pathlib import Path
from markdown_it import MarkdownIt
import re
import sys
from typing import NoReturn

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

COLON_BULLET_RE = re.compile(r"^([^:]+)\s*:\s*(.+)$")
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


def validate_colon_bullet(text, file):
    if text.count(":") != 1:
        error(
            f"Invalid topic bullet (must contain exactly one colon): '{text}'",
            file
        )

    if text.strip().endswith(":"):
        error(
            f"Trailing colon not allowed in topic bullet: '{text}'",
            file
        )

    parts = text.split(":", 1)
    topic = parts[0].strip()
    details_content = parts[1].strip()
    details = [d.strip() for d in re.split(r";|,", details_content) if d.strip()]

    if not topic or not details:
        error(
            f"Empty topic or details in bullet: '{text}'",
            file
        )

    return topic, details

def extract_course_header(md_tokens, file) -> tuple[str, str, str]:
    title = None
    code = None
    ltpc = None
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

    ltpc_match = re.search(
        r"L\s*-\s*T\s*-\s*P\s*-\s*C\s*:\s*(\d+\s*-\s*\d+\s*-\s*\d+\s*-\s*\d+)",
        full_text,
        re.IGNORECASE
    )
    
    if ltpc_match is None:
        error("Missing L-T-P-C information", file)

    # Normalize LTPC (remove spaces)
    ltpc = re.sub(r"\s*", "", ltpc_match.group(1))

    return title, code, ltpc

# -------------------------
# Semantic Model Builders
# -------------------------

def build_course(md_tokens, file, title, code, ltpc):
    course = {
        "title": title,
        "code": code,
        "ltpc": ltpc,
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
        # Unknown section
        # -------------------------
        error(
            f"Unit {unit['number']}: Invalid section heading '{section_title}'",
            file
        )

    return unit, i

# -------------------------
# LaTeX Emission (Semantic Only)
# -------------------------

def emit_latex(courses):
    out = []

    for c in courses:
        out.append(f"\\BeginCourse{{{c['code']}}}{{{c['title']}}}{{{c['ltpc']}}}")

        out.append("\\CourseObjectives{")
        for o in c["objectives"]:
            out.append(f"  \\COItem{{{o}}}")
        out.append("}")

        out.append("\\CourseOutcomes{")
        for o in c["outcomes"]:
            out.append(f"  \\COItem{{{o}}}")
        out.append("}")

        for u in c["units"]:
            out.append(f"\\BeginUnit{{{u['number']}}}{{{u['title']}}}")
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
            title, code, ltpc = extract_course_header(tokens, md_file.name)
            course = build_course(tokens, md_file.name, title, code, ltpc)
            courses.append(course)
        except SyllabusError as e:
            print(f"\nERROR:\n{e}")
            sys.exit(1)
    output.parent.mkdir(exist_ok=True)
    output.write_text(emit_latex(courses), encoding="utf-8")
    print("Semantic LaTeX generated:", output)


if __name__ == "__main__":
    main()
