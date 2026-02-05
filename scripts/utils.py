import re
from typing import Optional
from scripts.patterns import SECTION_TITLE_MAP

# Helper to ensure consistent key generation across all stages
def get_section_key(title: str) -> str:
    """Transforms 'COURSE DESCRIPTION' into 'course_description'"""
    return title.lower().replace(" ", "_")

def normalize_line_endings(text: str) -> str:
    """Stage-0 Utility: Standardizes text for cross-platform parsing."""
    if not text:
        return ""
    # Handle Windows (\r\n) and old Mac (\r) to standard Unix (\n)
    return text.replace('\r\n', '\n').replace('\r', '\n')

def get_clean_section_title(line: str) -> Optional[str]:
    """
    Stage-1 Utility: Detects if a line is a Verbatim R2025 Section Header.
    Returns the Canonical Key (e.g., 'course_topics') or None.
    """
    # Remove Markdown symbols like '###' and leading/trailing whitespace
    clean = line.strip().lstrip('#').strip().upper()
    
    # Check against our Stage-1 Verbatim Registry in patterns.py
    if clean in SECTION_TITLE_MAP:
        return SECTION_TITLE_MAP[clean]
    return None

def extract_between(text: str, start_marker: str, end_marker: Optional[str]) -> str:
    """
    General Utility: Extracts text block between two markers.
    Used for partitioning the Header and Footer zones.
    """
    try:
        start_idx = text.find(start_marker)
        if start_idx == -1:
            return ""
        
        start_pos = start_idx + len(start_marker)
        
        if not end_marker:
            return text[start_pos:].strip()
            
        end_pos = text.find(end_marker, start_pos)
        if end_pos == -1:
            return text[start_pos:].strip()
            
        return text[start_pos:end_pos].strip()
    except Exception:
        return ""

def strip_markdown_formatting(text: str) -> str:
    """Removes bold/italic symbols for clean data extraction."""
    return text.replace("**", "").replace("__", "").replace("*", "").strip()

def normalize_syllabus_text(text: str, is_title: bool = False) -> str:
    """
    Common normalization logic for all syllabus strings.
    - Preserves words that are already in ALL CAPS (Acronyms).
    - Applies grammatical Title Case to other words if is_title=True.
    - Standardizes replacements like Lab -> Laboratory and & -> and.
    """
    if not text:
        return ""

    # Rule 1: Replace '&' with 'and'
    text = text.replace("&", " and ")

    # Rule 2: Replace 'Lab' with 'Laboratory' (using word boundaries)
    text = re.sub(r'\bLab\b', 'Laboratory', text, flags=re.IGNORECASE)

    # Rule 3: "Introduction to/of" -> "Fundamentals of"
    text = re.sub(r'\bIntroduction\s+(to|of)\b', 'Fundamentals of', text, flags=re.IGNORECASE)

    # Rule 4: Clean whitespaces
    text = " ".join(text.split())

    if is_title:
        words = text.split() # Don't lower() here yet, we need to check original case
        minor_words = {'of', 'to', 'and', 'for', 'with', 'in', 'on', 'at', 'the', 'a', 'an'}
        
        result = []
        for i, word in enumerate(words):
            # RULE: If word is already ALL CAPS and length > 1, preserve it (e.g., VLSI, DSP)
            if word.isupper() and len(word) > 1:
                result.append(word)
                continue
                
            word_lower = word.lower()
            # Capitalize first word or major words
            if i == 0 or word_lower not in minor_words:
                result.append(word_lower.capitalize())
            else:
                result.append(word_lower)
        text = " ".join(result)
    
    # Rule 5: Final Sanitization for JSON/TeX
    text = text.replace('"', "''") 

    return text
def escape_latex(text):
    """
    Standard LaTeX escaping utility to prevent compilation errors.
    """
    if text is None:
        return ""
    text = " ".join(text.split())
    
    # Map of special LaTeX characters to their escaped versions
    # Order matters: we escape backslash first so we don't escape our own escapes!
    map_chars = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    
    # Regex to find any of these characters
    regex = re.compile('|'.join(re.escape(str(key)) for key in map_chars.keys()))
    
    return regex.sub(lambda mo: map_chars[mo.group()], str(text))