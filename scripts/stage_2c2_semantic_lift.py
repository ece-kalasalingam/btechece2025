import re
from typing import List, Tuple
from dataclasses import dataclass
from scripts.contracts import UnitBlock, ActivityBlock, StructuredSection
from scripts.patterns import UNIT_HEADER_PATTERN
from scripts.utils import find_sections_by_title_pattern

@dataclass
class UnitParseContext:
    """Transient container for raw hour strings."""
    raw_theory_str: str = "0"
    raw_lab_str: str = "0"
    raw_x_str: str = "0"

def lift_units_strictly(structured_sections: List[StructuredSection]) -> Tuple[List[UnitBlock], List[UnitParseContext]]:
    unit_sections = find_sections_by_title_pattern(structured_sections, UNIT_HEADER_PATTERN)
    """
    Deterministic State Machine for R2025 Units.
    Transitions: TITLE -> CO_MAPPING -> HOURS -> CONTENT
    """
    units: List[UnitBlock] = []
    contexts: List[UnitParseContext] = []
    CO_MARKERS = ["COs:", "Mapped COs:", "Course Outcomes:"]
    
    for idx, s_sec in enumerate(unit_sections, 1):
        lines = [l.strip() for l in s_sec.section.body.split('\n') if l.strip()]
        if not lines: continue
        
        unit = UnitBlock(number=idx, title=lines[0])
        ctx = UnitParseContext()
        current_mode = "TITLE"
        
        for line in lines[1:]:
            # 1. Articulation Gate
            if any(line.startswith(m) for m in CO_MARKERS):
                unit.raw_co_indices = [int(d) for d in re.findall(r'\d+', line)]
                current_mode = "CO_MAPPED"
                continue
            
            # 2. Regulatory Markers
            if "Theory Hours:" in line:
                ctx.raw_theory_str = _extract_digits(line)
                current_mode = "THEORY"
                continue
            elif "Practical Hours:" in line:
                ctx.raw_lab_str = _extract_digits(line)
                current_mode = "PRACTICAL"
                continue
            elif "X-Activity Hours:" in line:
                ctx.raw_x_str = _extract_digits(line)
                current_mode = "X_ACTIVITY"
                continue

            # 3. Content Logic
            if current_mode == "THEORY" and line.startswith("-"):
                parts = line.lstrip("- ").split(":", 1)
                unit.topics.append((parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""))
            
            elif current_mode in ["PRACTICAL", "X_ACTIVITY"]:
                target_list = unit.experiments if current_mode == "PRACTICAL" else unit.x_activities
                if line.startswith("-"):
                    target_list.append(ActivityBlock(title=line.lstrip("- ").strip(), description=""))
                elif (line.startswith(" ") or line.startswith("*")) and target_list:
                    target_list[-1].description += " " + line.strip("* ").strip()

        units.append(unit)
        contexts.append(ctx)
        
    return units, contexts

def _extract_digits(text: str) -> str:
    match = re.search(r'\d+', text)
    return match.group() if match else "0"