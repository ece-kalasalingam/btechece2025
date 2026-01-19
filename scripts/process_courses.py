from pathlib import Path
from TexSoup import TexSoup
from datetime import datetime
from dataclasses import dataclass
from typing import List
import sys
import re

@dataclass
class Course:
    code: str
    name: str
    category: str
    ctype: str
    L: str
    T: str
    P: str
    X: str
    C: str
    prereq: str
    description: str
    objectives_tex: str
    outcomes: List[str]
    nba_rows: List[List[str]]
    abet_rows: List[List[str]]
    references_tex: str

ALLOWED_CATEGORIES = {"FCM", "FCE", "PM", "PE", "SEM", "SEE", "MDM", "MDE"}
ALLOWED_TYPES = {"ICT", "ICP", "TC", "PC"}
SMALL_WORDS = {'of', 'and', 'in', 'the', 'with', 'for', 'to', 'a', 'on', 'at', 'by'}
ROMAN_NUMERALS = {'i', 'ii', 'iii', 'iv', 'v', 'vi'}
PO_COUNT = 11
PSO_COUNT = 3
SO_COUNT = 7
NBA_COLS = PO_COUNT + PSO_COUNT
ABET_COLS = SO_COUNT + PSO_COUNT

ROOT = Path(__file__).resolve().parent.parent
COURSES_DIR = ROOT / "courses"
OUT_DIR = ROOT / "outputs" / "a4"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def get_scalar(soup, cmd, course):
    node = soup.find(cmd)
    if not node:
        raise ValueError(f"{course}: Missing \\{cmd}")
    return "".join(str(x) for x in node.contents).strip()
def format_course_title(text):
    words = text.strip().split()
    if not words:
        return ""

    formatted = []

    for i, word in enumerate(words):
        # Preserve surrounding punctuation
        prefix = re.match(r'^\W+', word)
        suffix = re.match(r'.*?(\W+)$', word)

        core = re.sub(r'^\W+|\W+$', '', word)

        # Acronyms
        if core.isupper():
            new = core

        # Roman numerals
        elif core.lower() in ROMAN_NUMERALS:
            new = core.upper()

        # Small words (not first)
        elif i > 0 and core.lower() in SMALL_WORDS:
            new = core.lower()

        # Hyphenated words
        elif '-' in core:
            new = '-'.join(p.capitalize() for p in core.split('-'))

        # Slash-separated words
        elif '/' in core:
            new = '/'.join(p.capitalize() for p in core.split('/'))

        else:
            new = core.capitalize()

        formatted.append(
            f"{prefix.group(0) if prefix else ''}"
            f"{new}"
            f"{suffix.group(1) if suffix else ''}"
        )

    return " ".join(formatted)
def normalize_course_name(name: str) -> str:
    """
    Normalize course name according to syllabus rules:
    - '&' → 'AND'
    - 'Lab' → 'Laboratory'
    - 'Introduction to/of X' → 'Foundations of X'
    """

    n = name.strip()

    # Replace '&' with 'AND'
    n = n.replace("&", "and")

    # Replace 'Lab' as a word (case-insensitive)
    n = re.sub(r"\bLab\b", "Laboratory", n, flags=re.IGNORECASE)

    # Replace 'Introduction to/of X' → 'Foundations of X'
    n = re.sub(
        r"^Introduction\s+(to|of)\s+(.+)$",
        r"Foundations of \2",
        n,
        flags=re.IGNORECASE
    )

    return n
def load_category_order(path: Path, allowed_categories):
    order = {}
    current_category = None

    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw = line
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("[") and line.endswith("]"):
            cat = line[1:-1]
            if cat not in allowed_categories:
                raise ValueError(
                    f"{path.name}:{lineno} Invalid category '{cat}'"
                )
            if cat in order:
                raise ValueError(
                    f"{path.name}:{lineno} Duplicate category block '{cat}'"
                )
            order[cat] = []
            current_category = cat
            continue

        if current_category is None:
            raise ValueError(
                f"{path.name}:{lineno} Course listed outside category block: '{raw}'"
            )

        if " " in line or "\t" in line:
            raise ValueError(
                f"{path.name}:{lineno} Invalid course code '{line}'"
            )

        order[current_category].append(line)

    return order

