"""
PIPELINE STAGE: 2 (Orchestrator)
Verbatim: Coordinates the execution of 2a through 2f.
It delegates the "heavy lifting" of state-machine parsing to stage_2_semantic_lift.
"""
import re
from typing import List, Tuple, Dict
from scripts.contracts import (
    CourseMetadata, 
    ValidationWarning, 
    ContentShape,
    UnitBlock,
    StructuredSection
)

# Import Worker Modules
import scripts.stage_2a_extract_metadata as meta_extractor
import scripts.stage_2b_infer_shape as shape_engine
import scripts.stage_2b1_co_extractor as co_extractor
import scripts.stage_2c_validate_structure as struct_validator
import scripts.stage_2c2_semantic_lift as semantic_lifter 
import scripts.stage_2d_validate_grammar as grammar_validator
import scripts.stage_2e_validate_semantics as semantic_validator
import scripts.stage_2f_validate_regulations as reg_validator

def run_stage_2(
    course_code: str, 
    structured_sections: List[StructuredSection]
) -> Tuple[CourseMetadata, ContentShape, List[UnitBlock],  List[Dict], List[ValidationWarning]]:
    """
    Orchestrates the transition from Raw StructuredSections to Enriched UnitBlocks.
    """
    warnings: List[ValidationWarning] = []

    # 1. Metadata Extraction (Stage 2a)
    metadata = meta_extractor.extract_course_metadata(course_code, structured_sections)

    # 2. Shape Inference (Stage 2b)
    shape_input = shape_engine.InferenceInput(
        course_code=course_code,
        category=metadata.category,
        course_type=metadata.course_type
    )
    content_shape = shape_engine.infer_content_shape(shape_input)

    # 2b1. Extract the Course Outcomes
    extracted_cos = co_extractor.extract_course_outcomes(structured_sections)

    # 3. Structural Validation (Stage 2c)
    # Identifies the 5 Unit sections and ensures they exist.
    struct_validator.validate_course_structure(course_code, structured_sections, content_shape)

    # 4. SEMANTIC LIFTING (Stage 2C2_Semantic_Lift)
    # Delegated: Transforms raw markdown into UnitBlock objects and captures hour strings.
    units, contexts = semantic_lifter.lift_units_strictly(structured_sections)

    # 5. GRAMMAR VALIDATION (Stage 2d)
    # Syntax-only check: Colon rules in topics and bullet-nesting in activities.
    grammar_validator.validate_content_blocks(course_code, units, content_shape)

    # 6. SEMANTIC QUALITY CHECK (Stage 2e)
    # Pedagogical check: Bloom's Taxonomy and procedural depth.
    semantic_validator.validate_semantic_blocks(course_code, units, content_shape)

    # 7. REGULATORY ENRICHMENT & LEGALITY (Stage 2f)
    # Numeric check: Casts hour strings, checks TC/PC/IC legality, and runs credit math.
    reg_validator.enrich_and_legalize(course_code, units, contexts, metadata)
    
    # Final Regulation Policy Check against Metadata
    reg_validator.validate_basic_metadata(course_code, metadata)
    reg_validator.validate_regulation_policies(course_code, metadata, content_shape, warnings)

    return metadata, content_shape, units, extracted_cos, warnings