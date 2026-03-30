import os
import csv
import sys
import argparse
from datetime import date
from pathlib import Path

# Bootstrap Shared module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from Shared.config import PROJECT_ROOT, BRAIN_ROOT

# Constants
DEFAULT_CSV_PATH = str(BRAIN_ROOT / "db" / "Project_Master_Index.csv")
DEFAULT_F_DRIVE_ROOT = str(PROJECT_ROOT)

def generate_folder_structure(target_path):
    """Creates the 'Flat 3' structure for the new project."""
    folders = ["01_Brief", "02_Work", "03_Shared"]
    try:
        os.makedirs(target_path, exist_ok=True)
        for folder in folders:
            os.makedirs(os.path.join(target_path, folder), exist_ok=True)
        print(f"[+] Created folder structure at {target_path}")
        return True
    except Exception as e:
        print(f"[-] Error creating folder structure: {e}")
        return False

def create_changelog(target_path, code, name, client):
    """Creates a CHANGELOG.md inside the new project folder."""
    changelog_path = os.path.join(target_path, "CHANGELOG.md")
    today = date.today().isoformat()
    content = f"""# {code} — {name}

**Client:** {client}
**Created:** {today}

---

## Changelog

### {today} — Project Initialized
- Folder structure created by `new_project.py`.
- Awaiting brief in `01_Brief/`.
"""
    try:
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Created CHANGELOG.md at {changelog_path}")
        return True
    except Exception as e:
        print(f"[-] Error creating CHANGELOG.md: {e}")
        return False

def update_master_database(csv_path, code, name, client, f_drive_path):
    """Appends the new project to the master CSV database."""
    file_exists = os.path.exists(csv_path)
    try:
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Code", "Project Name", "Client", "F: Drive Path", "Status"])
            writer.writerow([code, name, client, f_drive_path, "Active"])
            print(f"[+] Appended project {code} to {csv_path}")
            return True
    except Exception as e:
        print(f"[-] Error updating master database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate a new project environment (Zero-Lock-In).")
    parser.add_argument("--code", required=True, help="Unique project code (e.g., KIL11285)")
    parser.add_argument("--name", required=True, help="Human-readable project name")
    parser.add_argument("--client", default="Unknown", help="Client name for CRM tracking")

    args = parser.parse_args()

    safe_name = args.name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    folder_name = f"{args.code}_{safe_name}"
    target_path = os.path.join(DEFAULT_F_DRIVE_ROOT, folder_name)
    f_drive_path_str = target_path.replace("\\", "/")

    print(f"=== Initializing New Project: {args.code} ===")

    if not generate_folder_structure(target_path):
        sys.exit(1)

    if not create_changelog(target_path, args.code, args.name, args.client):
        print("[-] Warning: CHANGELOG.md not created.")

    if not update_master_database(DEFAULT_CSV_PATH, args.code, args.name, args.client, f_drive_path_str):
        sys.exit(1)

    print(f"=== Success! Project {args.code} is ready at {target_path} ===")

if __name__ == "__main__":
    main()
