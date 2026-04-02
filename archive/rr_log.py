import os
import sys
import argparse
from datetime import datetime


def rr_log(message, project_dir="."):
    changelog_path = os.path.join(project_dir, "CHANGELOG.md")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"- [{timestamp}] {message}"

    if not os.path.exists(changelog_path):
        print(f"Creating new CHANGELOG.md at {changelog_path}...")
        with open(changelog_path, 'w', encoding='utf-8') as f:
            f.write("# Changelog\n\n")

    with open(changelog_path, 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')

    print(f"Logged: {log_entry} to {changelog_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Append a timestamped entry to CHANGELOG.md")
    parser.add_argument("message", help="The message to log to the CHANGELOG.md")
    parser.add_argument("--project-dir", default=".", help="Optional: The project directory containing CHANGELOG.md")
    args = parser.parse_args()

    rr_log(args.message, args.project_dir)
