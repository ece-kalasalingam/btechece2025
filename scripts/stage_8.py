import os
import json
from jinja2 import Environment, FileSystemLoader
from scripts.contracts import (
    OUTPUT_DIR,
    OUTPUT_JSON_FILE,
    OUTPUT_SYLL_DIR,
    TEMPLATES_DIR,
    MAIN_LATEX_TEMPLATE_FILE,
    VIEW_CONFIG
)

def run_book_generation(view_type="a4"):
    if view_type not in VIEW_CONFIG:
        raise ValueError(f"Unknown view type: {view_type}")

    json_path = os.path.join(OUTPUT_DIR, OUTPUT_JSON_FILE)
    output_syll_dir = os.path.join(OUTPUT_DIR, OUTPUT_SYLL_DIR, view_type)
    os.makedirs(output_syll_dir, exist_ok=True)

    # --------------------------------------------------
    # MODEL B: Jinja templates live in templates/jinja
    # --------------------------------------------------
    jinja_templates_dir = os.path.join(TEMPLATES_DIR, "jinja")

    env = Environment(
        loader=FileSystemLoader(jinja_templates_dir),
        block_start_string='[%', block_end_string='%]',
        variable_start_string='[[', variable_end_string=']]'
    )

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    success_courses = data.get("success", [])
    warning_entries = data.get("warning", [])
    warning_courses = [
        entry["course_data"]
        for entry in warning_entries
        if "course_data" in entry
    ]

    all_courses = success_courses + warning_courses

    template = env.get_template(MAIN_LATEX_TEMPLATE_FILE)

    rendered_book = template.render(
        courses=all_courses,
        base_template=VIEW_CONFIG[view_type]
    )

    tex_path = os.path.join(output_syll_dir, f"syllabus_{view_type}.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(rendered_book)
