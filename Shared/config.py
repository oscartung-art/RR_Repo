r"""
Centralized Configuration for RR_Repo Scripts
Real Rendering — Zero-Lock-In Architecture

Drive Topology:
  D:\\ (Sync)     — Google Drive mirror. The Brain & Project Spine.
  F:\\ (Projects) — NAS for large active project files (3ds Max, Unreal, Fusion).
  G:\\ (Assets)   — NAS for 3D asset archives.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Drive Root Paths
# ---------------------------------------------------------------------------

# D:\ — Google Drive mirror (Brain & Project Spine)
BRAIN_ROOT = Path("D:/RR_Repo")

# Alias for scripts that reference the sync layer directly
SYNC_ROOT = Path("D:/GoogleDrive")

# F:\ — Active project files on NAS
PROJECT_ROOT = Path("F:/Projects")

# G:\ — 3D asset archives on NAS
ASSET_ROOT = Path("G:/")

# ---------------------------------------------------------------------------
# Google Sheets IDs
# ---------------------------------------------------------------------------

LANDSCAPE_SPREADSHEET_ID = "1kvXmUldDFyiXMJLQb2yPclFnHZOTsFHom7uGS7GGLPk"

# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

DEFAULT_CSV_ENCODING = "utf-8-sig"

