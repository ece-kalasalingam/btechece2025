import streamlit as st
import subprocess
import json
import os
import sys
import time
from scripts.paths import get_path
from scripts.contracts import DASHBOARD_DIR, DASHBOARD_JSON_FILE, VIEW_CONFIG

# =========================================================
# 1. PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="KARE Syllabus Command Center",
    page_icon="🛠️",
    layout="wide"
)

# Container for execution logs (appears at the top of the main area)
output_container = st.container()

# =========================================================
# 2. SESSION STATE MAPPING
# =========================================================
if "is_running" not in st.session_state:
    st.session_state.is_running = False

if "pending_command" not in st.session_state:
    st.session_state.pending_command = None

if "run_state" not in st.session_state:
    st.session_state.run_state = "IDLE"  # IDLE | ARMED | RUNNING


# =========================================================
# 3. VISUAL SIDEBAR LOCK (CSS LEVEL)
# =========================================================
if st.session_state.is_running:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            pointer-events: none;
            opacity: 0.6;
            cursor: not-allowed;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# 4. COMMAND EXECUTION ENGINE
# =========================================================
def run_command(command_args, container):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    # Ensure we use the same Python interpreter
    full_cmd = f'"{sys.executable}" {command_args}'

    with container:
        st.info(f"🚀 Executing: `{command_args}`")
        with st.spinner("Pipeline in progress..."):
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                encoding="utf-8",
                text=True,
                env=env,
                cwd=os.getcwd()
            )

        if result.returncode == 0:
            st.success("✅ Build Successful")
            if result.stdout:
                with st.expander("Show Detailed Console Output"):
                    st.code(result.stdout)
            return True
        else:
            st.error("❌ Build Failed")
            st.code(result.stderr)
            return False


# =========================================================
# 5. DATA MANAGEMENT
# =========================================================
manifest_path = get_path(DASHBOARD_DIR, DASHBOARD_JSON_FILE)
master_sha = "None"
data = {"views": []}

if manifest_path.exists():
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            master_sha = data.get("global_source_sha", "None")
    except Exception as e:
        st.error(f"Manifest load error: {e}")


# =========================================================
# 6. SIDEBAR UI
# =========================================================
st.sidebar.title("🛠 Control Panel")

if st.session_state.is_running:
    st.sidebar.warning("⚙️ System Locked: Build Active")

display_sha = master_sha[:7] if master_sha != "None" else "MISSING"
st.sidebar.info(f"**Master SHA:** `{display_sha}`")
st.sidebar.divider()

# Master Data Buttons
if master_sha == "None":
    st.sidebar.warning("Data not initialized")
    if st.sidebar.button("🚀 Initialize Project", use_container_width=True, disabled=st.session_state.is_running):
        st.session_state.is_running = True
        st.session_state.pending_command = "driver.py --view=none"
        st.session_state.run_state = "ARMED"
        st.rerun()
else:
    st.sidebar.success("Data Initialized")
    if st.sidebar.button("🔄 Refresh Master Data", use_container_width=True, disabled=st.session_state.is_running):
        st.session_state.is_running = True
        st.session_state.pending_command = "driver.py --view=none"
        st.session_state.run_state = "ARMED"
        st.rerun()
    st.sidebar.divider()
    st.sidebar.subheader("📄 Generate Views")
    # View-Specific Buttons
    for view_key in VIEW_CONFIG.keys():
        if st.sidebar.button(f"Build {view_key.upper()}", key=f"btn_{view_key}", use_container_width=True, disabled=st.session_state.is_running):
            st.session_state.is_running = True
            st.session_state.pending_command = f"driver.py --view={view_key}"
            st.session_state.run_state = "ARMED"
            st.rerun()



if st.session_state.is_running:
    if st.sidebar.button("🔓 Emergency Unlock"):
        st.session_state.is_running = False
        st.session_state.run_state = "IDLE"
        st.rerun()

# =========================================================
# 7. MAIN AREA DASHBOARD
# =========================================================
st.title("Syllabus Build Dashboard")
st.write(f"Hi, monitor your builds below.")

if manifest_path.exists():
    st.subheader("Current Build Status")
    
    # Table Header
    h1, h2, h3 = st.columns([1, 2, 1])
    h1.caption("DOCUMENT VIEW")
    h2.caption("INTEGRITY STATUS")
    h3.caption("LAST AUDIT")
    st.divider()

    for view in data.get("views", []):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            st.markdown(f"**{view['view'].upper()}**")
        with col2:
            status = view["status"]
            if status == "SYNCHRONIZED":
                st.success("Synchronized")
            elif status == "OUTDATED":
                st.warning("Outdated")
            else:
                st.error("Missing File")
        with col3:
            st.text(view.get("last_modified", "N/A"))
else:
    st.info("Dashboard data not found. Use the sidebar to initialize.")

# =========================================================
# 8. THE ENGINE (2-STEP EXECUTION)
# =========================================================
if st.session_state.is_running and st.session_state.pending_command:

    # Step 1: Armed -> Running (Reruns to paint the 'Locked' UI)
    if st.session_state.run_state == "ARMED":
        st.session_state.run_state = "RUNNING"
        st.rerun()

    # Step 2: Running -> Idle (Blocking execution)
    if st.session_state.run_state == "RUNNING":
        success = run_command(st.session_state.pending_command, output_container)

        if success:
            with output_container:
                st.toast("Syncing filesystem...")
                time.sleep(3)

        # Reset states
        st.session_state.is_running = False
        st.session_state.pending_command = None
        st.session_state.run_state = "IDLE"
        st.rerun()

st.divider()
st.caption("© 2026 KARE | Department of Electronics and Communication Engineering")