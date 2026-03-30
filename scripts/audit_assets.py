import os
import re
import argparse

# This would ideally be dynamically parsed from Naming_Convention.md
# For now, we'll hardcode a simplified version of the core rules.
# This can be expanded later into a more robust parser.
# Example Rule: [Category]_[Source]_[Description]_[ID].zip
ASSET_ZIP_PATTERN = re.compile(r"^[A-Za-z]+_[A-Za-z0-9]+_[A-Za-z0-9_]+_\d+\.zip$")

# Example Rule: T_[ProjectCode]_[Category]_[Description]_[Suffix].ext
TEXTURE_PATTERN = re.compile(r"^T_[A-Z0-9]+_[A-Za-z]+_[A-Za-z0-9_]+_[A-Z]\.(jpg|png|exr|tx)$")

# Example Rule for Renders: [ProjectCode]_[ViewName]_[Description]_v###.[ext]
RENDER_PATTERN = re.compile(r"^[A-Z0-9]+_.+_.+_v\d{3,}\.(jpg|png|exr)$")


def audit_directory(directory_path):
    """
    Scans a directory and identifies files that do not conform to the
    hardcoded naming conventions.
    """
    violations = []

    if not os.path.isdir(directory_path):
        print(f"Error: Provided path '{directory_path}' is not a valid directory.")
        return

    for root, _, files in os.walk(directory_path):
        for filename in files:
            # Skip common nuisance files
            if filename.lower() in [".ds_store", "desktop.ini", "thumbs.db"]:
                continue

            filepath = os.path.join(root, filename)
            
            # Simple check based on file extension or name patterns
            if filename.endswith(".zip"):
                if not ASSET_ZIP_PATTERN.match(filename):
                    violations.append({
                        "file": filepath,
                        "rule_violated": "Asset ZIP Pattern",
                        "suggestion": "Should be like: [Category]_[Source]_[Description]_[ID].zip"
                    })
            elif filename.startswith("T_"):
                 if not TEXTURE_PATTERN.match(filename):
                    violations.append({
                        "file": filepath,
                        "rule_violated": "Project Texture Pattern",
                        "suggestion": "Should be like: T_[ProjectCode]_[Category]_[Description]_[Suffix].ext"
                    })
            # Add more checks here as the logic evolves...
            # This is a starting point. A more advanced version would parse
            # Naming_Convention.md to build these regex patterns dynamically.

    return violations


def main():
    """Main function to parse arguments and print the audit results."""
    parser = argparse.ArgumentParser(description="Audit a directory against project naming conventions.")
    parser.add_argument("directory", help="The full path to the directory to audit.")
    args = parser.parse_args()

    print(f"Auditing directory: {args.directory}")
    violations = audit_directory(args.directory)

    if not violations:
        print("
✅ All scanned files conform to the basic naming conventions!")
        return

    print("
--- Naming Convention Violations ---")
    print("| File | Rule Violated | Suggestion |")
    print("| :--- | :--- | :--- |")
    for v in violations:
        # To make paths more readable in the table
        relative_path = os.path.relpath(v['file'], start=args.directory)
        print(f"| {relative_path} | {v['rule_violated']} | {v['suggestion']} |")
    print("------------------------------------")


if __name__ == "__main__":
    main()
