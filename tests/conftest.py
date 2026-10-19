"""Test-session prefect isolation: fresh PREFECT_HOME per run so the local
telemetry sqlite never locks across parallel/sequential flow runs."""

import os
import tempfile

os.environ["PREFECT_HOME"] = tempfile.mkdtemp(prefix="prefect-test-")
os.environ["PREFECT_LOGGING_LEVEL"] = "ERROR"
