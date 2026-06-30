import subprocess
import sys
from pathlib import Path


def test_pipeline_runs_and_projects():
    cmd = [sys.executable, "src/run.py", "--inputs", "samples/ats_sample.json", "samples/github_sample.json", "--config", "samples/config_technical.json"]
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
    assert result.returncode == 0, f"Pipeline failed: {result.stderr}"
    # Expect the projected output to include the primary_email field from the config
    assert 'primary_email' in result.stdout or 'primary_email' in result.stderr
