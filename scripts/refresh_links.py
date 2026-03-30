import os

PROJECTS_DIR = r"D:\GoogleDrive\RR_Repo\projects"
DASHBOARD = r"D:\GoogleDrive\RR_Repo\dashboard.md"

def refresh_dashboard():
    # 1. Get all project files
    # Ensure the projects directory exists, otherwise create it
    if not os.path.exists(PROJECTS_DIR):
        os.makedirs(PROJECTS_DIR)

    files = [f for f in os.listdir(PROJECTS_DIR) if f.endswith(".md")]

    # 2. Build the text list
    lines = ["# 🎛️ PROJECT INDEX (Auto-Generated)\n"]
    for f in files:
        project_name = f.replace(".md", "")
        # Standard Markdown Link (VS Code Native)
        lines.append(f"- [{project_name}](projects/{f})")

    # 3. Write to a separate index file so it doesn't mess up your manual dashboard
    with open(os.path.join(os.path.dirname(DASHBOARD), "index.md"), "w", encoding="utf-8") as f:
        f.writelines("\n".join(lines))
    print("✅ Index refreshed. Use Ctrl+Click to navigate.")

if __name__ == "__main__":
    refresh_dashboard()
