import os
import json
import scripts.layouts_defaults
import subprocess
from pathlib import Path
from scripts.paths import get_path
from jinja2 import Environment, FileSystemLoader
from scripts.layout_registry import get_layout

from scripts.contracts import (
    TEMP_OUTPUT_DIR,
    ACADEMIC_JSON_FILE,
    OUTPUT_SYLL_DIR,
    TEMPLATES_DIR,
    VIEW_CONFIG,
    JINJA_TEMPLATES_DIR,
    DESTINATION_DIR,
    CHECKPOINTS_DIR,
    CourseCategory
)

cleanup_exts = {
        ".aux",
        ".out",
        ".toc",
        ".lof",
        ".lot",
        ".nav",
        ".snm",
        ".fls",
        ".fdb_latexmk",
        ".synctex.gz",
        ".tex",
        ".json"
    }

# --------------------------------------------------
# PRE-FLIGHT CHECK
# --------------------------------------------------

def check_latex_env() -> bool:
    try:
        subprocess.run(
            ["xelatex", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except Exception:
        return False


# --------------------------------------------------
# STAGE 9A — COMPILE LaTeX (MODEL B)
# --------------------------------------------------

def compile_latex(view_type: str = "a4"):
    if view_type not in VIEW_CONFIG:
        raise ValueError(f"Unknown view type: {view_type}")
    #raise RuntimeError(
        #"Stage 9 (PDF compilation) is disabled in Python. "
        #"XeLaTeX must be run ONLY via GitHub Actions."
    #)
    base_dir = Path(TEMP_OUTPUT_DIR) / OUTPUT_SYLL_DIR / view_type
    tex_file = base_dir / f"syllabus_{view_type}.tex"

    if not tex_file.exists():
        raise FileNotFoundError(
            f"Stage 8: LaTeX file not found at {tex_file} or No courses were rendered."
        )

    if not check_latex_env():
        raise RuntimeError("Stage 8: XeLaTeX not available. Please ensure it is installed and in the system PATH.")
    # --------------------------------------------------
    # MODEL B: Tell XeLaTeX where templates & assets live
    # --------------------------------------------------
    env = os.environ.copy()
    env["TEXINPUTS"] = (
        str(Path("templates").resolve()) + os.pathsep +
        str(Path("assets").resolve()) + os.pathsep +
        env.get("TEXINPUTS", "")
    )

    cmd = [
        "xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        tex_file.name
    ]

    try:
        # --------------------------------------------------
        # TWO PASSES — REQUIRED FOR BOOKMARKS
        # --------------------------------------------------
        for run in range(2):
            result = subprocess.run(
                cmd,
                cwd=str(base_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:    
                # Capture the last 25 lines of the log for the error message
                log_lines = (result.stdout + "\n" + result.stderr).splitlines()[-25:]
                error_log = "\n".join(log_lines)
                
                # Raise the Runtime Error with the log details included
                raise RuntimeError(f"Stage 8: LaTeX compilation failed at pass {run + 1}. \nLast 25 lines of log:\n{error_log}")
    except Exception as e:
        raise RuntimeError(f"Stage 8: XeLaTeX execution error: {e}") from e

# --------------------------------------------------
# STAGE 9B — FINALIZE OUTPUT
# --------------------------------------------------

def finalize_output(view_type: str = "a4"):
    base_dir = Path(TEMP_OUTPUT_DIR) / OUTPUT_SYLL_DIR / view_type
    pdf_path = base_dir / f"syllabus_{view_type}.pdf"

    if not pdf_path.exists():
        raise FileNotFoundError(f"Stage 8: PDF not generated at {pdf_path}")

    if pdf_path.stat().st_size == 0:
        raise RuntimeError(f"Stage 8: Generated PDF at {pdf_path} is empty (0 bytes). Compilation likely failed silently.")
    
    dest_dir = Path(DESTINATION_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)

    final_name = f"KARE_Syllabus_{view_type}.pdf"
    pdf_path.replace(dest_dir / final_name)

# --------------------------------------------------
# STAGE 9C — CLEAN THE FOLDERS
# 
def cleanup_artifacts(view_type: str = "a4"):
    """
    Removes LaTeX auxiliary files generated during Stage 9.
    Keeps the .log file for debugging/audit purposes.
    """

    base_dir = Path(TEMP_OUTPUT_DIR) / OUTPUT_SYLL_DIR / view_type

    # Explicit whitelist of extensions to remove
    

    for item in base_dir.iterdir():
        if not item.is_file():
            continue

        # Handle .synctex.gz separately
        if item.name.endswith(".synctex.gz"):
            item.unlink(missing_ok=True)
            continue

        if item.suffix in cleanup_exts:
            item.unlink(missing_ok=True)

def cleanup_checkpoints():
    """
    Removes LaTeX auxiliary files generated during Stage 9.
    Keeps the .log file for debugging/audit purposes.
    """

    base_dir = Path(TEMP_OUTPUT_DIR) / CHECKPOINTS_DIR

    # Explicit whitelist of extensions to remove
    

    for item in base_dir.iterdir():
        if not item.is_file():
            continue

        # Handle .synctex.gz separately
        if item.name.endswith(".synctex.gz"):
            item.unlink(missing_ok=True)
            continue

        if item.suffix in cleanup_exts:
            item.unlink(missing_ok=True)


def generate_pdf(view_type="a4"):
    if view_type not in VIEW_CONFIG:
        raise ValueError(f"Invalid view type: {view_type}")

    json_path = get_path(TEMP_OUTPUT_DIR, ACADEMIC_JSON_FILE)
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

    total_count = 0

    for cat in CourseCategory:
        category = cat.code
        courses = courses_by_category.get(category, [])

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

    output_syll_dir = os.path.join(TEMP_OUTPUT_DIR, OUTPUT_SYLL_DIR, view_type)
    os.makedirs(output_syll_dir, exist_ok=True)

    # --------------------------------------------------
    # MODEL B: Jinja templates live in templates/jinja
    # --------------------------------------------------
    jinja_templates_dir = get_path(TEMPLATES_DIR, JINJA_TEMPLATES_DIR)

    env = Environment(
        loader=FileSystemLoader(jinja_templates_dir),
        block_start_string='[%', block_end_string='%]',
        variable_start_string='[[', variable_end_string=']]'
    )
    
    view_config = VIEW_CONFIG.get(view_type)

    if not view_config:
        raise RuntimeError(f"No configuration found for view '{view_type}'")

    template_name = view_config.get("template")

    if not template_name:
        raise RuntimeError(f"No LaTeX template configured for view '{view_type}'")
    layout = get_layout(view_type)

    template = env.get_template(template_name)

    category_order = [
        {
            "code": cat.code,
            "full_name": cat.full_name
        }
        for cat in CourseCategory
    ]

    rendered_book = template.render(
        courses=courses_by_category,
        layout=layout,
        category_order=category_order
    )

    tex_path = os.path.join(output_syll_dir, f"syllabus_{view_type}.tex")
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(rendered_book)
    
    compile_latex(view_type)
    finalize_output(view_type)
    cleanup_artifacts(view_type)
    cleanup_checkpoints()