# scripts/stage_9.py
import json
from pathlib import Path
from datetime import datetime, timezone
from scripts.paths import get_path
from scripts.utils import (
    get_current_git_commit, 
    get_git_metadata,      
    get_live_git_hash      
)
from scripts.contracts import (
    DESTINATION_DIR,
    VIEW_CONFIG,
    DASHBOARD_DIR,
    DASHBOARD_JSON_FILE,
    TEMP_OUTPUT_DIR,
    ACADEMIC_JSON_FILE
)

def build_dashboard_data():
    dashboard_path = get_path(DASHBOARD_DIR)
    dashboard_path.mkdir(exist_ok=True)

    # 1. Source of Truth Check
    source_json_path = get_path(TEMP_OUTPUT_DIR, ACADEMIC_JSON_FILE)
    latest_source_mtime = source_json_path.stat().st_mtime if source_json_path.exists() else 0

    current_repo_commit = get_current_git_commit()
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    output_data = {
        "generated_at": now_utc,
        "current_commit": current_repo_commit,
        "views": []
    }

    for view_name, config in VIEW_CONFIG.items():
        # --- DYNAMIC FILENAME LOGIC ---
        ext = config.get("ext", "pdf")
        output_file = f"KARE_SYLLABUS_{view_name}.{ext}"
        output_file_path = get_path(DESTINATION_DIR, output_file)

        view_info = {
            "view": view_name,
            "status": "NOT_GENERATED",
            "file": None,
            "version": "N/A",
            "stale": True,
            "sync_status": "MISSING",
            "live_hash": "N/A",
            "last_commit_hash": "N/A"
        }

        if not output_file_path.exists():
            output_data["views"].append(view_info)
            continue

        # File exists - perform integrity audit
        doc_version, _, saved_hash = get_git_metadata(output_file_path)
        live_hash = get_live_git_hash(output_file_path)
        file_mtime = output_file_path.stat().st_mtime

        view_info.update({
            "status": "GENERATED",
            "file": str(output_file_path.relative_to(get_path()).as_posix()),
            "version": doc_version,
            "last_commit_hash": saved_hash,
            "live_hash": live_hash,
            "last_modified": datetime.fromtimestamp(file_mtime, tz=timezone.utc).isoformat()
        })

        # --- SYNC LOGIC ---
        # --- IMPROVED LOCAL-FRIENDLY SYNC LOGIC ---
        
        # 1. Check if the master data has changed since this file was built
        if file_mtime < latest_source_mtime:
            view_info["sync_status"] = "OUTDATED_SOURCE"
            view_info["stale"] = True
            
        # 2. If the file is newer than the source data, it is "Fresh"
        # We don't care about the Git Hash here because we are in local development
        elif file_mtime >= latest_source_mtime:
            # Check if it's actually committed (for the dashboard badge)
            if live_hash == saved_hash:
                view_info["sync_status"] = "SYNCHRONIZED"
                view_info["stale"] = False
            else:
                # This is the "Green" state for local development
                view_info["sync_status"] = "LOCAL_BUILD_VALID"
                view_info["stale"] = False

        output_data["views"].append(view_info)

    # Save to JSON
    json_file = dashboard_path / DASHBOARD_JSON_FILE
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4)

    print(f"✅ Audit Complete. File Prefix: KARE_SYLLABUS | Views Tracked: {len(output_data['views'])}")

if __name__ == "__main__":
    build_dashboard_data()