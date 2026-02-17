from unittest import result
from dataclasses import asdict
from scripts.contracts import MONTH_MAP, CourseExecutionContext, CO_MIN_COUNT, CO_MAX_COUNT 
from scripts.utils import normalize_syllabus_text, capitalize_if_first_char_english
from scripts.md_to_latex import MarkdownToLatexConverter
from typing import Any, Dict, List, Set, Union

def normalize_bos_date(date_str: str) -> str:
    """Targeted normalization for the date component only."""
    if not date_str or date_str.upper() in ["N/A", "NONE"]:
        return "N/A"
    
    # Split "Jan/25" or "January/2025"
    parts = date_str.split('/')
    if len(parts) != 2:
        return date_str # Fallback if format is weird
    
    month_part = parts[0].strip().lower().replace(".", "")
    year_part = parts[1].strip()
    
    # Use MONTH_MAP from contracts.py
    normalized_month = MONTH_MAP.get(month_part, month_part.capitalize())
    
    # Normalize Year (2-digit to 4-digit)
    if len(year_part) == 2:
        normalized_year = f"20{year_part}"
    else:
        normalized_year = year_part
        
    return f"{normalized_month} {normalized_year}"

def sum_syllabus_hours(data) -> Dict[str, Union[int, float]]:
    """
    Recursively finds and sums all keys ending in '_hours'.
    This is agnostic to display_type and handles new hour categories automatically.
    """
    # Use a dictionary to store dynamic categories (theory, practical, seminar, etc.)
    # Initializing with 0.0 handles the Pylance 'float' assignment error.
    totals: Dict[str, Union[int, float]] = {}

    def recurse(node):
        if isinstance(node, dict):
            for key, value in node.items():
                # General check: find any key that ends in '_hours'
                if isinstance(key, str) and key.endswith("_hours"):
                    if isinstance(value, (int, float)):
                        # If category doesn't exist yet, start at 0.0
                        if key not in totals:
                            totals[key] = 0.0
                        totals[key] += value
                
                # Continue searching through the value
                recurse(value)
        
        elif isinstance(node, list):
            for item in node:
                recurse(item)
        
        elif hasattr(node, "__dict__"):
            recurse(node.__dict__)

    # Start the process
    recurse(data)
    return totals
