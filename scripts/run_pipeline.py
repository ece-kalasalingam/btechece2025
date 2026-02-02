"""
=====================================================================
PIPELINE DRIVER : STAGE-0 → STAGE-4 (KARE R2025)
=====================================================================

- Course-level fail-fast
- Batch continues
- Stage-4 emits masterdata.json
=====================================================================
"""

import json
import enum
from contracts import ValidationError, ValidationWarning
from paths import get_path

# -------------------------------------------------
# Stage-0 / Stage-1
# -------------------------------------------------
from read_courses import load_courses, split_markdown_sections

# -------------------------------------------------
# Metadata
# -------------------------------------------------
from extract_metadata import extract_course_metadata

# -------------------------------------------------
# Stage-2
# -------------------------------------------------
from infer_content_shape import infer_content_shape, InferenceInput
from validate_structure import validate_course, extract_units
from validate_content_blocks import validate_content_blocks
from validate_semantic_blocks import (
    validate_semantic_blocks,
    extract_declared_cos,
)
from validate_regulation_policies import validate_regulation_policies

# -------------------------------------------------
# Stage-3
# -------------------------------------------------
from stage_3_driver import run_stage_3

# -------------------------------------------------
# Stage-4
# -------------------------------------------------
from masterdata_schema import empty_masterdata
from stage_4_masterdata import (
    add_course_to_masterdata,
    finalize_masterdata,
    add_failed_course
)

LOG_FILE = "pipeline_log.json"

def json_default_handler(obj):
    # 1. Handle Enums (CourseCategory, CourseType, etc.)
    if isinstance(obj, enum.Enum):
        return obj.value
    
    # 2. Handle Sets (Unique PO/PSO/CO mappings)
    if isinstance(obj, set):
        return sorted(list(obj)) # sorted() makes the output deterministic
    
    # 3. Handle Custom Dataclasses (if any)
    if hasattr(obj, "__dict__"):
        return obj.__dict__

    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')

def main():
    outputs = get_path("outputs", create=True)

    masterdata = empty_masterdata()
    emitted_courses_count = 0
    all_errors = []
    all_warnings = []

    courses, load_errors, total = load_courses()

    if load_errors:
        raise RuntimeError(load_errors[0])

    for course_code, md_text in courses.items():
        course_warnings = []

        try:
            # -----------------------------
            # Stage-1
            # -----------------------------
            sections = split_markdown_sections(md_text)
            title = next(s.title for s in sections if s.title and s.title.strip())
            meta = extract_course_metadata(course_code, sections)

            # -----------------------------
            # Stage-2a
            # -----------------------------
            inference = infer_content_shape(
                InferenceInput(
                    course_code=course_code,
                    course_title=title,
                    category=meta.category,
                    course_type=meta.course_type,
                )
            )

            # -----------------------------
            # Stage-2b
            # -----------------------------
            validate_course(
                course_code,
                inference.inferred_shape,
                sections,
                meta,
                course_warnings,
            )
            units = extract_units(course_code, sections)

            # -----------------------------
            # Stage-2c
            # -----------------------------
            validate_content_blocks(course_code, units)

            # -----------------------------
            # Stage-2d
            # -----------------------------
            validate_semantic_blocks(
                course_code,
                inference.inferred_shape,
                sections,
                units,
            )

            # -----------------------------
            # Stage-2e
            # -----------------------------
            validate_regulation_policies(course_code, meta, course_warnings)

            # -----------------------------
            # Stage-3
            # -----------------------------
            declared_cos = extract_declared_cos(course_code, sections)
            stage3_out = run_stage_3(course_code, sections, declared_cos)

            # -----------------------------
            # Stage-4 (MASTERDATA)
            # -----------------------------
            course_data = {
                "course_code": course_code,
                "course_title": title,
                "metadata": meta,
                "content_shape": inference.inferred_shape,
                "units": units,
                "course_outcomes": stage3_out["course_outcomes"],
                "warnings": course_warnings,
            }

            add_course_to_masterdata(masterdata, course_data)
            emitted_courses_count =len(masterdata["courses"])
            all_warnings.extend(course_warnings)

        except ValidationError as ve:
            error_entry = {
                "course_code": course_code,
                "stage": "Validation",
                "error": str(ve)
            }
            all_errors.append(error_entry)

            add_failed_course(
                masterdata,
                course_code=course_code,
                error=str(ve)
            )
            continue


        except Exception as e:
            print("\nFATAL RUNTIME ERROR")
            print(f"Course : {course_code}")
            print(f"Error  : {e}")
            raise

    # -----------------------------
    # Finalize masterdata
    # -----------------------------
    final_masterdata = finalize_masterdata(
        masterdata,
        errors=all_errors,
        warnings=[
            {
                "course_code": w.course_code,
                "code": w.code,
                "message": w.message
            } for w in all_warnings
        ]
    )

    (outputs / "masterdata.json").write_text(
        json.dumps(final_masterdata, indent=2, default=json_default_handler),
        encoding="utf-8"
    )
    status = "SUCCESSFULLY COMPLETED"
    if all_errors or all_warnings:
        status = "PARTIALLY COMPLETED"

    (outputs / LOG_FILE).write_text(
        json.dumps({
            "status": status,
            "total_courses": total,
            "courses_emitted": emitted_courses_count,
            "courses_omitted": total - emitted_courses_count,
            "errors": all_errors,
            "warnings": final_masterdata["warnings"]
        }, indent=2),
        encoding="utf-8"
    )
    print("\nPipeline completed.")
    print(f"Status: {status}")
    print(f"masterdata.json generated with {emitted_courses_count} courses.")

if __name__ == "__main__":
    main()