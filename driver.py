import traceback
import argparse
from scripts.contracts import CourseExecutionContext, VIEW_CONFIG
import scripts.stage_0 as stage_0
import scripts.stage_1 as stage_1
import scripts.stage_2 as stage_2
import scripts.stage_3 as stage_3
import scripts.stage_5 as stage_5
import scripts.stage_6 as stage_6
import scripts.stage_4 as stage_4
import scripts.stage_7 as stage_7
import scripts.stage_8 as stage_8
import scripts.stage_9 as stage_9

def run_pipeline():
    available_views = list(VIEW_CONFIG.keys())
    if not available_views:
        raise ValueError("VIEW_CONFIG in contracts.py is empty!")
    cli_choices = available_views + ["all"]
    parser = argparse.ArgumentParser(description="Syllabus Generator")
    parser.add_argument(
        "--view", 
        choices=cli_choices, 
        default=available_views[0], 
        help=f"Select layout (Default: {available_views[0]})"
    )
    args = parser.parse_args()
    if args.view == "all":
        views_to_process = available_views
    else:
        views_to_process = [args.view]

    # 1. Load all courses using stage_0 (uses index.md and courses_md/ folder)
    # This calls stage_0.ingest internally to normalize text
    #raw_inputs = stage_0.load_all_courses()
    
    master_report = []
    seen_codes = set()

    #for idx, (code, raw_text) in enumerate(raw_inputs.items()):
    for idx, (code, raw_text, error) in enumerate(stage_0.iter_courses()):
        # 2. Initialize Context
        ctx = CourseExecutionContext(course_code=code, source_index=idx)
        if error is not None:
            ctx.log(
                stage="STAGE-0",
                code="COURSE-INGEST-FAILED",
                msg=error,
                fatal=True
            )
            master_report.append(ctx)
            continue
        assert raw_text is not None
        try:
            if code in seen_codes:
                ctx.log(
                    stage="STAGE-0",
                    code="DUPLICATE-FILE",
                    msg=f"The course code '{code}' has already been processed in this batch.",
                    fatal=True
                )
                master_report.append(ctx)
                print(f"❌ {code}: Failed - Duplicate entry in index.")
                continue
            
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

            # 6.  STAGE 4: Body Grammar Gate
            # Validates grammar in sections as per contracts.py
            if ctx.is_eligible:
                stage_4.process_body_logic(ctx)
            
            # 7.  STAGE 5: Structural Assembly
            # Group metadata into CourseMeta and creates CanonicalCourse object
            if ctx.is_eligible:
                stage_5.run_course_assembly(ctx)

            actual_code = ctx.course_code if ctx.course else None
            # Check for conflicting course codes   
            if actual_code and actual_code in seen_codes:
                ctx.log(
                    stage="STAGE-4",
                    code="CONFLICTING-CODE",
                    msg=f"Internal course code '{actual_code}' is already used by another file.",
                    fatal=True
                )
            else:
                # If unique, we register it
                seen_codes.add(actual_code if actual_code else code)

            # 8. STAGE 6: Policy & Normalization
            # Validates credit math and applies Title Case to course_title
            if ctx.is_eligible:
                stage_6.run_policy_gate(ctx)

            if ctx.is_eligible:
                stage_7.save_course_checkpoint(ctx)
        except Exception as e:
            # CAPTURE SYSTEM CRASHES
            # We log the actual Python error message and a snippet of the traceback
            print("❌ UNHANDLED EXCEPTION")
            traceback.print_exc()
            ctx.log(
                stage="SYSTEM",
                code="UNHANDLED-EXCEPTION",
                msg=f"Internal Engine Error: Please check system logs for details.",
                fatal=True
            )
        # Final Logging
        if ctx.is_eligible and ctx.course:
            # course_title is now inside the course_meta object
            final_title = ctx.course.course_meta.course_title
            print(f"✅ {code}: Processed successfully. Title: {final_title}")
        else:
            # Report the first fatal violation that caused the failure
            error = ctx.violations[-1].message if ctx.violations else "Unknown error"
            code = ctx.violations[-1].code if ctx.violations else "Unknown error"
            stage = ctx.violations[-1].stage if ctx.violations else "Stage Unknown"
            print(f"❌ {ctx.course_code}: {code} - Failed at {stage} - {error}")
            
        master_report.append(ctx)
    stage_7.export_master_data(master_report)
    for v in views_to_process:
        # print(f"🛠️ Processing PDF View: {v}")
        # Stage 8 will now use VIEW_CONFIG[v] internally
        stage_8.run_book_generation(view_type=v)
        stage_9.run_stage9(view_type=v)
    
    print(f"\n--- Pipeline Complete. Processed {len(master_report)} courses. ---")

if __name__ == "__main__":
    run_pipeline()