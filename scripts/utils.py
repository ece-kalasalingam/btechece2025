import hashlib
import re
import shutil
import sys
from typing import Optional, Any, TypeVar
from scripts.contracts import EXTENSION_GUARDS, VIEW_CONFIG
from scripts.patterns import SECTION_TITLE_MAP

from pathlib import Path
import subprocess
COURSE_CODE_PATTERN = re.compile(r"^[A-Z0-9_]+$")

FORBIDDEN_SUBSTRINGS = {
    "/", "\\", "..", ".", ":", "~"
}
T = TypeVar('T', bound=Any)

# Helpers
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
    ##cGeneral Utility: Extracts text block between two markers.
    ## Used for partitioning the Header and Footer zones.
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
def strip_markdown_emphasis(text: str) -> str:
    """
    Safely removes Markdown emphasis (*, **, _, __) while preserving:
    - math expressions ($...$, $$...$$)
    - subscripts, identifiers, and semantic symbols (*, _)
    - LaTeX commands and grouping
    Also unescapes Markdown-escaped punctuation (e.g., \\* -> *) outside math.
    """
    # --------------------------------------------------
    # 1. Protect math blocks ($...$ and $$...$$)
    # --------------------------------------------------
    math_blocks = []

    def protect_math(match):
        key = f"<<<MATH_BLOCK_{len(math_blocks)}>>>"
        math_blocks.append(match.group(0))
        return key

    temp = re.sub(
        r'\$\$.*?\$\$|\$.*?\$',
        protect_math,
        text,
        flags=re.DOTALL
    )

    # --------------------------------------------------
    # 2. Strip Markdown emphasis (outside math only)
    #    IMPORTANT:
    #    - remove paired markers, not characters
    #    - do NOT span lines for italics/bold
    # --------------------------------------------------
    emphasis_patterns = [
        # bold + italic
        (r'\*\*\*(.+?)\*\*\*', r'\1'),
        (r'___(.+?)___', r'\1'),

        # bold
        (r'\*\*(.+?)\*\*', r'\1'),
        (r'__(.+?)__', r'\1'),

        # italic (asterisk)
        (r'\*([^\*\n]+?)\*', r'\1'),

        # italic (underscore) – avoid snake_case
        (r'(?<!_)_([^_\n]+?)_(?!_)', r'\1'),
    ]

    # --------------------------------------------------
    # Apply emphasis stripping ONLY to non-placeholder text
    # --------------------------------------------------
    parts = re.split(r'(<<<MATH_BLOCK_\d+>>>)', temp)

    processed_parts = []
    for part in parts:
        if part.startswith('<<<MATH_BLOCK_'):
            # 🔒 Do NOT touch placeholders
            processed_parts.append(part)
        else:
            # Safe to apply emphasis stripping
            for pattern, repl in emphasis_patterns:
                part = re.sub(pattern, repl, part)
            processed_parts.append(part)

    temp = ''.join(processed_parts)

    # --------------------------------------------------
    # 2.5 Unescape Markdown-escaped punctuation
    #      (outside math, explicit & safe)
    # --------------------------------------------------
    markdown_escapes = {
        r'\*': '*',
        r'\_': '_',
        r'\#': '#',
        r'\%': '%',
        r'\&': '&',
        r'\~': '~',
        r'\\': '\\',
        r'\`': '`',
    }

    for esc, char in markdown_escapes.items():
        temp = temp.replace(esc, char)

    # --------------------------------------------------
    # 3. Restore math blocks (in order)
    # --------------------------------------------------
    for i, block in enumerate(math_blocks):
        temp = temp.replace(f"<<<MATH_BLOCK_{i}>>>", block)

    return temp
