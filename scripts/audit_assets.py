import os
from pathlib import Path

def audit_library(root_path):
    print(f"🔍 Scanning: {root_path}")
    model_exts = {'.zip', '.max', '.fbx', '.obj', '.blend', '.rar'}
    img_exts = {'.jpg', '.jpeg', '.png'}
    
    all_files = list(Path(root_path).rglob('*'))
    images = {f.stem.lower(): f for f in all_files if f.suffix.lower() in img_exts}
    assets = {f.stem.lower(): f for f in all_files if f.suffix.lower() in model_exts or f.is_dir()}

    # Filter out root and system folders
    assets = {k: v for k, v in assets.items() if k not in {'3d-sky', 'assets', 'temp'}}

    orphans = set(assets.keys()) - set(images.keys())
    print(f"\n✅ Audit Complete. Found {len(assets)} potential assets.")
    
    if orphans:
        print(f"❌ Found {len(orphans)} assets missing thumbnails:")
        with open("orphans_log.txt", "w", encoding="utf-8") as f:
            for o in sorted(orphans):
                f.write(f"{assets[o]}\n")
        print("📝 List saved to orphans_log.txt")
    else:
        print("⭐ All assets are perfectly paired!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        audit_library(sys.argv[1])
    else:
        print("Please provide a folder path to audit.")
