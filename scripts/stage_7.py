# scripts/stage_7.py
import json
import os
import dataclasses
from typing import List, TypeVar, Any
from scripts.contracts import CourseExecutionContext, OUTPUT_DIR, OUTPUT_JSON_FILE, ViolationLevel, MasterExportData
from scripts.utils import escape_latex

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

def export_master_data(report: List[CourseExecutionContext], output_path: str = "master_data.json"):
    """
    STAGE-7: Exporter.
    Collects all eligible courses and saves them as a structured JSON.
    """
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    except Exception as e:
        print(f"❌ Stage 7: Failed to create directory {OUTPUT_DIR}. Error: {e}")
        return
    
    master_data = MasterExportData()

    for ctx in report:
        # 1. ERROR: Fatal violations
        if not ctx.is_eligible:
            fatal_v = next((v for v in ctx.violations if v.level == ViolationLevel.FATAL), None)
            master_data.error.append({
                "course_code": ctx.course_code,
                "reason": fatal_v.message if fatal_v else "Unknown Fatal Error"
            })

        # 2. WARNING: Eligible but has warnings
        elif ctx.is_eligible and any(v.level == ViolationLevel.WARNING for v in ctx.violations):
            warnings = [v.message for v in ctx.violations if v.level == ViolationLevel.WARNING]
            course_dict = dataclasses.asdict(ctx.course) if ctx.course else {"course_code": ctx.course_code}
            escaped_course = recursive_escape_latex(course_dict)
            master_data.warning.append({
                "course_data": escaped_course,
                "warnings": warnings
            })

        # 3. SUCCESS: Perfectly clean
        elif ctx.course:
            course_dict = dataclasses.asdict(ctx.course)
            escaped_course = recursive_escape_latex(course_dict)
            master_data.success.append(escaped_course)

    # Write to file
    file_path = os.path.join(OUTPUT_DIR, OUTPUT_JSON_FILE)
    with open(file_path, "w", encoding="utf-8") as f:
        # Convert the object back to a dict for JSON writing
        json.dump(dataclasses.asdict(master_data), f, indent=4, ensure_ascii=False)