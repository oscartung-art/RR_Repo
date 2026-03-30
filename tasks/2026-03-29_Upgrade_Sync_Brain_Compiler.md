---
id: 2026-03-29_Upgrade_Sync_Brain_Compiler
title: Upgrade sync_brain.py to a Master Compiler
status: done
---

We are upgrading our automated brain sync script so that it compiles all of our active SOPs and logs into a single Google Doc for Gemini Web to read.

1.  **Rewrite the Python Script:**
    Rewrite the file at `D:\GoogleDrive\RR_Repo\scripts\sync_brain.py` using the `google-api-python-client` and `google-auth` libraries.
    The script must perform the following logic:
    -   Define a master string of text to hold the combined markdown.
    -   Read the entire contents of `D:\GoogleDrive\RR_Repo\gemini.md` and add it to the string.
    -   Scan the directories `D:\GoogleDrive\RR_Repo\docs` and `D:\GoogleDrive\RR_Repo\log`.
    -   For every `.md` file found in those directories, check the filename. If the filename contains the word "archive", skip it.
    -   For all other `.md` files, read their text and append it to the master string, using clear separators (e.g., `

--- START OF docs/action_log.md ---

`).
    -   Authenticate with Google Workspace.
    -   Target the Google Doc with ID: `1EmnIcp81vS5ao6isWBVTGol7jVGUQVcArC-VxHPG1w8`.
    -   Fetch the current document to find its end index, send a `DeleteContentRangeRequest` to clear the existing text, and then send an `InsertTextRequest` to paste the new master string at index 1.

2.  **Update `gemini.md` (Single Source of Truth):**
    Change the bullet point under the **Technical Notes & Troubleshooting** section in `gemini.md` to read:
    `- **Automated Master Brain Sync:** We use a compiler script at \scripts/sync_brain.py` that stitches `gemini.md` and all non-archived `.md` files from `docs/` and `log/` into a single, live Google Doc. Whenever Gemini CLI or Manus updates any core `.md` file, they MUST execute `python scripts/sync_brain.py` immediately afterward to keep Gemini Web's context complete.`

3.  **Execute and Verify:**
    Once you have rewritten the script and updated `gemini.md`, execute `python scripts/sync_brain.py` to push the newly compiled 2nd Brain to the cloud.
    Once the CLI finishes executing this, your "Split Brain" will be fully mature. Every time an active log is updated or an SOP is changed, the entire web of rules is instantly synchronized into one perfectly readable file for me.
    Let me know when the CLI has completed this!
