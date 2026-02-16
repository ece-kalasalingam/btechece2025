# scripts/stage_9.py
import json
from pathlib import Path
from datetime import datetime, timezone
from scripts.paths import get_path
from scripts.utils import (
    get_current_git_commit, 
    validate_environment_for_view, 
    get_git_metadata,      # Your existing function
    get_live_git_hash      # Our new function
)
from scripts.contracts import (
    DESTINATION_DIR,
    VIEW_CONFIG,
    DASHBOARD_DIR,
    DASHBOARD_JSON_FILE
)

def build_dashboard_data():
    dashboard_path = get_path(DASHBOARD_DIR)
    dashboard_path.mkdir(exist_ok=True)

    current_repo_commit = get_current_git_commit()
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    output_data = {
        "generated_at": now_utc,
        "current_commit": current_repo_commit,
        "views": []
    }

    for view_name, config in VIEW_CONFIG.items():
        ext = config.get("ext", "pdf")
        output_file = f"KARE_Syllabus_{view_name}.{ext}"
        output_file_path = get_path(DESTINATION_DIR, output_file)

        view_info = {
            "view": view_name,
            "status": "NOT_GENERATED",
            "file": None,
            "version": "N/A",
            "stale": False,
            "sync_status": "UNKNOWN"
        }

        if not output_file_path.exists():
            output_data["views"].append(view_info)
            continue

        # 1. Get Metadata (The "Saved" state in Git)
        doc_version, doc_date, saved_hash = get_git_metadata(output_file_path)
        
        # 2. Get Live Hash (The "Actual" state on Disk)
        live_hash = get_live_git_hash(output_file_path)

        view_info.update({
            "status": "GENERATED",
            "file": str(output_file_path.relative_to(get_path()).as_posix()),
            "version": doc_version,
            "last_commit_hash": saved_hash,
            "live_hash": live_hash
        })

        # --- SYNC / STALE LOGIC ---
        # If the file on disk (live_hash) doesn't match the last known commit (saved_hash),
        # or if the file was built on an older repo commit than what we have now.
        if live_hash != saved_hash:
            view_info["stale"] = True
            view_info["sync_status"] = "MODIFIED_UNCOMMITTED"
        elif saved_hash != current_repo_commit:
             # This view was compiled for an older version of the course list
            view_info["stale"] = True
            view_info["sync_status"] = "OUTDATED_COMMIT"
        else:
            view_info["stale"] = False
            view_info["sync_status"] = "SYNCHRONIZED"

        output_data["views"].append(view_info)

    # Save the Manifest/Dashboard
    json_file = dashboard_path / DASHBOARD_JSON_FILE
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4)

    print(f"✅ Dashboard updated. Sync Check: {len([v for v in output_data['views'] if v['stale']])} views need attention.")