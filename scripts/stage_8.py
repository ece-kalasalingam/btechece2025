from scripts.stage_8_xlsx import generate_excel_courses_list
from scripts.stage_8_docx import generate_word_co_bloom
from scripts.stage_8_pdf import generate_pdf

from scripts.contracts import (
    VIEW_CONFIG
)

OTHER_VIEW_HANDLERS = {
    "xlsx-courses-list": generate_excel_courses_list,
    "docx-co-bloom": generate_word_co_bloom
    # we can add more handlers here in the future if needed
}

def run_book_generation(view_type="a4"):
    if view_type not in VIEW_CONFIG:
        raise ValueError(f"Unknown view type: {view_type}")
    if view_type.startswith("xlsx") or view_type.startswith("docx"):
        handler = OTHER_VIEW_HANDLERS.get(view_type)
        if not handler:
            raise ValueError(f"No handler for view: {view_type}")
        handler()
        return
    # For PDF views, use the PDF generation logic
    generate_pdf(view_type=view_type) 
