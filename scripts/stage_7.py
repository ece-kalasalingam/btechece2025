# scripts/stage_7.py
import json
import os
import dataclasses
from typing import List
from scripts.contracts import CourseExecutionContext, OUTPUT_DIR, ACADEMIC_JSON_FILE, ViolationLevel, CHECKPOINTS_DIR, CourseReportRecord, REPORT_JSON_FILE
from scripts.utils import  validate_course_code

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
    
    if ctx.render_report:
        course_dict["render_report"] = dataclasses.asdict(ctx.render_report)
    escaped_data = course_dict
    
    validate_course_code(ctx.course_code)
    file_path = os.path.join(checkpoint_dir, f"{ctx.course_code}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(escaped_data, f, indent=4)

#def export_master_data(report: List[CourseExecutionContext], output_path: str = "master_data.json"):
def export_master_data(report: List[CourseReportRecord], output_path: str = "master_data.json"):
    """
    STAGE-7: Exporter.
    Collects all eligible courses and saves them as a structured JSON.
    """
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    except Exception as e:
        print(f"❌ Stage 7: Failed to create directory {OUTPUT_DIR}. Error: {e}")
        return
    
    courses_by_category = {}
    execution_report = {
        "warnings": [],
        "errors": []
    }
    for rec in report:
        # 1. Fatal errors
        if not rec.is_eligible:
            fatal_v = next((v for v in rec.violations if v.level == ViolationLevel.FATAL), None)
            execution_report["errors"].append({
                "course_code": rec.course_code,
                "reason": fatal_v.message if fatal_v else "Unknown Fatal Error"
            })
            continue
        # 2. Load checkpoint
        validate_course_code(rec.course_code)
        checkpoint_path = os.path.join(
            OUTPUT_DIR, CHECKPOINTS_DIR, f"{rec.course_code}.json"
        )

        if not os.path.exists(checkpoint_path):
            continue

        with open(checkpoint_path, "r", encoding="utf-8") as f:
            course_data = json.load(f)

        category = rec.course_category or "UNSPECIFIED"

        if category not in courses_by_category:
            courses_by_category[category] = []
        courses_by_category[category].append(course_data)

        # 3. Warnings
        warnings = [v.message for v in rec.violations if v.level == ViolationLevel.WARNING]
        if warnings:
            execution_report["warnings"].append({
                "course_code": rec.course_code,
                "warnings": warnings
            })
        
    #Write master data of eligible courses by category
    file_path = os.path.join(OUTPUT_DIR, ACADEMIC_JSON_FILE)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump({
            "courses": courses_by_category,
            "execution_report": execution_report
        }, f, indent=4, ensure_ascii=False)
    
    # Also save the execution report separately for easy access
    report_path = os.path.join(OUTPUT_DIR, REPORT_JSON_FILE)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(execution_report, f, indent=4, ensure_ascii=False)