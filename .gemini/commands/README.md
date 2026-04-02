# Gemini CLI Custom Commands — Reference

This file documents all custom TOML commands available in this repo.
Load this into Gemini CLI context with: `@.gemini/commands/README.md`

Gemini CLI does not auto-generate help. Run `/commands list` to see one-line descriptions.
For full usage, refer to this file or read the individual `.toml` files directly.

---

## Available Commands

### `/ingest`

**Purpose:** Intelligent routing — takes raw input and updates the correct file automatically.

**Usage:**
```
/ingest [raw text | file path | pasted content]
```

**Examples:**
```
/ingest "Client Oscar called, wants R04 by Friday. Project PLS."
/ingest db/inbox.md
/ingest "New contact: John Lam, john@example.com, ABC Ltd"
```

**Routing Logic:**

| Input Type | Destination |
| :--- | :--- |
| Studio rules / SOPs / decisions | `gemini.md` |
| Project status / contacts / links | `projects/[CODE].md` YAML |
| Contact name / email / org | `db/Master_CRM.csv` |
| Asset file path | `tools/ingest_asset.py` |

**Safety:** Always proposes changes and waits for confirmation before writing.

---

### `/audit`

**Purpose:** System integrity check — naming, hardcoded paths, script logic, and doc neatness.

**Usage:**
```
/audit [path]
```

**Examples:**
```
/audit tools/
/audit scripts/
/audit projects/PLS.md
/audit D:/GoogleDrive/RR_Repo
```

**Checks Performed:**

| Check | What It Looks For |
| :--- | :--- |
| Naming | Files/folders violating naming conventions in `gemini.md` |
| Logic | Hardcoded paths, missing `Shared/config.py` imports, duplicate logic |
| Neatness | Plural names, conversational text, sections already in `gemini.md` |

**Output:** Prioritized refactor table: File | Issue | Severity | Recommended Fix

---

### `/clean`

**Purpose:** Deep purge — redundant files, dead code, stale docs.

**Usage:**
```
/clean [path]
```
If no path is given, scans the entire `D:/GoogleDrive/RR_Repo`.

**Examples:**
```
/clean tools/
/clean scripts/
/clean D:/GoogleDrive/RR_Repo
```

**Scan Targets:**

| Category | What It Flags |
| :--- | :--- |
| Files | Temp files (`~$*`, `*.tmp`), old versioned files, redundant thumbnails |
| Code | Dead functions, unused imports, logic duplicating `tools/rr/` commands |
| Docs | Standalone `.md` files already consolidated into `gemini.md` |

**Output:** Purge & Refactor table: File | Type | Reason | Action
**Safety:** Never deletes or moves anything without explicit user confirmation.

---

## Notes

- All commands re-read `gemini.md` before acting to ensure full context.
- TOML files live in `.gemini/commands/` — edit them directly to adjust behaviour.
- After editing any `.toml`, run `/commands reload` in Gemini CLI to pick up changes.
- To add a new command, create a new `.toml` file in this directory and add it to this README.
