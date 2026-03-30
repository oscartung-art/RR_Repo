# Project: RR_Repo (The Studio Brain)

> This is the **single source of truth** for all three agents: Gemini Web, Gemini CLI, and Manus AI.
> All agents read this file. All agents write to this file. There is no separate `manus.md`.

## The Unifying Principle
> **Google Drive = Brain & Project Spine | NAS = File Mass**

The repo lives on Google Drive and is mirrored locally at `D:\GoogleDrive\RR_Repo\`. GitHub is not used.

---

## Core Architecture

| Drive | Role | Contents |
| :--- | :--- | :--- |
| **D:\\** (Google Drive Mirror) | **Brain & Project Spine** | `RR_Repo\` — scripts, SOPs, gemini.md, docs/, tasks/ |
| **F:\\** (NAS — Projects) | Project Mass | Large active project files (3ds Max, Unreal, Fusion) |
| **G:\\** (NAS — Assets) | Asset Mass | 3D assets and textures, indexed via `_index.csv` |

- **Local Path:** `D:\GoogleDrive\RR_Repo\` (same on Desktop and Notebook — Google Drive mirrors automatically)
- **Shared Python Module:** `D:\GoogleDrive\RR_Repo\Shared\config.py` — Pathlib-based constants for all drive roots.

---

## Three-Agent Collaboration Protocol

| Agent | Role | Capability |
| :--- | :--- | :--- |
| **Gemini Web** | Planner & Architect | Discusses and designs. Exports task files to Google Drive root as `.gdoc`. |
| **Gemini CLI** | Local Executor (VS Code) | Reads `tasks/` folder, executes plans locally, marks tasks done. |
| **Manus AI** | Autonomous Executor | Reads `tasks/` folder via Google Drive mount, executes, marks tasks done. |

**Handoff Flow:**
1. Gemini Web plans → exports a Google Doc titled `TASK_YYYY-MM-DD_Task_Name` to the **Google Drive root** (acts as the inbox).
2. Executor (Gemini CLI or Manus) reads the `.gdoc`, converts it to a `.md` task file, and saves it to `tasks/` with the appropriate status (`pending`, `on-hold`, or `done`).
3. Executor moves the original `.gdoc` from the Drive root into `D:\GoogleDrive\bridge\` to keep the root clean.
4. **An empty Drive root = all tasks processed.** Any `.gdoc` remaining at the root is unprocessed.
5. See `tasks/README.md` for the full protocol and `tasks/TASK_FORMAT.md` for the standard format.

---

## Executive Functions

- **The Brain Dump:** Use `log/brain_dump.md` for rapid thought capture via the "Log to inbox:" command.
- **Consistency Audits:** Run `python scripts/audit_assets.py [path]` periodically on G:\Assets and active projects to ensure naming compliance.
- **Project Setup:** Use `python scripts/init_project.py [ProjectCode]` for all new commissions to maintain structural parity across drives.

---

## The Landing Zone & Bridge

```
D:\GoogleDrive\          ← Inbox: Gemini Web drops .gdoc task files here
├── bridge\              ← Archive: processed .gdoc files moved here by executor
└── RR_Repo\             ← The Brain (see structure below)
```

> **Inbox Rule:** After processing any `.gdoc` from the Drive root, always move it to `D:\GoogleDrive\bridge\`. Never leave processed files at the root.

---

## Project Structure

```
D:\GoogleDrive\RR_Repo\
├── gemini.md              ← Single brain for all agents (this file)
├── docs/                  ← SOPs, guides, naming conventions
├── tasks/                 ← Handoff task files (pending → on-hold → done)
│   ├── README.md
│   ├── TASK_FORMAT.md
│   ├── 2026-03-28_Setup_Shared_Config.md          (done)
│   ├── 2026-03-28_Communication_Ping.md           (done)
│   └── 2026-03-28_Everything_Search_Integration.md (on-hold)
├── Shared/                ← Shared Python package
│   ├── __init__.py
│   ├── config.py          ← Centralized path constants
│   └── google_auth.py
├── pipeline/              ← Asset enrichment scripts
├── schedule-matcher/      ← Schedule-to-asset matching (planned)
├── tools/                 ← Utility scripts
├── quotes/                ← Client quotations
├── db/                    ← Project Master Index, CRM
├── archive/               ← Obsolete scripts
└── scratch/               ← Exploratory / legacy scripts
```

---

## F:\ Drive — Project Structure

- **Convention:** `[CODE]_[ProjectName]` (e.g., `3HG_HillGrove`)
- **"Flat 3" Structure:** `01_Brief/`, `02_Work/`, `03_Shared/`
- **Project Log:** `CHANGELOG.md` inside each project folder

---

## G:\ Drive — Asset Structure

- Files indexed in `_index.csv` (no proprietary DAM)
- **Naming Convention:** `[Category]_[Source]_[Description]_[ID].zip`
- Everything Search (VoidTools) indexes `_index.csv` for fast local search

---

## Strategic Workflows

1. **Asset Normalization (Ingest):** New downloads pass through `ingest_asset.py` — renames, hashes for duplicates, moves to G:\.
2. **Asset Sync:** `sync_assets.py` scans G:\, maintains `_index.csv`, mirrors thumbnails to D:\.
3. **Knowledge Base:** `docs/` — flat Markdown files. Convention: `Title_Case_With_Underscores.md`.
4. **Quotations & Invoicing:** `quotes/` folder — Markdown templates exported to PDF via script.
5. **Project Master Index & CRM:** `db/Project_Master_Index.csv` and `db/Master_CRM.csv`.
6. **Proactive Maintenance:** Gemini CLI updates `docs/` and `gemini.md` automatically when new preferences or tools are discovered. Fixes hardcoded paths. Enforces TDD for master data tools.
7. **Task Tracking:** Active tasks logged in `log/action_log.md` using #ID for quick status updates.
8. **The Studio Dashboard Display:** When asked to 'check log', display the log in the 'Minimalist' table format for readability.
9. **Secrets:** API/Local secrets in `.env` files (excluded from sync). Primary passwords in Google Password Manager.

---

## Executive Functions

These capabilities form the "Second Brain" layer of the Studio OS.

- **Memory Capture:** `log/inbox.md` — dump thoughts anytime. Say *"Log to inbox: [text]"* and any agent will append a row with today's date and status `Unfiled`.
- **The Brain Dump:** `log/brain_dump.md` — dump thoughts anytime. Say *"Log to inbox: [text]"* and any agent will append a row with today's date and status `Unfiled`.
- **The Studio Dashboard:** `RR_Studio_Dashboard` (Google Sheet ID: `1Ve4LjD4YGC7tmOnEipJ58Jn230IYnKe9ojJk4SFNcag`) — live mirror of the action log. Run `tools/sync_brain.py` to push updates.
- **Cloud Brain Doc:** Google Doc ID: `1EmnIcp81vS5ao6isWBVTGol7jVGUQVcArC-VxHPG1w8` — stitched `.md` files for mobile reading.
- **Audits:** `tools/audit_assets.py --dir [path] --type [asset|project|docs|tools]` — scans any directory and prints a Markdown violation report with suggested corrected names.
- **Project Initialization:** `tools/init_project.py --code [CODE] --name [Name] --client [Client]` — creates `F:\[CODE]_[Name]\` with Flat 3 structure, `CHANGELOG.md`, per-project log in `log/`, and appends to `db/Project_Master_Index.csv`.
- **Master Sync:** `tools/sync_brain.py` — one command to update Cloud Brain Doc, Dashboard Sheet, and apply conditional colour formatting to Status column.

---

## Key Automation Goals (Phase 1)

- [ ] **`sync_assets.py`** — Scan G:\, maintain `_index.csv`, mirror thumbnails to D:\. *(Prerequisite for EFU export)*
- [ ] **`ingest_asset.py`** — Normalization Station: rename, hash, move to G:\.
- [ ] **`new_project.py`** — Generate standard project folder on F:\ with `CHANGELOG.md`.
- [ ] **`schedule_matcher.py`** — Parse FF&E schedule PDFs, fuzzy-match against asset database.
- [ ] **`export_efu.py`** — Export `_index.csv` to `.efu` for Everything Search. *(On hold — needs `_index.csv` first)*
- [ ] **`unreal_cleanup.py`** — Automate Unreal Engine Flat & Singular asset structure.

---

## Next Actions

Open items for any executor to pick up or for Gemini Web to plan:

### B. Furniture Schedule Matching Pipeline
Architecture planning needed for `schedule_matcher.py`: parse FF&E schedule PDFs/Excel files, fuzzy-match against the asset database using RapidFuzz, generate an Excel report with match status and local file paths.

---

## Session Log

Chronological record of significant actions taken by any executor. Most recent first.

| Date | Agent | Action |
| :--- | :--- | :--- |
| 2026-03-29 | Gemini CLI | Test entry: abc. |
| 2026-03-29 | Gemini CLI | Performed automated brain sync test. |
| 2026-03-29 | Gemini CLI | Established and tested the `action_log.md` system, moved it to `log/`, and configured the 'Minimalist' display format. |
| 2026-03-30 | Manus | Executed Master Directive: created `tools/audit_assets.py`, `tools/sync_brain.py`, `tools/init_project.py`. Added IDs to `Shared/config.py`. Added `## Executive Functions` to gemini.md. |
| 2026-03-29 | Manus | Purged all `E:\Git`, `E:\RR-vault`, and GitHub remnants across 8 files. Migrated 2 Python scripts to `Shared.config`. Rewrote 3 docs. |
| 2026-03-29 | Manus | Merged `manus.md` into `gemini.md` as single brain. Removed `manus.md`. |
| 2026-03-29 | Manus | Added Gemini CLI context refresh protocol to Technical Notes. |
| 2026-03-29 | Manus | Created `D:\GoogleDrive\bridge\`. Moved all `.gdoc` files from Drive root to `bridge\`. |
| 2026-03-29 | Manus | Archived EFU Export task as `tasks/2026-03-28_Everything_Search_Integration.md` with `status: on-hold`. Blocked on `G:\_index.csv`. |
| 2026-03-28 | Manus | Created `Shared/config.py` with Pathlib-based path constants. `BRAIN_ROOT` updated to `D:/GoogleDrive/RR_Repo`. |
| 2026-03-28 | Gemini CLI | Established Three-Agent Handoff Protocol. Created `tasks/README.md` and `tasks/TASK_FORMAT.md`. |
| 2026-03-28 | Gemini CLI | Verified connection test. Created `logs/connection_test.txt`. |

---

## Technical Stack

- **Automation:** Python 3.9+, Unreal Engine Python API
- **CLI Tools:** Gemini CLI, Manus AI
- **Search:** Everything Search (VoidTools) indexing `_index.csv`
- **Documentation:** Markdown (VS Code / Gemini)
- **Visualization:** Mermaid.js (architecture maps, stored in Markdown)

---

## Technical Notes & Troubleshooting

- **Gemini CLI Context Refresh (Three-Agent Parallel Workflow):** Gemini CLI loads `gemini.md` once at startup. It does **not** hot-reload mid-session. When running all three agents simultaneously (Gemini Web, Gemini CLI, Manus), after any architecture change that updates `gemini.md`, tell Gemini CLI: *"Re-read `gemini.md`."* It will read the file from disk and update its working context for the rest of the session. No restart or `/chat clear` required.

- **Google Drive Authentication for Manus:** When Manus needs to read `.gdoc` task files exported by Gemini Web to the Drive root, it uses the `gws` CLI via API. This requires the Google Drive integration in Manus Project Settings to be connected to the exact account that created the `.gdoc` (e.g., `oscartung@real-hk.com`). If credentials are changed or newly connected, a **fresh Manus session** must be started so the new tokens are injected into the environment variables (`GOOGLE_WORKSPACE_CLI_TOKEN`).

- **Local-First File Reading:** Manus always reads files directly from `D:\GoogleDrive\` via the local mount. The `gws` CLI is only used as a fallback for Google-native formats (`.gdoc`, `.gsheet`, `.gslides`) that cannot be read as plain text locally.
- **File Write Safety Protocol (Read-Modify-Write):** To prevent race conditions, any agent (Gemini CLI or Manus) MUST perform a final `read_file` on `gemini.md` immediately before writing to it. This ensures the agent is always modifying the most current version of the file, preventing one agent from overwriting another's changes.
- **Automated Master Brain Sync:** We use a compiler script at `tools/sync_brain.py` that stitches `gemini.md` and all non-archived `.md` files from `docs/` and `log/` into a single, live Google Doc. Whenever Gemini CLI or Manus updates any core `.md` file, they MUST execute `python tools/sync_brain.py` immediately afterward to keep Gemini Web's context complete.
