"""
run_audit_pipeline.py

Top-level orchestrator: lets you pick one submarket (or all of them)
and runs the full precheck -> extract -> validate -> exception-report
chain in order for each one, stopping immediately if any stage fails.
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(__file__)
submarkets = os.listdir(os.path.join(SCRIPT_DIR, "raw_data"))
print("Available submarkets:")
print(submarkets)

# Ordered pipeline stages -- each script receives the submarket name
# as a command-line argument.
PIPELINE_STAGES = [
    "precheck_report_type_a.py",
    "process_report_type_a.py",
    "precheck_report_type_b_part1.py",
    "process_report_type_b_part1.py",
    "precheck_report_type_b_part2.py",
    "process_report_type_b_part2.py",
    "generate_exception_report.py",
]


def run_stage(script_name, submarket):
    script_path = os.path.join(SCRIPT_DIR, script_name)
    print(f"\n=== Running: {script_name} ===")

    try:
        subprocess.run(["python", script_path, submarket], check=True)
    except subprocess.CalledProcessError:
        print(f"\nERROR: {script_name} failed. Stopping pipeline.")
        sys.exit(1)

    print(f"Completed: {script_name}")


def main():
    print("Starting audit pipeline...\n")
    print("Available submarkets:\n")
    for i, sm in enumerate(submarkets, start=1):
        print(f" [{i}] {sm}")

    print("\nOptions:")
    print(f" - Enter a number (1-{len(submarkets)}) to select a submarket")
    print(" - Type ALL to process every submarket\n")

    choice = input("Enter your choice: ").strip().upper()

    if choice == "ALL":
        submarket_list = submarkets
        print("\nYou selected: ALL SUBMARKETS\n")
    else:
        if not choice.isdigit():
            print("\nInvalid input. Please enter a number or ALL.")
            sys.exit(1)

        index = int(choice)
        if index < 1 or index > len(submarkets):
            print("\nInvalid index. Please choose a number from the list.")
            sys.exit(1)

        submarket_list = [submarkets[index - 1]]
        print(f"\nYou selected: {submarket_list[0]}\n")

    for sm in submarket_list:
        print("\n==============================")
        print(f" Processing Submarket: {sm}")
        print("==============================\n")

        for stage in PIPELINE_STAGES:
            run_stage(stage, sm)

    print("\nAll audit phases completed successfully!")


if __name__ == "__main__":
    main()
