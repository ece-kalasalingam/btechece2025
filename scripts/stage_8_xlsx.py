from scripts.paths import get_path
import json
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.styles import Border, Side

from scripts.contracts import (
    OUTPUT_DIR,
    OUTPUT_JSON_FILE,
    DESTINATION_DIR
)
json_path = get_path(OUTPUT_DIR, OUTPUT_JSON_FILE)
thin = Side(style="thin")
full_border = Border(left=thin, right=thin, top=thin, bottom=thin)

def autosize_columns(ws):
    for col_idx, column_cells in enumerate(ws.columns, start=1):
        max_length = 0
        for cell in column_cells:
            if cell.value is not None:
                max_length = max(max_length, len(str(cell.value)))

        adjusted_width = max_length + 2  # padding
        ws.column_dimensions[get_column_letter(col_idx)].width = adjusted_width

def generate_excel_courses_list():
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    for category, courses in data.get("courses", {}).items():
        for course in courses:
            meta = course.get("course_meta", {})
            course_code = course.get("course_code", "")
            course_title = meta.get("course_title", "")
            course_category = meta.get("course_category", "")
            course_l = meta.get("l", "")
            course_t = meta.get("t", "")
            course_p = meta.get("p", "")
            course_x = meta.get("x", "")
            course_c = meta.get("c", "")
            rows.append({
                "Course Code": course_code,
                "Course Title": course_title,
                "Course Category": course_category,
                "L": course_l,
                "T": course_t,
                "P": course_p,
                "X": course_x,
                "C": course_c
            })
    try:
        df = pd.DataFrame(rows)
        out_path = get_path(DESTINATION_DIR, "Courses_List.xlsx")
        df.to_excel(out_path, index=False, engine="openpyxl")
        wb = load_workbook(out_path)
        ws = wb.active
        if ws is None:
            raise RuntimeError("Workbook has no active worksheet")
        ws.freeze_panes = "A2"
        center_align = Alignment(horizontal="center", vertical="center")

        # Column headers you want centered
        center_columns = {"Course Category", "L", "T", "P", "X", "C"}

        # Map header names to column indices
        header_row = 1
        for col_idx, cell in enumerate(ws[header_row], start=1):
            if cell.value in center_columns:
                for row in ws.iter_rows(
                    min_row=2,
                    min_col=col_idx,
                    max_col=col_idx
                ):
                    row[0].alignment = center_align

        for col_idx, column_cells in enumerate(ws.columns, start=1):
            max_length = 0
            for cell in column_cells:
                if cell.value is not None:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[get_column_letter(col_idx)].width = max_length + 2
        
        for row in ws.iter_rows(
            min_row=1,
            max_row=ws.max_row,
            min_col=1,
            max_col=ws.max_column
        ):
            for cell in row:
                cell.border = full_border
        
        wb.save(out_path)
        print(f"✅ Excel file generated: {out_path}")
    except Exception as e:
        print(f"❌ Failed to generate Excel file: {e}")