def parse_course(path: Path):
    soup = TexSoup(path.read_text(encoding="utf-8"))

    code = get_scalar(soup, "CourseCode", path.name)
    raw_name = get_scalar(soup, "CourseName", code)
    normalized_name = normalize_course_name(raw_name)
    name = format_course_title(normalized_name)
    category = get_scalar(soup, "CourseCategory", code)
    ctype = get_scalar(soup, "CourseType", code)
    ltpx_node = soup.find("CourseLTPXHours")
    if not ltpx_node:
        raise ValueError(f"{code}: Missing \\CourseLTPXHours")
    args = [str(arg).strip() for arg in ltpx_node.args]

    if len(args) != 4:
        raise ValueError(
            f"{code}: \\CourseLTPXHours must have 4 arguments (L,T,P,X)"
        )

    L, T, P, X = args
    C = get_scalar(soup, "CourseCredits", code)

    prereq = get_scalar(soup, "CoursePrerequisite", code)


    if category not in ALLOWED_CATEGORIES:
        raise ValueError(f"{code}: Invalid category {category}")

    if ctype not in ALLOWED_TYPES:
        raise ValueError(f"{code}: Invalid type {ctype}")
     # ---------- Course Description ----------
    desc_node = soup.find("CourseDescription")
    if not desc_node:
        raise ValueError(f"{code}: Missing \\CourseDescription")

    description = " ".join(
        "".join(str(x) for x in desc_node.contents).split()
    )
    # ---------- Course Objectives ----------
    obj_node = soup.find("CourseObjectives")
    if not obj_node:
        raise ValueError(f"{code}: Missing \\CourseObjectives")

    objectives_tex = "".join(str(x) for x in obj_node.contents).strip()

    if not objectives_tex:
        raise ValueError(f"{code}: Empty \\CourseObjectives")
    # ---------- Course Outcomes ----------
    outcomes_node = soup.find("CourseOutcomes")
    if not outcomes_node:
        raise ValueError(f"{code}: Missing \\CourseOutcomes")

    outcomes = []
    for item in outcomes_node.find_all("item"):
        outcomes.append("".join(str(x) for x in item.contents).strip())
    # ---------- NBA Articulation ----------
    nba_node = soup.find("CourseNBAArticulation")
    if not nba_node:
        raise ValueError(f"{code}: Missing \\CourseNBAArticulation")

    nba_rows = []
    for block in nba_node.contents:
        text = str(block).strip()
        if text.startswith("{") and text.endswith("}"):
            row = [x.strip() for x in text[1:-1].split(",")]
            nba_rows.append(row)

    if len(outcomes) != len(nba_rows):
        raise ValueError(
            f"{code}: Outcomes={len(outcomes)} NBA rows={len(nba_rows)}"
        )

    for i, row in enumerate(nba_rows, 1):
        if len(row) != NBA_COLS:
            raise ValueError(
                f"{code}: NBA row {i} has {len(row)} columns (expected {NBA_COLS})"
            )
    # ---------- ABET Articulation ----------
    abet_node = soup.find("CourseABETArticulation")
    if not abet_node:
        raise ValueError(f"{code}: Missing \\CourseABETArticulation")
    abet_rows = []
    for block in abet_node.contents:
        text = str(block).strip()
        if text.startswith("{") and text.endswith("}"):
            row = [x.strip() for x in text[1:-1].split(",")]
            abet_rows.append(row)
    if len(outcomes) != len(abet_rows):
        raise ValueError(
            f"{code}: Outcomes={len(outcomes)} ABET rows={len(abet_rows)}"
        )
    for i, row in enumerate(abet_rows, 1):
        if len(row) != ABET_COLS:
            raise ValueError(
                f"{code}: ABET row {i} has {len(row)} columns (expected {ABET_COLS})"
            )
    # ---------- Course References ----------
    ref_node = soup.find("CourseReferences")
    if not ref_node:
        raise ValueError(f"{code}: Missing \\CourseReferences")
    references_tex = "".join(str(x) for x in ref_node.contents).strip()
    if not references_tex:
        raise ValueError(f"{code}: Empty \\CourseReferences")
    # ---------- Object definition for return ----------
    course = Course(
        code=code,
        name=name,
        category=category,
        ctype=ctype,
        L=L,
        T=T,
        P=P,
        X=X,
        C=C,
        prereq=prereq,
        description=description,
        objectives_tex=objectives_tex,
        outcomes=outcomes,
        nba_rows=nba_rows,
        abet_rows=abet_rows,
        references_tex=references_tex,
    )
    return course


