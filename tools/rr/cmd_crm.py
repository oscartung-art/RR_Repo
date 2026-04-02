"""
cmd_crm.py — rr crm [search_term]
Display and search the Master CRM contacts database.
"""

import csv
from .utils import CRM_PATH, c


def run(args):
    if not CRM_PATH.exists():
        print(c("red", f"CRM not found at {CRM_PATH}"))
        return

    search = args[0].lower() if args else None

    with open(str(CRM_PATH), encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if search:
        rows = [r for r in rows if any(search in str(v).lower() for v in r.values())]

    if not rows:
        suffix = f" matching: '{search}'" if search else ""
        print(c("red", f"No contacts found{suffix}."))
        return

    # Header
    header = f"{'NAME':<25} {'ORGANIZATION':<28} {'EMAIL':<32} PHONE"
    print(f"\n  {c('white', header)}")
    print(f"  {c('grey', '-' * 90)}")

    for row in rows:
        given  = (row.get("Given Name")   or "").strip()
        family = (row.get("Family Name")  or "").strip()
        name   = f"{given} {family}".strip() or "-"
        org    = (row.get("Organization") or "-").strip()
        email  = (row.get("Email")        or "-").strip()
        phone  = (row.get("Phone 1 - Value") or row.get("Phone") or "-").strip()
        print(f"  {c('cyan', f'{name:<25}')} {org:<28} {c('grey', f'{email:<32}')} {c('grey', phone)}")

    print(c("grey", f"\n  {len(rows)} contact(s) shown.\n"))
