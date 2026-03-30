"""
init_project.py — Project Initializer (alias for new_project.py)
Creates a new project folder on F:\\ with the standard "Flat 3" structure,
a CHANGELOG.md, and a per-project log in D:\\GoogleDrive\\RR_Repo\\log\\.

Usage: python tools/init_project.py --code KIL115 --name HillGrove --client "ABC Developer"

This script wraps new_project.py and adds a per-project log file in log/.
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import date

# Bootstrap Shared module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from Shared.config import BRAIN_ROOT

# Import new_project functions directly
from tools.new_project import generate_folder_structure, create_changelog, update_master_database
import importlib.util

def create_project_log(code, name, client):
    """Creates a per-project log file in D:\\GoogleDrive\\RR_Repo\\log\\."""
    log_dir = BRAIN_ROOT / 'log'
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"{code}_log.md"
    today = date.today().isoformat()
    content = f"""# {code} — Project Log

**Project:** {name}
**Client:** {client}
**Created:** {today}

---

## Log

| Date | Entry |
| :--- | :--- |
| {today} | Project initialized via `init_project.py`. |
"""
    log_path.write_text(content, encoding='utf-8')
    print(f"[+] Created project log at {log_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Initialize a new RR studio project.")
    parser.add_argument('--code', required=True, help='Project code (e.g., KIL115)')
    parser.add_argument('--name', required=True, help='Project name (e.g., HillGrove)')
    parser.add_argument('--client', default='Unknown', help='Client name')
    args = parser.parse_args()

    # Resolve paths
    from Shared.config import PROJECT_ROOT
    safe_name = args.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    folder_name = f"{args.code}_{safe_name}"
    target_path = str(PROJECT_ROOT / folder_name)
    f_drive_path_str = target_path.replace('\\', '/')
    csv_path = str(BRAIN_ROOT / 'db' / 'Project_Master_Index.csv')

    print(f"=== Initializing Project: {args.code} ===")

    if not generate_folder_structure(target_path):
        sys.exit(1)

    create_changelog(target_path, args.code, args.name, args.client)
    create_project_log(args.code, args.name, args.client)
    update_master_database(csv_path, args.code, args.name, args.client, f_drive_path_str)

    print(f"=== Done! {args.code} ready at {target_path} ===")
    print(f"    Log: {BRAIN_ROOT / 'log' / f'{args.code}_log.md'}")


if __name__ == '__main__':
    main()
