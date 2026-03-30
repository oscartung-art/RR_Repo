r"""
Centralized Configuration for RR_Repo Scripts
Real Rendering — Zero-Lock-In Architecture

Drive Topology:
  D:\\ (Sync)     — Google Drive mirror. The Brain & Project Spine.
  F:\\ (Projects) — NAS for large active project files (3ds Max, Unreal, Fusion).
  G:\\ (Assets)   — NAS for 3D asset archives.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Drive Root Paths
# ---------------------------------------------------------------------------

# D:\ — Google Drive mirror (Brain & Project Spine)
BRAIN_ROOT = Path("D:/GoogleDrive/RR_Repo")

# Alias for scripts that reference the sync layer directly
SYNC_ROOT = Path("D:/GoogleDrive")

# F:\ — Active project files on NAS
PROJECT_ROOT = Path("F:/Projects")

# G:\ — 3D asset archives on NAS
ASSET_ROOT = Path("G:/Assets")

# ---------------------------------------------------------------------------
# Google Sheets IDs
# ---------------------------------------------------------------------------

LANDSCAPE_SPREADSHEET_ID = "1kvXmUldDFyiXMJLQb2yPclFnHZOTsFHom7uGS7GGLPk"

# RR Studio Dashboard (Google Sheet — Live project status mirror)
DASHBOARD_SHEET_ID = "1Ve4LjD4YGC7tmOnEipJ58Jn230IYnKe9ojJk4SFNcag"

# Cloud Brain Doc (Google Doc — stitched .md files for mobile reading)
CLOUD_BRAIN_DOC_ID = "1EmnIcp81vS5ao6isWBVTGol7jVGUQVcArC-VxHPG1w8"

# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

DEFAULT_CSV_ENCODING = "utf-8-sig"

# ---------------------------------------------------------------------------
# Helper: Environment Variable Loader
# ---------------------------------------------------------------------------

def get_env_variable(var_name: str, default: str = None) -> str:
    """
    Retrieve an environment variable by name.
    Raises ValueError if the variable is not set and no default is provided.
    """
    value = os.environ.get(var_name, default)
    if value is None:
        raise ValueError(
            f"Environment variable '{var_name}' is not set. "
            f"Add it to your .env file or system environment."
        )
    return value
