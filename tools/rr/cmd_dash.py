"""
cmd_dash.py — rr dash
Terminal project dashboard: Leads / Active / Completed.
Reads all projects/*.md files and displays a categorised summary.
"""

import os
import datetime
from .utils import PROJECTS_DIR, c, parse_front_matter


def run(args):
    if not PROJECTS_DIR.exists():
        print(c("red", f"No projects/ directory found at {PROJECTS_DIR}"))
        return

    leads, active, completed = [], [], []

    for filename in sorted(os.listdir(str(PROJECTS_DIR))):
        if not filename.endswith(".md"):
            continue
        filepath = PROJECTS_DIR / filename
        data = parse_front_matter(filepath)
        if not data:
            continue

        code   = str(data.get("code", os.path.splitext(filename)[0])).upper()
        name   = data.get("name", "-")
        client = data.get("client", "Unknown")
        status = str(data.get("status", "lead")).strip().lower()

        rends = data.get("renderings", {})
        anis  = data.get("animations", {})
        if not isinstance(rends, dict): rends = {}
        if not isinstance(anis, dict):  anis  = {}
        total = len(rends) + len(anis)
        done  = sum(
            1 for v in list(rends.values()) + list(anis.values())
            if isinstance(v, str) and v.lower() in ("active", "final", "confirmed")
        )
        count = c("grey", f" ({done}/{total})") if total > 0 else ""

        if status == "lead":
            leads.append(
                f"  {c('cyan', f'{code:<10}')}  {name:<24}  {c('grey', client)}"
            )
        elif status == "active":
            active.append(
                f"  {c('green', f'{code:<10}')}{count}  {name:<24}  {c('grey', client)}"
            )
        elif status == "completed":
            date = data.get("last_updated", datetime.date.today().isoformat())
            completed.append(
                f"  {c('grey', f'{code:<10}')}  {name:<24}  {c('grey', 'Finished: ' + date)}"
            )

    print(f"\n{c('cyan', '=== LEADS ===')}")
    print("\n".join(leads) if leads else c("grey", "  No leads."))

    print(f"\n{c('green', '=== ACTIVE ===')}")
    print("\n".join(active) if active else c("grey", "  No active projects."))

    print(f"\n{c('grey', '=== COMPLETED ===')}")
    print("\n".join(completed) if completed else c("grey", "  No completed projects."))
    print()