def extract_unique_syllabus_cos(syllabus: dict) -> list[int]:
    unique_cos = set()

    def traverse(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "cos" and isinstance(v, list):
                    unique_cos.update(
                        co for co in v if isinstance(co, int)
                    )
                else:
                    traverse(v)
        elif isinstance(obj, list):
            for item in obj:
                traverse(item)

    traverse(syllabus)

    return sorted(unique_cos)   # return as list


def run_policy_gate(ctx: CourseExecutionContext):
    """
    STAGE-6: Policy & Data Normalization.
    """
    if not ctx.is_eligible or ctx.course is None:
        return

    meta = ctx.course.course_meta

    # 1. Credit Granularity Check
    if meta.c % 0.5 != 0:
        ctx.log("STAGE-6", "CREDIT-GRANULARITY", f"Credits {meta.c} not a multiple of 0.5.", fatal=False)

    # 2. Credit Equation and Hours Validation
    calculated_c = (meta.l + meta.t) + (meta.p / 2) + (meta.x / 3)
    if abs(calculated_c - meta.c) > 0.1:
        ctx.log("STAGE-6", "CREDIT-MISMATCH", f"Equation check failed: {calculated_c} != {meta.c},", fatal=True)
    # Additionally, we can validate the total hours against the credit calculation
    totals = sum_syllabus_hours(ctx.course.syllabus.__dict__)
    total_theory_hours = totals.get("theory_hours", 0)  
    total_practical_hours = totals.get("practical_hours", 0)
    total_x_activity_hours = totals.get("x_activity_hours", 0)    
    
    if((total_theory_hours>0) or (total_practical_hours>0) or (total_x_activity_hours>0)):
        calculated_c = (total_theory_hours + (total_practical_hours/2) + (total_x_activity_hours/3))/15
        if (abs(calculated_c - meta.c) > 0.1): 
            ctx.log("STAGE-6", "CREDITS-HOURS-MISMATCH", f"Credits calculated from total hours {calculated_c} does not align with expected credits {meta.c}.", fatal=True)

    # 3. Use the Common Utility for Title Normalization
    meta.course_title = normalize_syllabus_text(meta.course_title, is_title=True)

    # 4. Course Type PC must have P > 0 and must have L+T = 0
    if meta.course_type.upper() == "PC":
        if meta.p <= 0:
            ctx.log("STAGE-6", "PC-PRACTICAL-REQUIREMENT", f"Course Type 'PC' must have P > 0 but has P  {meta.p}.", fatal=True)
        if (meta.l + meta.t) != 0:
            ctx.log("STAGE-6", "PC-LT-CONSTRAINT", f"Course Type 'PC' must have L+T = 0 but has L = {meta.l} and T = {meta.t}.", fatal=True)       
    
    #5 Coure Type TC must have P = 0 and must have (L+T) > 0
    if meta.course_type.upper() == "TC":
        if meta.p != 0:
            ctx.log("STAGE-6", "TC-PRACTICAL-CONSTRAINT", f"Course Type 'TC' must have P =0 but has P = {meta.p}.", fatal=True)
        if (meta.l + meta.t) <= 0:
            ctx.log("STAGE-6", "TC-LT-REQUIREMENT", f"Course Type 'TC' must have (L+T) > 0 but has L = {meta.l} and T = {meta.t}.", fatal=True)
    
    # 6. Coure Type IC (IC-T or IC-P) must have P+X > 0 and must have L+T > 0
    if meta.course_type.upper() in ["IC-T", "IC-P"]:
        if (meta.p + meta.x) <= 0:
            ctx.log("STAGE-6", "IC-PX-REQUIREMENT", f"Course Type '{meta.course_type}' must have P+X > 0 but has P = {meta.p} and X = {meta.x}.", fatal=True)
        if (meta.l + meta.t) <= 0:
            ctx.log("STAGE-6", "IC-LT-REQUIREMENT", f"Course Type '{meta.course_type}' must have L+T > 0 but has L = {meta.l} and T = {meta.t}.", fatal=True)   


    # 7. Capitalize the starting English alphabet in the description, objectives and outcomes if they are not already capitalized.
    ctx.course.description = capitalize_if_first_char_english(ctx.course.description)
    ctx.course.objectives = [
        capitalize_if_first_char_english(obj)
        for obj in ctx.course.objectives
    ]
    for co in ctx.course.outcomes:
        co["outcome"] = capitalize_if_first_char_english(co["outcome"])
    # Apply capitalization to Unit and Topic titles
    for unit in ctx.course.syllabus.units:
        # Capitalize Unit Title
        if "unit_title" in unit:
            unit["unit_title"] = normalize_syllabus_text(unit["unit_title"], is_title=True)
        
        # Capitalize Topic Titles within the unit
        for topic in unit.get("topics", []):
            if "title" in topic:
                topic["title"] = capitalize_if_first_char_english(topic["title"])

    # Apply capitalization to PC Experiment titles (for Laboratory courses)
    for exp in ctx.course.syllabus.pc_experiments:
        if "title" in exp:
            exp["title"] = normalize_syllabus_text(exp["title"], is_title=True)

    # 8. To do check the CO count
    co_count = len(ctx.course.outcomes)
    if not (CO_MIN_COUNT <= co_count <= CO_MAX_COUNT):
        ctx.log(
            "STAGE-6",
            "OUTCOMES-COUNT",
            f"Course must contain {CO_MIN_COUNT}-{CO_MAX_COUNT} valid outcomes, but found {co_count} outcomes.",
            fatal=True
        )

    # 9. Convert MD to Latex for the special courses
    converter = MarkdownToLatexConverter()
    raw_list = ctx.course.syllabus.raw_content
    if raw_list:
        # 1. Reference the specific dictionary inside the list
        entry = raw_list[0]
        
        # 2. Get the content and convert it
        content = entry.get("content", "No content found")
        latex = converter.convert(content)
        
        # 3. Insert the new key/value pair into the SAME dictionary
        entry["latex"] = latex

    # 10. Check all the COs are mapped in the syllabus
    if ctx.course.outcomes:
        total_cos = len(ctx.course.outcomes)
        expected_ids = set(range(1, total_cos + 1))
        actual_ids = set(extract_unique_syllabus_cos(asdict(ctx.course.syllabus)))
        if actual_ids:
            if not expected_ids.issubset(actual_ids):
                missing = sorted(expected_ids - actual_ids)
                if missing:
                    ctx.log(
                        "STAGE-6",
                        "SYLLABUS-CO-COVERAGE-MISSING",
                        f"Syllabus is missing mappings for COs: {missing}",
                        fatal=True
                    )

    # 4. Course Level range (0–6) is a policy guideline, not a hard constraint.
    # if not (0 <= meta.course_level <= 6):
      #  ctx.log(
       #     "STAGE-6",
        #    "COURSE-LEVEL-POLICY-VIOLATION",
         #   f"Course Level {meta.course_level} is outside the recommended range (0–6).",
          #  fatal=False
        #)

    #if ctx.is_eligible:
        #print(f"✅ Stage 6: Policy & Normalization complete for {ctx.course_code}")