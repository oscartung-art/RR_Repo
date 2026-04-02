#!/usr/bin/env bash
# setup_bash.sh — RR_Repo Bash Environment Setup (Git Bash / WSL)
# Run this once on any new machine to wire up the `rr` CLI in Bash.
#
# Usage (from repo root in Git Bash):
#   bash tools/setup_bash.sh

REPO_ROOT="D:/GoogleDrive/RR_Repo"
BASHRC="$HOME/.bashrc"
VENV_ACTIVATE="$REPO_ROOT/.venv/Scripts/activate"

echo ""
echo "=== RR_Repo Bash Setup ==="
echo ""

# 1. Add rr alias to ~/.bashrc
RR_ALIAS="rr() { python \"$REPO_ROOT/tools/rr.py\" \"\$@\"; }"
RR_COMMENT="# RR Studio CLI"

if grep -q "tools/rr.py" "$BASHRC" 2>/dev/null; then
    echo "[=] rr alias already present in $BASHRC — skipping."
else
    echo "" >> "$BASHRC"
    echo "$RR_COMMENT" >> "$BASHRC"
    echo "$RR_ALIAS" >> "$BASHRC"
    echo "[+] Added rr alias to $BASHRC"
fi

# 2. Add .venv auto-activation (optional, only if .venv exists)
VENV_LINE="[ -f \"$VENV_ACTIVATE\" ] && source \"$VENV_ACTIVATE\""
if grep -q "RR_Repo/.venv" "$BASHRC" 2>/dev/null; then
    echo "[=] .venv activation already present in $BASHRC — skipping."
else
    echo "" >> "$BASHRC"
    echo "# RR_Repo Python venv auto-activate" >> "$BASHRC"
    echo "$VENV_LINE" >> "$BASHRC"
    echo "[+] Added .venv auto-activation to $BASHRC"
fi

# 3. Source the updated .bashrc
echo ""
echo "Setup complete. Run the following to activate in your current session:"
echo ""
echo "  source ~/.bashrc"
echo ""
echo "Then test with:"
echo "  rr help"
echo ""
