import re
from scripts.contracts import COURSE_SECTION_SEQUENCE

# Map verbatim titles to normalized keys
# Extract 'title' from the dictionary before normalizing it
SECTION_TITLE_MAP = {
    item["title"].upper(): item["title"].lower().replace(" ", "_") 
    for item in COURSE_SECTION_SEQUENCE
}

#LIST PATTERN (USED IN STAGE-4 GRAMMAR)
BULLET_LINE_PATTERN = re.compile(r"^\s*[-*•]\s+")
NUMBERED_LIST_PATTERN = re.compile(r"^\s*\d+\.\s+")
# Matches "K1: Course Outcome 1" or "K2: Course Outcome 2"
#CO_PATTERN = re.compile(r"^\s*-\s*K([1-6])\s*:\s+.+$")
CO_PATTERN = re.compile(
    r"^\s*-\s*K(?P<k_level>[1-3])-(?P<bloom>RE|UN|AP|AN|EV|CR)\s*:\s+.+$"
)

CO_INDEXED_BULLET_PATTERN = re.compile(
    r"^\s*-\s*CO\d+\s*:",
    re.IGNORECASE
)

# PATTERN FOR SPLITTING CO NUMBER AND TEXT IN STAAGE 5
#CO_SPLIT_PATTERN = re.compile(r"^K([1-6])\s*:\s*(.+)$")
CO_SPLIT_PATTERN = re.compile(
    r"^K([1-3])-(RE|UN|AP|AN|EV|CR)\s*:\s*(.+)$"
)

# PARAGRAPH PATTERN (USED IN STAGE-4 GRAMMAR)
PARAGRAPH_BULLET_START_PATTERN = re.compile(r"^[\s]*[-*•\d\.]")

# Metadata Patterns
META_PATTERNS = {
    "category": re.compile(r"^[ \t]*[-*]?\s*Course\s*Category\s*:\s*([A-Z]+)$", re.I | re.M),
    "type":     re.compile(r"^[ \t]*[-*]?\s*Course\s*Type\s*:\s*([\w-]+)$", re.I | re.M),
    "ltpxc":    re.compile(r"^[ \t]*[-*]?\s*L-T-P-X-C\s*:\s*(\d)\s*-\s*(\d)\s*-\s*(\d)\s*-\s*(\d)\s*-\s*(\d(?:\.\d)?)$", re.I | re.M),
}
COURSE_CODE_HEADER_PATTERN = re.compile(r"^COURSE\s*CODE\s*:\s*([A-Z0-9]+)$", re.I | re.M)
# Matches "Course Title: Digital Systems"
H1_PATTERN = re.compile(r"^#\s+(.+)$")
COURSE_TITLE_PATTERN = re.compile(r"^COURSE\s*TITLE\s*:\s*(.*)$", re.I | re.M)

# Matches "Prerequisite: CS101" or "Prerequisite: None"
PREREQ_PATTERN = re.compile(r"^\s*[-\*]?\s*PRE-?REQUISITE\s*:\s*(.*)$", re.I | re.M)

# Matches "Corequisite: EC202" or "Co-requisite: NIL"
COREQ_PATTERN = re.compile(r"^\s*[-\*]?\s*CO-?REQUISITE\s*:\s*(.*)$", re.I | re.M)

