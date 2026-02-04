from scripts.contracts import CourseExecutionContext
from scripts.utils import normalize_syllabus_text

def run_policy_gate(ctx: CourseExecutionContext):
    """
    STAGE-5: Policy & Data Normalization.
    """
    if not ctx.is_eligible or ctx.course is None:
        return

    meta = ctx.course.course_meta

    # 1. Credit Granularity Check
    if meta.c % 0.25 != 0:
        ctx.log("STAGE-5", "CREDIT-GRANULARITY", f"Credits {meta.c} not a multiple of 0.25.")

    # 2. Credit Equation Validation
    calculated_c = (meta.l + meta.t) + (meta.p / 2) + (meta.x / 3)
    if abs(calculated_c - meta.c) > 0.01:
        ctx.log("STAGE-5", "CREDIT-MISMATCH", f"Equation check failed: {calculated_c} != {meta.c}")

    # 3. Use the Common Utility for Title Normalization
    meta.course_title = normalize_syllabus_text(meta.course_title, is_title=True)

    if ctx.is_eligible:
        print(f"✅ Stage 5: Policy & Normalization complete for {ctx.course_code}")