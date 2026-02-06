import re
from typing import Optional, Any, TypeVar
from scripts.patterns import SECTION_TITLE_MAP

from pathlib import Path
import subprocess
COURSE_CODE_PATTERN = re.compile(r"^[A-Z0-9_]+$")

FORBIDDEN_SUBSTRINGS = {
    "/", "\\", "..", ".", ":", "~"
}

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

def escape_latex(text: str) -> str:
    """
    Optimized Single-Pass LaTeX Escaper.
    Prevents double-escaping and ordering bugs.
    """
    if not text:
        return ""
        
    # Standardize whitespace
    text = " ".join(text.split())

    # Map of special characters
    map_chars = {
        '\\': r'\textbackslash{}',
        '&':  r'\&',
        '%':  r'\%',
        '$':  r'\$',
        '#':  r'\#',
        '_':  r'\_',
        '{':  r'\{',
        '}':  r'\}',
        '~':  r'\textasciitilde{}',
        '^':  r'\textasciicircum{}',
    }

    # Create a regex pattern that matches any of the keys in map_chars
    # re.escape(key) is used to handle characters like '^' or '$' in the regex itself
    pattern = re.compile('|'.join(re.escape(key) for key in map_chars.keys()))

    # The lambda function looks up the match in the map
    return pattern.sub(lambda match: map_chars[match.group()], text)

T = TypeVar('T', bound=Any)
def recursive_escape_latex(data: T) -> T:
    """
    Recursively walks through data and escapes strings for LaTeX.
    The TypeVar T ensures that if a dict goes in, the linter expects a dict out.
    """
    if isinstance(data, dict):
        return {k: recursive_escape_latex(v) for k, v in data.items()} # type: ignore
    elif isinstance(data, list):
        return [recursive_escape_latex(i) for i in data] # type: ignore
    elif isinstance(data, str):
        return escape_latex(data) # type: ignore
    return data
def get_git_metadata(file_path: Path):
    """
    Returns machine-readable Git metadata:
    (commit_count, last_commit_date_iso)
    """
    try:
        # 1. Document Version: Total commit count for this specific file
        count_cmd = ["git", "rev-list", "--count", "HEAD", "--", str(file_path)]
        count = subprocess.check_output(count_cmd, stderr=subprocess.DEVNULL, encoding="utf-8").strip()
        doc_version = count if count and count != "0" else "N/A"
        
        # 2. Git Hash: Hash Signature  of the very last commit and date of the commit in ISO format (YYYY-MM-DD)
        hash_cmd = ["git", "log", "-1", "--format=%h %as", "--", file_path]
        commit_out = subprocess.check_output(hash_cmd, stderr=subprocess.DEVNULL, encoding="utf-8").strip()
        if commit_out:
            doc_git_hash, doc_date = commit_out.split(" ", 1)
        else:
            doc_git_hash, doc_date = "N/A", "N/A"
        # If the file is new and not yet committed, commit details will be empty
        if not doc_date:
            doc_date = "N/A"
        if not doc_git_hash:
            doc_git_hash = "N/A"

    except Exception:
        # Fallback for local environments without Git or fresh files
        return "N/A", "N/A", "N/A"

    return doc_version, doc_date, doc_git_hash
def get_git_hash(file_path):
    # Returns the unique 7-character identifier for the current version
    return subprocess.check_output(
        ['git', 'rev-parse', '--short', 'HEAD'], 
        encoding='utf-8'
    ).strip()
def validate_course_code(code: str) -> None:
    """
    Validates course code for security and structural correctness.
    Raises ValueError if invalid.
    """
    if not code:
        raise ValueError("Empty course code")

    if any(bad in code for bad in FORBIDDEN_SUBSTRINGS):
        raise ValueError(f"Illegal characters in course code: {code}")

    if not COURSE_CODE_PATTERN.fullmatch(code):
        raise ValueError(f"Invalid course code format: {code}")