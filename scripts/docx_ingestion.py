import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

LABEL_COURSE_DESCRIPTION = "course description"
LABEL_COURSE_OBJECTIVE = "course objective"
LABEL_COURSE_OUTCOMES = "course outcomes"
LABEL_MAPPING = "mapping of course outcomes"
LABEL_COURSE_TOPICS = "course topics"
LABEL_LAB_EXPERIMENTS = "laboratory experiments"
LABEL_TEXTBOOKS = "textbooks"
LABEL_REFERENCES = "references"


def _norm(text: str) -> str:
    text = text.replace("\u00a0", " ")
    return " ".join(text.strip().split())


def _latex_safe(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "and")
        .replace("%", " percent")
        .replace("#", "")
        .replace("_", " ")
    )


def _read_docx_lines(docx_path: Path) -> List[str]:
    with zipfile.ZipFile(docx_path) as zf:
        xml = zf.read("word/document.xml")

    root = ET.fromstring(xml)
    lines: List[str] = []

    for para in root.findall(f".//{W_NS}p"):
        text = "".join(t.text for t in para.findall(f".//{W_NS}t") if t.text)
        text = _norm(text)
        if text:
            lines.append(text)
    return lines


def _find_index(lines: List[str], prefix: str) -> int:
    target = prefix.lower()
    for i, line in enumerate(lines):
        if line.lower().startswith(target):
            return i
    return -1


def _next_meaningful(lines: List[str], start: int) -> str:
    skip = {":", "don’t fill any one of this red coloured rows", "don't fill any one of this red coloured rows"}
    for i in range(start, len(lines)):
        candidate = lines[i].strip()
        if not candidate:
            continue
        if candidate.lower() in skip:
            continue
        return candidate
    return ""


def _slice_between_markers(lines: List[str], start_marker: str, end_markers: List[str]) -> List[str]:
    start_idx = _find_index(lines, start_marker)
    if start_idx == -1:
        return []
    start_idx += 1
    end_idx = len(lines)
    lower_ends = [m.lower() for m in end_markers]
    for i in range(start_idx, len(lines)):
        cur = lines[i].lower()
        if any(cur.startswith(m) for m in lower_ends):
            end_idx = i
            break
    return [line for line in lines[start_idx:end_idx] if line.strip()]


def _extract_ltpxc(lines: List[str]) -> Tuple[int, int, int, int, float]:
    nums: List[float] = []
    for i, line in enumerate(lines):
        if line.upper() == "L" and i + 4 < len(lines):
            if [lines[i + j].upper() for j in range(5)] == ["L", "T", "P", "X", "C"]:
                for token in lines[i + 5:]:
                    token = token.strip()
                    if re.fullmatch(r"\d+(?:\.\d+)?", token):
                        nums.append(float(token))
                        if len(nums) == 5:
                            break
                break
    if len(nums) != 5:
        return 0, 0, 0, 0, 0.0
    return int(nums[0]), int(nums[1]), int(nums[2]), int(nums[3]), float(nums[4])


def _map_category(raw: str) -> str:
    text = raw.lower()
    if "foundation" in text:
        return "FCM"
    if "skill" in text:
        return "SEM"
    if "program core" in text or "programme core" in text or "engineering core" in text:
        return "PCM"
    return "PCM"


def _map_type(raw: str) -> str:
    text = raw.lower()
    if "practical" in text or "laboratory" in text:
        return "PC"
    if "integrated" in text:
        return "IC-T"
    if "theory" in text:
        return "TC"
    if "skill" in text:
        return "SC"
    return "SC"


def _pick_title(lines: List[str], fallback_code: str) -> str:
    ignore = {"course name", "course title"}
    for line in lines[:12]:
        low = line.lower()
        if low in ignore:
            continue
        if re.fullmatch(r"[A-Z]{2,}\d+[A-Z0-9]*", line):
            continue
        if len(line) >= 4:
            return line
    return fallback_code


def _extract_objectives(block: List[str]) -> List[str]:
    result = []
    for line in block:
        low = line.lower()
        if low.startswith("the objectives of this course"):
            continue
        result.append(_latex_safe(line))
    return result


def _extract_outcomes(lines: List[str]) -> Dict[int, str]:
    block = _slice_between_markers(
        lines,
        LABEL_COURSE_OUTCOMES,
        [LABEL_MAPPING, LABEL_COURSE_TOPICS, LABEL_TEXTBOOKS],
    )
    outcomes: Dict[int, str] = {}
    i = 0
    while i < len(block):
        m = re.fullmatch(r"CO(\d+)", block[i], re.IGNORECASE)
        if not m:
            i += 1
            continue
        co_id = int(m.group(1))
        j = i + 1
        text = ""
        while j < len(block):
            token = block[j].strip()
            if token == ":":
                j += 1
                continue
            if re.fullmatch(r"CO\d+", token, re.IGNORECASE):
                break
            if token.lower().startswith("fill the cos"):
                break
            text = token
            break
        if text:
            outcomes[co_id] = text
        i = max(j, i + 1)
    return outcomes


