# Project: RR_Repo (The Studio Brain)

> This is the **single source of truth**. Gemini Web discussions are pasted manually. We operate on a purely text-based, extensionless system. Visualization is text-based. Navigation relies on native VS Code tools.

## The Unifying Principle
> **Google Drive = Brain & Project Spine | NAS = File Mass**

The repo lives on Google Drive and is mirrored locally at `D:\GoogleDrive\RR_Repo`. GitHub is not used.

---

## Core Architecture

| Drive | Role | Contents |
| :--- | :--- | :--- |
| **D:\** (Google Drive Mirror) | **Brain & Project Spine** | `RR_Repo` — scripts, SOPs, gemini.md, docs/, logs/ |
| **F:\** (NAS — Projects) | Project Mass | Large active project files (3ds Max, Unreal, Fusion) |
| **G:\** (NAS — Assets) | Asset Mass | 3D assets and textures, indexed via `_index.csv` |

- **Local Path:** `D:\GoogleDrive\RR_Repo` (same on Desktop and Notebook — Google Drive mirrors automatically)
- **Shared Python Module:** `D:\GoogleDrive\RR_Repo\Shared\config.py` — Pathlib-based constants for all drive roots.

---

## Executive Functions

These capabilities form the "Second Brain" layer of the Studio OS.

- **Memory Capture / The Brain Dump:** Use `log/brain_dump.md` or `log/inbox.md` for rapid thought capture. Say *"Log to inbox: [text]"* to append a row with today's date and status `Unfiled`.
- **Consistency Audits:** Run `python scripts/audit_assets.py [path]` periodically on G:\Assets and active projects to ensure naming compliance.
- **Project Setup:** Use `python scripts/init_project.py [ProjectCode]` for all new commissions to maintain structural parity across drives.
- **Proactive Maintenance:** Gemini CLI updates `docs/` and `gemini.md` automatically when new preferences or tools are discovered. Fixes hardcoded paths. Enforces TDD for master data tools.
- **Task Tracking:** Active tasks are now manually pasted into `log/action_log.md`. Display the log in the 'Minimalist' table format for readability.
- **Cancellation Rule:** Anytime a system, tool, or workflow is cancelled by the user, the agent MUST comprehensively remove it from code, delete related files from the filesystem, and wipe references from all documentation (cancel and clean).

---

## Project Structure

```text
D:\GoogleDrive\RR_Repo
├── gemini.md              ← Single brain (this file)
├── docs/                  ← SOPs, guides, naming conventions
├── logs/                  ← Log files (action_log.md, brain_dump.md, inbox.md)
├── Shared/                ← Shared Python package
│   ├── __init__.py
│   └── config.py          ← Centralized path constants
├── pipeline/              ← Asset enrichment scripts
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
6. **Secrets:** API/Local secrets in `.env` files (excluded from sync). Primary passwords in Google Password Manager.

---

## Key Automation Goals (Phase 1)

- [ ] **`sync_assets.py`** — Scan G:\, maintain `_index.csv`, mirror thumbnails to D:\. *(Prerequisite for EFU export)*
- [ ] **`ingest_asset.py`** — Normalization Station: rename, hash, move to G:\.
- [ ] **`new_project.py`** — Generate standard project folder on F:\ with `CHANGELOG.md`.
- [ ] **`export_efu.py`** — Export `_index.csv` to `.efu` for Everything Search. *(On hold — needs `_index.csv` first)*
- [ ] **`unreal_cleanup.py`** — Automate Unreal Engine Flat & Singular asset structure.

---

## Session Log

Chronological record of significant actions. Most recent first.

| Date | Agent | Action |
| :--- | :--- | :--- |
| 2026-03-30 | Gemini CLI | Cancelled `tasks` folder. Removed all multi-agent sync elements and task handoff protocols. |
| 2026-03-30 | Gemini CLI | Cancelled 3-way sync, Dashboard, and Cloud Brain. Shifted to text-only VSCode-centric workflow. |
| 2026-03-30 | Manus | Executed Master Directive: created tools/audit_assets.py, tools/init_project.py. |
| 2026-03-29 | Gemini CLI | Established and tested the action_log.md system. |
| 2026-03-28 | Gemini CLI | Established Three-Agent Handoff Protocol. |

---

## Technical Stack

- **Automation:** Python 3.9+, Unreal Engine Python API
- **Search:** Everything Search (VoidTools) indexing `_index.csv`
- **Documentation:** Markdown (VS Code / Gemini)
- **Visualization:** Text-based ASCII flowcharts and structured Markdown (No Mermaid.js)

---

## Technical Notes & Troubleshooting

- **File Write Safety Protocol (Read-Modify-Write):** Always perform a final `read_file` on `gemini.md` before writing to ensure you are modifying the current version.
- **VSCode Centric Navigation:** Utilize native VSCode tools for file searches and navigation. We operate on a purely text-based extensionless system.