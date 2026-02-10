from typing import List
from scripts.patterns import (
    TABLE_ROW_PATTERN,
    TABLE_SEPARATOR_PATTERN,
    H3_PATTERN,
    H4_PATTERN,
    BLOCK_MATH_PATTERN,
    LATEX_ENV_PATTERN,
)
from scripts.utils import get_column_cells

def sanitize_dollar(text: str) -> str:
    """
    If the number of $ is odd, treat $ as literal currency
    and escape all of them.
    """
    if text.count("$") % 2 == 1:
        return text.replace("$", r"\$")
    return text

def escape_latex(text: str) -> str:
    # If the cell contains math (balanced $), don't escape the contents of the math
    if text.count("$") >= 2 and text.count("$") % 2 == 0:
        # This is a simple way to preserve math while escaping other text
        return text 
    
    # Otherwise, escape standard LaTeX special chars
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "|": r"|", # Keep pipe as is, or use \textbar{}
        "\\": r"\textbackslash{}", # Crucial: escape literal backslashes
        "^": r"\textasciicircum{}"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

class MarkdownToLatexConverter:
    def __init__(self):
        self.output: List[str] = []
        self.in_itemize = False

    # ---------- state ----------
    def close_lists(self):
        if self.in_itemize:
            self.output.append(r"\end{itemize}")
            self.in_itemize = False

    # ---------- table ----------
    def emit_table(self, headers, rows):
        self.close_lists()

        col_spec = "|" + "|".join(["X"] * len(headers)) + "|"
        self.output.append(r"\begin{tabularx}{\textwidth}{" + col_spec + "}")
        self.output.append(r"\hline")

        self.output.append(
            " & ".join(r"\textbf{" + escape_latex(h) + "}" for h in headers) + r" \\"
        )
        self.output.append(r"\hline")

        for row in rows:
            processed_cells = [escape_latex(cell) for cell in row]
            self.output.append(" & ".join(processed_cells) + r" \\")
            self.output.append(r"\hline")

        self.output.append(r"\end{tabularx}")
        self.output.append(r"\par")

    def handle_table(self, lines, start):
        headers = get_column_cells(lines[start])
        rows = []

        i = start + 2  # skip separator
        while i < len(lines) and TABLE_ROW_PATTERN.match(lines[i]):
            rows.append(get_column_cells(lines[i]))
            i += 1

        self.emit_table(headers, rows)
        return i

    # ---------- line ----------
    def handle_line(self, line: str):
        stripped = line.strip()

        # Raw LaTeX env or math
        if LATEX_ENV_PATTERN.search(stripped) or BLOCK_MATH_PATTERN.search(stripped):
            self.close_lists()
            self.output.append(stripped)
            return

        # Empty
        if not stripped:
            self.output.append(r"\par")
            return

        # Headings
        if H3_PATTERN.match(stripped):
            self.close_lists()
            self.output.append(r"\textbf{" + escape_latex(stripped[4:]) + r"}")
            self.output.append(r"\par")
            return

        if H4_PATTERN.match(stripped):
            self.close_lists()
            self.output.append(r"\textit{" + escape_latex(stripped[5:]) + r"}")
            self.output.append(r"\par")
            return

        if stripped.startswith("#"):
            self.close_lists()
            self.output.append(escape_latex(stripped.lstrip("#").strip()))
            self.output.append(r"\par")
            return

        # Bullet list
        if stripped.startswith("- "):
            if not self.in_itemize:
                self.output.append(r"\begin{itemize}[leftmargin=*, nosep]")
                self.in_itemize = True
            self.output.append(r"\item " + escape_latex(stripped[2:]))
            return

        # Paragraph
        self.close_lists()
        self.output.append(escape_latex(stripped))
        self.output.append(r"\par")

    # ---------- entry ----------
    def convert(self, markdown: str) -> str:
        lines = markdown.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i]

            # Table detection (grammar-approved)
            if (
                TABLE_ROW_PATTERN.match(line)
                and i + 1 < len(lines)
                and TABLE_SEPARATOR_PATTERN.match(lines[i + 1])
            ):
                i = self.handle_table(lines, i)
                continue

            self.handle_line(line)
            i += 1

        self.close_lists()
        return "\n".join(self.output)