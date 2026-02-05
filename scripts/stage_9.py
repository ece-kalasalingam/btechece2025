import os
import subprocess
import shutil
from scripts.contracts import VIEW_CONFIG, OUTPUT_DIR, OUTPUT_SYLL_DIR, DESTINATION_DIR

def compile_latex(view_type="a4"):
    """
    STAGE-9: PDF Compilation.
    Compiles the .tex files generated in Stage 8 into PDFs.
    """
    if view_type not in VIEW_CONFIG:
        raise ValueError(f"Unknown view type: {view_type}")
    input_sylltex_dir = os.path.join(OUTPUT_DIR, OUTPUT_SYLL_DIR, view_type)
    tex_file = f"syllabus_{view_type}.tex"
    tex_path = os.path.join(input_sylltex_dir, tex_file)
    if not os.path.exists(tex_path):
        print(f"❌ Stage 9 Error: {tex_path} not found.")
        return
    tex_path_for_latex = tex_path.replace("\\", "/")
    # print(f"🚀 Stage 9: Compiling {view_type}...")

    # We run the command via subprocess
    # -interaction=nonstopmode: Don't stop for user input on errors
    # -output-directory: Keep the output files organized
    command = [
        "xelatex", 
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={input_sylltex_dir}",
        tex_path_for_latex
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"⚠️ LaTeX Error Log Snippet:\n{result.stdout[-500:]}") 
        # This prints the end of the log so you can see the error in the console
    
    try:
        # Run LaTeX twice to ensure Table of Contents and Hyperlinks are correct
        for i in range(2):
            result = subprocess.run(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            
        if result.returncode != 0:
            print(f"⚠️ Stage 9: LaTeX Warning/Error in {view_type}. Check logs.")
            # Optional: print(result.stdout[-500:]) # Print last 500 chars of log
            
    except FileNotFoundError:
        print("❌ Stage 9 Error: 'xelatex' not found. Is LaTeX installed on this system?")
def finalize_output(view_type="a4"):
    if view_type not in VIEW_CONFIG:
        raise ValueError(f"Unknown view type: {view_type}")
    input_sylltex_dir = os.path.join(OUTPUT_DIR, OUTPUT_SYLL_DIR, view_type)
    pdf_file = f"syllabus_{view_type}.pdf"
    pdf_path = os.path.join(input_sylltex_dir, pdf_file)

    if not os.path.exists(pdf_path):
        print(f"❌ Stage 9 Error: {pdf_path} not found.")
        return
    
    try:
        os.makedirs(DESTINATION_DIR, exist_ok=True)
    except Exception as e:
        print(f"❌ Stage 9: Failed to create directory {DESTINATION_DIR}. Error: {e}")
        return
    
    # shutil.move is safer than os.rename across different drives/filesystems
    shutil.move(pdf_path, os.path.join(DESTINATION_DIR, f"KARE_Syllabus_{view_type}.pdf"))
    #print(f"🚚 Moved final PDF to {DESTINATION_DIR}")

def cleanup_artifacts(view_type="a4"):
    """Removes auxiliary files (.log, .aux, .toc) to keep the folder clean."""
    input_dir = os.path.join("output_generated", "books")
    extensions = [".aux", ".log", ".toc", ".out"]
    
    for ext in extensions:
        file_to_remove = os.path.join(input_dir, f"syllabus_{view_type}{ext}")
        if os.path.exists(file_to_remove):
            os.remove(file_to_remove)
    #print(f"🧹 Stage 9: Cleaned up auxiliary files for {view_type}.")