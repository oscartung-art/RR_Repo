try:
    import unreal
except ImportError:
    unreal = None
    print("Warning: 'unreal' module not available. This script must run inside Unreal Editor's Python environment.")
import os
import sys

"""
unreal_cleanup.py
Standardizes Unreal Engine project structure and naming conventions.
Mandate: Flat & Singular (e.g., 'Mesh' not 'Meshes')
"""

# Configuration
CORE_FOLDERS = ["Map", "Mesh", "Mat", "Seq", "Core", "Datasmith"]
PREFIXES = {
    "StaticMesh": "SM_",
    "Material": "M_",
    "MaterialInstanceConstant": "MI_",
    "Texture2D": "T_",
    "BlueprintGeneratedClass": "BP_",
    "World": "LV_",
    "LevelSequence": "LS_"
}

def rename_assets():
    """Renames assets based on their type and the project prefix."""
    selected_assets = unreal.EditorUtilityLibrary.get_selected_assets()
    
    if not selected_assets:
        unreal.log_warning("No assets selected for renaming.")
        return

    for asset in selected_assets:
        asset_class = asset.get_class().get_name()
        asset_name = asset.get_name()
        prefix = PREFIXES.get(asset_class, "")
        
        if prefix and not asset_name.startswith(prefix):
            new_name = f"{prefix}{asset_name}"
            unreal.EditorAssetLibrary.rename_asset(asset.get_path_name(), f"{os.path.dirname(asset.get_path_name())}/{new_name}")
            unreal.log(f"Renamed: {asset_name} -> {new_name}")

def organize_folders():
    """Moves root assets into standard Project/ folder structure."""
    root_path = "/Game"
    project_root = "/Game/Project"
    
    # Ensure core folders exist
    for folder in CORE_FOLDERS:
        unreal.EditorAssetLibrary.make_directory(f"{project_root}/{folder}")

    # Logic to move assets based on type would go here
    # Warning: Moving assets in Unreal can break references if not done carefully.
    unreal.log("Standard folders ensured in /Game/Project/")

if __name__ == "__main__":
    if unreal is None:
        print("Error: This script must be run inside Unreal Editor's Python environment.")
        sys.exit(1)
    # By default, we just ensure the structure.
    # Renaming is best triggered manually per-selection.
    organize_folders()
