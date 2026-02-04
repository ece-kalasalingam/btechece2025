"""
STAGE 2d: Grammar Validation
Verbatim: Acts as a Syntax Checker for the UnitBlock. 
Enforces colon-rules, bullet-nesting, and string length constraints.
"""
from typing import List
from scripts.contracts import ContentShape, UnitBlock, ValidationError

def validate_content_blocks(
    course_code: str, 
    units: List[UnitBlock], 
    shape: ContentShape
):
    """
    Syntax-only validation. 
    Checks the 'form' of the data, not the 'legality' of the credits.
    """
    for unit in units:
        # 1. Theory Topic Grammar (Colon Rules)
        # We expect [(Topic_Head, Topic_Detail), ...]
        if shape in [ContentShape.ACADEMIC_THEORY, ContentShape.ACADEMIC_INTEGRATED]:
            if not unit.topics:
                raise ValidationError(
                    course_code, 
                    "GRAM-MISSING-TOPICS", 
                    f"Unit {unit.number} lacks theory topics."
                )

            for head, detail in unit.topics:
                # Rule: Topic must have a head (before colon)
                if len(head) < 3:
                    raise ValidationError(
                        course_code, "GRAM-TOPIC-SHORT", 
                        f"Topic head '{head}' in Unit {unit.number} is too brief."
                    )
                
                # Rule: Atomic Split must have resulted in a detail (after colon)
                if not detail or len(detail) < 5:
                    raise ValidationError(
                        course_code, "GRAM-MALFORMED-COLON", 
                        f"Topic '{head}' in Unit {unit.number} is missing required colon-separated details."
                    )

        # 2. Activity Bullet Shape (Nesting Rules)
        # Applies to both Practical and X-Activity lists
        _validate_activity_shape(course_code, unit.number, "Practical", unit.experiments)
        _validate_activity_shape(course_code, unit.number, "X-Activity", unit.x_activities)

        # 3. Articulation Syntax (CO Tokens)
        # Ensure the extracted indices are present if the mode reached content
        # Note: Semantic range check (e.g. CO6 vs 5 COs) happens in Stage 3.
        if not unit.raw_co_indices and shape != ContentShape.PROJECT:
            # We raise a grammar error if no CO tokens were found in the header
            raise ValidationError(
                course_code, 
                "GRAM-MISSING-CO-MAP", 
                f"Unit {unit.number} header is missing valid CO tokens (e.g., 'COs: 1, 2')."
            )

def _validate_activity_shape(course_code: str, unit_num: int, label: str, activities: List):
    """
    Helper to ensure every 'Title' bullet has a corresponding 'Description' sub-bullet.
    """
    for act in activities:
        # Check Title Grammar
        if len(act.title) < 5:
            raise ValidationError(
                course_code, 
                "GRAM-ACT-TITLE-SHORT", 
                f"{label} title '{act.title}' in Unit {unit_num} is too short."
            )
        
        # Check Nesting Grammar (Description must not be empty)
        # This enforces that the parser successfully found sub-bullets.
        if not act.description or len(act.description.strip()) < 10:
            raise ValidationError(
                course_code, 
                "GRAM-ACT-NESTING-FAIL", 
                f"{label} '{act.title}' in Unit {unit_num} must have a detailed sub-bullet description."
            )