import os
import re
import datetime

# Define project root relative to the script's location (scripts/ folder)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(PROJECT_ROOT, "projects")
DASHBOARD_PATH = os.path.join(PROJECT_ROOT, "dashboard.md")

def parse_front_matter(content):
    front_matter = {}
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if match:
        yaml_block = match.group(1)
        for line in yaml_block.splitlines():
            line = line.split('#')[0].strip()
            if ':' in line and not line.startswith(' '):
                key, val = line.split(':', 1)
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                front_matter[key.strip()] = val
    return front_matter

def get_project_data():
    all_projects = []
    if not os.path.exists(PROJECTS_DIR): return all_projects
    for filename in os.listdir(PROJECTS_DIR):
        if filename.endswith(".md"):
            filepath = os.path.join(PROJECTS_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                data = parse_front_matter(content)
                if data:
                    data.setdefault('code', os.path.splitext(filename)[0])
                    all_projects.append(data)
    return all_projects

def print_terminal_dashboard(projects):
    leads, active, completed = [], [], []
    for p in sorted(projects, key=lambda x: x.get('code', '')):
        code = p.get('code', 'UNK')
        name = p.get('name', '-')
        client = p.get('client', 'Unknown')
        status = p.get('status', 'Lead').lower()
        
        if status == 'lead':
            leads.append(f"  \033[36m{code:<10}\033[0m | {name:<20} | {client}")
        elif status == 'active':
            active.append(f"  \033[32m{code:<10}\033[0m | {name:<20} | {client}")
        elif status == 'completed':
            date = p.get('last_updated', datetime.date.today().strftime("%Y-%m-%d"))
            completed.append(f"  \033[90m{code:<10}\033[0m | {name:<20} | Finished: {date}")

    print("\n\033[1;36m=== 🔵 LEADS (Inquiry Stage) ===\033[0m")
    print("\n".join(leads) if leads else "  No leads.")

    print("\n\033[1;32m=== 🟢 ACTIVE (Production) ===\033[0m")
    print("\n".join(active) if active else "  No active projects.")

    print("\n\033[1;90m=== ⚪ COMPLETED (Archive) ===\033[0m")
    print("\n".join(completed) if completed else "  No completed projects.")
    print()

def generate_dashboard_content(projects):
    leads = []
    active = []
    completed = []
    for p in sorted(projects, key=lambda x: x.get('code', '')):
        code = p.get('code', 'UNK')
        name = p.get('name', '-')
        client = p.get('client', 'Unknown')
        status = p.get('status', 'Lead').lower()
        line = f"- [{code}](projects/{code}.md) | {name} | Client: {client}"
        if status == 'lead': leads.append(line)
        elif status == 'active': active.append(line)
        elif status == 'completed':
            date = p.get('last_updated', datetime.date.today().strftime("%Y-%m-%d"))
            completed.append(f"- [x] [{code}](projects/{code}.md) | Finished {date}")
    
    out = ["## ?? LEADS (Inquiry Stage)"]
    out.extend(leads if leads else ["- No leads."])
    out.append("\n## ?? ACTIVE (Production)")
    out.extend(active if active else ["- No active projects."])
    out.append("\n## ?? COMPLETED (Archive)")
    out.extend(completed if completed else ["- No completed projects."])
    return "\n".join(out)

def update_dashboard(new_content):
    with open(DASHBOARD_PATH, 'r', encoding='utf-8') as f:
        full = f.read()
    
    # Use a simpler regex that doesn't fail on complex characters
    # Look for the first '---' and the last '---'
    parts = full.split('---')
    if len(parts) >= 2:
        header = parts[0].strip()
        new_full = f"{header}\n---\n\n{new_content}\n\n---\n"
        with open(DASHBOARD_PATH, 'w', encoding='utf-8') as f:
            f.write(new_full)
        print("? Dashboard updated.")
    else:
        print("? Could not find dashboard structure.")

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate and update the project dashboard.")
    parser.add_argument("--print-only", action="store_true", help="Print dashboard content to stdout instead of updating dashboard.md")
    args = parser.parse_args()

    if args.print_only:
        print_terminal_dashboard(get_project_data())
    else:
        dashboard_content = generate_dashboard_content(get_project_data())
        update_dashboard(dashboard_content)
