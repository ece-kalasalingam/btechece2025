"""
PIPELINE STAGE: 1 (Structural Parsing)

Purpose:
- Transform raw Markdown text into a sequence of StructuredSection objects.
- Identify headers while respecting variable-length fenced code blocks.
- Decompose bodies into raw blocks (bullets vs paragraphs) via Enum types.
- Provide pure pattern-based search and splitting utilities.

ARCHITECTURAL CONSTRAINTS:
- STAGE 1 MUST NOT KNOW: "Units", "Outcomes", "Activities", or "Credits".
- STAGE 1 MUST: Provide the structural "geometry" for Stage 2 to interpret.
"""

import re
from typing import List, Dict
from scripts.contracts import MarkdownSection, StructuredSection, MarkdownBlock, PREAMBLE_TITLE, BlockType


# ---------------------------------------------------------------------
# 2. Structural Patterns (Non-Semantic)
# ---------------------------------------------------------------------

# ... keep existing BULLET_PATTERN and TITLE_PARAGRAPH_PATTERN ...

# NEW: Identifies hour metadata in brackets or hyphens within headers
# Matches patterns like (3L-0T-2P-0X) or 3-0-2-1
HOURS_PATTERN = re.compile(r"\(?(\d+)L?\s*-\s*(\d+)T?\s*-\s*(\d+)P?\s*-\s*(\d+)X?\)?", re.I)

# ---------------------------------------------------------------------
# 3. Structural Patterns (Non-Semantic)
# ---------------------------------------------------------------------

# Identifies lines starting with bullet markers (No re.M needed for line-by-line)
BULLET_PATTERN = re.compile(r"^\s*[-*+]\s+(.+)")

# Splits text into a first sentence/line and the rest
TITLE_PARAGRAPH_PATTERN = re.compile(r"^([^.!?\n]+[.!?])\s*(.*)", re.S)

# ---------------------------------------------------------------------
# 4. Pattern-Based Utilities (Non-Semantic)
# ---------------------------------------------------------------------

def extract_header_hours(header_text: str) -> tuple[int, int, int]:
    """
    Extracts L, T, P, X integers from a header string.
    Returns: (theory_hours, practical_hours, x_hours)
    Note: Theory = L + T
    """
    match = HOURS_PATTERN.search(header_text)
    if match:
        # Convert captured groups to integers
        l, t, p, x = map(int, match.groups())
        return (l + t), p, x
    return 0, 0, 0

# ---------------------------------------------------------------------
# 5. Main Logic
# ---------------------------------------------------------------------

def split_markdown_sections(md_text: str) -> List[StructuredSection]:
    """
    Core Stage 1 Logic: Performs structural decomposition.
    Uses the robust header/fence logic from the original version.
    """
    raw_sections: List[MarkdownSection] = []
    
    current_level = 0
    current_title = PREAMBLE_TITLE
    current_body = []
    
    in_code_block = False
    code_fence = None 

    lines = md_text.splitlines()

    for line in lines:
        stripped = line.lstrip()

        # 1. Handle Fenced Code Blocks (Variable length check)
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence_char = stripped[0]
            i = 0
            while i < len(stripped) and stripped[i] == fence_char:
                i += 1
            fence = stripped[:i]

            if not in_code_block:
                in_code_block = True
                code_fence = fence
            elif fence == code_fence:
                in_code_block = False
                code_fence = None

            current_body.append(line)
            continue

        # 2. Header Detection
        if not in_code_block and stripped.startswith("#"):
            i = 0
            while i < len(stripped) and stripped[i] == "#":
                i += 1

            if i > 0 and i < len(stripped) and stripped[i] == " " and stripped[i+1:].strip():
                # Close previous section
                body_text = "\n".join(current_body).strip()
                raw_sections.append(MarkdownSection(current_level, current_title, body_text))
                
                # Start new
                current_level = i
                current_title = stripped[i+1:].strip()
                current_body = []
                continue

        current_body.append(line)

    # Flush final
    raw_sections.append(MarkdownSection(current_level, current_title, "\n".join(current_body).strip()))

    # Wrap into StructuredSections
    structured_sections: List[StructuredSection] = []
    for rs in raw_sections:
        # Ignore empty preambles
        if rs.title == PREAMBLE_TITLE and not rs.body:
            continue
        blocks = _decompose_body_to_blocks(rs.body)
        structured_sections.append(StructuredSection(section=rs, blocks=blocks))

    return structured_sections

def _decompose_body_to_blocks(body: str) -> List[MarkdownBlock]:
    """Line-by-line decomposition into structural Enums."""
    blocks = []
    lines = body.splitlines()
    current_para_lines = []

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue
        
        bullet_match = BULLET_PATTERN.match(line)
        if bullet_match:
            if current_para_lines:
                blocks.append(MarkdownBlock(BlockType.PARAGRAPH, " ".join(current_para_lines)))
                current_para_lines = []
            blocks.append(MarkdownBlock(BlockType.BULLET, bullet_match.group(1).strip()))
        else:
            current_para_lines.append(stripped_line)

    if current_para_lines:
        blocks.append(MarkdownBlock(BlockType.PARAGRAPH, " ".join(current_para_lines)))
    
    return blocks

# ---------------------------------------------------------------------
# 4. Pattern-Based Utilities (Non-Semantic)
# ---------------------------------------------------------------------

def find_sections_by_title_pattern(
    structured_sections: List[StructuredSection],
    pattern: re.Pattern
) -> List[StructuredSection]:
    """Pure structural search by regex pattern."""
    return [s for s in structured_sections if pattern.search(s.section.title)]

def split_title_paragraph(text: str) -> Dict[str, str]:
    """
    Splits text based on first sentence punctuation.
    Returns neutral keys to avoid semantic bias in Stage 1.
    """
    match = TITLE_PARAGRAPH_PATTERN.match(text.strip())
    if match:
        return {
            "title_line": match.group(1).strip(), 
            "body": match.group(2).strip()
        }
    return {"title_line": text.strip(), "body": ""}