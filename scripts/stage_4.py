from scripts.contracts import CourseExecutionContext
from scripts.grammar import check_section_grammar

def process_body_logic(ctx: CourseExecutionContext):
    """
    STAGE-4: Body Grammar Gate.
    Applies grammar rules only to sections that have registered grammar handlers.
    """
    if not ctx.is_eligible or ctx.structure is None:
        return

    found_sections = ctx.structure.explicit_sections

    for key, content in found_sections.items():
        check_section_grammar(key, content, ctx)

    #if ctx.is_eligible:
        #print(f"✅ Stage 4: Body Grammar validated for {ctx.course_code}")