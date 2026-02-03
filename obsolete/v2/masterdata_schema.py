# ============================================================
# MASTERDATA SCHEMA (AUTHORITATIVE)
# ============================================================

SCHEMA_VERSION = "1.0"

def empty_masterdata():
    return {
        "schema_version": SCHEMA_VERSION,
        "meta": {
            "regulation": "KARE R2025",
            "pipeline_version": "v1.0",
            "generated_on": None
        },
        "courses": [],
        "errors": [],
        "warnings": []
    }