"""
=====================================================================
STAGE-4 : MASTERDATA CONSTRUCTION (KARE R2025)
=====================================================================

- Produces canonical masterdata.json
- No validation
- No rendering
- No inference
=====================================================================
"""

from datetime import date
from masterdata_schema import empty_masterdata

def to_primitive(x):
    """Converts Enums to values and other objects to strings for JSON safety."""
    return x.value if hasattr(x, "value") else str(x)

def build_content_blocks(content_shape, units):
    blocks = []

    if content_shape in {"Academic-Theory", "Academic-Integrated"}:
        for u in units:
            blocks.append({
                "block_type": "unit",
                "id": f"U{u.unit_no}",
                "title": u.title,
                "topics": u.topics,
                "experiments": getattr(u, "experiments", []),
                "hours": u.hours
            })

    elif content_shape == "Skill-Practice":
        for u in units:
            blocks.append({
                "block_type": "module",
                "id": u.unit_id,
                "activities": u.activities,
                "hours": u.hours
            })

    elif content_shape == "Project":
        blocks.append({
            "block_type": "project",
            "description": units[0].description,
            "hours": units[0].hours
        })

    return blocks

def add_course_to_masterdata(masterdata, course_data):
    shape_str = to_primitive(course_data["content_shape"])
    status = "OK"
    if course_data["warnings"]:
        status = "WARN"

    masterdata["courses"].append({
        "course_code": course_data["course_code"],
        "course_title": course_data["course_title"],
        "status": status,

        "metadata": {
            "category": to_primitive(course_data["metadata"].category),
            "course_type": to_primitive(course_data["metadata"].course_type),
            "ltpxc": {
                "l": course_data["metadata"].l,
                "t": course_data["metadata"].t,
                "p": course_data["metadata"].p,
                "x": course_data["metadata"].x,
                "c": course_data["metadata"].c
            }
        },

        "content_shape": shape_str,

        "content_blocks": build_content_blocks(
            shape_str,
            course_data["units"]
        ),

        "course_outcomes": course_data["course_outcomes"],

        "tools": course_data.get("tools", []),

        "references": course_data.get("references", {}),

        "warnings": [
            {
                "code": w.code,
                "message": w.message
            } for w in course_data["warnings"]
        ]
    })

def add_failed_course(masterdata, course_code, error):
    masterdata["courses"].append({
        "course_code": course_code,
        "status": "ERROR",
        "error": error
    })


def finalize_masterdata(masterdata, errors, warnings):
    masterdata["meta"]["generated_on"] = date.today().isoformat()
    masterdata["errors"] = errors
    masterdata["warnings"] = warnings
    return masterdata