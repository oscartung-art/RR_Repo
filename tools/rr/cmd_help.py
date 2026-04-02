"""
cmd_help.py — rr help [command]
All help content embedded — no external file dependency.
"""

from .utils import c

HELP = {
    "p": {
        "usage":       "rr p [CODE] [view]",
        "description": "Project Inspector — display project metadata and drive paths.",
        "views":       ["summary (default)", "docs", "contacts", "links", "rend", "ani", "full"],
        "examples":    ["rr p PLS", "rr p PLS full", "rr p PLS contacts", "rr p PLS rend"],
    },
    "open": {
        "usage":       "rr open [CODE]",
        "description": "Folder Opener — open the project F: drive directory in Windows Explorer.",
        "examples":    ["rr open PLS"],
    },
    "c": {
        "usage":       "rr c [CODE] [category] [field]",
        "description": "Clipboard Tool — copy a specific project field to the clipboard.",
        "examples":    ["rr c PLS links client_drive", "rr c PLS contacts client email"],
    },
    "dash": {
        "usage":       "rr dash",
        "description": "Project Dashboard — Leads / Active / Completed summary of all projects.",
        "examples":    ["rr dash"],
    },
    "crm": {
        "usage":       "rr crm [search_term]",
        "description": "CRM Viewer — display and search the Master CRM contacts database.",
        "examples":    ["rr crm", "rr crm oscar"],
    },
    "log": {
        "usage":       "rr log [CODE] [message]",
        "description": "Project Logger — append a timestamped entry to a project CHANGELOG on F: drive.",
        "examples":    ['rr log PLS "Client approved R03 render"'],
    },
    "find": {
        "usage":       "rr find [query | image_path] [--top N] [--stats]",
        "description": "Asset Finder — semantic CLIP search across G:\\ asset library.",
        "examples":    ['rr find "Modern Eames Chair"', 'rr find "G:/ref/photo.jpg"', 'rr find "warm wood" --top 20', 'rr find --stats'],
    },
    "help": {
        "usage":       "rr help [command]",
        "description": "Help Menu — list all commands or show details for a specific command.",
        "examples":    ["rr help", "rr help p", "rr help crm"],
    },
}


def run(args):
    if args:
        cmd = args[0].lower()
        if cmd not in HELP:
            print(c("red", f"Command '{cmd}' not found."))
            print(c("grey", "  Run 'rr help' to see all commands."))
            return
        info = HELP[cmd]
        print(f"\n{c('cyan', info['usage'])}")
        print(f"\n  {info['description']}\n")
        if "views" in info:
            views_str = "  ".join(c("yellow", v) for v in info["views"])
            print(f"  {c('bold', 'Views:')}  {views_str}\n")
        if "examples" in info:
            print(f"  {c('bold', 'Examples:')}")
            for ex in info["examples"]:
                print(f"    {c('yellow', ex)}")
        print()
    else:
        print(f"\n{c('green', '=== RR STUDIO CLI ===')}")
        print(f"  {c('grey', 'Usage: rr [command] [args]')}\n")
        for cmd, info in HELP.items():
            print(f"  {c('cyan', f'rr {cmd:<10}')} {c('grey', '-')} {info['description']}")
        hint = "Use 'rr help [command]' for details"
        print(f"\n  {c('grey', hint)}\n")
