"""
cmd_c.py — rr c [CODE] [category] [field]
Copy a specific project field to the Windows clipboard.
Example: rr c PLS links client_drive
"""

import subprocess
from .utils import PROJECTS_DIR, c, parse_front_matter


def run(args):
    if len(args) < 3:
        print(c("red", "Usage: rr c [CODE] [category] [field]"))
        print(c("grey", "  Example: rr c PLS links client_drive"))
        return

    code, category, field = args[0].upper(), args[1].lower(), args[2].lower()
    filepath = PROJECTS_DIR / f"{code}.md"

    data = parse_front_matter(filepath)
    if not data:
        print(c("red", f"Project '{code}' not found."))
        return

    section = data.get(category)
    if not isinstance(section, dict):
        print(c("red", f"Category '{category}' not found in {code}."))
        print(c("grey", f"  Available: {', '.join(k for k, v in data.items() if isinstance(v, dict))}"))
        return

    value = section.get(field)
    if not value or str(value).strip() == "-":
        print(c("red", f"Field '{field}' not found or empty in [{category}] for {code}."))
        print(c("grey", f"  Available fields: {', '.join(section.keys())}"))
        return

    result = subprocess.run(
        ["powershell", "-command", f"Set-Clipboard -Value '{value}'"],
        capture_output=True
    )
    if result.returncode == 0:
        print(c("green_fg", f"Copied to clipboard: {value}"))
    else:
        print(c("yellow", f"Clipboard copy failed. Value: {value}"))
