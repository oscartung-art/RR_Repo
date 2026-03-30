import os
import sys
import re
import csv

# Define project root relative to the script's location (tools/ folder)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(PROJECT_ROOT, "projects")
CRM_PATH = os.path.join(PROJECT_ROOT, "db", "Master_CRM.csv")

def parse_front_matter(filepath):
    """Parses nested YAML front matter without third-party libraries."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.search(r'^---\s*\n(.*?)\n---\s*', content, re.DOTALL | re.MULTILINE)
    if not match: return None
    
    lines = [l.split('#')[0].rstrip() for l in match.group(1).splitlines() if l.strip() and not l.lstrip().startswith('#')]
    
    def parse_block(index, current_indent):
        data = {}
        while index < len(lines):
            line = lines[index]
            indent = len(line) - len(line.lstrip())
            
            if indent < current_indent:
                break # Return to parent
                
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                
                if not val: # It's a parent node
                    # Look ahead to see if the next line is more indented
                    if index + 1 < len(lines):
                        next_indent = len(lines[index+1]) - len(lines[index+1].lstrip())
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
    """Loads CRM emails, names, and organizations for fast lookup."""
    crm_data = {'emails': set(), 'names': set(), 'organizations': set()}
    if not os.path.exists(CRM_PATH):
        return None
    with open(CRM_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = (row.get('Email') or '').strip().lower()
            given_name = (row.get('Given Name') or '').strip()
            family_name = (row.get('Family Name') or '').strip()
            org = (row.get('Organization') or '').strip()
            full_name = f"{given_name} {family_name}".strip().lower()
            if email: crm_data['emails'].add(email)
            if full_name: crm_data['names'].add(full_name)
            if org: crm_data['organizations'].add(org.lower())
    return crm_data

def get_crm_validation(name, email, crm_data):
    """Returns a visual tag if the contact is/isn't in the CRM."""
    if not crm_data: return ""
    name_str = str(name).strip().lower() if name and name != "-" else ""
    email_str = str(email).strip().lower() if email and email != "-" else ""
    if not name_str and not email_str: return ""
    
    if email_str and email_str not in crm_data['emails']:
        return " \033[1;41m[! EMAIL NOT IN CRM]\033[0m"
    if name_str and name_str not in crm_data['names'] and name_str not in crm_data['organizations']:
        return " \033[1;41m[! NAME NOT IN CRM]\033[0m"
        
    return " \033[92m[✓ CRM]\033[0m"

def print_row(label, value):
    """Prints a beautifully aligned row, dimming empty values."""
    if not value or value == "-":
        display_val = "\033[90m-\033[0m"
    else:
        display_val = str(value)
    print(f"  \033[36m{label:<15}\033[0m {display_val}")

def print_section(title, dictionary):
    """Prints a nested dictionary section if it has valid data."""
    if not dictionary or not isinstance(dictionary, dict): return
    # Only print section if there's at least one real value inside
    has_data = any(v and v != "-" for v in dictionary.values())
    if has_data:
        print(f"\n\033[1;37m{title}\033[0m")
        for k, v in dictionary.items():
            formatted_key = k.replace('_', ' ').title()
            print_row(formatted_key, v)

def main():
    if len(sys.argv) < 2:
        print("\033[91mUsage:\033[0m rr p [PROJECT_CODE]")
        sys.exit(1)

    code = sys.argv[1].upper()
    filename = f"{code}.md"
    filepath = os.path.join(PROJECTS_DIR, filename)

    if not os.path.exists(filepath):
        print(f"\033[90mProject '{code}' not found exactly. Searching...\033[0m")
        matches = [f for f in os.listdir(PROJECTS_DIR) if code.lower() in f.lower()]
        if not matches:
            print("\033[91mNo matching projects found.\033[0m")
            return
        filename = matches[0]
        filepath = os.path.join(PROJECTS_DIR, filename)

    data = parse_front_matter(filepath)
    if not data:
        print(f"\033[91mError: Could not parse metadata for {filename}\033[0m")
        return

    # Load background CRM data for passive verification
    crm_data = load_crm_data()

    # --- Minimalist Terminal Output ---
    project_code = data.get('code', code)
    status = data.get('status', 'Unknown')
    
    if status.lower() == 'active': status_color = "\033[32m" # Green
    elif status.lower() == 'completed': status_color = "\033[90m" # Gray
    else: status_color = "\033[33m" # Yellow

    print(f"\n\033[1;32m=== PROJECT: {project_code} ===\033[0m")
    print("\033[1;37mCORE INFO\033[0m")
    print_row("Name", data.get('name'))
    print_row("Client", data.get('client'))
    print_row("Status", f"{status_color}{status}\033[0m (Updated: \033[90m{data.get('last_updated', '-')}\033[0m)")
    print_row("F: Drive Path", data.get('f_drive_path'))

    print_section("SITE INFO", data.get("site_info"))
    
    if "contacts" in data:
        print("\n\033[1;37mCONTACTS\033[0m")
        for group, details in data["contacts"].items():
            if isinstance(details, dict):
                # For Client and CG (Dicts with Name/Email inside)
                has_data = any(v and v != "-" for v in details.values())
                if has_data:
                    print(f"  \033[90m[{group.title()}]\033[0m")
                    v_msg = get_crm_validation(details.get('name'), details.get('email'), crm_data)
                    for k, v in details.items():
                        disp = f"{v}{v_msg}" if k.lower() == 'name' and str(v).strip() != "-" else v
                        print_row(f"  {k.title()}", disp)
            else:
                # For flat groups (just in case they are formatted differently)
                print_row(f"  {group.title()}", details)
                        
    if "design_documents" in data:
        print("\n\033[1;37mDESIGN DOCUMENTS\033[0m")
        # Calculate max key length for perfect alignment in this section
        max_key_len = 15
        for details in data["design_documents"].values():
            if isinstance(details, dict):
                for k in details.keys():
                    formatted_key = k.replace('_', ' ').title()
                    if len(formatted_key) + 2 > max_key_len: # +2 for indent
                        max_key_len = len(formatted_key) + 2

        for group, details in data["design_documents"].items():
            if isinstance(details, dict):
                has_data = any(v and v != "-" for v in details.values())
                if has_data:
                    print(f"  \033[90m[{group.title().replace('_', ' ')}]\033[0m")
                    for k, v in details.items():
                        formatted_key = k.replace('_', ' ').title()
                        v_str = str(v).strip().lower()
                        if v_str == 'confirmed':
                            disp = f"\033[92m{v}\033[0m" # Green
                        elif v_str == 'received':
                            disp = f"\033[33m{v}\033[0m" # Yellow
                        elif v_str == 'pending' or v_str == '-':
                            disp = f"\033[91m{v}\033[0m" # Red
                        else:
                            disp = v
                        
                        # Use dynamic width for perfect alignment
                        label = f"  {formatted_key}"
                        print(f"  \033[36m{label:<{max_key_len}}\033[0m {disp}")
                        
    print_section("GIS DATA", data.get("gis"))
    print_section("LINKS", data.get("links"))

    print(f"\n\033[90mTo edit this project data, run: code {filepath}\033[0m\n")

if __name__ == "__main__":
    main()
