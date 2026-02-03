"""
STAGE 6c: Department Dashboard
Input: All Stage 5 JSONs
Output: dashboard_summary.md
"""
import json
import os
import pandas as pd # Optional: use pandas for CSV/Excel

def generate_dept_dashboard(verified_dir="output_verified"):
    summary = []
    
    for file in os.listdir(verified_dir):
        if file.endswith(".json"):
            with open(os.path.join(verified_dir, file), 'r') as f:
                data = json.load(f)
                summary.append({
                    "Code": data["course_code"],
                    "Title": data["syllabus_data"]["metadata"]["course_title"],
                    "Credits": data["syllabus_data"]["metadata"]["c"],
                    "L-T-P-X": f"{data['syllabus_data']['metadata']['l']}-{data['syllabus_data']['metadata']['t']}-{data['syllabus_data']['metadata']['p']}-{data['syllabus_data']['metadata']['x']}",
                    "Status": data["audit_meta"]["status"]
                })
    
    # Generate a Markdown Table for GitHub/Readme
    df = pd.DataFrame(summary)
    md_table = df.to_markdown(index=False)
    
    with open("DASHBOARD.md", "w") as f:
        f.write("# R2025 Syllabus Audit Dashboard\n\n")
        f.write(md_table)
    
    print("📊 Dashboard generated: DASHBOARD.md")