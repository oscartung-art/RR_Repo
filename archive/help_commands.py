"""
help_commands.py — rr help system
All help content is embedded here. No external file dependency.
"""

import sys

HELP = {
    "p": {
        "usage": "rr p [CODE] [view]",
        "description": "Project Inspector — display project metadata and drive paths.",
        "views": ["docs", "contacts", "links", "rend", "ani", "full"],
        "examples": [
            "rr p PLS",
            "rr p PLS full",
            "rr p PLS contacts",
            "rr p PLS rend",
        ],
    },
    "open": {
        "usage": "rr open [CODE]",
        "description": "Folder Opener — open the project F: drive directory in Windows Explorer.",
        "examples": ["rr open PLS"],
    },
    "c": {
        "usage": "rr c [CODE] [category] [field]",
        "description": "Clipboard Tool — copy a specific project field to the clipboard.",
        "examples": [
            "rr c PLS links client_drive",
            "rr c PLS contacts client email",
        ],
    },
    "dash": {
        "usage": "rr dash",
        "description": "Project Dashboard — categorized summary of all projects (Leads / Active / Completed).",
        "examples": ["rr dash"],
    },
    "crm": {
        "usage": "rr crm [search_term]",
        "description": "CRM Viewer — display and search the Master CRM contacts database.",
        "examples": ["rr crm", "rr crm oscar"],
    },
    "log": {
        "usage": "rr log [CODE] [message]",
        "description": "Project Logger — append a timestamped entry to a project CHANGELOG on F: drive.",
        "examples": ['rr log PLS "Client approved R03 render"'],
    },
    "help": {
        "usage": "rr help [command]",
        "description": "Help Menu — list all commands or show details for a specific command.",
        "examples": ["rr help", "rr help p", "rr help crm"],
    },
}


def _c(code, text):
    """Wrap text in ANSI colour code."""
    codes = {
        "cyan":   "\033[1;36m",
        "green":  "\033[1;32m",
        "yellow": "\033[33m",
        "grey":   "\033[90m",
        "red":    "\033[91m",
        "reset":  "\033[0m",
        "bold":   "\033[1m",
    }
    return f"{codes.get(code, '')}{text}{codes['reset']}"


def display_help(command_name=None):
    if command_name:
        cmd = command_name.lower()
        if cmd not in HELP:
            print(_c("red", f"Command '{cmd}' not found."))
            print(_c("grey", "  Run 'rr help' to see all commands."))
            return

        info = HELP[cmd]
        print(f"\n{_c('cyan', info['usage'])}")
        print(f"\n  {info['description']}\n")

        if "views" in info:
            print(f"  {_c('bold', 'Views:')} {', '.join(_c('yellow', v) for v in info['views'])}\n")

        if "examples" in info:
            print(f"  {_c('bold', 'Examples:')}")
            for ex in info["examples"]:
                print(f"    {_c('yellow', ex)}")
        print()

    else:
        print(f"\n{_c('green', '=== RR STUDIO CLI ===')}")
        print(f"  {_c('grey', 'Usage: rr [command] [args]')}\n")
        for cmd, info in HELP.items():
            print(f"  {_c('cyan', f'rr {cmd:<10}')} {_c('grey', '-')} {info['description']}")
        hint = "Use 'rr help [command]' for details"
        print(f"\n  {_c('grey', hint)}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        display_help(sys.argv[1])
    else:
        display_help()
