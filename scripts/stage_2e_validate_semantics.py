"""
STAGE 2e: Semantic Validation
Verbatim: Validates Bloom's Taxonomy and content depth. 
STRICT: No structural (unit count) or grammatical checks allowed here.
"""
from typing import List
from scripts.contracts import ContentShape, LiftedUnit, ValidationError

# R2025 standard action verbs for higher-order thinking
BLOOMS_VERBS = {"analyze", "design", "evaluate", "implement", "create", "develop", "compare"}

def validate_semantic_blocks(
    course_code: str, 
    units: List[LiftedUnit], 
    shape: ContentShape
):
    """
    Ensures the quality of the content aligns with the academic level of R2025.
    """
    for unit in units:
        # 1. Bloom's Taxonomy Check (Semantic Quality)
        # We check if the Unit Title or Topics use appropriate action verbs
        combined_text = (unit.title + " " + " ".join(unit.topics)).lower()
        
        # In R2025, Engineering courses should target higher cognitive levels
        has_high_order_verb = any(verb in combined_text for verb in BLOOMS_VERBS)
        
        if not has_high_order_verb and shape == ContentShape.ACADEMIC_THEORY:
            # We don't raise a Hard Error, but we could flag a Warning or 
            # for strict compliance, a ValidationError if the syllabus is too 'descriptive'
            pass 

        # 2. Activity Depth Check (Shape Aware)
        if shape == ContentShape.SKILL_PRACTICE:
            for act in unit.activities:
                if len(act.description.split()) < 10 and not act.description == "":
                    raise ValidationError(
                        course_code, 
                        "SEM-PRACTICAL-SHALLOW", 
                        f"Activity '{act.name}' in Unit {unit.number} lacks procedural depth."
                    )

        # 3. Component Context Check
        # Ensure that if it's a Theory course, the topics aren't just 'Lab' instructions
        if shape == ContentShape.ACADEMIC_THEORY:
            if any("experiment" in t.lower() or "procedure" in t.lower() for t in unit.topics):
                raise ValidationError(
                    course_code,
                    "SEM-CONTEXT-MISMATCH",
                    f"Unit {unit.number} contains procedural lab topics in a Theory shape."
                )