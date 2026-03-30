import os
import re
import csv
import collections

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from Shared.config import PROJECT_ROOT, BRAIN_ROOT

# Paths
VAULT_PROJECT_DIR = str(PROJECT_ROOT)  # F:\Projects (NAS project mass)
INDEX_PATH = str(BRAIN_ROOT / "db" / "Project_Master_Index.csv")

# Pre-defined mapping to resolve vault folder names to known project codes
FOLDER_TO_CODE = {
    "MaWoRoad": "MWR",
    "KIL112": "KIL11285",
    "KIL11285": "KIL11285",
    "3HG": "3HG",
    "FFS": "FFS",
    "KL1": "KL1",
    "MTC": "MTC",
    "PLS": "PLS",
    "MWR": "MWR"
}

def load_index(csv_path):
    projects = {}
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            # Fix corrupted lines like "-KIL11285"
            content = f.read().replace("-KIL11285", "\nKIL11285")
            
        if not content.strip():
            return {}

        reader = csv.DictReader(content.splitlines())
        for row in reader:
            code = row.get("Code", "").strip()
            if code:
                projects[code] = {
                    "Code": code,
                    "Project Name": row.get("Project Name", "Unknown"),
                    "Client": row.get("Client", "Unknown"),
                    "F: Drive Path": row.get("F: Drive Path", f"F:/{code}"),
                    "Share Link": row.get("Share Link", "-")
                }
    return projects

def save_index(csv_path, projects):
    header = ["Code", "Project Name", "Client", "F: Drive Path", "Share Link"]
    # Ensure directory exists
    dir_name = os.path.dirname(csv_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(csv_path, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        # Sort by code
        for code in sorted(projects.keys()):
            writer.writerow(projects[code])

def parse_markdown_table(content):
    data = {}
    # More robust regex for markdown tables that handles leading/trailing pipes and whitespace
    table_pattern = re.compile(r'\|?\s*(.+?)\s*\|\s*(.+?)\s*\|?\s*[\r\n]+\|?\s*[:\- |]+\s*\|?\s*[\r\n]+((?:\|?.+\|?[\r\n]*)+)')
    matches = table_pattern.findall(content)
    
    for match in matches:
        data_rows = match[2].strip().split('\n')
        for dr in data_rows:
            cols = [c.strip() for c in dr.split('|') if c.strip()]
            if len(cols) >= 2:
                data[cols[0]] = cols[1]
    return data

def parse_key_value(content):
    data = {}
    # Handles: **Key**\nValue
    kv_pattern = re.compile(r'\*\*([A-Za-z0-9_]+)\*\*\s*\n([^\n]+)')
    for match in kv_pattern.finditer(content):
        key = match.group(1).strip()
        val = match.group(2).strip()
        if not val.startswith("|") and not val.startswith("#"):
            data[key] = val
            
    # Handles: Key\nValue
    # E.g. ProjectAddress\n"Nos. 44 to 54A..."
    addr_pattern = re.search(r'ProjectAddress\s*\n\s*"([^"]+)"', content)
    if addr_pattern:
        data["ProjectAddress"] = addr_pattern.group(1)

    return data

def clean_text(text):
    if not text or text == "-" or text == "-\\<br>": return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
    return text.strip()

def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return {}

    extracted = {}
    table_data = parse_markdown_table(content)
    kv_data = parse_key_value(content)
    
    # Merge extracted data
    combined = {**table_data, **kv_data}
    
    name = clean_text(combined.get("Name") or combined.get("ProjectName"))
    if not name and combined.get("Lot"):
        name = "Lot " + clean_text(combined.get("Lot"))
    if not name and combined.get("ProjectAddress"):
        name = clean_text(combined.get("ProjectAddress"))
        
    client = clean_text(combined.get("ClientCompanyName") or combined.get("Client"))
    link = clean_text(combined.get("RenderingShareDriveUrl"))
    
    if name: extracted["Project Name"] = name
    if client: extracted["Client"] = client
    if link: extracted["Share Link"] = link
    
    return extracted

def main():
    projects = load_index(INDEX_PATH)
    
    print(f"Scanning {VAULT_PROJECT_DIR} for project metadata...")
    
    # Process files
    for root, dirs, files in os.walk(VAULT_PROJECT_DIR):
        # Determine the project code from the folder name
        # If we're at the root, we might infer from filename
        folder_name = os.path.basename(root)
        
        # Only look at files ending in .md
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                extracted = process_file(file_path)
                
                if not extracted:
                    continue
                
                # Try to figure out the code
                code = None
                if folder_name in FOLDER_TO_CODE:
                    code = FOLDER_TO_CODE[folder_name]
                elif folder_name == "project":
                    # We are in root of the project directory
                    for known_key in FOLDER_TO_CODE:
                        if known_key.lower() in file.lower():
                            code = FOLDER_TO_CODE[known_key]
                            break
                            
                if not code:
                    # Guess code from folder if not "Document"
                    if folder_name not in ["Document", "Contacts", "quotation"]:
                        code = folder_name.upper()

                if code:
                    if code not in projects:
                        projects[code] = {
                            "Code": code,
                            "Project Name": "Unknown",
                            "Client": "Unknown",
                            "F: Drive Path": f"F:/{code}",
                            "Share Link": "-"
                        }
                    
                    # Update fields if we found them
                    if "Project Name" in extracted and projects[code]["Project Name"] in ["Unknown", "-", ""]:
                        projects[code]["Project Name"] = extracted["Project Name"]
                    if "Client" in extracted and projects[code]["Client"] in ["Unknown", "-", ""]:
                        projects[code]["Client"] = extracted["Client"]
                    if "Share Link" in extracted and projects[code]["Share Link"] in ["Unknown", "-", ""]:
                        projects[code]["Share Link"] = extracted["Share Link"]

    print(f"Saving updated index to {INDEX_PATH}...")
    save_index(INDEX_PATH, projects)
    
    # Re-read to print
    for k, v in sorted(projects.items()):
        print(f"[{v['Code']}] {v['Project Name']} | Client: {v['Client']}")

if __name__ == "__main__":
    main()
