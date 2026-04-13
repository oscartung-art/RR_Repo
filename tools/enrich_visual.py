"""enrich_visual.py — Visual enrichment pass for furniture assets.

Reads the existing .metadata.efu database, finds Furniture rows where visual
fields (Genre, Company, Period) are still blank/dash, runs qwen3-vl on the
thumbnail image, and writes back only those three fields.

Column mapping (Furniture):
  Genre   → Primary Color / Material  (e.g. "walnut, brass, leather")
  Company → Shape Form                (e.g. "round, wall-mounted, freestanding")
  Period  → Style / Era               (e.g. "mid-century modern, contemporary")

Usage:
  python tools/enrich_visual.py [--dry-run] [--yes] [--limit=N]

Flags:
  --dry-run     Preview what would change; do not write to DB
  --yes, -y     Auto-confirm without prompting
  --limit=N     Process at most N rows (useful for testing)
  --force       Re-enrich rows even if visual fields are already filled
"""

import csv
import sys
import re
import base64
import json
import urllib.request
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Config — mirrors ingest_asset.py paths
# ---------------------------------------------------------------------------
THUMBNAIL_BASE   = Path(r"D:\DB")
METADATA_EFU_PATH = THUMBNAIL_BASE / ".metadata.efu"
OLLAMA_VISION_MODEL = "qwen3-vl:latest"
OLLAMA_ENDPOINT     = "http://127.0.0.1:11434/api/generate"

# Visual fields this script is responsible for
VISUAL_FIELDS = ("Genre", "Company", "Period")

EFU_HEADERS = [
    "Filename", "Rating", "Tags", "URL", "From",
    "Mood", "Author", "Writer", "Album", "Genre",
    "People", "Company", "Period", "Artist", "Title",
    "Comment", "To", "Manager", "Subject", "CRC-32",
]


# ---------------------------------------------------------------------------
# Spinner
# ---------------------------------------------------------------------------
class _Spinner:
    def __init__(self, message: str = "Working") -> None:
        self._msg = message
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self) -> None:
        width = 30
        progress = 0.0
        step = 3.0
        label = self._msg.ljust(16)
        try:
            while not self._stop.is_set():
                filled = int(width * progress / 100)
                bar = "[" + "#" * filled + "-" * (width - filled) + "]"
                sys.stderr.write(f"\r{label} {bar} {progress:5.1f}%")
                sys.stderr.flush()
                time.sleep(0.12)
                progress = min(progress + step, 90.0)
            sys.stderr.write(f"\r{label} [" + "#" * width + "] 100.0%" + " " * 10 + "\n")
            sys.stderr.flush()
        except Exception:
            pass

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join()


# ---------------------------------------------------------------------------
# Ollama helpers
# ---------------------------------------------------------------------------
def _ollama_generate(prompt: str, image_path: Path, timeout: int = 180) -> str:
    payload = {
        "model": OLLAMA_VISION_MODEL,
        "prompt": prompt,
        "stream": False,
        "images": [base64.b64encode(image_path.read_bytes()).decode("utf-8")],
    }
    req = urllib.request.Request(
        OLLAMA_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    spinner = _Spinner("Vision model...")
    spinner.start()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    finally:
        spinner.stop()
    return (body.get("response") or "").strip()


def _extract_json(text: str) -> dict[str, str]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    # Strip thinking block if present
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned, flags=re.IGNORECASE).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return {str(k): "" if v is None else str(v) for k, v in data.items()}
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return {str(k): "" if v is None else str(v) for k, v in data.items()}
    except json.JSONDecodeError:
        return {}
    return {}


# ---------------------------------------------------------------------------
# EFU helpers
# ---------------------------------------------------------------------------
def _load_efu(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        print(f"[ERROR] EFU file not found: {path}")
        sys.exit(1)
    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


def _save_efu(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=EFU_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "-") or "-" for k in EFU_HEADERS})


def _needs_visual(row: dict[str, str]) -> bool:
    """Return True if any visual field is missing or dash."""
    return any(
        not row.get(f, "").strip() or row.get(f, "").strip() == "-"
        for f in VISUAL_FIELDS
    )


def _is_furniture(row: dict[str, str]) -> bool:
    manager = row.get("Manager", "").strip()
    mood = row.get("Mood", "").strip()
    return "Furniture" in manager or mood.startswith("Furniture/")


