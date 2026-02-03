"""
STAGE 3: Validation & Articulation Driver
"""
from typing import List, Dict
from scripts.contracts import CourseMetadata, LiftedUnit, CourseComponent, ContentShape
import scripts.stage_3_regulation_audit as reg_audit
import scripts.stage_3_articulation as articulator

def run_stage_3(
    course_code: str,
    metadata: CourseMetadata,
    shape: ContentShape,
    units: List[LiftedUnit],
    course_outcomes: List[Dict] # ADDED THIS PARAMETER
) -> Dict[str, CourseComponent]:
    
    # 1. Mathematical Audit
    reg_audit.validate_r2025_quantum_alignment(course_code, metadata, units)
    
    # 2. Articulate Components 
    # Calling the updated function name from the other file
    final_components = articulator.articulate_r2025_curriculum(
        metadata, 
        units, 
        course_outcomes
    )
    
    return final_components