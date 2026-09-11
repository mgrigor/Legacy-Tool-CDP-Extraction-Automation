"""
create_submarket_payloads.py

Takes a set of captured base payload templates (one per report type,
captured via extract_payload.py) and stamps out a full set of
ready-to-send payloads for every submarket -- injecting each
submarket's market list, name, and the current run date into every
template.

Directory layout expected:
    base_payload_folder/          <- one .json template per report type
    submarket_def_folder/         <- one .json file per submarket, each
                                      defining {"marketList": [...], "subMarket": "..."}
    output_root/<submarket>/      <- generated payloads land here, one
                                      subfolder per submarket
"""

import json
import os
from datetime import date

run_date = date.today().strftime("%Y-%m-%d")

# Base folders
base_payload_folder = "payload_templates"
submarket_def_folder = "submarket_definitions"
output_root = "submarket_payloads"

os.makedirs(output_root, exist_ok=True)

for sub_def_file in os.listdir(submarket_def_folder):
    if not sub_def_file.lower().endswith(".json"):
        continue

    sub_def_path = os.path.join(submarket_def_folder, sub_def_file)

    with open(sub_def_path, "r", encoding="utf-8") as f:
        sub_def = json.load(f)

    market_list = sub_def.get("marketList")
    submarket = sub_def.get("subMarket")

    if isinstance(submarket, str):
        submarket = [submarket]

    folder_name = os.path.splitext(sub_def_file)[0]
    target_folder = os.path.join(output_root, folder_name)
    os.makedirs(target_folder, exist_ok=True)

    print(f"\n=== Processing {folder_name} ===")
    print(f"SubMarket: {submarket}")
    print(f"MarketList: {market_list}")

    for filename in os.listdir(base_payload_folder):
        if not filename.lower().endswith(".json"):
            continue

        base_path = os.path.join(base_payload_folder, filename)

        try:
            with open(base_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["marketList"] = market_list
            data["subMarket"] = submarket
            data["date"] = run_date

            target_path = os.path.join(target_folder, filename)
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            print(f"  Updated: {filename}")

        except Exception as e:
            print(f"  Skipped {filename} -> {e}")

print("\nAll submarkets processed successfully.")
