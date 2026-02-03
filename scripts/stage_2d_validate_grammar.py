"""
STAGE 2d: Grammar Validation
Verbatim: Enforces content-specific rules based on the detected ContentShape.
"""
from typing import List
from scripts.contracts import ContentShape, LiftedUnit, ValidationError

def validate_content_blocks(
    course_code: str, 
    units: List[LiftedUnit], 
    shape: ContentShape
):
    """
    Branching logic to ensure Units contain the correct 'parts of speech'.
    """
    for unit in units:
        # --- 1. Gating for ACADEMIC shapes (Theory/Integrated) ---
        if shape in [ContentShape.ACADEMIC_THEORY, ContentShape.ACADEMIC_INTEGRATED]:
            # Academic units MUST have topics (bullet points)
            if not unit.topics:
                raise ValidationError(
                    course_code, 
                    "GRAM-MISSING-TOPICS", 
                    f"Unit {unit.number} in an Academic course must contain at least one topic."
                )
            
            # Validation of topic length or format
            for topic in unit.topics:
                if len(topic) < 5:
                    raise ValidationError(
                        course_code, "GRAM-TOPIC-SHORT", 
                        f"Topic in Unit {unit.number} is too brief to be descriptive."
                    )

        # --- 2. Gating for SKILL_PRACTICE / LAB shapes ---
        elif shape == ContentShape.SKILL_PRACTICE:
            # Skill units MUST have activities/experiments
            if not unit.activities:
                raise ValidationError(
                    course_code, 
                    "GRAM-MISSING-ACTIVITIES", 
                    f"Unit {unit.number} in a Skill/Lab course must contain at least one activity/experiment."
                )

        # --- 3. Gating for PROJECT shapes ---
        elif shape == ContentShape.PROJECT:
            # We already validated in 2c that Projects shouldn't have units, 
            # but as a failsafe, we ensure no stray units made it here.
            pass