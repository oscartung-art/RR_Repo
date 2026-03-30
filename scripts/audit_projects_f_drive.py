'''import os
import re

F_DRIVE_PATH = r"F:"
REPO_PATH = r"D:\GoogleDrive\RR_Repo"
INDEX_MD_PATH = os.path.join(REPO_PATH, "index.md")

def get_f_drive_projects():
    f_drive_projects = set()
    # Exclude system folders and hidden directories
    excluded_folders = {'#recycle', '.', '..', 'System Volume Information', '$RECYCLE.BIN'}
    for item_name in os.listdir(F_DRIVE_PATH):
        item_path = os.path.join(F_DRIVE_PATH, item_name)
        if os.path.isdir(item_path) and item_name not in excluded_folders and not item_name.startswith('.') and not item_name.startswith('_'):
            f_drive_projects.add(item_name)
    return f_drive_projects

def get_indexed_projects():
    indexed_projects = set()
    if os.path.exists(INDEX_MD_PATH):
        with open(INDEX_MD_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            # Regex to find Markdown links like [PROJECT_NAME](projects/PROJECT_NAME.md)
            # and extract PROJECT_NAME
            # Assuming project names in index.md match the directory names
            matches = re.findall(r'\[(.*?)\]\(projects/.*?\.md\)', content)
            for match in matches:
                indexed_projects.add(match)
    return indexed_projects

def run_audit():
    f_drive_projects = get_f_drive_projects()
    indexed_projects = get_indexed_projects()

    missing_from_index = f_drive_projects - indexed_projects
    not_found_on_f_drive = indexed_projects - f_drive_projects

    report_lines = []
    report_lines.append("# Project Audit Report")
    report_lines.append(f"Run Date: {os.path.basename(os.getcwd())}")
    report_lines.append("") # Empty string for newline after run date

    if missing_from_index:
        report_lines.append("## ❌ Projects on F:\ Drive but NOT in index.md (Missing from Dashboard Linkage)")
        for project in sorted(list(missing_from_index)):
            report_lines.append(f"- {project}")
    else:
        report_lines.append("## ✅ All F:\ Drive projects are linked in index.md")

    report_lines.append("
---
") # Separator

    if not_found_on_f_drive:
        report_lines.append("## ⚠️ Projects in index.md but NOT on F:\ Drive (Or Name Mismatch)")
        for project in sorted(list(not_found_on_f_drive)):
            report_lines.append(f"- {project} (Consider renaming on F:\ or removing from index.md)")
    else:
        report_lines.append("## ✅ All indexed projects are present on F:\ Drive (by name)")

    # Output the report to a markdown file in the scratch directory
    report_file_path = os.path.join(REPO_PATH, "scratch", "project_audit_report.md")
    os.makedirs(os.path.dirname(report_file_path), exist_ok=True)
    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write("
".join(report_lines))

    print(f"✅ Project audit complete. Report saved to: {report_file_path}")

if __name__ == "__main__":
    run_audit()''