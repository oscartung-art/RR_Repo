import os
import sys
import re
import subprocess

# Define project root relative to the script's location (tools/ folder)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(PROJECT_ROOT, "projects")

def parse_front_matter(filepath):
    """Parses nested YAML front matter without third-party libraries."""
    if not os.path.exists(filepath): return None
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
            if indent < current_indent: break
            if ':' in line:
                key, val = line.split(':', 1)
                key, val = key.strip(), val.strip().strip("'\"")
                if not val:
                    if index + 1 < len(lines):
                        next_indent = len(lines[index+1]) - len(lines[index+1].lstrip())
                        if next_indent > indent:
                            nested_data, index = parse_block(index + 1, next_indent)
                            data[key] = nested_data
                            continue
                else: data[key] = val
            index += 1
        return data, index
    parsed_data, _ = parse_block(0, 0)
    return parsed_data

def copy_to_clipboard(text):
    """Pipes text directly to the Windows clipboard via the 'clip' command."""
    # Use subprocess.run to execute the built-in Windows 'clip' command.
    # We encode to utf-8 to handle any special characters properly.
    process = subprocess.Popen('clip', stdin=subprocess.PIPE, shell=True)
    process.communicate(input=text.encode('utf-8'))

def extract_value(data, keys):
    """Recursively traverses the dictionary using a list of keys."""
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current

def main():
    if len(sys.argv) < 3:
        print("\033[91mUsage:\033[0m rr c [PROJECT_CODE] [category] [field]")
        print("  \033[90mExample 1:\033[0m rr c PLS links client_drive")
        print("  \033[90mExample 2:\033[0m rr c PLS contacts client email")
        sys.exit(1)

    code = sys.argv[1].upper()
    filepath = os.path.join(PROJECTS_DIR, f"{code}.md")
    
    data = parse_front_matter(filepath)
    if not data:
        print(f"\033[91mProject '{code}' not found.\033[0m")
        sys.exit(1)

    # The remaining arguments are the path to the desired data (e.g., ['links', 'client_drive'])
    path_keys = [k.lower() for k in sys.argv[2:]]
    
    value = extract_value(data, path_keys)

    if value and value != "-":
        copy_to_clipboard(str(value))
        path_str = " -> ".join(path_keys)
        print(f"\033[92mCopied to clipboard:\033[0m {path_str} \033[90m({code})\033[0m")
    else:
        path_str = " -> ".join(path_keys)
        print(f"\033[91mError:\033[0m No valid data found for '{path_str}' in {code}.")

if __name__ == "__main__":
    main()
