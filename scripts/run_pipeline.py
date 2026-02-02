"""
=====================================================================
PIPELINE DRIVER : STAGE-0 → STAGE-3 (KARE R2025)
=====================================================================

Runs the syllabus compiler deterministically and fail-fast.

Stages:
0–1.5 : Ingestion + structural parsing
2a    : Content shape inference
2b    : Structural validation
2c    : Content block grammar validation
2d    : Semantic block presence validation
3     : Articulation extraction + rule validation

Stage-4 is intentionally excluded.
=====================================================================
"""

import json
import sys
from typing import Any
from contracts import ValidationError, ValidationWarning


warnings: list[ValidationWarning]
# -------------------------------------------------
# Stage-0 / Stage-1.5
# -------------------------------------------------
from read_courses import load_courses, split_markdown_sections

# -------------------------------------------------
# Metadata extraction (NEW, REQUIRED)
# -------------------------------------------------
from extract_metadata import extract_course_metadata

# -------------------------------------------------
# Stage-2a
# -------------------------------------------------
from infer_content_shape import infer_content_shape, InferenceInput

# -------------------------------------------------
# Stage-2b
# -------------------------------------------------
from validate_structure import validate_course, extract_units

# -------------------------------------------------
# Stage-2c
# -------------------------------------------------
from validate_content_blocks import validate_content_blocks

# -------------------------------------------------
# Stage-2d
# -------------------------------------------------
from validate_semantic_blocks import validate_semantic_blocks
from validate_semantic_blocks import extract_declared_cos

# -------------------------------------------------
# Stage-2e
# -------------------------------------------------
from validate_regulation_policies import (
    validate_regulation_policies,
    LTPXCTuple,
)

# -------------------------------------------------
# Stage-3
# -------------------------------------------------
from stage_3_driver import run_stage_3

# -------------------------------------------------
# Shared
# -------------------------------------------------
from paths import get_path



LOG_FILE = "pipeline_log.json"


#def fatal(stage: str, course_code: str, error: Exception):
def fatal(stage: str, course_code: str, error: Any):
    """
    Fail-fast handler: write single fatal log and exit.
    """
    out_dir = get_path("outputs", create=True)
    log_path = out_dir / LOG_FILE

    payload = {
        "status": "FATAL",
        "stage": stage,
        "course_code": course_code,
        "error": str(error),
    }

    log_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\nFATAL ERROR")
    print(f"Stage      : {stage}")
    print(f"Course     : {course_code}")
    print(f"Violation  : {error}")

    sys.exit(1)


def main():
    outputs = get_path("outputs", create=True)
    warnings = []

    # =================================================
    # STAGE 0 → 1.5 : Ingestion
    # =================================================
    courses, load_errors, total = load_courses()

    if load_errors:
        fatal("Stage-0", "__PIPELINE__", load_errors[0])

    # =================================================
    # PER-COURSE PIPELINE
    # =================================================
    for course_code, md_text in courses.items():
        try:
            # -----------------------------
            # Stage-1 : Section parsing
            # -----------------------------
            sections = split_markdown_sections(md_text)

            # -----------------------------
            # Metadata extraction (AUTHORITATIVE)
            # -----------------------------
            meta = extract_course_metadata(course_code, sections)


            # Course title = first level-1 heading
            title = next(
                s.title for s in sections if s.title and s.title.strip()
            )

            # -----------------------------
            # Stage-2a : Content shape inference
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
            # Stage-2b : Structural validation
            # -----------------------------
            validate_course(
                course_code,
                inference.inferred_shape,
                sections,
                meta,
                warnings
            )

            units = extract_units(course_code, sections)

            # -----------------------------
            # Stage-2c : Grammar validation
            # -----------------------------
            validate_content_blocks(course_code, units)

            # -----------------------------
            # Stage-2d : Semantic block presence
            # -----------------------------
            validate_semantic_blocks(
                course_code,
                inference.inferred_shape,
                sections,
                units,
            )

            # -----------------------------
            # Stage-2e : Regulation policy validation
            # -----------------------------
            validate_regulation_policies(
                course_code,
               meta,
                warnings
            )

            # -----------------------------
            # Stage-3 : Articulation validation
            # -----------------------------

            declared_cos = extract_declared_cos(course_code, sections)
            run_stage_3(course_code, sections, declared_cos)

        except ValidationError as ve:
            fatal("Validation", course_code, ve)
        except Exception as e:
            fatal("Runtime", course_code, e)

    if warnings:
        print("\nWARNINGS:")
        for w in warnings:
            print(f"  - {w.course_code} [{w.code}]: {w.message}")
    # =================================================
    # SUCCESS
    # =================================================
    success = {
        "status": "OK",
        "courses_processed": len(courses),
        "stages_completed": "0 → 3",
        "ready_for_stage_4": True,
    }

    (outputs / LOG_FILE).write_text(
        json.dumps(success, indent=2),
        encoding="utf-8",
    )

    print("\nPipeline completed successfully.")
    print("Stage-4 may now proceed.")


if __name__ == "__main__":
    main()