def emit_nba_longtblr(course):
    lines = []
    lines.append(r"\par") 
    lines.append(r"\noindent\textbf{Articulation Matrix CO to PO, PSO}")

    # The block below must be appended as a continuous string or 
    # consecutive lines without any \par or empty strings between them.
    lines.append(r"\begin{longtblr}[")
    lines.append(r"  entry = none, caption = {}, label = none")
    lines.append(r"]{")
    lines.append(rf"  colspec = {{| X[1.2,c,m] | *{{{PO_COUNT}}}{{X[0.6, c,m] |}} *{{{PSO_COUNT}}}{{X[0.6, c,m] |}} }},")
    lines.append(r"  hlines = {0.5pt}, row{1,2} = {font=\bfseries}, rowhead = 2,")
    lines.append(r"  abovesep = 0pt, belowsep = 0pt, rowsep = 1.5pt,  font = \small") 
    lines.append(r"}") 

    # Header Row 1 - Note the corrected ampersand counts
    header_row = (
        rf"\SetCell[r=2]{{c}} CO & " 
        rf"\SetCell[c={PO_COUNT}]{{c}} PO " + "& " * (PO_COUNT - 1) + " & " +
        rf"\SetCell[c={PSO_COUNT}]{{c}} PSO " + "& " * (PSO_COUNT - 2) + 
        r"\\"
    )
    lines.append(header_row)

    # Header Row 2
    po_indices = " & ".join(str(i + 1) for i in range(PO_COUNT))
    pso_indices = " & ".join(str(i + 1) for i in range(PSO_COUNT))
    lines.append(rf" & {po_indices} & {pso_indices} \\")

    # Data Rows
    for i, row in enumerate(course.nba_rows, 1):
        values = " & ".join(row)
        lines.append(rf"CO{i} & {values} \\")

    lines.append(r"\end{longtblr}")
    return lines

def emit_abet_longtblr(course):
    lines = []
    # Scope font size safely
    lines.append(r"\par") 
    lines.append(r"\noindent\textbf{Articulation Matrix CO to SO, PSO}")

    # ---- longtblr start ----
    lines.append(
        r"\begin{longtblr}["
        r" entry = none,"
        r" caption = {},"
        r" label = none"
        r"]{"
        rf"colspec = {{| X[1.2,c,m] | *{{{SO_COUNT}}}{{X[0.6,c,m] |}} *{{{PSO_COUNT}}}{{X[0.6,c,m] |}} }},"
        r"  hlines = {0.5pt},"
        r"  row{1,2} = {font=\bfseries},"
        r" rowhead = 2,"
        r" abovesep = 0pt,"
        r" belowsep = 0pt,"
        r" font = \small,"
        r"}"
    )

    # ---------- HEADER ROW 1 (MERGED GROUP HEADERS) ----------
    abet_header_row = (
        rf"\SetCell[r=2]{{c}} CO & " 
        rf"\SetCell[c={SO_COUNT}]{{c}} SO & " + "& " * (SO_COUNT - 1) +
        rf"\SetCell[c={PSO_COUNT}]{{c}} PSO & " + "& " * (PSO_COUNT - 2) + 
        r"\\"
    )
    lines.append(abet_header_row)

    # ---------- HEADER ROW 2 (INDICES) ----------
    so_indices = " & ".join(str(i + 1) for i in range(SO_COUNT))
    pso_indices = " & ".join(str(i + 1) for i in range(PSO_COUNT))

    # IMPORTANT: leading '&' aligns under CO column
    lines.append(
        rf" & {so_indices} & {pso_indices} \\"
    )

    # ---------- DATA ROWS ----------
    for i, row in enumerate(course.abet_rows, 1):
        po_vals = row[:SO_COUNT]
        pso_vals = row[SO_COUNT:SO_COUNT + PSO_COUNT]

        values = " & ".join(po_vals + pso_vals)
        lines.append(rf"CO{i} & {values} \\")

    # ---------- CLOSE TABLE ----------
    lines.append(r"\end{longtblr}")
    return lines

