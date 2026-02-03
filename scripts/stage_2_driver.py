"""
PIPELINE STAGE: 2 (Driver / Orchestrator)
Verbatim: Coordinates 2a-2f and performs "Semantic Lifting".
"""
import re
from typing import List, Tuple, Dict

# Import shared contracts
from scripts.contracts import (
    CourseMetadata, 
    ValidationWarning, 
    ContentShape,
    BlockType,
    LiftedUnit,
    LiftedActivity,
    StructuredSection
)

# Import Stage 1 structures
from scripts.stage_1_parsing import (
    find_sections_by_title_pattern, 
    split_title_paragraph,
    extract_header_hours
)

# Import Worker Modules
import scripts.stage_2a_extract_metadata as meta_extractor
import scripts.stage_2b_infer_shape as shape_engine
import scripts.stage_2c_validate_structure as struct_validator
import scripts.stage_2d_validate_grammar as grammar_validator
import scripts.stage_2e_validate_semantics as semantic_validator
import scripts.stage_2f_validate_regulations as reg_validator

def run_stage_2(
    course_code: str, 
    structured_sections: List[StructuredSection]
) -> Tuple[CourseMetadata, ContentShape, List[LiftedUnit], List[Dict], List[ValidationWarning]]:
    
    warnings: List[ValidationWarning] = []

    # 1. Metadata Extraction
    metadata = meta_extractor.extract_course_metadata(course_code, structured_sections)
    reg_validator.validate_basic_metadata(course_code, metadata)

    # 2. Shape Inference
    content_shape = shape_engine.infer_content_shape(
        shape_engine.InferenceInput(
            course_code=course_code,
            category=metadata.category,
            course_type=metadata.course_type
        )
    )

    # 3. Unit Discovery & Structure Validation
    unit_pattern = re.compile(r"unit\s+\d+", re.I)
    unit_sections = find_sections_by_title_pattern(structured_sections, unit_pattern)
    struct_validator.validate_course_structure(course_code, unit_sections, content_shape)

    # 4. Course Outcome (CO) Extraction (FIX: Defining 'outcomes')
    # We look for the section titled "Course Outcomes"
    outcomes = _extract_course_outcomes(structured_sections)

    # 5. Semantic Lifting (Units and Hours)
    units = _lift_units_by_shape(course_code, unit_sections, content_shape)

    # 6. Content Validation
    reg_validator.validate_regulation_policies(course_code, metadata, content_shape, warnings)
    grammar_validator.validate_content_blocks(course_code, units, content_shape)
    semantic_validator.validate_semantic_blocks(course_code, units, content_shape)

    # FIX: Returning the 5-tuple expected by run_pipeline.py
    return metadata, content_shape, units, outcomes, warnings

def _extract_course_outcomes(sections: List[StructuredSection]) -> List[Dict]:
    """
    Locates the CO section and converts bullets into a list of outcome dictionaries.
    """
    co_pattern = re.compile(r"course\s+outcomes", re.I)
    co_sections = find_sections_by_title_pattern(sections, co_pattern)
    
    outcomes = []
    if co_sections:
        # Assuming the first matching section contains the COs
        for block in co_sections[0].blocks:
            if block.type == BlockType.BULLET:
                # Simple split logic: "K3 - Describe..." -> level: K3, text: Describe...
                content = block.content.strip()
                level_match = re.match(r"(K\d)", content)
                level = level_match.group(1) if level_match else "Unknown"
                outcomes.append({"level": level, "text": content})
                
    return outcomes

def _lift_units_by_shape(
    course_code: str, 
    unit_sections: List[StructuredSection], 
    shape: ContentShape
) -> List[LiftedUnit]:
    # ... (Keep your existing _lift_units_by_shape logic here) ...
    lifted_units = []
    for idx, s_sec in enumerate(unit_sections, 1):
        th_h, pr_h, x_h = extract_header_hours(s_sec.section.title)
        unit = LiftedUnit(
            number=idx, 
            title=s_sec.section.title,
            theory_hours=th_h,
            lab_hours=pr_h,
            x_hours=x_h
        )
        # ... logic for topics/activities ...
        lifted_units.append(unit)
    return lifted_units