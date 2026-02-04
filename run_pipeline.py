"""
MASTER PIPELINE: R2025 Syllabus Validator
Verbatim: Orchestrates the transition from structural geometry to validated curriculum data.
"""
import sys


# Stage 1: Structural Parsing & Extraction
import scripts.stage_1_parsing as stage_1 


# Stage 2: Orchestration & Semantic Lifting
import scripts.stage_2_driver as stage_2_driver

# Stage 3: Articulation & Regulatory Audit
import scripts.stage_3_articulation as stage_3_articulation
import scripts.stage_3_regulation_audit as stage_3_audit

from scripts.contracts import ValidationError, ValidationWarning

def process_syllabus(file_path: str):
    """
    Executes the 4-gate validation sequence for R2025 compliance.
    """
    course_code = file_path.split("/")[-1].split(".")[0]
    print(f"\n--- 🚀 Starting Pipeline for: {course_code} ---")

    try:
        # --- GATE 1: STRUCTURAL DECOMPOSITION ---
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        
        # 1a. Convert Markdown into Geometry (Sections/Blocks)
        structured_sections = stage_1.split_markdown_sections(raw_content)
        print(f"✅ [Stage 1] Structural Geometry built.")

        # --- GATE 2: SEMANTIC LIFTING & VALIDATION ---        
        # Driver orchestrates Shape, Structure, Grammar, and Regulations
        metadata, shape, units, extracted_cos, warnings = stage_2_driver.run_stage_2(
            course_code, 
            structured_sections
        )
        total_cos_defined = len(extracted_cos)
        print(f"✅ [Stage 2] Semantic Lifting and Unit Validation Complete. Found {total_cos_defined} COs.")

        # --- GATE 3: ARTICULATION GATE ---
        # Validates Unit -> CO range-mapping and promotes to ERP components
        components = stage_3_articulation.validate_and_articulate(
            course_code,
            metadata,
            units,
            extracted_cos
        )
        print(f"✅ [Stage 3a] Articulation Gate Passed (Unit-CO Mappings Verified).")

        # --- GATE 4: REGULATORY AUDIT ---
        # Mathematical verification of the 15-week multiplier
        stage_3_audit.validate_r2025_quantum_alignment(
            course_code,
            metadata,
            units
        )
        print(f"✅ [Stage 3b] 15-Week Regulatory Audit Passed.")

        # --- FINALIZATION ---
        _print_success_summary(course_code, units, warnings)
        
        return {
            "status": "SUCCESS",
            "course_code": course_code,
            "metadata": metadata,
            "units": units,
            "components": components,
            "warnings": [w.message for w in warnings]
        }

    except ValidationError as e:
        print(f"❌ VALIDATION ERROR in {e.course_code}: [{e.code}] {e.message}")
        return {"status": "ERROR", "code": e.code, "message": e.message}
    except Exception as e:
        import traceback
        print(f"💥 SYSTEM CRASH: {str(e)}")
        print(traceback.format_exc())
        return {"status": "CRASH", "message": str(e)}

def _print_success_summary(code, units, warnings):
    """Prints a scannable summary of the validated syllabus."""
    print(f"\n✨ COMPLIANCE SUMMARY for {code}:")
    if warnings:
        print(f"   ⚠️  {len(warnings)} Policy Warnings issued.")
    
    for u in units:
        # Show COs validated by Stage 3
        co_map = ", ".join(u.mapped_cos) if u.mapped_cos else "None"
        print(f"   [Unit {u.number}] {u.title}")
        print(f"      Mapped Outcomes: {co_map}")
        print(f"      Load: {u.theory_hours}h Theory | {u.lab_hours}h Lab | {u.x_hours}h X-Activity")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        process_syllabus(sys.argv[1])
    else:
        print("Usage: python run_pipeline.py <path_to_syllabus.md>")