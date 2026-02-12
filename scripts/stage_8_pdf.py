import os
import json
from scripts.paths import get_path
from jinja2 import Environment, FileSystemLoader
from scripts.layout_registry import get_layout
import scripts.layouts_defaults 

from scripts.contracts import (
    OUTPUT_DIR,
    OUTPUT_JSON_FILE,
    OUTPUT_SYLL_DIR,
    TEMPLATES_DIR,
    JINJA_TEMPLATES_DIR,
    MAIN_LATEX_TEMPLATE_FILE,
    VIEW_CONFIG,
    CATEGORY_ORDER
)
json_path = get_path(OUTPUT_DIR, OUTPUT_JSON_FILE)

def generate_pdf(view_type="a4"):
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

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    courses_by_category = data.get("courses", {})
    courses_by_category_count = sum(len(courses) for courses in courses_by_category.values())
    if (not courses_by_category) or courses_by_category_count == 0:
        print("❌ Stage 8: No courses found in the JSON data. Skipping PDF generation.")
        return
    layout = get_layout(view_type)

    template = env.get_template("base.tex.j2")

    rendered_book = template.render(
        courses=courses_by_category,
        category_order=CATEGORY_ORDER,
        layout=layout
    )

    tex_path = os.path.join(output_syll_dir, f"syllabus_{view_type}.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(rendered_book)