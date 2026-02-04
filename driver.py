import sys
from scripts.paths import get_path
from scripts.contracts import CourseExecutionContext
import scripts.stage_0 as stage_0
import scripts.stage_1 as stage_1

def run_pipeline():
    # Load all courses (preserves index.md order)
    raw_inputs = stage_0.load_all_courses()
    
    master_report = []
    
    for idx, (code, raw_text) in enumerate(raw_inputs.items()):
        # Initialize Context
        ctx = CourseExecutionContext(course_code=code, source_index=idx)
        
        # STAGE 0: Ingestion
        safe_text = stage_0.ingest(raw_text)
        
        # STAGE 1: Structure (Gate 1)
        # If this fails, is_eligible becomes False
        stage_1.validate_structure(safe_text, ctx)
        
        if ctx.is_eligible:
            # Future Stages: 2, 3, 4...
            print(f"✅ {code}: Structural validation passed.")
        else:
            print(f"❌ {code}: Failed structural gates.")
            
        master_report.append(ctx)

    # Generate Audit/Dashboard
    # (Stage 6 logic goes here)

if __name__ == "__main__":
    run_pipeline()