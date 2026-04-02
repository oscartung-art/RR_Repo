"""
cmd_p.py — rr p [CODE] [view]
Project Inspector: display project metadata and drive paths.
Views: summary (default), docs, contacts, links, rend, ani, full
"""

import os
import csv
import re
from .utils import (
    PROJECTS_DIR, CRM_PATH, c, print_row, parse_front_matter
)


def load_crm():
    crm = {"emails": set(), "names": set(), "orgs": set()}
    if not CRM_PATH.exists():
        return None
    with open(str(CRM_PATH), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            e = (row.get("Email") or "").strip().lower()
            n = f"{row.get('Given Name','')} {row.get('Family Name','')}".strip().lower()
            o = (row.get("Organization") or "").strip().lower()
            if e: crm["emails"].add(e)
            if n: crm["names"].add(n)
            if o: crm["orgs"].add(o)
    return crm


def crm_tag(name, email, crm):
    if not crm:
        return ""
    n = str(name or "").strip().lower()
    e = str(email or "").strip().lower()
    if not n and not e:
        return ""
    if e and e not in crm["emails"]:
        return f" {c('red_bg', '[! EMAIL NOT IN CRM]')}"
    if n and n not in crm["names"] and n not in crm["orgs"]:
        return f" {c('red_bg', '[! NAME NOT IN CRM]')}"
    return f" {c('green_fg', '[CRM]')}"


def show_core(data):
    status = data.get("status", "Unknown")
    s_col = "green" if status.lower() == "active" else "grey" if status.lower() == "completed" else "yellow"
    print(f"\n{c('green', '=== PROJECT: ' + str(data.get('code', '?')) + ' ===')}")
    print_row("Name",       data.get("name"))
    print_row("Client",     data.get("client"))
    print_row("Status",     c(s_col, status) + c("grey", f"  (Updated: {data.get('last_updated', '-')})"))
    print_row("F: Drive",   data.get("f_drive_path"))


def show_contacts(data, crm):
    contacts = data.get("contacts")
    if not isinstance(contacts, dict):
        return
    print(f"\n{c('white', 'CONTACTS')}")
    for group, details in contacts.items():
        if not isinstance(details, dict):
            continue
        print(f"  {c('grey', '[' + group.title() + ']')}")
        tag = crm_tag(details.get("name"), details.get("email"), crm)
        for k, v in details.items():
            disp = f"{v}{tag}" if k.lower() == "name" and str(v).strip() != "-" else v
            print_row(f"  {k.title()}", disp, width=16)


def show_docs(data):
    docs = data.get("design_documents")
    if not isinstance(docs, dict):
        return
    print(f"\n{c('white', 'DESIGN DOCUMENTS')}")
    for group, details in docs.items():
        if not isinstance(details, dict):
            continue
        print(f"  {c('grey', '[' + group.title().replace('_', ' ') + ']')}")
        for k, v in details.items():
            v_s = str(v).strip().lower()
            col = "green_fg" if v_s == "confirmed" else "yellow" if v_s == "received" else "red"
            print_row(f"  {k.replace('_', ' ').title()}", c(col, v), width=26)


def show_links(data):
    links = data.get("links")
    if not isinstance(links, dict):
        return
    print(f"\n{c('white', 'DRIVE LINKS')}")
    for k, v in links.items():
        print_row(k.replace("_", " ").title(), v, width=22)


def show_deliverables(data, key, title):
    items = data.get(key)
    if not isinstance(items, dict):
        return
    print(f"\n{c('white', title)}")
    print(f"  {c('grey', f'  ID    Status     Description')}")
    for k, v in sorted(items.items()):
        if isinstance(v, dict):
            status = v.get("status", "-")
            desc   = v.get("desc", "-")
        else:
            val = str(v).strip()
            m = re.match(r"^([^(]+)\s*\(([^)]+)\)$", val)
            status, desc = (m.group(1).strip(), m.group(2).strip()) if m else (val, "-")
        s_l = status.lower()
        col = "green_fg" if s_l == "final" else "green" if s_l == "active" else "yellow" if s_l == "draft" else "grey"
        print(f"  {c('cyan', f'{k:<6}')} {c(col, f'{status:<10}')} {c('grey', desc)}")


def run(args):
    if not args:
        print(c("red", "Usage: rr p [CODE] [docs|contacts|links|rend|ani|full]"))
        return

    code = args[0].upper()
    view = args[1].lower() if len(args) > 1 else "summary"
    filepath = PROJECTS_DIR / f"{code}.md"

    data = parse_front_matter(filepath)
    if not data:
        print(c("red", f"Project '{code}' not found at {filepath}"))
        return

    crm = load_crm()
    show_core(data)

    if view == "summary":
        docs_data = data.get("design_documents", {})
        all_docs = [v for g in docs_data.values() if isinstance(g, dict) for v in g.values()]
        if all_docs:
            conf = sum(1 for v in all_docs if str(v).strip().lower() == "confirmed")
            print(f"\n{c('white', 'STATUS OVERVIEW')}")
            print_row("Documents", f"{conf}/{len(all_docs)} Confirmed")
        rends = data.get("renderings", {})
        anis  = data.get("animations", {})
        if rends or anis:
            all_vals = list(rends.values()) + list(anis.values())
            active = sum(1 for v in all_vals if isinstance(v, str) and v.lower() in ["active", "final", "confirmed"])
            print_row("Deliverables", f"{active}/{len(all_vals)} Active/Final")
        print(c("grey", f"\n  Run 'rr p {code} [docs|contacts|links|rend|ani|full]' for more."))
    elif view == "contacts":
        show_contacts(data, crm)
    elif view == "docs":
        show_docs(data)
    elif view == "links":
        show_links(data)
    elif view in ("rend", "renderings"):
        show_deliverables(data, "renderings", "RENDERINGS")
    elif view in ("ani", "animations"):
        show_deliverables(data, "animations", "ANIMATIONS")
    elif view == "full":
        show_contacts(data, crm)
        show_docs(data)
        show_deliverables(data, "renderings", "RENDERINGS")
        show_deliverables(data, "animations", "ANIMATIONS")
        show_links(data)

    print(c("grey", f"\n  To edit: code {filepath}\n"))
