"""Enterprise data platform demo.

Usage:
    python run.py seed        # generate synthetic source systems
    python run.py etl         # prefect flow: raw -> marts -> gold + contracts
    python run.py dashboard
    python run.py all
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# keep prefect's local state out of the repo and out of our way
os.environ.setdefault("PREFECT_HOME", tempfile.mkdtemp(prefix="prefect-run-"))
os.environ.setdefault("PREFECT_LOGGING_LEVEL", "WARNING")

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import flow, seeder  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["seed", "etl", "dashboard", "all"])
    args = parser.parse_args()

    if args.command in ("seed", "all"):
        seeder.seed()

    if args.command in ("etl", "all"):
        flow.run_pipeline()

    if args.command == "dashboard":
        app = PROJECT_ROOT / "dashboards" / "app.py"
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(app)], check=True)


if __name__ == "__main__":
    main()
