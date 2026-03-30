import os
import argparse
import datetime

# Using the constants from gemini.md
PROJECTS_ROOT = r"F:\Projects"
LOG_ROOT = r"D:\GoogleDrive\RR_Repo\log"
SUBDIRECTORIES = ["01_Models", "02_Textures", "03_Renders", "04_Fusion"]

def initialize_project(project_code):
    """
    Creates a new project directory structure and its corresponding log file.
    """
    # 1. Create the main project directory
    project_path = os.path.join(PROJECTS_ROOT, project_code)
    try:
        os.makedirs(project_path, exist_ok=True)
        print(f"✅ Created project directory: {project_path}")
    except OSError as e:
        print(f"❌ Error creating project directory: {e}")
        return

    # 2. Create the standard subdirectories
    for subdir in SUBDIRECTORIES:
        subdir_path = os.path.join(project_path, subdir)
        os.makedirs(subdir_path, exist_ok=True)
        print(f"   - Created subdirectory: {subdir_path}")

    # 3. Create the project log file
    log_filename = f"{project_code}_log.md"
    log_filepath = os.path.join(LOG_ROOT, log_filename)
    
    # Initial content for the log file
    today = datetime.date.today().isoformat()
    initial_content = f"""# Project Log: {project_code}

| Date       | Description         | Status      |
| :--------- | :------------------ | :---------- |
| {today}    | Project Initialized | In Progress |
"""
    
    try:
        if not os.path.exists(log_filepath):
            with open(log_filepath, "w") as f:
                f.write(initial_content)
            print(f"✅ Created project log file: {log_filepath}")
        else:
            print(f"⚠️ Project log file already exists: {log_filepath}")
    except OSError as e:
        print(f"❌ Error creating log file: {e}")


def main():
    """Main function to parse arguments and initialize the project."""
    parser = argparse.ArgumentParser(description="Initialize a new project structure and log file.")
    parser.add_argument("project_code", help="The unique project code (e.g., KIL115).")
    args = parser.parse_args()

    print(f"
Initializing project: {args.project_code}...")
    initialize_project(args.project_code)
    print("
Project initialization complete.")


if __name__ == "__main__":
    main()
