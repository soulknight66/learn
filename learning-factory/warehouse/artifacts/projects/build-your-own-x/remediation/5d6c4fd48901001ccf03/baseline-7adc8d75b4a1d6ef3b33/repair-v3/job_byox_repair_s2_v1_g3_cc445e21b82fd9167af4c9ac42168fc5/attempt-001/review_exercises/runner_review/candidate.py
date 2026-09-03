"""Deliberately unsafe launcher for review; do not use."""

import os
import subprocess


def run(command):
    completed = subprocess.run(
        " ".join(command),
        shell=True,
        env=os.environ,
        capture_output=True,
    )
    return completed.returncode == 0
