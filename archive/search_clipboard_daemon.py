"""
search_clipboard_daemon.py — LanceDB Clipboard Brain for Everything Search

Routes clipboard events while Everything Search is the foreground window:
  vibe: <text>   -> query LanceDB top-50, copy filelist:"...";"..." to clipboard
  ai: <task>     -> merge task + last copied files -> write ai_task.md -> open VS Code

Passive at all times: remembers the last detected file list copied to the clipboard.

Install:
    pip install lancedb[embeddings] sentence-transformers pyperclip pywin32

Run:
    python scripts/search_clipboard_daemon.py
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
LANCEDB_URI    = WORKSPACE_ROOT / "db" / "assets.lancedb"
LANCE_TABLE    = os.environ.get("RR_LANCE_TABLE", "assets")
DATABASE_ROOT  = os.environ.get("DATABASE_ROOT", "")   # optional: expands relative paths
AI_TASK_PATH   = WORKSPACE_ROOT / "ai_task.md"
CHECK_INTERVAL = 0.2    # seconds — 200 ms is responsive without hammering the CPU
VIBE_TOP_K     = int(os.environ.get("RR_VIBE_TOP_K", "50"))

# ---------------------------------------------------------------------------
# WINDOWS IMPORTS — this script is Windows-only
# ---------------------------------------------------------------------------
try:
    import win32gui
    import winsound
    import pyperclip
except ImportError as exc:
    sys.exit(
        f"[daemon] Missing required package: {exc}\n"
        "Install with: pip install pywin32 pyperclip"
    )

# ---------------------------------------------------------------------------
# RUNTIME STATE
# ---------------------------------------------------------------------------
_last_seen:         str = ""
_last_copied_files: str = ""
_lance_table               = None   # lazy-loaded on first vibe:

# Asset file extensions used for the passive file-list heuristic
_FILE_EXTS = frozenset({
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tga", ".tiff", ".exr", ".hdr",
    ".obj", ".fbx", ".zip", ".max", ".blend", ".mp4", ".avi", ".mov",
    ".pdf", ".ai", ".psd", ".dwg", ".svg",
})

# ---------------------------------------------------------------------------
# HELPERS — foreground-window guard
# ---------------------------------------------------------------------------
def _is_everything_active():
    """Return True only when Everything Search is the active foreground window."""
    try:
        hwnd  = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        return "everything" in title.lower()
    except Exception:
        return False

# ---------------------------------------------------------------------------
# HELPERS — file-list heuristic
# ---------------------------------------------------------------------------
def _looks_like_file_list(text):
    """Cheap heuristic: does this clipboard text look like a list of file paths?"""
    low = text.lower()
    if ".\\" in low or "./" in low:
        return True
    for ext in _FILE_EXTS:
        if ext in low:
            return True
    return False

# ---------------------------------------------------------------------------
# HELPERS — LanceDB (lazy init)
# ---------------------------------------------------------------------------
def _get_lance_table():
    global _lance_table
    if _lance_table is not None:
        return _lance_table
    try:
        import lancedb
    except ImportError:
        raise RuntimeError(
            "lancedb not installed. Run: pip install lancedb[embeddings]"
        )
    db = lancedb.connect(str(LANCEDB_URI))
    if LANCE_TABLE not in db.table_names():
        raise RuntimeError(
            f"LanceDB table '{LANCE_TABLE}' not found at {LANCEDB_URI}.\n"
            "Run search_lancedb_indexer.py first to build the index."
        )
    _lance_table = db.open_table(LANCE_TABLE)
    print(f"[daemon] LanceDB table '{LANCE_TABLE}' loaded from {LANCEDB_URI}")
    return _lance_table


def _query_lancedb(query_text, top_k=None):
    """Return up to top_k relative_filepath strings matching query_text."""
    if top_k is None:
        top_k = VIBE_TOP_K
    tbl     = _get_lance_table()
    results = tbl.search(query_text).limit(top_k).to_pandas()
    paths   = results["relative_filepath"].tolist()
    if DATABASE_ROOT:
        base  = Path(DATABASE_ROOT)
        paths = [str(base / p) for p in paths]
    # Normalise to Windows backslashes (Everything convention)
    return [str(Path(p)) for p in paths]

# ---------------------------------------------------------------------------
# HELPERS — Everything 1.5 filelist format
# ---------------------------------------------------------------------------
def _build_filelist(paths):
    """Build Everything 1.5 filelist: query string from a list of paths."""
    quoted = ";".join(f'"{p}"' for p in paths if p)
    return f"filelist:{quoted}"

# ---------------------------------------------------------------------------
# HELPERS — audio feedback
# ---------------------------------------------------------------------------
def _beep(kind):
    mapping = {
        "success":  winsound.MB_ICONASTERISK,
        "error":    winsound.MB_ICONHAND,
        "no_match": winsound.MB_ICONEXCLAMATION,
    }
    try:
        winsound.MessageBeep(mapping.get(kind, winsound.MB_ICONASTERISK))
    except Exception:
        pass

# ---------------------------------------------------------------------------
# ROUTE: vibe:
# ---------------------------------------------------------------------------
def _handle_vibe(query):
    """
    Query LanceDB, build filelist string, write to clipboard.
    Returns the filelist string on success, or None on failure.
    """
    try:
        paths = _query_lancedb(query)
    except Exception as exc:
        print(f"[daemon] vibe: LanceDB query failed: {exc}")
        _beep("error")
        return None

    if not paths:
        print(f"[daemon] vibe: no results for '{query}'")
        _beep("no_match")
        return None

    filelist = _build_filelist(paths)
    try:
        pyperclip.copy(filelist)
    except Exception as exc:
        print(f"[daemon] vibe: clipboard write failed: {exc}")
        _beep("error")
        return None

    _beep("success")
    print(f"[daemon] vibe: '{query}' -> {len(paths)} results -> clipboard")
    return filelist

# ---------------------------------------------------------------------------
# ROUTE: ai:
# ---------------------------------------------------------------------------
def _handle_ai(task):
    """
    Combine the ai: instruction with last_copied_files, write ai_task.md,
    and open it in VS Code.
    """
    context = _last_copied_files.strip() if _last_copied_files else "(none)"
    content = (
        "# AI Task\n\n"
        "## Instruction\n\n"
        f"{task}\n\n"
        "## Context: Last Copied Files\n\n"
        f"{context}\n"
    )
    try:
        AI_TASK_PATH.write_text(content, encoding="utf-8")
        print(f"[daemon] ai_task.md written -> {AI_TASK_PATH}")
    except OSError as exc:
        print(f"[daemon] ai: failed to write ai_task.md: {exc}")
        _beep("error")
        return
    try:
        subprocess.run(["code", str(AI_TASK_PATH)], check=False)
    except FileNotFoundError:
        print("[daemon] 'code' not found on PATH - open ai_task.md manually.")

# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------
def run():
    global _last_seen, _last_copied_files

    print(f"[daemon] LanceDB: {LANCEDB_URI}")
    print(f"[daemon] Polling every {CHECK_INTERVAL}s - routes active only while Everything is foreground.")
    print("[daemon] Routes:  'vibe: <text>'  |  'ai: <task>'    (Ctrl+C to stop)\n")

    while True:
        try:
            time.sleep(CHECK_INTERVAL)

            # --- Safe clipboard read ---
            try:
                current = (pyperclip.paste() or "").strip()
            except Exception:
                continue

            if not current or current == _last_seen:
                continue

            # --- Passive memory: capture file lists regardless of foreground window ---
            if _looks_like_file_list(current) and not current.lower().startswith(("vibe:", "ai:")):
                if current != _last_copied_files:
                    _last_copied_files = current
                    print(f"[daemon] File list remembered ({len(current)} chars).")

            # --- Only route vibe:/ai: while Everything is the active window ---
            if not _is_everything_active():
                _last_seen = current
                continue

            low = current.lower()

            # --- Route: vibe: ---
            if low.startswith("vibe:"):
                query = current[5:].strip()
                if query:
                    result = _handle_vibe(query)
                    # Point _last_seen at the new clipboard content so the loop
                    # skips it on the next tick and avoids re-processing the result.
                    _last_seen = result if result is not None else current
                else:
                    _last_seen = current

            # --- Route: ai: ---
            elif low.startswith("ai:"):
                task = current[3:].strip()
                if task:
                    _handle_ai(task)
                _last_seen = current

            else:
                _last_seen = current

        except KeyboardInterrupt:
            print("\n[daemon] Stopped.")
            break
        except Exception as exc:
            # Never let an unhandled exception kill the background loop.
            print(f"[daemon] Unhandled error (continuing): {exc}")
            continue


if __name__ == "__main__":
    run()
