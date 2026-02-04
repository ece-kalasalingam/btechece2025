import re
from typing import Optional, List
from scripts.patterns import SECTION_TITLE_MAP

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