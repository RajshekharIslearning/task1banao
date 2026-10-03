"""
run.py — single-command entry point for the Vireo Audio SLA tool.

Usage:
    python run.py --data ./data

Runs, in order:
    1. clean.py   -> out/clean.csv
    (future steps: report.py, cost.py, memo.py will be added here)

Fails loudly and stops on any non-zero exit code.
"""

import argparse
import subprocess
import sys
import pathlib

def run_step(script: str, extra_args: list[str] = []) -> None:
    cmd = [sys.executable, script] + extra_args
    print(f"\n{'='*60}")
    print(f"RUNNING: {' '.join(cmd)}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"\nFATAL: {script} exited with code {result.returncode}. Stopping.")
        sys.exit(result.returncode)

def main() -> None:
    parser = argparse.ArgumentParser(description="Vireo Audio SLA Breach Report Tool")
    parser.add_argument(
        "--data",
        default="./data",
        help="Path to the data directory (default: ./data)",
    )
    args = parser.parse_args()

    data_path = pathlib.Path(args.data)
    if not data_path.is_dir():
        print(f"ERROR: data directory not found: {data_path}")
        sys.exit(1)

    # Change into the workspace root so all scripts use relative paths
    import os
    os.chdir(pathlib.Path(__file__).parent)

    print(f"Step 1/3: Running clean.py to prepare data...")
    run_step("clean.py")
    
    print(f"Step 2/3: Running analysis.py to generate insights...")
    run_step("analysis.py")
    
    print(f"Step 3/3: Running report.py to generate final HTML and CSVs...")
    run_step("report.py")

    print("\n" + "="*60)
    print("ALL STEPS COMPLETE. Outputs are in out/")
    print("="*60)

if __name__ == "__main__":
    main()
