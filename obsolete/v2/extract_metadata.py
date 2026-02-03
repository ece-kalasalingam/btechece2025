import re
from typing import Optional
from contracts import MarkdownSection, ValidationError, CourseMetadata, CourseCategory, CourseType


META_RE = {
    "category": re.compile(r"course\s+category\s*:\s*(\w+)", re.I),
    "type": re.compile(r"course\s+type\s*:\s*(\S+)", re.I),
    "ltpxc": re.compile(
    r"l\s*-\s*t\s*-\s*p\s*-\s*x\s*-\s*c\s*:\s*"
    r"(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)",
    re.I
    ),
    "prereq": re.compile(r"prerequisite\s*:\s*(.*)", re.I),
    "coreq": re.compile(r"corequisite\s*:\s*(.*)", re.I),
}

def clean_req(match: Optional[re.Match]) -> Optional[str]:
        if not match:
            return None
        val = match.group(1).strip()
        # If the text says "None", "Nil", or is empty, treat as empty string
        if val.lower() in ["none", "nil", "n/a", ""]:
            return ""
        return val

def extract_course_metadata(
    course_code: str,
    sections: list[MarkdownSection],
) -> CourseMetadata:

    meta_sec = next(
        (s for s in sections if s.title.lower() == "course metadata"),
        None
    )

    if not meta_sec:
        raise ValidationError(
            course_code,
            "META-MISSING",
            "Course Metadata section is missing"
        )

    text = meta_sec.body

    m_cat = META_RE["category"].search(text)
    m_typ = META_RE["type"].search(text)
    m_ltpxc = META_RE["ltpxc"].search(text)
    m_prereq = META_RE["prereq"].search(text)
    m_coreq = META_RE["coreq"].search(text)

    if not m_cat:
        raise ValidationError(course_code, "META-CATEGORY-MISSING", "Course Category not declared")
    if not m_typ:
        raise ValidationError(course_code, "META-TYPE-MISSING", "Course Type not declared")
    if not m_ltpxc:
        raise ValidationError(course_code, "META-LTPXC-MISSING", "L-T-P-X-C  not declared")
    prerequisite = clean_req(m_prereq)
    corequisite = clean_req(m_coreq)
    try:
        category = CourseCategory(m_cat.group(1).upper())
    except ValueError:
        raise ValidationError(course_code, "META-CATEGORY-INVALID", m_cat.group(1))

    try:
        course_type = CourseType(m_typ.group(1).upper())
    except ValueError:
        raise ValidationError(course_code, "META-TYPE-INVALID", m_typ.group(1))

    groups = m_ltpxc.groups()
    L, T, P, X = map(int, groups[:4])
    C = float(groups[4])
    total_hours = 15 * (L + T + P + X)

    if total_hours == 0:
        raise ValidationError(course_code, "META-HOURS-ZERO", "Total LTPX hours cannot be zero")

    return CourseMetadata(
        category=category,
        course_type=course_type,
        l=L,
        t=T,
        p=P,
        x=X,
        ltpxtotal_hours=total_hours,
        c=C,
        prerequisite=prerequisite,
        corequisite=corequisite,
    )