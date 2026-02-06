import re
from scripts.contracts import COURSE_SECTION_SEQUENCE

# Map verbatim titles to normalized keys
# Extract 'title' from the dictionary before normalizing it
SECTION_TITLE_MAP = {
    item["title"].upper(): item["title"].lower().replace(" ", "_") 
    for item in COURSE_SECTION_SEQUENCE
}

# Metadata Patterns
META_PATTERNS = {
    "category": re.compile(r"^[ \t]*[-*]?\s*Course\s*Category\s*:\s*([A-Z]+)$", re.I | re.M),
    "type":     re.compile(r"^[ \t]*[-*]?\s*Course\s*Type\s*:\s*([\w-]+)$", re.I | re.M),
    "ltpxc":    re.compile(r"^[ \t]*[-*]?\s*L-T-P-X-C\s*:\s*(\d)\s*-\s*(\d)\s*-\s*(\d)\s*-\s*(\d)\s*-\s*(\d(?:\.\d)?)$", re.I | re.M),
}
COURSE_CODE_HEADER_PATTERN = re.compile(r"^COURSE\s*CODE\s*:\s*([A-Z0-9]+)$", re.I | re.M)
# Matches "Course Title: Digital Systems"
COURSE_TITLE_PATTERN = re.compile(r"^COURSE\s*TITLE\s*:\s*(.*)$", re.I | re.M)

# Matches "Prerequisite: CS101" or "Prerequisite: None"
PREREQ_PATTERN = re.compile(r"^\s*[-\*]?\s*PRE-?REQUISITE\s*:\s*(.*)$", re.I | re.M)

# Matches "Corequisite: EC202" or "Co-requisite: NIL"
COREQ_PATTERN = re.compile(r"^\s*[-\*]?\s*CO-?REQUISITE\s*:\s*(.*)$", re.I | re.M)

# Regex for Footer Governance (Structured Metadata at the bottom)
FOOTER_PATTERNS = {
    # Supports "- Course Author: ..."
    "course_author": re.compile(r"^[ \t]*[-*]?\s*Course\s*Author\s*:\s*(.*)$", re.I | re.M),
    
    # Flexible month name + / + 2 or 4 digit year
    "bos_date":      re.compile(r"^[ \t]*[-*]?\s*BoS\s*Approval\s*:\s*([a-zA-Z]+\.?/\d{2,4})$", re.I | re.M),
    
    # Matches "- Course Revision: 1.0"
    "course_revision":       re.compile(r"^[ \t]*[-*]?\s*Course\s*Revision\s*:\s*([\d\.]+)$", re.I | re.M),
    
    # Matches "- Course Level: 1"
    "course_level":  re.compile(r"^[ \t]*[-*]?\s*Course\s*Level\s*:\s*(\d+)$", re.I | re.M),
}