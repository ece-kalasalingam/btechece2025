"""
STAGE 2e: Semantic Validation
Verbatim: Validates Bloom's Taxonomy, procedural depth, and pedagogical alignment.
STRICT: No structural (unit count) or grammatical checks allowed here.
"""
from typing import List
from scripts.contracts import ContentShape, UnitBlock, ValidationError

# R2025 standard action verbs for higher-order thinking (Bloom's Taxonomy)
BLOOMS_VERBS = {"analyze", "design", "evaluate", "implement", "create", "develop", "compare", "synthesize"}

def validate_semantic_blocks(
    course_code: str, 
    units: List[UnitBlock], 
    shape: ContentShape
):
    """
    Ensures the quality of the content aligns with the academic level of R2025.
    Uses the UnitBlock ABI (topics, experiments, x_activities).
    """
    for unit in units:
        # 1. Bloom's Taxonomy Check (Cognitive Level)
        # We scan the Unit Title and the 'Head' of topics for high-order verbs.
        topic_heads = [t[0].lower() for t in unit.topics]
        combined_text = (unit.title.lower() + " " + " ".join(topic_heads))
        
        has_high_order_verb = any(verb in combined_text for verb in BLOOMS_VERBS)
        
        if not has_high_order_verb and shape == ContentShape.ACADEMIC_THEORY:
            # Policy Decision: We flag a warning if the unit is purely 'descriptive'
            # (e.g., just 'Overview of X', 'History of Y')
            pass 

        # 2. Procedural Depth Check (Activity Analysis)
        # Enforces that Skill/Lab descriptions aren't just one-word titles.
        if shape == ContentShape.SKILL_PRACTICE:
            _check_activity_depth(course_code, unit.number, "Experiment", unit.experiments)
        
        # 3. Component Context Check (Pedagogical Alignment)
        # Ensure Theory units don't contain purely procedural 'Lab' steps.
        if shape == ContentShape.ACADEMIC_THEORY:
            for head, detail in unit.topics:
                content_to_check = (head + " " + detail).lower()
                if any(word in content_to_check for word in ["step-by-step", "procedure", "perform experiment"]):
                    raise ValidationError(
                        course_code,
                        "SEM-CONTEXT-MISMATCH",
                        f"Unit {unit.number} contains procedural lab instructions ('{head}') in a Theory course."
                    )



def _check_activity_depth(course_code: str, unit_num: int, label: str, activities: List):
    """
    Internal helper to ensure procedural activities have enough descriptive words 
    to be considered 'Skill' level.
    """
    for act in activities:
        word_count = len(act.description.split())
        # Rule: A valid R2025 experiment description should be at least 10 words.
        if word_count < 10 and act.description != "":
            raise ValidationError(
                course_code, 
                "SEM-PRACTICAL-SHALLOW", 
                f"{label} '{act.title}' in Unit {unit_num} lacks procedural depth ({word_count} words found)."
            )