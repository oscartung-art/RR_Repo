"""
audit_assets.py — Asset Naming Convention Auditor
Scans a target directory and reports files violating the RR naming conventions.
Usage: python tools/audit_assets.py --dir "G:\\" --type asset
       python tools/audit_assets.py --dir "F:\\3HG_HillGrove\\02_Work" --type project
"""

import os
import re
import sys
import argparse
from pathlib import Path
from datetime import date

# Bootstrap Shared module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from Shared.config import BRAIN_ROOT

# ─── Naming Rules ────────────────────────────────────────────────────────────

ASSET_PATTERN = re.compile(
    r'^[A-Z][a-zA-Z]+_[A-Z][a-zA-Z0-9]+_[A-Z][a-zA-Z0-9]+\.(zip|jpg|jpeg|png)$'
)
# Formula: [Family]_[ModelName]_[Brand].ext  e.g. Armchair_Eames_HermanMiller.zip

PROJECT_FOLDER_PATTERN = re.compile(r'^[A-Z0-9]+_[A-Z][a-zA-Z0-9]+$')
# Formula: [CODE]_[ProjectName]  e.g. 3HG_HillGrove

BRIEF_FILE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}_[A-Z][a-zA-Z0-9_]+\.\w+$')
WORK_FILE_PATTERN  = re.compile(r'^[A-Z0-9]+_[A-Z][a-zA-Z0-9_]+_v\d{3}\.\w+$')
SHARED_FILE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}_[A-Z0-9]+_[A-Z][a-zA-Z0-9_]+_v\d{3}\.\w+$')

DOCS_PATTERN = re.compile(r'^[A-Z][a-zA-Z0-9]+(_[A-Z][a-zA-Z0-9]+)*\.md$')
SCRIPT_PATTERN = re.compile(r'^[a-z][a-z0-9_]+\.py$')

SKIP_EXTENSIONS = {'.ini', '.db', '.lnk', '.tmp', '.log', '.gitkeep'}
SKIP_NAMES = {'desktop.ini', 'thumbs.db', '.DS_Store', '__pycache__'}

# ─── Suggestion Helpers ───────────────────────────────────────────────────────

def to_pascal(s):
    """Convert a string to PascalCase."""
    return ''.join(word.capitalize() for word in re.split(r'[\s_\-]+', s) if word)

def suggest_asset_name(filename):
    stem = Path(filename).stem
    ext  = Path(filename).suffix
    parts = re.split(r'[\s_\-]+', stem)
    if len(parts) >= 3:
        return f"{to_pascal(parts[0])}_{to_pascal(parts[1])}_{to_pascal(parts[2])}{ext}"
    return f"{to_pascal(stem)}_Unknown_Unknown{ext}"

def suggest_script_name(filename):
    stem = Path(filename).stem
    return re.sub(r'[^a-z0-9_]', '', stem.lower().replace(' ', '_').replace('-', '_')) + '.py'

# ─── Audit Functions ──────────────────────────────────────────────────────────

def audit_asset_dir(directory):
    """Audit G:\\ style asset directory — expects [Family]_[ModelName]_[Brand].zip"""
    violations = []
    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if os.path.isdir(fpath):
            continue
        if fname.lower() in SKIP_NAMES or Path(fname).suffix.lower() in SKIP_EXTENSIONS:
            continue
        if not ASSET_PATTERN.match(fname):
            violations.append({
                'file': fname,
                'rule': 'Global Asset: `[Family]_[ModelName]_[Brand].ext`',
                'suggestion': suggest_asset_name(fname)
            })
    return violations

