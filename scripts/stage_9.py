# scripts/stage_9.py

import os
import subprocess
from pathlib import Path
from scripts.contracts import (
    VIEW_CONFIG,
    OUTPUT_DIR,
    OUTPUT_SYLL_DIR,
    DESTINATION_DIR,
)


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

def compile_latex(view_type: str = "a4") -> bool:
    if view_type not in VIEW_CONFIG:
        raise ValueError(f"Unknown view type: {view_type}")
    #raise RuntimeError(
        #"Stage 9 (PDF compilation) is disabled in Python. "
        #"XeLaTeX must be run ONLY via GitHub Actions."
    #)
    base_dir = Path(OUTPUT_DIR) / OUTPUT_SYLL_DIR / view_type
    tex_file = base_dir / f"syllabus_{view_type}.tex"

    if not tex_file.exists():
        print(f"❌ Stage 9: Missing .tex file: {tex_file}")
        return False

    if not check_latex_env():
        print("❌ Stage 9: XeLaTeX not available.")
        return False

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
        # 🔁 TWO PASSES — REQUIRED FOR BOOKMARKS
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
                print(f"❌ Stage 9: LaTeX failed on pass {run + 1}")
                log = (result.stdout + "\n" + result.stderr).splitlines()[-25:]
                print("\n".join(log))
                return False

        return True

    except Exception as e:
        print(f"❌ Stage 9: XeLaTeX execution error: {e}")
        return False

# --------------------------------------------------
# STAGE 9B — FINALIZE OUTPUT
# --------------------------------------------------

def finalize_output(view_type: str = "a4") -> bool:
    base_dir = Path(OUTPUT_DIR) / OUTPUT_SYLL_DIR / view_type
    pdf_path = base_dir / f"syllabus_{view_type}.pdf"

    if not pdf_path.exists():
        print(f"❌ Stage 9: PDF not found: {pdf_path}")
        return False

    if pdf_path.stat().st_size == 0:
        print("❌ Stage 9: Generated PDF is empty.")
        return False

    dest_dir = Path(DESTINATION_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)

    final_name = f"KARE_Syllabus_{view_type}.pdf"
    pdf_path.replace(dest_dir / final_name)

    return True
# --------------------------------------------------
# STAGE 9C — CLEAN THE FOLDERS
# 
def cleanup_artifacts(view_type: str = "a4") -> None:
    """
    Removes LaTeX auxiliary files generated during Stage 9.
    Keeps the .log file for debugging/audit purposes.
    """

    base_dir = Path(OUTPUT_DIR) / OUTPUT_SYLL_DIR / view_type

    # Explicit whitelist of extensions to remove
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
        ".tex"
    }

    for item in base_dir.iterdir():
        if not item.is_file():
            continue

        # Handle .synctex.gz separately
        if item.name.endswith(".synctex.gz"):
            item.unlink(missing_ok=True)
            continue

        if item.suffix in cleanup_exts:
            item.unlink(missing_ok=True)


# --------------------------------------------------
# STAGE 9 ORCHESTRATOR (ONLY ENTRY POINT)
# --------------------------------------------------

def run_stage9(view_type: str = "a4") -> bool:
    if not compile_latex(view_type):
        return False

    if not finalize_output(view_type):
        return False
    
    cleanup_artifacts(view_type)
    return True