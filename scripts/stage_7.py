# scripts/stage_7.py
import json
import os
import dataclasses
from typing import List
from scripts.contracts import (
    DASHBOARD_JSON_FILE, CourseCategory, 
    CourseExecutionContext, TEMP_OUTPUT_DIR, 
    ACADEMIC_JSON_FILE, ViolationLevel, 
    CHECKPOINTS_DIR, CourseReportRecord, 
    REPORT_JSON_FILE, DASHBOARD_DIR
)
from scripts.utils import  validate_course_code, get_file_sha256
from scripts.paths import get_path

from jsonschema import ValidationError, validate
import json

def validate_export_schema(export_data: dict):
    schema_path = os.path.join("schemas", "r2025_syllabus_schema.json")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    try:
        validate(instance=export_data, schema=schema)
    except ValidationError as e:
        print("❌ JSON Schema Validation Failed")
        print(f"Path: {list(e.path)}")
        print(f"Message: {e.message}")
        raise RuntimeError("Stage-7 schema validation failed.") from e


def save_course_checkpoint(ctx: CourseExecutionContext):
    """
    Saves a single course result immediately to disk.
    This prevents data loss if a later course causes a crash.
    """
    checkpoint_dir = os.path.join(TEMP_OUTPUT_DIR, CHECKPOINTS_DIR)
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
def export_master_data(report: List[CourseReportRecord], output_path: str = ACADEMIC_JSON_FILE):
    """
    STAGE-7: Exporter.
    Collects all eligible courses and saves them as a structured JSON.
    """
    try:
        os.makedirs(TEMP_OUTPUT_DIR, exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"Stage 7 : Failed to create directory: {TEMP_OUTPUT_DIR}. Error: {e}")
    
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
            TEMP_OUTPUT_DIR, CHECKPOINTS_DIR, f"{rec.course_code}.json"
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
    # 1️⃣ Enforce category order using Enum
    ordered_courses_by_category = {}

    for cat in CourseCategory:
        if cat.code in courses_by_category:
            ordered_courses_by_category[cat.code] = courses_by_category[cat.code]

    courses_by_category = ordered_courses_by_category

    # 2️⃣ Enforce ascending course_code order inside each category
    for category in courses_by_category:
        courses_by_category[category] = sorted(
            courses_by_category[category],
            key=lambda c: c.get("course_code", "")
        )

    final_payload = {
        "courses": courses_by_category,
        "execution_report": execution_report
    }
    validate_export_schema(final_payload)

    file_path = os.path.join(TEMP_OUTPUT_DIR, ACADEMIC_JSON_FILE)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=4, ensure_ascii=False)
    
    # Also save the execution report separately for easy access
    report_path = os.path.join(TEMP_OUTPUT_DIR, REPORT_JSON_FILE)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(execution_report, f, indent=4, ensure_ascii=False)
    
    source_path = get_path(TEMP_OUTPUT_DIR, ACADEMIC_JSON_FILE)
    if source_path.exists():
        current_sha = get_file_sha256(source_path)
        if current_sha is None:
            raise RuntimeError(f"Stage 7 : SHA-256 Hash couldn't be calculated.")
        
        """Stores the latest Source Data signature in the manifest."""
        manifest_path = get_path(DASHBOARD_DIR, DASHBOARD_JSON_FILE)
              
        if manifest_path.exists():
            with open(manifest_path, 'r', encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
        data["global_source_sha"] = current_sha
        
        with open(manifest_path, 'w', encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"✅ Source Data SHA calculated: {current_sha[:10]}...")