def audit_project_dir(directory):
    """Audit F:\\ style project directory — checks subfolders and files by context."""
    violations = []
    for root, dirs, files in os.walk(directory):
        rel = os.path.relpath(root, directory)
        depth = 0 if rel == '.' else len(Path(rel).parts)

        # Depth 0: root folder name
        if depth == 0:
            folder = os.path.basename(directory)
            if not PROJECT_FOLDER_PATTERN.match(folder):
                violations.append({
                    'file': folder + '/',
                    'rule': 'Project Root: `[CODE]_[ProjectName]`',
                    'suggestion': folder  # hard to auto-suggest without knowing code
                })

        for fname in files:
            if fname.lower() in SKIP_NAMES or Path(fname).suffix.lower() in SKIP_EXTENSIONS:
                continue
            parent = os.path.basename(root)
            if parent == '01_Brief' and not BRIEF_FILE_PATTERN.match(fname):
                violations.append({
                    'file': os.path.join(rel, fname),
                    'rule': '01_Brief: `YYYY-MM-DD_Description.ext`',
                    'suggestion': f"{date.today().isoformat()}_{to_pascal(Path(fname).stem)}{Path(fname).suffix}"
                })
            elif parent == '02_Work' and not WORK_FILE_PATTERN.match(fname):
                violations.append({
                    'file': os.path.join(rel, fname),
                    'rule': '02_Work: `CODE_Description_v###.ext`',
                    'suggestion': f"CODE_{to_pascal(Path(fname).stem)}_v001{Path(fname).suffix}"
                })
            elif parent == '03_Shared' and not SHARED_FILE_PATTERN.match(fname):
                violations.append({
                    'file': os.path.join(rel, fname),
                    'rule': '03_Shared: `YYYY-MM-DD_CODE_Description_v###.ext`',
                    'suggestion': f"{date.today().isoformat()}_CODE_{to_pascal(Path(fname).stem)}_v001{Path(fname).suffix}"
                })
    return violations

def audit_tools_dir(directory):
    """Audit tools/ — expects snake_case.py"""
    violations = []
    for fname in os.listdir(directory):
        if not fname.endswith('.py'):
            continue
        if fname.lower() in SKIP_NAMES:
            continue
        if not SCRIPT_PATTERN.match(fname):
            violations.append({
                'file': fname,
                'rule': 'Script: `snake_case.py`',
                'suggestion': suggest_script_name(fname)
            })
    return violations

# ─── Report Renderer ──────────────────────────────────────────────────────────

def render_report(violations, directory, audit_type):
    lines = [
        f"# Asset Audit Report",
        f"",
        f"**Directory:** `{directory}`",
        f"**Type:** `{audit_type}`",
        f"**Date:** {date.today().isoformat()}",
        f"**Violations Found:** {len(violations)}",
        f"",
    ]
    if not violations:
        lines.append("> All files comply with the naming convention.")
    else:
        lines += [
            "| File | Rule Violated | Suggested Name |",
            "| :--- | :--- | :--- |",
        ]
        for v in violations:
            lines.append(f"| `{v['file']}` | {v['rule']} | `{v['suggestion']}` |")
    return '\n'.join(lines)

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RR Asset Naming Convention Auditor")
    parser.add_argument('--dir', required=True, help='Directory to audit')
    parser.add_argument(
        '--type',
        choices=['asset', 'project', 'tools'],
        default='asset',
        help='Audit type: asset (G:\\), project (F:\\), tools (tools/)'
    )
    parser.add_argument('--save', action='store_true', help='Save report to log/ folder')
    args = parser.parse_args()

    directory = args.dir
    if not os.path.isdir(directory):
        print(f"[-] Directory not found: {directory}")
        sys.exit(1)

    audit_fn = {
        'asset':   audit_asset_dir,
        'project': audit_project_dir,
        'tools':   audit_tools_dir,
    }[args.type]

    violations = audit_fn(directory)
    report = render_report(violations, directory, args.type)
    print(report)

    if args.save:
        log_dir = BRAIN_ROOT / 'log'
        log_dir.mkdir(exist_ok=True)
        report_path = log_dir / f"{date.today().isoformat()}_audit_{args.type}.md"
        report_path.write_text(report, encoding='utf-8')
        print(f"\n[+] Report saved to {report_path}")

if __name__ == '__main__':
    main()
