import re
from typing import List, Dict
from scripts.contracts import StructuredSection, BlockType
from scripts.utils import find_sections_by_title_pattern

def extract_course_outcomes(sections: List[StructuredSection]) -> List[Dict]:
    """
    Locates the CO section and returns a list of dictionaries.
    The length of this list is the 'Total CO Count' used in Stage 3.
    """
    # Look for "Course Outcomes" or "Course Objectives"
    co_pattern = re.compile(r"course\s+outcomes", re.I)
    
    # Assuming find_sections_by_title_pattern is accessible
    co_sections = find_sections_by_title_pattern(sections, co_pattern)
    
    outcomes = []
    if co_sections:
        # We look into the blocks for bullet points
        for block in co_sections[0].blocks:
            if block.type == BlockType.BULLET:
                content = block.content.strip()
                # Store text; we will count the length of this list later
                outcomes.append({"text": content})
                
    return outcomes