# Regex for Footer Governance (Structured Metadata at the bottom)
FOOTER_PATTERNS = {
    "course_author": re.compile(
        r"^[ \t]*[-*]?\s*Course\s*Author\s*:\s*([^\n\r]*)$",
        re.I | re.M
    ),
    "bos_date": re.compile(
        r"^[ \t]*[-*]?\s*BoS\s*Approval\s*:\s*([^\n\r]+)$",
        re.I | re.M
    ),
    "course_revision": re.compile(
        r"^[ \t]*[-*]?\s*Course\s*Revision\s*:\s*([^\n\r]+)$",
        re.I | re.M
    ),
}
UNIT_HEADING_PATTERN = re.compile(
    r"^###\s+Unit\s*(?P<number>\d+)(?:\s*[:\- ]\s*(?P<title>.*?))?\s*$",
    re.IGNORECASE | re.MULTILINE
)
THEORY_HEADER_PATTERN = re.compile(
    r"^####\s*Theory\s*$",
    re.IGNORECASE | re.MULTILINE
)
HOURS_PATTERN = re.compile(
    r"""
    ^\s*
    (?:[-*]\s*)?          # optional bullet
    Hours                 # literal Hours
    \s*
    [:=\-]?\s*            # optional separator :, =, -
    (?P<hours>\d+)        # capture integer hours
    \s*$
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE
)

PRACTICAL_HEADER_PATTERN = re.compile(
    r"^####\s*Experiments\s*$",
    re.IGNORECASE | re.MULTILINE
)

XACT_HEADER_PATTERN = re.compile(
    r"^####\s*X-Activities\s*$",
    re.IGNORECASE | re.MULTILINE
)
UNIT_CO_MAP_PATTERN = re.compile(
    r"^\s*-\s*COs\s*:\s*(CO\d+(?:\s*,\s*CO\d+)*)\s*$",
    re.IGNORECASE | re.MULTILINE
)
CO_NUMBER_PATTERN = re.compile(r"^CO(\d+)$", re.IGNORECASE)
PC_EXPERIMENT_CO_PATTERN = re.compile(
    r"^\s*[-*]\s*COs?\s*:\s*(CO\d+(?:\s*,\s*CO\d+)*)\s*$",
    re.IGNORECASE
)

ACTIVITY_TITLE_PATTERN = re.compile(
    r"^\s*[-*]\s*Title\s*:\s*(.+)$",
    re.IGNORECASE
)
DESCRIPTION_SUB_BULLET_PATTERN=re.compile(
    r"^\s+[-*]\s*Description\s*:\s*(.+)$",
    re.IGNORECASE
)

#syllabus content markdown patterns
TABLE_ROW_PATTERN = re.compile(r"^\s*\|.*\|\s*$")
#TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|\s*[-: ]+\|\s*$")
#TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$")
TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|(\s*:?-+:?\s*\|)+\s*$")
H3_PATTERN = re.compile(r"^###\s+.+$")
H4_PATTERN = re.compile(r"^####\s+.+$")
INVALID_HEADER_PATTERN = re.compile(r"^#{1,2}\s+|^#{5,}")
CODE_BLOCK_PATTERN = re.compile(r"^\s*```")
BLOCKQUOTE_PATTERN = re.compile(r"^\s*>")
#HTML_PATTERN = re.compile(r"<[^>]+>")
HTML_PATTERN = re.compile(r"</?[a-zA-Z][^>]*>")
PARAGRAPH_PATTERN = re.compile(r"^[^\s#|\-*•\d].+")
BLOCK_MATH_PATTERN = re.compile(r"\$\$")
LATEX_ENV_PATTERN = re.compile(r"\\begin\{")

# --- TEXTBOOKS GRAMMAR (Option-2: quoted title) ---

URL_PATTERN = re.compile(r'(https?://|www\.)', re.IGNORECASE)
TEXTBOOKS_NUMBERED_LINE_PATTERN = re.compile(r'^\s*(?P<num>\d+)\.\s+\S') 

ISBN_PATTERN = re.compile(
    r'(\bISBN\b|'
    r'\b97[89][-\s]?\d{1,5}[-\s]?\d{1,7}[-\s]?\d{1,7}[-\s]?\d\b|'
    r'\b\d{9}[\dX]\b)',
    re.IGNORECASE
)

PAGE_PATTERN = re.compile(
    r'(\bpp?\.\s*\d+|\bpages?\b|\b\d+\s*[--]\s*\d+\b)',
    re.IGNORECASE
)

BIBTEX_APA_PATTERN = re.compile(
    r'(^\s*@\w+\s*\{|\bdoi\s*:\b|\bretrieved\s+from\b|\(\s*\d{4}\s*\))',
    re.IGNORECASE | re.MULTILINE
)

FORBIDDEN_PHRASES = [
    "lecture notes prepared by faculty",
    "internet sources",
    "wikipedia",
    "latest edition",
    "international edition",
    "reprint",
]

QUOTE_PAIRS = {
    '"': '"',
    "'": "'",
    "“": "”",
    "‘": "’",
}
TEXTBOOK_PATTERN = re.compile(
    r"""
    ^\s*\d+\.\s*
    (?P<authors>.+?)\s*,\s*
    ["“'](?P<title>[^"”']+)["”']\s*,\s*
    (?P<publisher>[^,]+?)\s*,\s*
    (?P<year>\d{4})\.?\s*$
    """,
    re.VERBOSE
)
STANDARD_DOMAINS = (
    "ieee.org",
    "iso.org",
    "iec.ch",
    "itu.int",
    "ansi.org",
    "rfc-editor.org",
)
