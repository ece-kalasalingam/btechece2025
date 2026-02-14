import os
import json
from scripts.paths import get_path
from jinja2 import Environment, FileSystemLoader
from scripts.layout_registry import get_layout

from scripts.contracts import (
    OUTPUT_DIR,
    ACADEMIC_JSON_FILE,
    OUTPUT_SYLL_DIR,
    TEMPLATES_DIR,
    VIEW_CONFIG,
    JINJA_TEMPLATES_DIR,
    MAIN_LATEX_TEMPLATE_FILE,
    CourseCategory
)
import scripts.layouts_defaults

def generate_pdf(view_type="a4"):
    if view_type not in VIEW_CONFIG:
        raise ValueError(f"Invalid view type: {view_type}")

    json_path = get_path(OUTPUT_DIR, ACADEMIC_JSON_FILE)
    if not os.path.exists(json_path):
        raise FileNotFoundError(
            f"Stage 8: Academic JSON file not found at {json_path}"
        )
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if "courses" not in data:
        raise ValueError("Stage 8: Missing 'courses' key in academic JSON.")
    
    courses_by_category = data["courses"]
    if not isinstance(courses_by_category, dict):
        raise TypeError("Stage 8: 'courses' must be a dictionary.")
    if not courses_by_category:
        raise RuntimeError("Stage 8: 'courses' dictionary is empty.")

    valid_categories = {cat.code for cat in CourseCategory}

    total_count = 0

    for category, courses in courses_by_category.items():

        if not isinstance(category, str):
            raise TypeError("Stage 8: Category keys must be strings.")

        if category not in valid_categories:
            raise ValueError(
                f"Stage 8: Invalid course category '{category}'. "
                f"Must be one of {sorted(valid_categories)}."
            )

        if not isinstance(courses, list):
            raise TypeError(
                f"Stage 8: Category '{category}' must contain a list of courses."
            )

        for course in courses:
            if not isinstance(course, dict):
                raise TypeError(
                    f"Stage 8: Course in category '{category}' must be a dictionary."
                )
            if "course_code" not in course:
                raise ValueError(
                    f"Stage 8: Course missing 'course_code' in category '{category}'."
                )

        total_count += len(courses)

    if total_count == 0:
        raise RuntimeError(
            "Stage 8: Categories exist but contain zero courses."
        )

    ordered_categories = [
        {
            "code": cat.code,
            "full_name": cat.full_name
        }
        for cat in CourseCategory
    ]    

    output_syll_dir = os.path.join(OUTPUT_DIR, OUTPUT_SYLL_DIR, view_type)
    os.makedirs(output_syll_dir, exist_ok=True)

    # --------------------------------------------------
    # MODEL B: Jinja templates live in templates/jinja
    # --------------------------------------------------
    jinja_templates_dir = os.path.join(TEMPLATES_DIR, JINJA_TEMPLATES_DIR)

    env = Environment(
        loader=FileSystemLoader(jinja_templates_dir),
        block_start_string='[%', block_end_string='%]',
        variable_start_string='[[', variable_end_string=']]'
    )
    
    layout = get_layout(view_type)

    template = env.get_template(MAIN_LATEX_TEMPLATE_FILE)

    rendered_book = template.render(
        courses=courses_by_category,
        category_order=ordered_categories,
        layout=layout
    )

    tex_path = os.path.join(output_syll_dir, f"syllabus_{view_type}.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(rendered_book)