def extract_bullet_items(text: str) -> list[str]:
    #Extracts bullet items only:
    #- Ignores paragraphs before and after the bullet list
    #- Removes bullet symbols (-, *, •, 1., 2.)
    #- Ignores empty bullet lines
    bullet_items = []
    bullet_started = False

    for line in text.splitlines():
        raw = line.rstrip()

        if not raw.strip():
            continue

        # Match bullet lines: -, *, •, 1., 2.
        match = re.match(r"^\s*(?:[-*•]|\d+\.)\s+(.*)", raw)
        if match:
            bullet_started = True
            item = match.group(1).strip()
            if item:
                bullet_items.append(item)
            continue

        # Once bullet list has started, stop on first non-bullet
        if bullet_started:
            break

        # Ignore paragraphs before first bullet
        continue

    return bullet_items
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
    #Optimized Single-Pass LaTeX Escaper.
    # Prevents double-escaping and ordering bugs.
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
def recursive_escape_latex(data: T) -> T:
    #Recursively walks through data and escapes strings for LaTeX.
    # The TypeVar T ensures that if a dict goes in, the linter expects a dict out.
    if isinstance(data, dict):
        return {k: recursive_escape_latex(v) for k, v in data.items()} # type: ignore
    elif isinstance(data, list):
        return [recursive_escape_latex(i) for i in data] # type: ignore
    elif isinstance(data, str):
        return escape_latex(data) # type: ignore
    return data
def get_current_git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            encoding="utf-8"
        ).strip()
    except Exception:
        return "N/A"
def get_git_metadata(file_path: Path):
    #Returns machine-readable Git metadata:
    # (commit_count, last_commit_date_iso)
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

def get_live_git_hash(file_path: Path):
    """Calculates the Git-style hash of a file on disk without reading it into Python RAM."""
    try:
        # 'git hash-object' is extremely fast and efficient
        return subprocess.check_output(
            ["git", "hash-object", str(file_path)], 
            stderr=subprocess.DEVNULL, 
            encoding="utf-8"
        ).strip()[:7] # Returning short 7-char hash
    except Exception:
        return "N/A"

def validate_course_code(code: str) -> None:
    if not code:
        raise ValueError("Empty course code")

    if any(bad in code for bad in FORBIDDEN_SUBSTRINGS):
        raise ValueError(f"Illegal characters in course code: {code}")

    if not COURSE_CODE_PATTERN.fullmatch(code):
        raise ValueError(f"Invalid course code format: {code}")  
def capitalize_if_first_char_english(text: str) -> str:
    #Capitalize the string ONLY if the first character is an English
    # lowercase alphabet (a–z). Otherwise, return the string unchanged.

    if not text:
        return text

    first = text[0]
    if 'a' <= first <= 'z':
        return first.upper() + text[1:]

    return text
def get_column_cells(line):
    # This regex looks for pipes that are NOT preceded by a backslash
    # or inside what looks like a math block (simplified for your case)
    stripped_line = line.strip().strip('|')
    parts = re.findall(r'(?:\\\||[^|])+', line.strip().strip('|'))
    pattern = re.compile(r'\|(?=(?:[^\$]*\$[^\$]*\$)*[^\$]*$)')
    parts = pattern.split(stripped_line)
    return [p.strip() for p in parts if p.strip()]
def get_column_count(line):
    # This regex looks for pipes that are NOT preceded by a backslash
    # or inside what looks like a math block (simplified for your case)
    parts = re.findall(r'(?:\\\||[^|])+', line.strip().strip('|'))
    return len(get_column_cells(line))
def is_tool_available(name: str) -> bool:
    """
    Robust check for system executables.
    Ensures we pass a string to avoid PathLike issues on older Windows/Python.
    """
    return shutil.which(str(name)) is not None
def validate_environment_for_view(view_name: str) -> bool:
    config = VIEW_CONFIG.get(view_name)
    if not config:
        raise ValueError(f"View '{view_name}' not found in VIEW_CONFIG.")
    ext = config.get("ext", "").lower().lstrip('.')
    suffix = config.get("suffix", view_name)
    if ext not in EXTENSION_GUARDS:
        raise RuntimeError(f"Extension '.{ext}' is not defined in the security guards.")
    required_mods = EXTENSION_GUARDS[ext]["modules"]
    if not any(mod in sys.modules for mod in required_mods):
        raise ImportError(
            f"Environment Mismatch: Configuration requested '.{ext}', "
            f"but none of the required modules {required_mods} are imported."
        )
    required_tools = EXTENSION_GUARDS[ext].get("tools", [])
    if required_tools is None:
        raise RuntimeError(f"Configuration Error: No tool list defined for '.{ext}' in guards.")
    for tool in required_tools:
        if not is_tool_available(tool):
            raise RuntimeError(
                f"System Tool Missing: '{tool}' is required to generate '.{ext}' "
                "but was not found in the system PATH."
            )
    return True
def get_file_sha256(file_path: Path):
    """Calculates the SHA-256 hash of a file's content."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except FileNotFoundError:
        return None