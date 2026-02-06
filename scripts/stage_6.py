from scripts.contracts import MONTH_MAP, CourseExecutionContext
from scripts.utils import normalize_syllabus_text

def normalize_bos_date(date_str: str) -> str:
    """Targeted normalization for the date component only."""
    if not date_str or date_str.upper() in ["N/A", "NONE"]:
        return "N/A"
    
    # Split "Jan/25" or "January/2025"
    parts = date_str.split('/')
    if len(parts) != 2:
        return date_str # Fallback if format is weird
    
    month_part = parts[0].strip().lower().replace(".", "")
    year_part = parts[1].strip()
    
    # Use MONTH_MAP from contracts.py
    normalized_month = MONTH_MAP.get(month_part, month_part.capitalize())
    
    # Normalize Year (2-digit to 4-digit)
    if len(year_part) == 2:
        normalized_year = f"20{year_part}"
    else:
        normalized_year = year_part
        
    return f"{normalized_month} {normalized_year}"

def run_policy_gate(ctx: CourseExecutionContext):
    """
    STAGE-6: Policy & Data Normalization.
    """
    if not ctx.is_eligible or ctx.course is None:
        return

    meta = ctx.course.course_meta

    # 1. Credit Granularity Check
    if meta.c % 0.5 != 0:
        ctx.log("STAGE-6", "CREDIT-GRANULARITY", f"Credits {meta.c} not a multiple of 0.5.", fatal=False)

    # 2. Credit Equation Validation
    calculated_c = (meta.l + meta.t) + (meta.p / 2) + (meta.x / 3)
    if abs(calculated_c - meta.c) > 0.01:
        ctx.log("STAGE-6", "CREDIT-MISMATCH", f"Equation check failed: {calculated_c} != {meta.c},", fatal=True)

    # 3. Use the Common Utility for Title Normalization
    meta.course_title = normalize_syllabus_text(meta.course_title, is_title=True)

    # 4. Course Level range (0–6) is a policy guideline, not a hard constraint.
    if not (0 <= meta.course_level <= 6):
        ctx.log(
            "STAGE-6",
            "COURSE-LEVEL-POLICY-VIOLATION",
            f"Course Level {meta.course_level} is outside the recommended range (0–6).",
            fatal=False
        )

    #if ctx.is_eligible:
        #print(f"✅ Stage 6: Policy & Normalization complete for {ctx.course_code}")