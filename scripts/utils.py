"""
SHARED DEFINITIONS
Common functions used across all pipeline stages.
"""
import re
from typing import List, Dict
from scripts.contracts import StructuredSection

def find_sections_by_title_pattern(
    structured_sections: List[StructuredSection],
    pattern: re.Pattern
) -> List[StructuredSection]:
    """Pure structural search by regex pattern."""
    return [s for s in structured_sections if pattern.search(s.section.title)]
