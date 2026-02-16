from scripts.stage_8_xlsx import generate_excel_courses_list
from scripts.stage_8_docx import generate_word_co_bloom
from scripts.stage_8_pdf import generate_pdf

from scripts.contracts import (
    VIEW_CONFIG
)
from scripts.utils import validate_environment_for_view

OTHER_VIEW_HANDLERS = {
    "courses-list": generate_excel_courses_list,
    "co-bloom": generate_word_co_bloom
    # we can add more handlers here in the future if needed
}

def run_book_generation(view_type="a4"):
    if view_type not in VIEW_CONFIG:
        raise ValueError(f"Unknown view type: {view_type}")
    view_config = VIEW_CONFIG.get(view_type, {})
    if view_config is None:
        raise ValueError(f"No configuration found for view type: {view_type}")  
    #if view_config.get("requires_pdf", False):
    if not validate_environment_for_view(view_type):
        raise RuntimeError(f"Stage 8 : Environment not suitable for generating view: {view_type}")
    if view_config.get("ext") == "pdf":
        generate_pdf(view_type=view_type)
    else:
        handler = OTHER_VIEW_HANDLERS.get(view_type)
        if not handler:
            raise ValueError(f"No handler for view: {view_type}")
        handler(view_type=view_type)