"""
PIPELINE ORCHESTRATOR
Verbatim: Packages data into MasterData and triggers Stage 5 Serialization.
"""
import os
import dataclasses
from typing import Dict, Any

# Stage Imports
from scripts.stage_1_parsing import split_markdown_sections
from scripts.stage_2_driver import run_stage_2
import scripts.stage_3_validation as stage_3  # Note: This is your driver file
import scripts.stage_4_assessment as stage_4
import scripts.stage_5_generator as stage_5

def run_full_pipeline(file_path: str):
    # Use relative paths for GitHub compatibility
    course_code = os.path.basename(file_path).split('.')[0]
    
    # --- DATA ACQUISITION ---
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_markdown = f.read()
    
    # STAGE 1 & 2
    sections = split_markdown_sections(raw_markdown)
    
    # FIX: Ensure run_stage_2 returns 'outcomes' (extracted from the CO section)
    metadata, shape, units, outcomes, warnings = run_stage_2(course_code, sections)

    # STAGE 3 & 4
    # FIX: Pass 'outcomes' to Stage 3 so it can perform Bloom Level validation
    components = stage_3.run_stage_3(course_code, metadata, shape, units, outcomes)
    
    strategy = stage_4.generate_assessment_strategy(metadata)

    # --- PACKAGING (The 'MasterData' interpretation) ---
    master_data: Dict[str, Any] = {
        "course_code": metadata.course_code,
        "audit_meta": {
            "version": "R2025-v1",
            "status": "VALIDATED",
            "warnings_count": len(warnings)
        },
        "syllabus_data": {
            "metadata": dataclasses.asdict(metadata),
            "articulation": {k: dataclasses.asdict(v) for k, v in components.items()},
            "outcomes": outcomes, # Including outcomes in the final JSON
            "assessment": dataclasses.asdict(strategy)
        }
    }

    # STAGE 5: Verbatim Dump
    output_path = stage_5.generate_verified_output(master_data, output_dir="output_verified")
    
    print(f"--- Pipeline Finished for {course_code} ---")
    print(f"Result: {output_path}")

if __name__ == "__main__":
    INPUT_DIR = "syllabi_input"
    # Ensure output directory exists
    os.makedirs("output_verified", exist_ok=True)
    
    if os.path.exists(INPUT_DIR):
        for file in os.listdir(INPUT_DIR):
            if file.endswith(".md"):
                run_full_pipeline(os.path.join(INPUT_DIR, file))