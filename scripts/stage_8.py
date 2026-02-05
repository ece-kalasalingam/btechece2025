import os
import json
from jinja2 import Environment, FileSystemLoader
from scripts.contracts import OUTPUT_DIR, OUTPUT_JSON_FILE, OUTPUT_SYLL_DIR, TEMPLATES_DIR, MAIN_LATEX_TEMPLATE_FILE, VIEW_CONFIG

def run_book_generation(view_type="a4"):
    if view_type not in VIEW_CONFIG:
        raise ValueError(f"Unknown view type: {view_type}")
    json_path= os.path.join(OUTPUT_DIR, OUTPUT_JSON_FILE)
    output_syll_dir = os.path.join(OUTPUT_DIR, OUTPUT_SYLL_DIR, view_type)
    try:
        os.makedirs(output_syll_dir, exist_ok=True)
    except Exception as e:
        print(f"❌ Stage 8: Failed to create directory {OUTPUT_DIR}. Error: {e}")
        return

    # Use custom delimiters [[ ]] and [% %] to avoid LaTeX { } conflicts
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        block_start_string='[%', block_end_string='%]',
        variable_start_string='[[', variable_end_string=']]'
    )

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    success_courses = data.get("success", []) # Returns a list
    warning_entries = data.get("warning", []) # Returns a list
    warning_courses = [entry["course_data"] for entry in warning_entries if "course_data" in entry]
    all_courses = success_courses + warning_courses
    template = env.get_template(MAIN_LATEX_TEMPLATE_FILE)
    rendered_book = template.render(
        courses=all_courses,
        base_template=VIEW_CONFIG[view_type]
    )

    file_name = f"syllabus_{view_type}.tex"
    with open(os.path.join(output_syll_dir, file_name), "w", encoding="utf-8") as f:
        f.write(rendered_book)
    
    # print(f"📖 Stage 8: {view_type.upper()} TeX generated.")