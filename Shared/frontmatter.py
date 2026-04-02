"""
Shared/frontmatter.py — Centralized YAML Front Matter Parser
Real Rendering — Zero-Lock-In Architecture

Provides a single, robust recursive parser for YAML front matter blocks
used in all project .md files. Import this instead of duplicating the
parser in individual scripts.

Usage:
    from Shared.frontmatter import parse_front_matter
    data = parse_front_matter("path/to/project.md")
"""

import re
import os


def parse_front_matter(filepath: str) -> dict | None:
    """
    Parses nested YAML front matter from a Markdown file without third-party libraries.

    Returns a dict of parsed key/value pairs (with nested dicts for indented blocks),
    or None if the file does not exist or contains no front matter.

    Supports:
      - Root-level key: value pairs
      - Nested blocks (indented key: value pairs under a root key)
      - Inline comments (# stripped)
      - Single and double quoted values
    """
    if not os.path.exists(filepath):
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'^---\s*\n(.*?)\n---\s*', content, re.DOTALL | re.MULTILINE)
    if not match:
        return None

    # Strip inline comments and blank lines
    lines = [
        l.split('#')[0].rstrip()
        for l in match.group(1).splitlines()
        if l.strip() and not l.lstrip().startswith('#')
    ]

    def parse_block(index: int, current_indent: int) -> tuple[dict, int]:
        data = {}
        while index < len(lines):
            line = lines[index]
            indent = len(line) - len(line.lstrip())
            if indent < current_indent:
                break
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if not val:
                    # Possibly a nested block follows
                    if index + 1 < len(lines):
                        next_indent = len(lines[index + 1]) - len(lines[index + 1].lstrip())
                        if next_indent > indent:
                            nested_data, index = parse_block(index + 1, next_indent)
                            data[key] = nested_data
                            continue
                else:
                    data[key] = val
            index += 1
        return data, index

    parsed_data, _ = parse_block(0, 0)
    return parsed_data
