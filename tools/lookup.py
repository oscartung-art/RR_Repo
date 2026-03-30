import os
import sys
import re

PROJECTS_DIR = r"D:\GoogleDrive\RR_Repo\projects"

def parse_yaml(filepath):
    """Simple parser to get top-level keys from YAML front matter."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.search(r'^---\s*\n(.*?)\n---\s*', content, re.DOTALL | re.MULTILINE)
    if not match:
        return None
    
    yaml_text = match.group(1)
    data = {}
    for line in yaml_text.splitlines():
        line = line.split('#')[0] # Remove comments
        if not line.strip(): continue
        if ':' in line and not line[0].isspace():
            key, val = line.split(':', 1)
            val = val.strip().strip("'\"")
            data[key.strip()] = val
    return data

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/lookup.py <PROJECT_CODE>")
        print("Example: python tools/lookup.py PLS")
        sys.exit(1)

    code = sys.argv[1].upper()
    filename = f"{code}.md"
    filepath = os.path.join(PROJECTS_DIR, filename)

    if not os.path.exists(filepath):
        # Try a partial search if exact code doesn't exist
        print(f"Project '{code}' not found exactly. Searching...")
        matches = [f for f in os.listdir(PROJECTS_DIR) if code.lower() in f.lower()]
        if not matches:
            print("No matching projects found.")
            return
        filename = matches[0]
        filepath = os.path.join(PROJECTS_DIR, filename)
        print(f"Found closest match: {filename}\n")

    data = parse_yaml(filepath)
    if not data:
        print(f"Error: Could not parse metadata for {filename}")
        return

    # Beautiful Terminal Output
    print("=" * 50)
    print(f"???  PROJECT INSPECTOR: {data.get('code', code)}")
    print("=" * 50)
    print(f"{'NAME:':<15} {data.get('name', '-')}")
    print(f"{'CLIENT:':<15} {data.get('client', '-')}")
    print(f"{'STATUS:':<15} {data.get('status', 'Unknown')}")
    print(f"{'LAST UPDATED:':<15} {data.get('last_updated', '-')}")
    print("-" * 50)
    print(f"{'F: DRIVE:':<15} {data.get('f_drive_path', '-')}")
    
    # Check for site info (simplified for the script)
    print("-" * 50)
    print(f"?? VS CODE CMD:  Ctrl+P -> {filename}")
    print("=" * 50)

if __name__ == "__main__":
    main()
