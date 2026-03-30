import json
import os
import sys

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_JSON_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "../projects.json"))
MIGRATION_OUTPUT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "../scratch/migration_output"))

def load_projects():
    if not os.path.exists(PROJECTS_JSON_PATH):
        print(f"Error: {PROJECTS_JSON_PATH} not found. Please run tools/migrate_db.py first.")
        return []
    with open(PROJECTS_JSON_PATH, "r") as f:
        return json.load(f)

def get_project_meta(project):
    # Try looking in the project's own folder first (on F:)
    if project.get("path"):
        meta_path = os.path.join(project["path"], "_project_meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                return json.load(f)

    # Fallback to migration output for non-deployed metadata
    meta_path = os.path.join(MIGRATION_OUTPUT_DIR, project["code"], "_project_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            return json.load(f)
    return None

def find_project(query):
    projects = load_projects()
    results = [p for p in projects if query.lower() in p["code"].lower() or query.lower() in p["name"].lower() or query.lower() in p["client"].lower()]
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/lookup.py <query>")
        print("Example: python tools/lookup.py PLS")
        sys.exit(1)

    query = sys.argv[1]
    results = find_project(query)

    if not results:
        print(f"No projects found matching '{query}'.")
        return

    for p in results:
        print(f"\n--- Project: {p['code']} ---")
        print(f"Name:   {p['name']}")
        print(f"Client: {p['client']}")
        print(f"Path:   {p['path']}")
        
        meta = get_project_meta(p)
        if meta:
            print("\n  [Site Info]")
            for k, v in meta.get("project_info", {}).items():
                if v and v != "-":
                    print(f"    {k}: {v}")
            
            print("\n  [Share Links]")
            for k, v in meta.get("links", {}).items():
                if v and v != "-":
                    print(f"    {k}: {v}")
            
            if meta.get("gis") and any(v != "-" for v in meta["gis"].values()):
                print("\n  [GIS Data]")
                for k, v in meta["gis"].items():
                    if v and v != "-":
                        print(f"    {k}: {v}")
        else:
            print("\n  (Detailed metadata not found)")

if __name__ == "__main__":
    main()