def _hml_to_int(value: str) -> int:
    v = value.strip().upper()
    if v == "H":
        return 3
    if v == "M":
        return 2
    if v == "L":
        return 1
    if v in {"1", "2", "3"}:
        return int(v)
    return 0


def _extract_articulation(lines: List[str], max_co: int) -> Dict[int, Dict[str, int]]:
    block = _slice_between_markers(
        lines,
        LABEL_MAPPING,
        [LABEL_COURSE_TOPICS, LABEL_LAB_EXPERIMENTS, LABEL_TEXTBOOKS],
    )
    rows: Dict[int, Dict[str, int]] = {}
    i = 0
    while i < len(block):
        m = re.fullmatch(r"CO(\d+)", block[i], re.IGNORECASE)
        if not m:
            i += 1
            continue
        co_id = int(m.group(1))
        i += 1
        values: List[int] = []
        while i < len(block) and not re.fullmatch(r"CO\d+", block[i], re.IGNORECASE):
            cur = block[i].strip()
            if cur.lower().startswith("course topics"):
                break
            score = _hml_to_int(cur)
            if score > 0:
                values.append(score)
            i += 1

        if 1 <= co_id <= max_co:
            mapped: Dict[str, int] = {}
            for idx, score in enumerate(values[:11], start=1):
                mapped[f"PO{idx}"] = score
            pso_start = 11
            for idx, score in enumerate(values[pso_start:pso_start + 3], start=1):
                mapped[f"PSO{idx}"] = score
            if "PO1" not in mapped:
                mapped["PO1"] = 1
            if "PSO1" not in mapped:
                mapped["PSO1"] = 1
            mapped["SO1"] = max(mapped.get("PO1", 1), 1)
            rows[co_id] = mapped
    return rows


def _split_labeled_entries(block: List[str], prefix: str) -> List[List[str]]:
    entries: List[List[str]] = []
    current: List[str] = []
    pat = re.compile(rf"^{re.escape(prefix)}\d+$", re.IGNORECASE)
    for line in block:
        if pat.match(line):
            if current:
                entries.append(current)
            current = []
            continue
        current.append(line)
    if current:
        entries.append(current)
    return entries


def _year_and_edition(text: str) -> Tuple[str, str]:
    y = re.search(r"(19|20)\d{2}", text)
    year = int(y.group(0)) if y else 2020
    year = max(2015, min(2026, year))
    e = re.search(r"(\d+(?:st|nd|rd|th)\s+Edition)", text, re.IGNORECASE)
    edition = e.group(1) if e else "1st Edition"
    return str(year), edition


def _extract_books(
    lines: List[str],
    start_marker: str,
    end_markers: List[str],
    label_prefix: str,
    allow_urls: bool = True,
) -> List[str]:
    block = _slice_between_markers(lines, start_marker, end_markers)
    entries = _split_labeled_entries(block, label_prefix)
    numbered: List[str] = []
    for i, entry in enumerate(entries, start=1):
        clean = [x.strip() for x in entry if x.strip()]
        if not clean:
            continue
        if len(clean) == 1 and ("http://" in clean[0].lower() or "https://" in clean[0].lower()):
            if not allow_urls:
                continue
            numbered.append(f"{i}. {clean[0]}")
            continue
        authors = _latex_safe(clean[0] if len(clean) > 0 else "Unknown")
        title = _latex_safe(clean[1] if len(clean) > 1 else "Untitled")
        publisher = _latex_safe(clean[2] if len(clean) > 2 else "Unknown Publisher")
        year_line = clean[3] if len(clean) > 3 else "2020 (1st Edition)"
        year, edition = _year_and_edition(year_line)
        numbered.append(f'{i}. {authors}, "{title}", {edition}, {publisher}, {year}.')
    return numbered


def _extract_syllabus(lines: List[str]) -> str:
    topic_block = _slice_between_markers(lines, LABEL_COURSE_TOPICS, [LABEL_LAB_EXPERIMENTS, LABEL_TEXTBOOKS, LABEL_REFERENCES])
    lab_block = _slice_between_markers(lines, LABEL_LAB_EXPERIMENTS, [LABEL_TEXTBOOKS, LABEL_REFERENCES])
    out: List[str] = ["legacy_docx_source: true", ""]

    i = 0
    while i < len(topic_block):
        m = re.fullmatch(r"Unit\s*(\d+)\s*:?", topic_block[i], re.IGNORECASE)
        if not m:
            i += 1
            continue
        unit_no = int(m.group(1))
        unit_title = _latex_safe(topic_block[i + 1] if i + 1 < len(topic_block) else f"Unit {unit_no}")
        desc = _latex_safe(topic_block[i + 2] if i + 2 < len(topic_block) else "")
        out.append(f"### Unit {unit_no}: {unit_title}")
        if desc:
            out.append(desc)
        out.append("")
        i += 3

    if lab_block:
        out.append("### Laboratory Experiments")
        idx = 1
        i = 0
        while i < len(lab_block):
            if re.fullmatch(r"\d+", lab_block[i]):
                if i + 1 < len(lab_block):
                    out.append(f"{idx}. {_latex_safe(lab_block[i + 1])}")
                    idx += 1
                i += 2
            else:
                i += 1
        out.append("")
    return "\n".join(out).strip()


