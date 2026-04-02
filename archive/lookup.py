import os
import sys
import re
import csv
from pathlib import Path

# Bootstrap Shared module
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from Shared.config import BRAIN_ROOT

PROJECTS_DIR = str(BRAIN_ROOT / "projects")
CRM_PATH = str(BRAIN_ROOT / "db" / "Master_CRM.csv")


def parse_front_matter(filepath):
    """Parses nested YAML front matter without third-party libraries."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'^---\s*\n(.*?)\n---\s*', content, re.DOTALL | re.MULTILINE)
    if not match:
        return None
    lines = [l.split('#')[0].rstrip() for l in match.group(1).splitlines() if l.strip() and not l.lstrip().startswith('#')]

    def parse_block(index, current_indent):
        data = {}
        while index < len(lines):
            line = lines[index]
            indent = len(line) - len(line.lstrip())
            if indent < current_indent:
                break
            if ':' in line:
                key, val = line.split(':', 1)
                key, val = key.strip(), val.strip().strip("'\"")
                if not val:
                    if index + 1 < len(lines):
                        next_indent = len(lines[index + 1]) - len(lines[index + 1].lstrip())
                        if next_indent > indent:
                            nested_data, index = parse_block(index + 1, next_indent)
                            data[key] = nested_data
                            continue
                else:
                    data[key] = val
            index += 1
        return data, index

    parsed_data, _ = parse_block(0, 0)
    return parsed_data


def load_crm_data():
    crm_data = {'emails': set(), 'names': set(), 'organizations': set()}
    if not os.path.exists(CRM_PATH):
        return None
    with open(CRM_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = (row.get('Email') or '').strip().lower()
            full_name = f"{(row.get('Given Name') or '')} {(row.get('Family Name') or '')}".strip().lower()
            org = (row.get('Organization') or '').strip().lower()
            if email: crm_data['emails'].add(email)
            if full_name: crm_data['names'].add(full_name)
            if org: crm_data['organizations'].add(org)
    return crm_data


def get_crm_tag(name, email, crm_data):
    if not crm_data:
        return ""
    n, e = str(name or "").strip().lower(), str(email or "").strip().lower()
    if not n and not e:
        return ""
    if e and e not in crm_data['emails']:
        return " \033[1;41m[! EMAIL NOT IN CRM]\033[0m"
    if n and n not in crm_data['names'] and n not in crm_data['organizations']:
        return " \033[1;41m[! NAME NOT IN CRM]\033[0m"
    return " \033[92m[CRM]\033[0m"


def print_row(label, value, width=15):
    if not value or value == "-":
        disp = "\033[90m-\033[0m"
    else:
        disp = str(value)
    print(f"  \033[36m{label:<{width}}\033[0m {disp}")


def show_core(data):
    status = data.get('status', 'Unknown')
    s_color = "\033[32m" if status.lower() == 'active' else "\033[90m" if status.lower() == 'completed' else "\033[33m"
    print(f"\n\033[1;32m=== PROJECT: {data.get('code')} ===\033[0m")
    print_row("Name", data.get('name'))
    print_row("Client", data.get('client'))
    print_row("Status", f"{s_color}{status}\033[0m (Updated: \033[90m{data.get('last_updated', '-')}\033[0m)")
    print_row("F: Drive Path", data.get('f_drive_path'))


def show_contacts(data, crm):
    if "contacts" not in data:
        return
    print("\n\033[1;37mCONTACTS\033[0m")
    for group, details in data["contacts"].items():
        if not isinstance(details, dict):
            continue
        print(f"  \033[90m[{group.title()}]\033[0m")
        v_tag = get_crm_tag(details.get('name'), details.get('email'), crm)
        for k, v in details.items():
            disp = f"{v}{v_tag}" if k.lower() == 'name' and str(v).strip() != "-" else v
            print_row(f"  {k.title()}", disp)


def show_docs(data):
    if "design_documents" not in data:
        return
    print("\n\033[1;37mDESIGN DOCUMENTS\033[0m")
    for group, details in data["design_documents"].items():
        if not isinstance(details, dict):
            continue
        print(f"  \033[90m[{group.title().replace('_', ' ')}]\033[0m")
        for k, v in details.items():
            v_s = str(v).strip().lower()
            disp = f"\033[92m{v}\033[0m" if v_s == 'confirmed' else f"\033[33m{v}\033[0m" if v_s == 'received' else f"\033[91m{v}\033[0m"
            print_row(f"  {k.replace('_', ' ').title()}", disp, width=25)


def show_links(data):
    if "links" not in data:
        return
    print("\n\033[1;37mDRIVE LINKS\033[0m")
    for k, v in data["links"].items():
        print_row(k.replace('_', ' ').title(), v, width=20)


def show_deliverables(data, key, title):
    if key not in data:
        return
    print(f"\n\033[1;37m{title}\033[0m")
    items = data[key]
    if not isinstance(items, dict):
        return

    print(f"  \033[90m{'ID':<5} {'Description':<30} {'Status':<10} {'Comment'}\033[0m")

    for k, v in sorted(items.items()):
        if isinstance(v, dict):
            status = v.get('status', '-')
            desc = v.get('desc', '-')
            comment = v.get('comment', '-')
        else:
            val_str = str(v).strip()
            match = re.match(r'^([^(]+)\s*\(([^)]+)\)$', val_str)
            if match:
                status, desc = match.group(1).strip(), match.group(2).strip()
                comment = "-"
            else:
                status, desc, comment = val_str, "-", "-"

        s_lower = status.lower()
        s_color = (
            "\033[92m" if s_lower == 'final' else
            "\033[32m" if s_lower == 'active' else
            "\033[33m" if s_lower == 'draft' else
            "\033[90m"
        )

        print(f"  \033[36m{k:<5}\033[0m \033[37m{desc:<30}\033[0m {s_color}{status:<10}\033[0m \033[90m{comment}\033[0m")


def main():
    if len(sys.argv) < 2:
        print("\033[91mUsage:\033[0m rr p [CODE] [docs|contacts|links|rend|ani|full]")
        sys.exit(1)

    code = sys.argv[1].upper()
    view = sys.argv[2].lower() if len(sys.argv) > 2 else "summary"
    filepath = os.path.join(PROJECTS_DIR, f"{code}.md")

    data = parse_front_matter(filepath)
    if not data:
        print(f"\033[91mProject '{code}' not found.\033[0m")
        return

    crm = load_crm_data()
    show_core(data)

    if view == "summary":
        if "design_documents" in data:
            all_docs = [v for g in data["design_documents"].values() if isinstance(g, dict) for v in g.values()]
            conf = all_docs.count("Confirmed")
            print(f"\n\033[1;37mSTATUS OVERVIEW\033[0m")
            print_row("Documents", f"{conf}/{len(all_docs)} Confirmed")

        rends = data.get('renderings', {})
        anis = data.get('animations', {})
        if rends or anis:
            all_vals = list(rends.values()) + list(anis.values())
            active = sum(1 for v in all_vals if isinstance(v, str) and v.lower() in ['active', 'final', 'confirmed'])
            print_row("Deliverables", f"{active}/{len(all_vals)} Active/Final")

        print(f"\033[90m\nRun 'rr p {code} [docs|contacts|links|rend|ani|full]' for more.\033[0m")

    elif view == "contacts":
        show_contacts(data, crm)
    elif view == "docs":
        show_docs(data)
    elif view == "links":
        show_links(data)
    elif view in ["renderings", "rend"]:
        show_deliverables(data, 'renderings', 'RENDERINGS')
    elif view in ["animations", "ani"]:
        show_deliverables(data, 'animations', 'ANIMATIONS')
    elif view == "full":
        show_contacts(data, crm)
        show_docs(data)
        show_deliverables(data, 'renderings', 'RENDERINGS')
        show_deliverables(data, 'animations', 'ANIMATIONS')
        show_links(data)

    print(f"\n\033[90mTo edit: code {filepath}\033[0m\n")


if __name__ == "__main__":
    main()
