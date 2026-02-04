"""
STAGE 5: Final Serialization
Verbatim: Writes the final verified MasterData to disk. 
STRICT: No interpretation, no mapping, no key-renaming.
"""
import json
import os
import logging

from scripts.contracts import OUTPUTS_DIRNAME

def generate_verified_output(
    final_masterdata: dict,
    output_dir: str = OUTPUTS_DIRNAME
) -> str:
    """
    Serializes the dictionary provided by the previous stages as-is.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Use course_code for the filename, which is guaranteed to exist in MasterData
    course_code = final_masterdata.get("course_code", "unknown_course")
    output_path = os.path.join(output_dir, f"{course_code}_verified.json")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # We use indent=4 to make it human-readable for GitHub audits
            json.dump(final_masterdata, f, indent=4)
        
        logging.info(f"✅ Stage 5: MasterData serialized to {output_path}")
        return output_path
    
    except Exception as e:
        logging.error(f"❌ Stage 5: Failed to write output: {e}")
        raise