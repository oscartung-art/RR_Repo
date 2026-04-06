import csv
import json
import os
import re
import subprocess
from collections import defaultdict

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "../../../Database/ProjectDB.csv"))
REPO_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
PROJECTS_JSON_PATH = os.path.join(REPO_ROOT, "db", "projects.json")
PROJECT_MASS_DIR = "F:/" 

KNOWN_CODES = ["PLS", "KL1", "YKS", "MLS", "MWR", "3HG", "CSW", "HWC", "FS3", "GLC", "KIL112", "KR1", "URA"]

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '', name).strip()
    return name[:50]

def get_real_paths():
    mapping = {}
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-ChildItem F:\\ -Directory | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            folders = result.stdout.splitlines()
            for folder in folders:
                match = re.match(r'^([A-Z0-9]{2,6})\b', folder)
                if match:
                    code = match.group(1)
                    mapping[code] = os.path.join(PROJECT_MASS_DIR, folder)
    except Exception as e:
        print(f"Warning: Could not scan F: drive: {e}")
    return mapping

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    real_path_mapping = get_real_paths()
    
    projects = defaultdict(lambda: {
        "info": {},
        "contacts": [],
        "gis": {},
        "links": {},
        "schedules": defaultdict(list),
        "design_docs": []
    })

    with open(DB_PATH, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Try to find a known code in any potential column
            project_code = None
            potential_cols = ["Title", "Period", "Company", "To", "Subject", "People", "Rating"]
            
            for col in potential_cols:
                val = (row.get(col) or "").strip()
                if val in KNOWN_CODES:
                    project_code = val
                    break
            
            if not project_code:
                # Search for known codes within larger strings
                row_str = " ".join(row.values())
                for code in KNOWN_CODES:
                    if code in row_str:
                        project_code = code
                        break
            
            if not project_code:
                continue
            
            tag = (row.get("Tags") or "").strip()
            url = (row.get("URL") or "").strip()
            filename = (row.get("Filename") or "").strip()
            from_col = (row.get("From") or "").strip()
            mood_col = (row.get("Mood") or "").strip()
            author_col = (row.get("Author") or "").strip()
            writer_col = (row.get("Writer") or "").strip()
            album_col = (row.get("Album") or "").strip()
            genre_col = (row.get("Genre") or "").strip()

            if tag == "ProjectInfo":
                if url == "SiteInfo": projects[project_code]["info"][from_col] = mood_col
                elif url == "Contact": projects[project_code]["info"][f"Contact.{from_col}"] = mood_col
                elif url == "GIS": projects[project_code]["gis"][from_col] = mood_col
                elif url == "Link": projects[project_code]["links"][from_col] = mood_col

            elif tag == "DesignDocument":
                projects[project_code]["design_docs"].append({
                    "ID": filename, "Type": url, "Status": from_col, "Confirmation": mood_col, "Source": author_col
                })

            elif url == "Contact" or filename == "Contact":
                projects[project_code]["contacts"].append({
                    "Company": from_col, "Person": mood_col, "Email": author_col, "Phone": writer_col, "Address": album_col
                })

            elif "Rendering" in url or "Animation" in url:
                type_key = "Rendering" if "Rendering" in url else "Animation"
                projects[project_code]["schedules"][type_key].append({
                    "Path": filename, "Label": url, "Subject": from_col, "Status": author_col, "Date": album_col, "Engine": genre_col
                })

            elif url in ["Texture", "Furniture", "Vegetation", "Fixture", "Material"]:
                projects[project_code]["schedules"]["Asset"].append({
                    "ID": tag, "Path": filename, "Category": url, "SubCategory": mood_col, "Location": author_col,
                    "Description": genre_col, "Spec": writer_col, "Dimensions": album_col, "Finish": row.get("People")
                })

    master_index = []
    output_base = os.path.join(REPO_ROOT, "scratch", "migration_output")
    os.makedirs(output_base, exist_ok=True)

    for code, data in projects.items():
        safe_code = sanitize_filename(code)
        
        real_path = real_path_mapping.get(safe_code)
        if not real_path:
            p_name = data["info"].get("Name") or data["info"].get("Lot") or "Project"
            real_path = os.path.join(PROJECT_MASS_DIR, f"{safe_code}_{sanitize_filename(p_name)}")

        p_name = data["info"].get("Name") or data["info"].get("Lot") or "Unknown"
        p_client = data["info"].get("Contact.Client.Name") or "Unknown"

        master_index.append({
            "code": safe_code,
            "name": p_name,
            "client": p_client,
            "path": real_path.replace("\\", "/")
        })
        
        out_dir = os.path.join(output_base, safe_code)
        os.makedirs(out_dir, exist_ok=True)

        meta = {
            "project_info": data["info"],
            "gis": data["gis"],
            "links": data["links"],
            "contacts": data["contacts"],
            "design_docs": data["design_docs"]
        }
        with open(os.path.join(out_dir, "_project_meta.json"), "w") as f:
            json.dump(meta, f, indent=4)

        for sched_name, items in data["schedules"].items():
            if not items: continue
            with open(os.path.join(out_dir, f"{sched_name.lower()}_schedule.csv"), "w", newline="", encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=items[0].keys())
                writer.writeheader()
                writer.writerows(items)

    with open(PROJECTS_JSON_PATH, "w") as f:
        json.dump(master_index, f, indent=4)
    
    print(f"Exported master index to {PROJECTS_JSON_PATH}")
    print(f"Migration output generated in scratch/migration_output/")

if __name__ == "__main__":
    migrate()
