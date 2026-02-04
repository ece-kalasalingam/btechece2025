from scripts.contracts import CourseExecutionContext
import scripts.stage_0 as stage_0
import scripts.stage_1 as stage_1
import scripts.stage_2 as stage_2
import scripts.stage_3 as stage_3
import scripts.stage_4 as stage_4
import scripts.stage_5 as stage_5
import scripts.stage_6 as stage_6

def run_pipeline():
    # 1. Load all courses using stage_0 (uses index.md and courses_md/ folder)
    # This calls stage_0.ingest internally to normalize text
    raw_inputs = stage_0.load_all_courses()
    
    master_report = []
    
    for idx, (code, raw_text) in enumerate(raw_inputs.items()):
        # 2. Initialize Context
        ctx = CourseExecutionContext(course_code=code, source_index=idx)
        
        # 3. STAGE 1: Structural Validation & Partitioning
        # Requires two arguments: (raw_text, ctx)
        stage_1.validate_structure(raw_text, ctx)
        
        # 4. STAGE 2: Format Gate (Mandatory Header check & Section check)
        # Function name in your file is run_format_gate, not run_validation_gate
        if ctx.is_eligible:
            stage_2.run_format_gate(ctx)
            
        # 5. STAGE 3: Metadata Extraction
        # Extracts title, category, type, and LTPXC into ctx.metadata
        if ctx.is_eligible:
            stage_3.run_metadata_extraction(ctx)

        # 6. STAGE 4: Structural Assembly
        # Group metadata into CourseMeta and creates CanonicalCourse object
        if ctx.is_eligible:
            stage_4.run_course_assembly(ctx)

        # 7. STAGE 5: Policy & Normalization
        # Validates credit math and applies Title Case to course_title
        if ctx.is_eligible:
            stage_5.run_policy_gate(ctx)
        # 8. STAGE 6: Body Grammar Gate
        # Validates grammar in sections as per contracts.py
        if ctx.is_eligible:
            stage_6.process_body_logic(ctx)
        # Final Logging
        if ctx.is_eligible and ctx.course:
            # course_title is now inside the course_meta object
            final_title = ctx.course.course_meta.course_title
            print(f"✅ {code}: Processed successfully. Title: {final_title}")
        else:
            # Report the first fatal violation that caused the failure
            error = ctx.violations[-1].message if ctx.violations else "Unknown error"
            print(f"❌ {code}: Failed - {error}")
            
        master_report.append(ctx)

    print(f"\n--- Pipeline Complete. Processed {len(master_report)} courses. ---")
    print(f"\nSummary Report: {master_report}")

if __name__ == "__main__":
    run_pipeline()