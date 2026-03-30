import os
import re

PROJECTS_DIR = r"D:\GoogleDrive\RR_Repo\projects"

def validate_file(filepath):
    filename = os.path.basename(filepath)
    issues = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.search(r'^---\s*\n(.*?)\n---\s*', content, re.DOTALL | re.MULTILINE)
    if not match:
        return ["? CRITICAL: Missing or malformed YAML front matter"]
    
    yaml_text = match.group(1)
    data = {}
    
    # Use a more explicit line-by-line parsing with debug prints if needed
    lines = yaml_text.splitlines()
    for line in lines:
        original_line = line
        line = line.split('#')[0] # Remove comments but preserve indentation for now
        
        if not line.strip(): continue
        
        # A top-level key must start at the beginning of the line (no spaces/tabs)
        if ':' in line and not line[0].isspace():
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            data[key] = val
    
    required = ['code', 'name', 'client', 'f_drive_path', 'status', 'last_updated']
    for req in required:
        if req not in data:
            issues.append(f"? Missing required key: {req}")
        elif not data[req] and req != 'name':
             issues.append(f"?? Key '{req}' exists but is empty")
            
    if 'code' in data:
        expected_code = os.path.splitext(filename)[0]
        if data['code'] != expected_code:
            issues.append(f"? Code mismatch: YAML says '{data['code']}', filename is '{expected_code}'")
            
    return issues

def run_validation():
    if not os.path.exists(PROJECTS_DIR): return
    files = [f for f in os.listdir(PROJECTS_DIR) if f.endswith('.md')]
    global_report = []
    for f in files:
        res = validate_file(os.path.join(PROJECTS_DIR, f))
        if res:
            global_report.append(f"### {f}")
            for msg in res:
                global_report.append(msg)
            global_report.append("")
    
    if not global_report:
        print("? ALL CLEAR: All project files passed validation.")
    else:
        print("# Project Validation Report\n")
        print("\n".join(global_report))

if __name__ == "__main__":
    run_validation()
