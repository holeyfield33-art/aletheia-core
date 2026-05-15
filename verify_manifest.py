import json
import sys

try:
    with open("/workspaces/aletheia-core/data/semantic_manifest.json", "r") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    ta_ids = ["ta_001", "ta_002", "ta_003", "ta_004"]
    found_ta_ids = []
    found_categories = set()

    for entry in entries:
        if entry.get("id") in ta_ids:
            found_ta_ids.append(entry.get("id"))
        if entry.get("category"):
            found_categories.add(entry.get("category"))

    print(f"Found entries: {', '.join(found_ta_ids)}")
    for tid in ta_ids:
        if tid not in found_ta_ids:
            print(f"MISSING entry: {tid}")

    if "tool_abuse" in found_categories:
        print("tool_abuse category is present in entries.")
    else:
        print("tool_abuse category NOT found in any entry.")

    # Check for Pydantic models in the project
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
