import re

# Stage 1: Mandatory Sequence
COURSE_SECTION_SEQUENCE = [
    "COURSE DESCRIPTION",
    "COURSE OBJECTIVES",
    "COURSE OUTCOMES",
    "ARTICULATION MATRIX",
    "COURSE TOPICS",
    "SELF-LEARNING TOPICS",
    "TEXTBOOK",
    "REFERENCES",
    "ASSESSMENT SCHEMES",
    "RUBRICS"
]

# Map verbatim titles to normalized keys
SECTION_TITLE_MAP = {title: title.lower().replace(" ", "_") for title in COURSE_SECTION_SEQUENCE}

# Stage 2A: Metadata Patterns
META_PATTERNS = {
    "category": re.compile(r"^category\s*:\s*([A-Z]+)$", re.I | re.M),
    "type": re.compile(r"^type\s*:\s*([\w-]+)$", re.I | re.M),
    "ltpxc": re.compile(r"(\d)\s*-\s*(\d)\s*-\s*(\d)\s*-\s*(\d)\s*-\s*(\d(?:\.\d)?)$", re.M),
}