# ---------------------------------------------------------------------------
# Vision prompt
# ---------------------------------------------------------------------------
VISION_PROMPT = (
    "You are a strict furniture visual metadata extractor. "
    "Look at this product image carefully. "
    "Return ONLY compact JSON with exactly these three keys:\n"
    "  primary_material_or_color: the dominant material(s) and/or color(s) visible "
    "    (e.g. 'walnut wood, brass legs', 'white marble, chrome', 'dark leather'). "
    "    List up to 3 comma-separated descriptors. Use '-' if unclear.\n"
    "  shape_form: the physical form/shape of the product "
    "    (e.g. 'round', 'rectangular', 'wall-mounted', 'freestanding', 'cantilevered'). "
    "    Use '-' if unclear.\n"
    "  style_period: the design style or era "
    "    (e.g. 'mid-century modern', 'contemporary', 'industrial', 'Scandinavian', 'art deco'). "
    "    Use '-' if unclear.\n"
    "STRICT rules: (1) Use '-' for any field you are not confident about. "
    "(2) No extra keys. (3) No explanation. (4) No markdown."
)


# ---------------------------------------------------------------------------
# Main enrichment logic
# ---------------------------------------------------------------------------
def enrich_visual(
    efu_path: Path = METADATA_EFU_PATH,
    thumbnail_base: Path = THUMBNAIL_BASE,
    dry_run: bool = False,
    auto_yes: bool = False,
    limit: int | None = None,
    force: bool = False,
) -> None:
    rows = _load_efu(efu_path)

    # Find rows that need visual enrichment
    candidates = [
        (i, row) for i, row in enumerate(rows)
        if _is_furniture(row) and (force or _needs_visual(row))
    ]

    if limit is not None:
        candidates = candidates[:limit]

    total = len(candidates)
    if total == 0:
        print("No rows need visual enrichment. All Genre/Company/Period fields are filled.")
        return

    print(f"\nFound {total} furniture row(s) with missing visual fields.")
    if dry_run:
        print("[DRY RUN] No changes will be written.\n")
        for _, row in candidates:
            fname = row.get("Filename", "?")
            img = thumbnail_base / fname
            missing = [f for f in VISUAL_FIELDS if not row.get(f, "").strip() or row.get(f, "").strip() == "-"]
            img_ok = "OK" if img.exists() else "NOT FOUND"
            print(f"  {fname}  ->  missing: {', '.join(missing)}  |  image: {img_ok}")
        return

    if not auto_yes:
        choice = input(f"\nEnrich {total} row(s) with vision model? [y/N]: ").strip().lower()
        if choice not in {"y", "yes"}:
            print("Aborted.")
            return

    updated = 0
    skipped = 0

    for idx, (row_idx, row) in enumerate(candidates, start=1):
        fname = row.get("Filename", "")
        img_path = thumbnail_base / fname
        print(f"\n[{idx}/{total}] {fname}")

        if not img_path.exists():
            print(f"  [SKIP] Image not found: {img_path}")
            skipped += 1
            continue

        try:
            raw = _ollama_generate(VISION_PROMPT, img_path)
            data = _extract_json(raw)
        except Exception as exc:
            print(f"  [ERROR] Vision model failed: {exc}")
            skipped += 1
            continue

        # Map extracted keys to EFU columns
        genre   = (data.get("primary_material_or_color", "") or "").strip()
        company = (data.get("shape_form", "") or "").strip()
        period  = (data.get("style_period", "") or "").strip()

        # Only update fields that are still blank (unless --force)
        changed: list[str] = []
        current_row = rows[row_idx]

        def _update(field: str, value: str) -> None:
            if not value or value == "-":
                return
            if force or not current_row.get(field, "").strip() or current_row.get(field, "").strip() == "-":
                current_row[field] = value
                changed.append(f"{field}={value}")

        _update("Genre",   genre)
        _update("Company", company)
        _update("Period",  period)

        if changed:
            print(f"  Updated: {' | '.join(changed)}")
            updated += 1
        else:
            print(f"  No usable values returned (all '-').")
            skipped += 1

    # Write back
    _save_efu(efu_path, rows)
    print(f"\nDone. Updated: {updated} | Skipped/failed: {skipped} | Total: {total}")
    print(f"Saved to: {efu_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def _parse_args() -> dict:
    args = {
        "dry_run": False,
        "auto_yes": False,
        "limit": None,
        "force": False,
    }
    for arg in sys.argv[1:]:
        if arg in ("--dry-run", "--dryrun"):
            args["dry_run"] = True
        elif arg in ("--yes", "-y"):
            args["auto_yes"] = True
        elif arg == "--force":
            args["force"] = True
        elif arg.startswith("--limit="):
            try:
                args["limit"] = int(arg.split("=", 1)[1])
            except ValueError:
                print(f"[WARN] Invalid --limit value: {arg}")
        elif arg in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        else:
            print(f"[WARN] Unknown argument: {arg}")

    return args


if __name__ == "__main__":
    args = _parse_args()
    enrich_visual(
        dry_run=args["dry_run"],
        auto_yes=args["auto_yes"],
        limit=args["limit"],
        force=args["force"],
    )
