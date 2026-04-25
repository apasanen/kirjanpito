"""
Version information for the application.
"""

import subprocess
from pathlib import Path


def get_version_info() -> dict:
    """Get the current version and commit SHA."""
    try:
        # Get latest tag
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--always"],
            cwd=Path(__file__).parent.parent,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        tag = "unknown"
    
    try:
        # Get short commit SHA
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).parent.parent,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sha = "unknown"
    
    return {
        "version": tag,
        "commit": sha,
        "full": f"{tag} ({sha})"
    }


# Cache version info at module load
VERSION_INFO = get_version_info()
