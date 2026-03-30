import os
import sys
import re

# Define base directory relative to the script's location (tools/ folder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMANDS_REFERENCE_PATH = os.path.join(BASE_DIR, "docs", "System_Commands_Reference.md")

def format_for_terminal(text):
    """Converts basic markdown to ANSI terminal escape sequences for beautiful output."""
    # Command Title: ### `command` -> Bold Cyan
    text = re.sub(r'### `(.*?)`', r'\033[1;36m\1\033[0m', text)
    # Bold headers: **Header:** -> Bold White
    text = re.sub(r'\*\*(.*?)\*\*', r'\033[1m\1\033[0m', text)
    # Code blocks: ``` ... ``` -> Yellow
    text = re.sub(r'```[a-z]*\n?(.*?)\n?```', r'  \033[33m\1\033[0m', text, flags=re.DOTALL)
    # Inline code: `code` -> Yellow
    text = re.sub(r'`(.*?)`', r'\033[33m\1\033[0m', text)
    return text

def display_help(command_name=None):
    if not os.path.exists(COMMANDS_REFERENCE_PATH):
        print(f"\033[91mError: Command reference file not found at {COMMANDS_REFERENCE_PATH}\033[0m")
        return

    with open(COMMANDS_REFERENCE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if command_name:
        pattern = rf'### `({re.escape(command_name)})`\s*\n(.*?)(?=\n### `|$)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            formatted_text = format_for_terminal(match.group(0).strip())
            print(f"\n{formatted_text}\n")
        else:
            print(f"\033[91mCommand '{command_name}' not found in reference.\033[0m")
    else:
        # Minimalist List View
        print("\n\033[1;32m--- SYSTEM COMMANDS ---\033[0m")
        # Find all commands and their descriptions, excluding the [COMMAND_NAME] template
        # Pattern: ### `command` followed by Description: text
        # We start searching after "## Available Commands:" to skip the template section
        available_start = content.find("## Available Commands:")
        if available_start != -1:
            search_content = content[available_start:]
        else:
            search_content = content

        matches = re.finditer(r'### `(.*?)`(.*?)(?=\n### `|$)', search_content, re.DOTALL)
        for m in matches:
            cmd = m.group(1).strip()
            if cmd == "[COMMAND_NAME]" or not cmd: continue
            
            block = m.group(2)
            
            # Extract description
            desc_match = re.search(r'\*\*Description:\*\*\s*(.*?)(?=\n\*\*)', block, re.DOTALL)
            desc = desc_match.group(1).strip().replace("**", "").replace("_", "") if desc_match else "No description."
            
            # Extract usage
            usage_match = re.search(r'\*\*Usage:\*\*\s*```\w*\n(.*?)\n```', block, re.DOTALL)
            usage = usage_match.group(1).strip() if usage_match else cmd
            
            print(f"  \033[1;36m{usage:<20}\033[0m \033[90m-\033[0m {desc}")
        print("\n  \033[90mUse 'rr help [command]' for details\033[0m\n")



if __name__ == "__main__":
    if len(sys.argv) > 1:
        display_help(sys.argv[1])
    else:
        display_help()