def generate_a4_body(courses):
    tex = []

    generated_on = datetime.now().strftime("%Y-%m-%d %H:%M")
    course_count = len(courses)

    tex.append("% ==================================================")
    tex.append("% AUTO-GENERATED FILE - DO NOT EDIT")
    tex.append("% GENERATED-BY : scripts/process_courses.py")
    tex.append("% VERSION      : v1.0")
    tex.append("% VIEW         : A4")
    tex.append(f"% COURSE_COUNT : {course_count}")
    tex.append(f"% GENERATED_ON : {generated_on}")
    tex.append("% CONTENT-ONLY FILE - NO PACKAGES, NO MACROS")
    tex.append("% ==================================================")
    tex.append("")
    for course in courses:
        outcomes = course.outcomes  
        tex.append(rf"\BeginCourse{{{course.code}}}")
         # ---------- Course Title----------
        tex.append(rf"\CourseTitle{{{course.code}}}{{{course.name}}}")
         # ---------- Course LTPC Table----------
        tex.append(
            rf"\CourseMetaTable{{{course.code} {course.name}}}"
            rf"{{{course.L}}}{{{course.T}}}{{{course.P}}}{{{course.X}}}{{{course.C}}}"
            rf"{{{course.prereq}}}"
            rf"{{{course.category}/{course.ctype}}}"
        )
        # ---------- Course Description ----------
        tex.append(r"\par \noindent \textbf{Course Description} \par \noindent")
        tex.append(course.description)
        # ---------- Course Objectives ----------
        tex.append(
            r"\par \noindent\textbf{Course Objectives}"
        )
        tex.append(course.objectives_tex)
        # ---------- Course Outcomes ----------
        tex.append(r"\par")
        tex.append(r"\noindent")
        tex.append(r"\textbf{Course Outcomes}")
        tex.append(r"\begin{enumerate}[label=\textbf{CO\arabic*:}, leftmargin=*, nosep, topsep=0pt]")
        for co in outcomes:
            tex.append(rf"\item {co}")
        tex.append(r"\end{enumerate}")
        # ---------- NBA Articulation ----------
        tex.extend(emit_nba_longtblr(course))
        # ---------- ABET Articulation ----------
        tex.extend(emit_abet_longtblr(course))
        # ---------- Textbooks & References ------
        tex.append(r"\par ")
        tex.append(r"\noindent")
        tex.append(course.references_tex)      

    FORBIDDEN = (
        "\\usepackage",
        "\\newcommand",
        "\\def",
        "\\setcounter",
        "\\ExplSyntaxOn",
    )

    for line in tex:
        stripped = line.strip()
        if stripped.startswith(FORBIDDEN):
            raise ValueError(
                f"Forbidden LaTeX command in generated body.tex: {stripped}"
            )

    out_file = OUT_DIR / "body.tex"
    out_file.write_text("\n".join(tex), encoding="utf-8")
    print(f"Generated {out_file}")

def main():
    print("Starting course processing...")

    course_files = sorted(COURSES_DIR.glob("**/*.tex"))
    print(f"Found {len(course_files)} course files")

    courses = []
    for path in course_files:
        try:
            course = parse_course(path)
            courses.append(course)
            print(f"✓ Parsed {course.code}")
        except Exception as e:
            print(f"✗ ERROR in {path.name}: {e}")
            sys.exit(1)

    print("All courses parsed successfully.")

    # ----------------------------------------
    # Load category-based order file
    # ----------------------------------------
    order_file = ROOT / "config" / "course-order-a4.txt"
    category_order = load_category_order(order_file, ALLOWED_CATEGORIES)
    codes = [c.code for c in courses]
    duplicates = {c for c in codes if codes.count(c) > 1}
    if duplicates:
        raise ValueError(f"Duplicate course codes detected: {sorted(duplicates)}")

    # Map course code -> full course tuple
    course_map = {c.code: c for c in courses}

    ordered_courses = []
    seen = set()

    for category, codes in category_order.items():
        for code in codes:
            if code not in course_map:
                raise ValueError(
                    f"Order file references missing course: {code}"
                )

            course = course_map[code]

            if course.category != category:
                raise ValueError(
                    f"Category mismatch for {code}: "
                    f"order={category}, latex={course.category}"
                )

            ordered_courses.append(course)
            seen.add(code)

    # ----------------------------------------
    # Guardrails: completeness + uniqueness
    # ----------------------------------------
    extra = [c for c in course_map if c not in seen]
    if extra:
        raise ValueError(
            f"Courses not listed in order file: {extra}"
        )

    print(f"Using category-based order from {order_file}")
    print(f"Ordered {len(ordered_courses)} courses")

    generate_a4_body(ordered_courses)


if __name__ == "__main__":
    main()