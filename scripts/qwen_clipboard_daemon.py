"""
qwen_clipboard_daemon.py — Clipboard command router for masterdb.csv

Monitors clipboard for commands starting with "qwen:" and performs local operations.

Example commands:
    qwen: make WallLamp_SoffioWallHorizontal_CD2E46B2.jpg 5 stars
    qwen: rate Bench_TallixArtFoundry_2A7DFD3C.jpg 3 stars
    qwen: set Carpet_Cascade7629_79157840.jpg rating 4

On success: plays ding sound, logs action.
On failure: plays error sound, prints reason.
"""

import os
import re
import time
import winsound
from pathlib import Path

import pandas as pd

# --- CONFIG ---
REPO_ROOT = Path(__file__).resolve().parents[1]
MASTERDB_PATH = REPO_ROOT / "db" / "masterdb.csv"
QUERY_PREFIX = "qwen:"
CHECK_INTERVAL = 0.2  # seconds between clipboard polls

# Sound constants (Windows)
DING_OK = winsound.MB_ICONASTERISK
DING_ERR = winsound.MB_ICONHAND

# Regex patterns for command parsing
PATTERNS = [
    # "qwen: make <filename> N stars"
    re.compile(
        r"^\s*make\s+(?P<filename>[\w\-\.]+)\s+(?P<rating>[1-5])\s+stars?\s*$",
        re.IGNORECASE,
    ),
    # "qwen: rate <filename> N stars"
    re.compile(
        r"^\s*rate\s+(?P<filename>[\w\-\.]+)\s+(?P<rating>[1-5])\s+stars?\s*$",
        re.IGNORECASE,
    ),
    # "qwen: set <filename> rating N"
    re.compile(
        r"^\s*set\s+(?P<filename>[\w\-\.]+)\s+rating\s+(?P<rating>[1-5])\s*$",
        re.IGNORECASE,
    ),
]


def extract_command(text):
    """Parse clipboard text and return (filename, rating) or None."""
    if not text:
        return None

    stripped = text.strip()
    if not stripped:
        return None

    # Strip prefix
    prefix_pattern = re.escape(QUERY_PREFIX)
    match = re.match(rf"^\s*{prefix_pattern}\s*(.+?)\s*$", stripped, flags=re.IGNORECASE)
    if not match:
        return None

    command_body = match.group(1).strip()
    if not command_body:
        return None

    # Try each pattern
    for pattern in PATTERNS:
        cmd_match = pattern.match(command_body)
        if cmd_match:
            filename = cmd_match.group("filename")
            rating = int(cmd_match.group("rating"))
            return filename, rating

    return None


def update_masterdb(filename, rating):
    """Update the rating for filename in masterdb.csv. Returns (success, message)."""
    if not MASTERDB_PATH.exists():
        return False, f"masterdb.csv not found at {MASTERDB_PATH}"

    df = pd.read_csv(MASTERDB_PATH, keep_default_na=False)

    # Normalize filename for matching (handle forward/backslash differences)
    search_name = filename.replace("\\", "/")
    matched_rows = df["Filename"].str.contains(
        re.escape(filename), case=True, na=False
    ) | df["Filename"].str.contains(
        re.escape(search_name), case=True, na=False
    )

    if not matched_rows.any():
        return False, f"Asset not found: {filename}"

    # Update rating (use "-" for unrated, numeric for 1-5)
    rating_value = str(rating)
    df.loc[matched_rows, "Rating"] = rating_value

    # Save back
    df.to_csv(MASTERDB_PATH, index=False)

    count = matched_rows.sum()
    return True, f"Updated {count} row(s): {filename} → {rating} star(s)"


def play_sound(sound_type):
    """Play Windows system sound."""
    try:
        winsound.MessageBeep(sound_type)
    except Exception:
        pass  # Silent failure if sound not available


def run_daemon():
    print("=" * 60)
    print("QWEN CLIPBOARD DAEMON")
    print("=" * 60)
    print(f"Watching clipboard for: '{QUERY_PREFIX} <command>'")
    print(f"Database: {MASTERDB_PATH}")
    print()
    print("Supported commands:")
    print("  qwen: make <filename> 5 stars")
    print("  qwen: rate <filename> 3 stars")
    print("  qwen: set <filename> rating 4")
    print()
    print("Press Ctrl+C to stop.")
    print("=" * 60)
    print()

    # Verify database exists
    if not MASTERDB_PATH.exists():
        print(f"ERROR: masterdb.csv not found at {MASTERDB_PATH}")
        return

    print(f"[OK] Database loaded: {MASTERDB_PATH}")
    print(f"[OK] Listening on clipboard...\n")

    last_clipboard = ""
    processed_commands = set()

    try:
        while True:
            # Read clipboard
            try:
                import pyperclip
                current_clipboard = pyperclip.paste().strip()
            except ImportError:
                print("ERROR: pyperclip not installed. Run: pip install pyperclip")
                return
            except Exception:
                time.sleep(CHECK_INTERVAL)
                continue

            # Detect new clipboard content
            if current_clipboard and current_clipboard != last_clipboard:
                # Parse command
                result = extract_command(current_clipboard)
                if result:
                    filename, rating = result
                    cmd_key = f"{filename}:{rating}"

                    # Avoid re-processing same command
                    if cmd_key not in processed_commands:
                        print(f"\n[CMD] {filename} → {rating} star(s)")

                        success, message = update_masterdb(filename, rating)

                        if success:
                            print(f"[OK] {message}")
                            play_sound(DING_OK)
                        else:
                            print(f"[ERR] {message}")
                            play_sound(DING_ERR)

                        processed_commands.add(cmd_key)

                last_clipboard = current_clipboard

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n[STOP] Daemon stopped by user.")


if __name__ == "__main__":
    run_daemon()
