"""
rr.py — RR Studio CLI Entry Point
Real Rendering Studio Brain — Zero-Lock-In Architecture

This file is the Bash alias target. It is intentionally thin:
all command logic lives in tools/rr/cmd_*.py

Bash alias (added by setup_bash.sh):
    rr() { python "D:/RR_Repo/tools/rr.py" "$@"; }

Usage:
    rr help [command]
    rr p [CODE] [docs|contacts|links|rend|ani|full]
    rr open [CODE]
    rr c [CODE] [category] [field]
    rr dash
    rr crm [search_term]
    rr log [CODE] [message]
"""

import sys
import os
from pathlib import Path

# Ensure repo root is on sys.path regardless of cwd
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.rr import cmd_p, cmd_open, cmd_c, cmd_dash, cmd_crm, cmd_log, cmd_help, cmd_find
from tools.rr.utils import c

DISPATCH = {
    "p":    cmd_p.run,
    "open": cmd_open.run,
    "c":    cmd_c.run,
    "dash": cmd_dash.run,
    "crm":  cmd_crm.run,
    "log":  cmd_log.run,
    "find": cmd_find.run,
    "help": cmd_help.run,
}


def main():
    if len(sys.argv) < 2:
        cmd_help.run([])
        return

    command = sys.argv[1].lower()
    args    = sys.argv[2:]

    if command in DISPATCH:
        DISPATCH[command](args)
    else:
        print(c("red", f"Unknown command: '{command}'"))
        cmd_help.run([])


if __name__ == "__main__":
    main()
