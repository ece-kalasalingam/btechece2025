# scripts/stage_7.py
import json
import os
import dataclasses
from typing import List, TypeVar, Any
from scripts.contracts import CourseExecutionContext, OUTPUT_DIR, OUTPUT_JSON_FILE, ViolationLevel, MasterExportData, CHECKPOINTS_DIR
from scripts.utils import recursive_escape_latex, validate_course_code

def save_course_checkpoint(ctx: CourseExecutionContext):
    """
    Saves a single course result immediately to disk.
    This prevents data loss if a later course causes a crash.
    """
    checkpoint_dir = os.path.join(OUTPUT_DIR, CHECKPOINTS_DIR)
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    # We only save if there's a course object (Stage 4+ reached)
    if not ctx.course:
        return
    # Prepare data (LaTeX escaped for safety)
    course_dict = dataclasses.asdict(ctx.course)
    escaped_data = recursive_escape_latex(course_dict)
    
    validate_course_code(ctx.course_code)
    file_path = os.path.join(checkpoint_dir, f"{ctx.course_code}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(escaped_data, f, indent=4)

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
            continue

        # 2. Load the Checkpointed Data
        validate_course_code(ctx.course_code)
        checkpoint_path = os.path.join(OUTPUT_DIR, "checkpoints", f"{ctx.course_code}.json")
        if os.path.exists(checkpoint_path):
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                escaped_course = json.load(f)
            
            # Categorize into Success or Warning
            if any(v.level == ViolationLevel.WARNING for v in ctx.violations):
                warnings = [v.message for v in ctx.violations if v.level == ViolationLevel.WARNING]
                master_data.warning.append({
                    "course_data": escaped_course,
                    "warnings": warnings
                })
            else:
                master_data.success.append(escaped_course)

    # Write to file
    file_path = os.path.join(OUTPUT_DIR, OUTPUT_JSON_FILE)
    with open(file_path, "w", encoding="utf-8") as f:
        # Convert the object back to a dict for JSON writing
        json.dump(dataclasses.asdict(master_data), f, indent=4, ensure_ascii=False)