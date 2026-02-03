import streamlit as st
import os
import json
import pandas as pd
from run_pipeline import run_full_pipeline
from scripts.stage_6c_audit_dashboard import generate_dept_dashboard

st.set_page_config(page_title="R2025 Syllabus Auditor", layout="wide")

st.title("🎓 R2025 Syllabus Engineering Pipeline")
st.sidebar.header("Control Panel")

# 1. Pipeline Execution
input_dir = "syllabi_input"
if st.sidebar.button("🚀 Run Full Audit Pipeline"):
    with st.spinner("Processing syllabi..."):
        # This calls your existing orchestrator
        for file in os.listdir(input_dir):
            if file.endswith(".md"):
                run_full_pipeline(os.path.join(input_dir, file))
        generate_dept_dashboard() # Refresh dashboard data
    st.sidebar.success("Pipeline Complete!")

# 2. View Department Dashboard
st.header("📊 Department Audit Overview")
if os.path.exists("DASHBOARD.md"):
    # We can read the generated JSONs to show a live table
    verified_dir = "output_verified"
    summary_data = []
    for file in os.listdir(verified_dir):
        if file.endswith(".json"):
            with open(os.path.join(verified_dir, file), "r") as f:
                data = json.load(f)
                summary_data.append({
                    "Code": data["course_code"],
                    "Title": data["syllabus_data"]["metadata"]["course_title"],
                    "Credits": data["syllabus_data"]["metadata"]["c"],
                    "Status": data["audit_meta"]["status"]
                })
    st.table(pd.DataFrame(summary_data))
else:
    st.info("Run the pipeline to see the dashboard.")

# 3. Individual File Preview
st.header("📝 Syllabus Preview")
selected_file = st.selectbox("Select a verified course to view:", 
                             [f for f in os.listdir("output_verified") if f.endswith(".json")] if os.path.exists("output_verified") else [])

if selected_file:
    with open(os.path.join("output_verified", selected_file), "r") as f:
        content = json.load(f)
        st.json(content)