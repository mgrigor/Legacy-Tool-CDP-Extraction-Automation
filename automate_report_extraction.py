"""
automate_report_extraction.py

Replays the captured payloads directly against the legacy tool's
internal report-generation endpoint -- using the token captured by
extract_payload.py -- instead of clicking through the UI by hand.
Handles both ZIP and CSV response formats, and re-runs any payload
that didn't produce a report on the first pass.
"""

import os
import json
import requests
import zipfile
import io
from datetime import datetime

# -------- CONFIG --------
BASE_URL = "https://your-legacy-tool.internal/api/generateReport"
TOKEN_FILE = "token.txt"
OUTPUT_ROOT = "raw_data"
PAYLOAD_ROOT = "submarket_payloads"
date_tag = datetime.now().strftime("%Y%m%d")
testfiles = []
csvfiles = []
# ------------------------


def choose_submarket():
    print("\nAvailable submarkets:")
    submarkets = []

    for i, name in enumerate(os.listdir(PAYLOAD_ROOT)):
        row_idx = f"[{i + 1}]"
        full_path = os.path.join(PAYLOAD_ROOT, name)
        if os.path.isdir(full_path):
            submarkets.append(name)
            print(row_idx, name)

    choice = input("\nEnter the submarket you want to run: ").strip()

    chosen = None
    for i, name in enumerate(os.listdir(PAYLOAD_ROOT)):
        if str(i + 1) == choice:
            chosen = name

    if chosen not in submarkets:
        print(f"\n[ERROR] '{chosen}' is not a valid submarket folder.")
        exit(1)

    out_dir = os.path.join(OUTPUT_ROOT, chosen)
    return chosen, out_dir


def prepare_output_folders():
    subfolders = ["report_type_a/part_1", "report_type_b/part_1", "report_type_b/part_2"]
    for subfolder in subfolders:
        path = os.path.join(out_dir, subfolder)
        if os.path.exists(path):
            for file in os.listdir(path):
                os.remove(os.path.join(path, file))
        else:
            os.makedirs(path)


def load_token_and_payloads():
    submarket_path = os.path.join(PAYLOAD_ROOT, chosen)

    print("\n[STEP] Loading token from token.txt...")
    with open(TOKEN_FILE, "r") as f:
        token = f.read().strip()
    print("[OK] Token loaded.")

    print(f"\n[STEP] Scanning payloads in: {submarket_path}")
    jfiles = sorted(
        f for f in os.listdir(submarket_path) if f.lower().endswith(".json")
    )
    print(f"[INFO] Found {len(jfiles)} payload(s).")

    return token, jfiles


def choose_run_mode(files):
    print("\nRun mode options:")
    print("  1. Run ALL payloads")
    print("  2. Run SPECIFIC payloads only")

    mode = input("\nChoose run mode (1 or 2): ").strip()

    if mode == "1":
        payloads_to_run = files
        generated = run_all_payloads(payloads_to_run)
        summary(generated, payloads_to_run)
        return generated, payloads_to_run

    print("\n[ERROR] Invalid mode.")
    exit(1)


def run_all_payloads(payloads_to_run):
    submarket_path = os.path.join(PAYLOAD_ROOT, chosen)

    for json_file in payloads_to_run:
        payload_path = os.path.join(submarket_path, json_file)
        print(f"\n[REPORT] Running report: {chosen} {payload_path}")
        print("    -> Sending POST request to internal reporting endpoint...")

        with open(payload_path, "r") as f:
            payload = json.load(f)

        headers = {"Authorization": token, "Content-Type": "application/json"}
        resp = requests.post(BASE_URL, headers=headers, json=payload)

        if resp.status_code != 200:
            print(f"[ERROR] HTTP {resp.status_code} for {payload_path}")
            print(resp.text[:300])

        save_report(resp.content, out_dir, json_file)

    return csvfiles


def save_report(content, out_dir, json_file):
    print("      Saving report...")
    os.makedirs(out_dir, exist_ok=True)

    parts = json_file.split()
    if "TYPE_B" in parts:
        level = "TYPE_B " + parts[1]
    else:
        level = "TYPE_A"

    if level == "TYPE_A":
        subfolder = os.path.join("report_type_a", "part_1")
    elif level == "TYPE_B 1":
        subfolder = os.path.join("report_type_b", "part_1")
    elif level == "TYPE_B 2":
        subfolder = os.path.join("report_type_b", "part_2")
    else:
        subfolder = "report"

    sub_path = os.path.join(out_dir, subfolder)
    is_zip = content[:2] == b"PK"

    if is_zip:
        print("    -> ZIP detected. Extracting contents...")
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            z.extractall(sub_path)
        print(f"    -> ZIP extracted to: {sub_path}")
        return

    print("      CSV detected. Processing...")
    csv_text = content.decode("utf-8", errors="ignore")
    lines = csv_text.splitlines()

    if len(lines) >= 1 and "No data found" in lines[0]:
        print("    -> No data found. Skipping save.")
        return
    if len(lines) <= 1:
        print("    -> Empty CSV. Skipping save.")
        return

    csv_file = json_file.strip(".json") + " " + date_tag + ".csv"
    csv_path = os.path.join(sub_path, csv_file)
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_text)

    print(f"      CSV saved to: {csv_path}")
    testfiles.append(csv_file)
    csvfiles.append(csv_file)
    return csv_file


def summary(generated_files, payloads_to_run):
    print("\n==============================================")
    print("      REPORT GENERATION SUMMARY")
    print("==============================================")

    basenames = [" ".join(f.split()[:-1]) for f in generated_files]

    missing_reports = [
        p for p in payloads_to_run if p.strip(".json") not in basenames
    ]

    if missing_reports:
        print("\nMissing reports:")
        for m in missing_reports:
            print(f"  - {m}")
        print("\nRe-running for the missing reports...")
        run_all_payloads(missing_reports)
    else:
        print("\nAll reports generated successfully.")

    print("\n==============================================\n")
    return missing_reports


if __name__ == "__main__":
    chosen, out_dir = choose_submarket()
    prepare_output_folders()
    token, payloads = load_token_and_payloads()
    choose_run_mode(payloads)
