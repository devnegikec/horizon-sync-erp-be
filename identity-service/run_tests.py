#!/usr/bin/env python
"""Quick test runner to validate API changes"""

import subprocess
import sys

# Try to run pytest with the current Python interpreter
try:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_permissions.py",
            "tests/test_roles.py",
            "-v",
            "--tb=short",
        ],
        cwd=".",
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    sys.exit(result.returncode)
except Exception as e:
    print(f"Error running tests: {e}")
    sys.exit(1)
