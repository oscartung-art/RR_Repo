import json
import os
import shutil

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_JSON_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "../projects.json"))
MIGRATION_OUTPUT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "../scratch/migration_output"))

def deploy():
    if not os.path.exists(PROJECTS_JSON_PATH):
        print(f"Error: {PROJECTS_JSON_PATH} not found.")
        return

    with open(PROJECTS_JSON_PATH, "r") as f:
        projects = json.load(f)

    for p in projects:
        code = p["code"]
        target_path = p["path"]
        
        # Verify target folder exists
        if not os.path.exists(target_path):
            print(f"Skipping {code}: Target path {target_path} does not exist.")
            continue

        source_dir = os.path.join(MIGRATION_OUTPUT_DIR, code)
        if not os.path.exists(source_dir):
            print(f"Skipping {code}: Source migration data not found.")
            continue

        print(f"Deploying metadata for {code} to {target_path}...")
        
        # Move meta and schedules
        for item in os.listdir(source_dir):
            src_item = os.path.join(source_dir, item)
            dst_item = os.path.join(target_path, item)
            
            try:
                # If target exists, overwrite it
                if os.path.exists(dst_item):
                    if os.path.isdir(dst_item):
                        shutil.rmtree(dst_item)
                    else:
                        os.remove(dst_item)
                
                shutil.copy2(src_item, dst_item)
                print(f"  -> Copied {item}")
            except Exception as e:
                print(f"  !! Error copying {item}: {e}")

    print("\nDeployment complete.")

if __name__ == "__main__":
    deploy()