def convert_docx_to_normalized_markdown(course_code: str, docx_path: Path) -> str:
    lines = _read_docx_lines(docx_path)
    if not lines:
        raise ValueError(f"No readable text found in {docx_path}")

    title = _pick_title(lines, course_code)
    prerequisite = _latex_safe(_next_meaningful(lines, _find_index(lines, "Pre-requisite") + 1))
    category_raw = _next_meaningful(lines, _find_index(lines, "Course Category") + 1)
    type_raw = _next_meaningful(lines, _find_index(lines, "Course Type") + 1)
    category = _map_category(category_raw)
    course_type = _map_type(type_raw)
    l, t, p, x, c = _extract_ltpxc(lines)

    description_lines = _slice_between_markers(lines, LABEL_COURSE_DESCRIPTION, [LABEL_COURSE_OBJECTIVE, LABEL_COURSE_OUTCOMES])
    description = _latex_safe(" ".join(description_lines).strip() or "No description provided.")
    objectives = _extract_objectives(
        _slice_between_markers(lines, LABEL_COURSE_OBJECTIVE, [LABEL_COURSE_OUTCOMES, LABEL_MAPPING])
    )
    outcomes = _extract_outcomes(lines)
    if len(outcomes) > 6:
        outcomes = {k: outcomes[k] for k in sorted(outcomes.keys())[:6]}
    outcomes = {k: _latex_safe(v) for k, v in outcomes.items()}
    articulation_rows = _extract_articulation(lines, max_co=max(len(outcomes), 1))
    syllabus_text = _extract_syllabus(lines)

    textbooks = _extract_books(lines, LABEL_TEXTBOOKS, [LABEL_REFERENCES], "T", allow_urls=False)
    references = _extract_books(lines, LABEL_REFERENCES, [], "R", allow_urls=True)

    if not objectives:
        objectives = ["Understand key principles and apply them in engineering practice."]
    if not outcomes:
        outcomes = {1: "Demonstrate foundational competency in the subject area."}
    if not textbooks:
        textbooks = ['1. Unknown Author, "Course Textbook", 1st Edition, Unknown Publisher, 2020.']
    if not references:
        references = ['1. Unknown Author, "Reference Material", 1st Edition, Unknown Publisher, 2020.']

    articulation_lines: List[str] = []
    for co_id in sorted(outcomes.keys()):
        mapped = articulation_rows.get(co_id, {"PO1": 1, "PSO1": 1, "SO1": 1})
        parts = [f"{k}={v}" for k, v in mapped.items()]
        articulation_lines.append(f"- CO{co_id}: {', '.join(parts)}")

    output: List[str] = [
        f"# {title}",
        f"COURSE CODE: {course_code}",
        f"- Course Category: {category}",
        f"- Course Type: {course_type}",
        f"- L-T-P-X-C: {l}-{t}-{p}-{x}-{c:g}",
        f"- Pre-requisite: {prerequisite or 'None'}",
        "",
        "## COURSE DESCRIPTION",
        description,
        "",
        "## COURSE OBJECTIVES",
    ]
    output.extend(f"- {obj}" for obj in objectives)
    output.extend(["", "## COURSE OUTCOMES"])
    for _, outcome_text in sorted(outcomes.items()):
        output.append(f"- K2-AP: {outcome_text}")

    output.extend([
        "",
        "## SYLLABUS",
        syllabus_text,
        "",
        "## TEXTBOOKS",
    ])
    output.extend(textbooks)
    output.extend(["", "## REFERENCES"])
    output.extend(references)
    output.extend(["", "## ARTICULATION MATRIX"])
    output.extend(articulation_lines)
    output.extend([
        "",
        "## ASSESSMENT SCHEME",
        "Assessment follows department guidelines.",
        "",
        "## RUBRICS",
        "Rubrics are maintained in departmental records.",
        "",
        "---",
        "- Course Author: Department Curriculum Committee",
        "- BoS Approval: Jan/2025",
        "- Course Revision: 1.0",
    ])
    return "\n".join(output).strip() + "\n"
