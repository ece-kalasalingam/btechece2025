from scripts.contracts import CourseExecutionContext, CanonicalCourse
from scripts.grammar import check_section_grammar

def process_body_logic(ctx: CourseExecutionContext):
    """
    STAGE-6: Body Grammar Gate.
    Automatically identifies sections described in contracts.py and 
    validates their internal grammar.
    """
    if not ctx.is_eligible or ctx.structure is None:
        return

    # Automatically get section names from the Contract (CanonicalCourse)
    # This retrieves keys like 'units', 'outcomes', 'articulation', etc.
    contract_fields = CanonicalCourse.__annotations__.keys()
    
    # Sections partitioned by Stage 1
    found_sections = ctx.structure.explicit_sections

    for key, content in found_sections.items():
        # A. Gate: Only process if the section is defined in our Contract
        # (Using 'course_description' specifically to match your patterns.py key)
        if key in contract_fields or key == "course_description":
            
            # B. Execute the specific grammar logic from grammar.py
            # If a section (like 'units') has no grammar rule yet, it ignores softly.
            check_section_grammar(key, content, ctx)
            
        else:
            # Softly ignore sections not defined in contracts.py (headless sections)
            continue

    #if ctx.is_eligible:
        #print(f"✅ Stage 6: Body Grammar validated for {ctx.course_code}")