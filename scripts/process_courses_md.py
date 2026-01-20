# build_body_from_md.py

from pathlib import Path
from markdown_it import MarkdownIt
import re
import sys

# -------------------------
# Errors
# -------------------------

class SyllabusError(Exception):
    pass


def error(msg, file):
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

    m = COLON_BULLET_RE.match(text)
    if m is None:
        raise SyllabusError(
           f"Invalid topic bullet format.\n"
            f"Expected: Topic : details\n"
            f"Found: '{text}'",
            file
        )

    topic = m.group(1).strip()
    details = [d.strip() for d in re.split(r";|,", m.group(2)) if d.strip()]

    if not topic or not details:
        error(
            f"Empty topic or details in bullet: '{text}'",
            file
        )

    return topic, details

def extract_course_header(md_tokens, file):
    title = None
    code = None
    ltpc = None

    for i, t in enumerate(md_tokens):
        if t.type == "heading_open" and t.tag == "h1":
            title = md_tokens[i + 1].content.strip()
        # Metadata
        if t.type == "paragraph_open":
            line = md_tokens[i + 1].content.strip()
            print("RAW PARAGRAPH CONTENT >>>")
            print(repr(line))
            print("<<< END PARAGRAPH")
            if line.startswith("Course Code:"):
                code = line.split(":", 1)[1].strip()
            elif line.startswith("L-T-P-C:"):
                ltpc = line.split(":", 1)[1].strip()
                print("LTPC:", ltpc)

        # Stop early once header section ends
        if t.type == "heading_open" and t.tag == "h2":
            break

    if not title:
        error("Missing course title (H1 heading)", file)
    if not code:
        error("Missing Course Code", file)
    if not ltpc:
        error("Missing L-T-P-C information", file)

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
            unit = parse_unit(md_tokens, i, file)
            course["units"].append(unit)

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
    header = tokens[idx + 1].content.strip()

    unit_re = re.compile(
        r"^Unit\s+(\d+):\s+(.*?)\s+\((\d+)\s+Hours\)$"
    )

    m = unit_re.match(header)
    if m is None:
        raise SyllabusError(
            f"Invalid unit heading format.\n"
            f"Expected: Unit <number>: <title> (<hours> Hours)\n"
            f"Found: '{header}'"
        )

    unit = {
        "number": int(m.group(1)),
        "title": m.group(2).strip(),
        "hours": int(m.group(3)),
        "topics": []
    }

    i = idx + 2
    while i < len(tokens) and tokens[i].type != "heading_open":
        if tokens[i].type == "list_item_open":
            text = tokens[i + 2].content.strip()
            topic, details = validate_colon_bullet(text, file)
            unit["topics"].append((topic, details))
        i += 1

    if not unit["topics"]:
        error(f"Unit {unit['number']} has no topics", file)

    return unit

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
            out.append(f"\\BeginUnit{{{u['number']}}}{{{u['title']}}}{{{u['hours']}}}")
            for topic, details in u["topics"]:
                joined = "; ".join(details)
                out.append(f"\\UnitTopic{{{topic}}}{{{joined}}}")
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
            print(f"ERROR: {e}")
            sys.exit(1)

    output.parent.mkdir(exist_ok=True)
    output.write_text(emit_latex(courses), encoding="utf-8")
    print("Semantic LaTeX generated:", output)


if __name__ == "__main__":
    main()
