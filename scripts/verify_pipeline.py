import subprocess
import sys
from pathlib import Path

cmd = [sys.executable, "src/run.py", "--inputs", "samples/ats_sample.json", "samples/github_sample.json", "--config", "samples/config_technical.json"]
project_root = Path(__file__).resolve().parents[1]
print(f"Running: {' '.join(cmd)} in {project_root}")
res = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
print(res.stdout)
if res.returncode != 0:
    print("Pipeline failed:\n", res.stderr)
    sys.exit(2)
print("Verification script completed successfully.")
sys.exit(0)
