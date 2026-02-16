import json
from datetime import datetime
from scripts.paths import get_path, PROJECT_ROOT
from scripts.contracts import (
    DASHBOARD_DIR, 
    DASHBOARD_JSON_FILE, 
    DESTINATION_DIR, 
    VIEW_CONFIG
)

def build_dashboard_data():
    """
    Final Auditor: Scans the system and generates the manifest for the web UI.
    """
    manifest_path = get_path(DASHBOARD_DIR, DASHBOARD_JSON_FILE)
    
    # 1. Load existing data to preserve the SHAs we just stored
    if manifest_path.exists():
        with open(manifest_path, 'r', encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "global_source_sha": "None",
            "views": []
        }

    target_sha = data.get("global_source_sha", "None")
    updated_views = []

    # 2. Iterate through defined views in contracts.py
    for view_name, config in VIEW_CONFIG.items():
        # Construct the expected filename (e.g., syllabus_books/a4_syllabus.pdf)
        extension = config.get("ext", "pdf")
        filename = f"KARE_Syllabus_{view_name}.{extension}"
        file_path = get_path(DESTINATION_DIR, filename)
        # CALCULATE RELATIVE PATH: OS-agnostic path relative to the project root
        # This ensures the link works in GitHub Actions and different local folders
        try:
            relative_path = file_path.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            relative_path = filename
        
        # Find existing view metadata to keep the 'built_with_sha'
        existing_view = next((v for v in data.get("views", []) if v["view"] == view_name), {})
        built_sha = existing_view.get("built_with_sha", "None")

        # 3. Gather Live File Info
        file_exists = file_path.exists()
        file_size = "0 KB"
        last_mod = "N/A"
        
        if file_exists:
            stats = file_path.stat()
            file_size = f"{round(stats.st_size / 1024, 1)} KB"
            last_mod = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M')

        # 4. Compare SHAs for Status
        # Green if hashes match, Orange if they don't, Red if file missing
        if not file_exists:
            status = "MISSING"
        elif built_sha == target_sha and target_sha != "None" :
            status = "SYNCHRONIZED"
        else:
            status = "OUTDATED"

        updated_views.append({
            "view": view_name,
            "filename": filename,
            "relative_path": relative_path,
            "exists": file_exists,
            "size": file_size,
            "last_modified": last_mod,
            "built_with_sha": built_sha,
            "status": status
        })

    # 5. Save the finalized manifest
    data["views"] = updated_views
    data["last_audit"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(manifest_path, 'w', encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    
    print(f"📊 Dashboard Manifest updated at {data['last_audit']}")