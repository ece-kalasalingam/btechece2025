import re
from scripts.contracts import CourseExecutionContext

def _validate_description_grammar(content: str, ctx: CourseExecutionContext):
    """
    Grammar rules for Course Description:
    1. Must be substantial (at least 15 words).
    2. Must be prose (no bullet points at the start of the block).
    """
    text = content.strip()
    if not text:
        return # Basic empty check is handled in Stage 2

    # Rule 1: Length check
    words = text.split()
    if len(words) < 15:
        ctx.log(
            stage="STAGE-6",
            code="DESC-TOO-SHORT",
            msg="Course Description is too brief. It must be at least 15 words.",
            fatal=True
        )

    # Rule 2: Prose check (No bullets)
    # Check if the text starts with common markdown/text bullet symbols
    if re.match(r"^[\s]*[-*•\d\.]", text):
        ctx.log(
            stage="STAGE-6",
            code="DESC-NOT-PROSE",
            msg="Course Description must be written in prose paragraphs, not as a list.",
            fatal=False # Warnings for formatting issues
        )

# Map of canonical keys to their specific grammar functions.
# Other sections will be added to this map one by one later.
_GRAMMAR_REGISTRY = {
    "course_description": _validate_description_grammar
}

def check_section_grammar(key: str, content: str, ctx: CourseExecutionContext):
    """
    Dispatches content to the appropriate logic based on the section key.
    """
    handler = _GRAMMAR_REGISTRY.get(key)
    if handler:
        handler(content, ctx)
        