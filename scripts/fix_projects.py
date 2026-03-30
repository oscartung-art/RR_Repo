import os
import re
import datetime

PROJECTS_DIR = r"D:\GoogleDrive\RR_Repo\projects"

# Project Data Mappings from Active_Projects.md
project_data = {
    "FFS": {"name": "-", "client": "Unknown", "f_drive_path": "F:/FFS", "status": "Lead"},
    "KIL11285": {"name": "Wing Kwong Street / Sung On Street", "client": "Fortune Hope Limited", "f_drive_path": "F:/KIL11285", "status": "Lead"},
    "KL1": {"name": "Upper Prince", "client": "One KL Development Limited One KL II Development Limited One KL III Development Limite", "f_drive_path": "F:/KL1", "status": "Lead"},
    "MLS": {"name": "Unknown", "client": "Unknown", "f_drive_path": "F:/MLS", "status": "Lead"},
    "MTC": {"name": "-", "client": "Unknown", "f_drive_path": "F:/MTC", "status": "Lead"},
    "MWR": {"name": "PROPOSED COMPOSITE REDEVELOPMENT AT", "client": "New Merit Limited(WOP)", "f_drive_path": "F:/MWR mawo road", "status": "Lead"},
    "PLS": {"name": "PLS", "client": "NewMeritLimited", "f_drive_path": "F:/PLS", "status": "Completed"},
    "YKS": {"name": "Unknown", "client": "Unknown", "f_drive_path": "F:/YKS", "status": "Completed"}
}

def fix_project(code):
    filepath = os.path.join(PROJECTS_DIR, f"{code}.md")
    data = project_data.get(code)
    if not data: return

    # Construct YAML
    yaml_lines = [
        "---",
        f'code: "{code}"',
        f'name: "{data["name"]}"',
        f'client: "{data["client"]}"',
        f'f_drive_path: "{data["f_drive_path"]}"',
        f'status: "{data["status"]}"',
        f'last_updated: "{datetime.date.today().strftime("%Y-%m-%d")}"',
        "",
        "# Site Information",
        "site_info:",
        '  lot: "-"',
        '  address: "-"',
        "",
        "# Contact Information",
        "contacts:",
        "  client:",
        f'    name: "{data["client"]}"',
        '    email: "-"',
        '    address: "-"',
        '    phone: "-"',
        "  cg:",
        '    name: "RealRendering"',
        '    email: "info@real-hk.com"',
        "  team:",
        '    architect: "-"',
        "",
        "# GIS Data",
        "gis:",
        '  transformation: "-"',
        "",
        "# Important Links",
        "links:",
        '  rr_share: "-"',
        "---",
        ""
    ]
    
    # Read existing content (if any)
    content = ""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Strip existing YAML if present
            content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)
            # Remove the old headers we added manually earlier
            content = re.sub(r'^# .*\n\n- \*\*Project Name\*\*:.*\n- \*\*Client\*\*:.*\n- \*\*F: Drive Path\*\*:.*\n', '', content, flags=re.MULTILINE)
            content = content.strip()

    # Special handling for PLS detailed info
    if code == "PLS":
        # Keep the existing detailed PLS structure we just created
        pass 

    new_content = "\n".join(yaml_lines) + "\n\n" + (content if content else f"# {code} Project Details\n\nContent goes here.")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"? Fixed {code}.md")

if __name__ == "__main__":
    for code in project_data.keys():
        fix_project(code)
