# RR_Repo: The Studio Brain

> **Single Source of Truth** for Qwen Code.
> Raw Markdown only. No extensions. No Wikilinks. No Mermaid. Navigation via native VS Code tools.

---

## 0. Inbox

This portion is for copy and paste, clean and fit content automatically.

## 1. Core Architecture (The Mirror System)

The project is split across three distinct storage zones to balance speed, storage, and AI context.

| Zone | Path | Content | Role |
| :--- | :--- | :--- | :--- |
| **The Brain** | `D:\RR_Repo\` | Scripts, SOPs, Tasks, CRM, DB | Local + Git version control. AI context anchor. |
| **Project Mass** | `F:\` | 3ds Max, Unreal, Renders | High-speed local NAS. No cloud sync. |
| **Asset Mass** | `G:\` | 3D Library, Textures, HDRI | Indexed via `_index.parquet` and sidecar metadata. |

- **Local Path:** `D:\RR_Repo` — Git-managed repo.
- **Shared Python Module:** `Shared/config.py` — Pathlib-based constants for all drive roots.
- **Shared YAML Parser:** `Shared/frontmatter.py` — single authoritative parser for all project `.md` files.
- Version control via Git.

---

## 2. Repository Structure

```text
D:\RR_Repo
├── qwen.md                <- Single brain (this file)
├── Active_Projects.md     <- Canonical project dashboard
├── inbox.md               <- Raw inbox capture (to be processed)
├── rr / p.bat             <- CLI entry points (Bash / Windows)
├── .env.example           <- API key template (safe to commit)
├── Shared/                <- Shared Python package
│   ├── __init__.py
│   ├── config.py          <- Centralized path constants
│   └── frontmatter.py     <- Shared YAML front matter parser
├── tools/                 <- rr CLI commands and user-facing scripts
│   └── rr/                <- rr subcommand package (cmd_p, cmd_dash, etc.)
├── scripts/               <- Background/maintenance automation (audits, syncs)
├── projects/              <- Per-project .md files with YAML front matter
├── db/                    <- Local data stores (Master_CRM.csv)
├── log/                   <- Logs, notes, orphan reports
├── ipc/                   <- Everything Search SDK (DLL, header, examples)
├── example/quotes/        <- Sample client quotations (automation prototyping)
├── archive/               <- Cancelled or superseded scripts and docs
└── scratch/               <- Exploratory / legacy scripts
```

---

## 3. Executive Functions

- **Tone & Style:** Always explain things simply, like talking to a beginner. Use analogies, avoid jargon, and break down complex concepts into bite-sized pieces. Be direct, casual, and friendly.
- **Memory Capture:** Use `log/brain_dump.md` or `inbox.md` for rapid thought capture. Say *"Log to inbox: [text]"* to append a row with today's date and status `Unfiled`.
- **Consistency Audits:** Run `python tools/audit_assets.py [path]` periodically on `G:\Assets` and active projects to ensure naming compliance.
- **Proactive Maintenance:** Qwen CLI updates `qwen.md` automatically when new preferences or tools are discovered. Fixes hardcoded paths.
- **Task Tracking:** Active tasks are manually pasted into `log/action_log.md`. Use the Minimalist table format.
- **Cancellation Rule:** When any system, tool, or workflow is cancelled, the agent MUST remove it from code, delete related files, and wipe all references from documentation.
- **File Write Safety:** Always perform a `read_file` on `qwen.md` before writing (Read-Modify-Write protocol).
- **Documentation Hygiene:** Keep qwen.md lean. Remove redundant sections, stale references, and outdated goals regularly.

---

## 4. Project Management (Flexible Markdown)

All project data is stored in `projects/[CODE].md` as clean, flexible markdown.
**No YAML, no rigid schema** — each project has different sections, add/remove as needed.

**Format:**
```markdown
# CODE - Project Name

**Client:** Client Name  
**Status:** Lead | Active | Completed  
**F: Drive:** F:\[CODE]  
**Last Updated:** YYYY-MM-DD  

## Contacts
## Design Documents
## Links
## Renderings
## Animations
## Notes
```

**How to use:**
- Tell Qwen: *"Add contact John to KL1"*, *"Update PLS status to Active"*, *"Note that KL1 architect docs are confirmed"*
- Ask naturally: *"What's the status of KL1?"*, *"Which projects have pending architect docs?"*
- Qwen reads/updates files directly — no CLI needed

---

## 5. Naming & Organization Standards

### 5.1 Casing Rules

| Context | Convention | Example |
| :--- | :--- | :--- |
| Folder names / filenames | `lower_case` | `tools/`, `ingest_asset.py` |
| Knowledge files | `Title_Case_With_Underscores` | `Naming_Convention.md` |
| DB values / unique IDs / contact names | `PascalCase` | `HermanMiller`, `OscarTung` |
| Project folder | `CODE_PascalCase` | `3HG_HillGrove` |
| 3ds Max file | `CODE_Loc_Desc_v###` | `MLS99_Podium_Master_v005.max` |
| 3D Object (Mesh) | `SM_Desc_###` | `SM_Lobby_MainWall_001` |
| 3D Object (Proxy) | `PH_Desc_###` | `PH_Chair_Eames_042` |
| Material Instance | `MI_Desc` | `MI_Wood_Walnut` |
| Texture Map | `T_Desc_Suffix` | `T_Wood_Walnut_D` |
| UE Level / Map | `LV_PascalCase` | `LV_13_18_28FTerrace` |
| UE Asset (Mesh/Mat/BP) | `Prefix_PascalCase` | `SM_KidsRoomCabinet` |
| Rendered Output | `CODE_ID_Description.ext` | `PLS_R07_GFLobbyGreen.png` |
| Global Library Asset | `Family_ModelName_Brand` | `Armchair_Eames_HermanMiller.zip` |

### 5.2 Core Principles
- **Context determines case.** Use the table above — do not guess.
- **Prefer consistency over blanket rules.** Keep existing repository folder names stable (`tools/`, `scripts/`, `projects/`).
- **No spaces in any filename or folder name.**

### 5.3 The "No-Break" Rules (ZIP Extraction & Safe Renaming)

| File Type | Can Rename? | Rule |
| :--- | :--- | :--- |
| **Folder** | YES | Always rename parent folder to match convention. |
| **3ds Max (.max)** | YES | Usually safe. |
| **Textures (.jpg/.png)** | NO | Never rename — breaks .max links. |
| **Host CAD (.dwg)** | YES | Safe to rename the master file. |
| **Xref CAD (.dwg)** | NO | Never rename — breaks host link. |

---

## 6. F:\ Drive — Project Structure

- **Convention:** `[CODE]_[ProjectName]` (e.g., `PLS_PingLanStreet`)
- **"Flat 3" Structure:** `01_Brief/`, `02_Work/`, `03_Shared/`
- **Project Log:** `CHANGELOG.md` inside each project folder on F:\

---

## 7. G:\ Drive — Asset Library (Semantic Architecture 2026)

### Core Philosophy

- **Meaning over Naming:** No numerical prefixes (e.g., `10-01`). Discovery is handled by **Semantic Vector Search (CLIP)** — visual vibe, style, and conceptual meaning.
- **No Lock-in:** All metadata in open formats only — **Parquet, CSV, EFU, JPG**. No proprietary DAM databases.
- **Hardware-First (4090):** All indexing runs locally on the RTX 4090. The AI brain stays offline on `G:\`.

### Asset Anchor Standard (Pair Rule)

Every entry in `G:\Asset_Mass` must follow the Pair Rule — an asset without a visible thumbnail is invisible to both Everything Search and the AI index.

| Asset Type | Required Pair |
| :--- | :--- |
| Compressed | `filename.zip` + `filename.jpg` (thumbnail external to archive) |
| Uncompressed | `folder_name/` + `folder_name.jpg` (thumbnail beside the folder) |

**Naming:** Strictly `lower_case_with_underscores`. No spaces, no special characters, no version numbers in the base name.

### Hybrid Data Layer (`_index.parquet`)

The library map is a high-performance Parquet file — the bridge between the 4090's math and human search.

| Column | Type | Purpose |
| :--- | :--- | :--- |
| `path` | String | Unique ID — full path to the `.zip` or folder |
| `vector` | float32[512] | AI brain map — GPS coordinates in semantic space |
| `rating` | Integer | Human score (1–5 stars) |
| `projects` | String | Projects used in (e.g., `KIL112, KIL115`) |
| `designer` | String | Designer name (optional) |

Similarity is calculated via Cosine Similarity between query vector and stored vectors.

### Operational Workflow

**Step A — Audit (`tools/audit_assets.py`):** Run before any indexing. Identifies Orphans (models without thumbnails) and Ghosts (thumbnails without models). No asset enters the index until it is a valid Pair.

**Step B — Index (`scripts/search_index_master.py`):** Batch-processes thumbnails into `_index.parquet` using the RTX 4090. Incremental mode: only processes new or modified files.

**Step C — Find (`scripts/search_clip_text.py`):** Primary retrieval interface.
- Terminal: `rr find "Modern Eames Chair"` or `rr find "G:/ref/client_photo.jpg"`
- Generates a temporary EFU file and opens Everything Search visually.

### Coffee Shop Mode (Mobile)

Copy `_index.parquet` + the 4.5 GB CLIP model to the notebook. Text-to-vector runs on notebook CPU. Search across 40,000+ records remains instantaneous. Identify the asset path locally; fetch the actual `.zip` on return to studio.

### Policy

#### Metadata Hydration Protocol
- Do not encode Facts (Brand, Designer, Price) into the visual vector.
- Use the 4090 to generate the Visual Vector (the What).
- Use Python/Pandas logic to populate Metadata Columns (the Who/Where) from folder paths or source URLs.

#### Search Logic
- Always apply Metadata Filters (SQL/structured columns) before Vector Similarity (AI).
- For known brands, metadata-first retrieval is mandatory to preserve 100% factual accuracy.

### Deprecated (Stop Doing These)

- Numerical prefixes — do not rename files to `10-01_filename`
- Deep nesting — keep structure shallow, no more than 2 levels
- Manual CSV tagging — do not type tags into spreadsheets; let the AI see the thumbnail

### Implementation Status

- [ ] **Brain:** Download CLIP ViT-L/14 model
- [ ] **Map:** Generate first `_index.parquet` using the 4090
- [ ] **Interface:** Configure Everything Search `ai:` filter

---

## 8. Project Metadata Schema

All files in `projects/*.md` must contain this YAML front matter:

```yaml
code: [UPPERCASE_CODE]
name: [Project_Name]
client: [PascalCase_Name]
f_drive_path: F:/[CODE]
status: [Lead | Active | Completed]
last_updated: YYYY-MM-DD
site_info:
  lot: "-"
  address: "-"
contacts:
  client:
    name: "-"
    organization: "-"
    email: "-"
    phone: "-"
    address: "-"
  cg:
    name: "Oscar Tung"
    organization: "Real Rendering"
    email: "oscartung@real-hk.com"
  team:
    architect: "-"
    interior_design: "-"
    landscape: "-"
links:
  client_drive: "-"
  cg_drive: "-"
  architect_drive: "-"
design_documents:
  architect:
    general_building_plan: "Pending"
    camera_angle: "Pending"
    model_3d: "Pending"
  client:
    material_schedule: "Pending"
gis:
  transformation: "-"
  longitude: "-"
  latitude: "-"
renderings:
  R01: "Draft"
animations: {}
```

**Rules:**
- `contacts` and `links` must be **symmetrical** — link keys mirror contact role keys with `_drive` suffix.
- Document statuses: `Pending`, `Received`, `Confirmed`.
- Deliverable statuses: `Draft`, `Active`, `Final`, `Discarded`.
- Unknown fields: use `"-"` — never leave keys empty.

---

## 9. CRM Protocol

- **File:** `db/Master_CRM.csv`
- **Rule:** Contacts must be deduplicated by email. Role-based keys in project files must link to the `Name` column in this CSV.
- Qwen validates contacts against CRM when reading project files.

---

## 10. Rendered Outputs & Deliverables

### The "ID-Anchor" Naming Formula
`[ProjectCode]_[ID]_[Description].[ext]`
- **Example:** `PLS_R07_GFLobbyGreen.png`
- **ID:** Stable anchor — never changes once assigned (R01, R02... / A01, A02...).
- **Description:** PascalCase combined subject + option string.

### The "Backstage vs. Showroom" Strategy
1. **Backstage (`02_Work/`):** Render all iterations here. Overwrite each time — keep flat and current.
2. **Showroom (`03_Shared/`):** Copy only "Committed" renders here for the client.

### Unreal Engine MRQ Token
Output > File Name Format: `[ProjectCode]_{camera_name}`
Camera naming in Outliner: `[ID]_[Description]` (e.g., `R07_GFLobbyGreen`)

---

## 11. Action Log Status Tags

Used in `log/action_log.md`. No other tags permitted.

| Tag | Meaning |
| :--- | :--- |
| `Pending` | In queue, not started |
| `In Progress` | Actively being worked on |
| `Blocked` | Blocked by dependency or external factor |
| `Done` | Complete |
| `Cancelled` | No longer relevant |

---

## 12. Asset Prefixes (Master List)

| Prefix | Type | Description |
| :--- | :--- | :--- |
| `BP` | Blueprint | Unreal Engine Blueprint |
| `CAD` | CAD Drawing | Imported CAD files |
| `CO` | Cutout | 2D cutout assets |
| `FP` | ForestPack | Forest Pack Pro object |
| `HDR` | HDRI | High Dynamic Range Image |
| `LGT` | Light | 3ds Max light placeholder |
| `LV` | Level / Map | Unreal Engine Level file |
| `M` | Master Material | Unreal Engine Master Material |
| `MI` | Material Instance | Unreal Engine Material Instance |
| `PH` | Placeholder | Low-poly proxy for Unreal export |
| `RC` | RailClone | RailClone Pro object |
| `SK` | Skeletal Mesh | Unreal Engine Skeletal Mesh |
| `SM` | Static Mesh | Static Mesh geometry |
| `T` | Texture | Texture maps (UE prefix) |
| `iB1000` | Infrastructure | Infrastructure Base / Integrated Building |
| `Road_` | Road Hierarchy | Road spline organization prefix |

---

## 13. 3ds Max Workflow SOPs

- **N-gons:** Always subdivide N-gons for viewport performance. Never use as reference objects.
- **Post-Import:** Attach geometry + move to layers immediately after any import (CAD, FBX, OBJ).
- **Unreal Export:** Validate no overlapping splines. Convert RailClone to Proxy Mesh before export.

### RailClone (RC)
- User data on markers: compatible with **Node** values only (not Generator).
- Save library with `Ctrl+S` before any modifications.
- Z alignment: set to **Pivot**. Corners: unify to **Bezier Corners**.
- Sequencer Mode: **Adaptive Mode** unavailable when Sequencer Mode is active.

### CivilView (CV)
- In Centimeters: always use **Fixed Station** (not Random Station) for predictable spline placement.

---

## 14. Unreal Engine Content Folder Layout

```
Content/
├── Project/
│   ├── Level/     <- LV_ files
│   ├── Mesh/      <- Flat folder for custom meshes and textures
│   ├── Seq/       <- All LS_ Level Sequences
│   └── Datasmith/ <- Raw Datasmith imports (one subfolder per import)
├── Asset/
│   ├── Furniture/ <- SM_, MI_, T_ files flat inside
│   ├── Vegetation/
│   └── Material/
└── Plugin/        <- Marketplace plugin content
```

---

## 15. Strategic Workflows

1. **Asset Ingest:** New downloads → `tools/ingest_asset.py` → rename, hash for duplicates, move to `G:\`.
2. **Project Init:** Manual scaffold of F: folder + create `projects/[CODE].md`.
3. **Quotations:** Sample markdown source in `example/quotes/` for ingestion/automation prototyping.
4. **Secrets:** API/local secrets in `.env` (excluded from sync). Passwords in Google Password Manager.
5. **Inbox Processing:** Paste raw client text (WhatsApp, email) into `inbox.md`. Ask AI to process and extract tasks.

---

## 16. Key Automation Goals (Phase 1)

- [ ] **`tools/ingest_asset.py`** — Normalization Station: rename, hash, move to G:\.
- [ ] **`tools/unreal_cleanup.py`** — Automate Unreal Engine Flat & Singular asset structure.

---

## 17. AI Directives

> **"You are my Studio Manager. My UI is raw Markdown. When a new project starts:**
> 1. Create `projects/[CODE].md` with the standard YAML front matter (Section 8).
> 2. Manually scaffold F: drive folder with `01_Brief/`, `02_Work/`, `03_Shared/` and `CHANGELOG.md`.
> 3. Use standard Markdown links `[Title](path)`, **NOT** Wikilinks `[[Title]]`.
> 4. Keep text aligned and tidy using whitespace.
> 5. Always include a README file with generated code. The README must explain the purpose of the code and provide clear instructions on how to run it."

**AI Knowledge Management Rules:**
1. **Overwrite, do not append** — read the existing file, synthesize new decisions, rewrite cleanly.
2. **No chat history** — never include conversational text in docs. Only structured data and rules.
3. **Clarity over length** — keep files short while retaining 100% of technical constraints.
4. **Re-read `qwen.md`** at the start of every session to restore full context.

---

## 18. Technical Stack

- **Automation:** Python 3.9+, Unreal Engine Python API
- **Search:** Everything Search (VoidTools) + `_index.parquet` + `.metadata.efu` sidecars
- **Documentation:** Markdown (VS Code / Qwen Code) — raw, no extensions
- **Visualization:** Text-based ASCII flowcharts and structured Markdown tables (no Mermaid.js)
- **AI Agent:** Qwen Code (CLI) — local code operations, documentation, automation

---

## 19. Cross-Machine Setup

**New machine setup (run once):**
```powershell
D:\RR_Repo\tools\setup_notebook.ps1
```
Then:
```bash
bash tools/setup_bash.sh
source ~/.bashrc
```

**Daily resumption:**
1. Confirm Git sync is complete (if using Git).
2. Launch Qwen Code — it auto-loads `qwen.md`.
3. If context is stale mid-session: *"Re-read `qwen.md`."*

---

## 20. Session Log

Chronological record of significant actions. Most recent first.

| Date | Agent | Action |
| :--- | :--- | :--- |
| 2026-04-14 | Qwen | Retired entire rr CLI system (`tools/rr.py`, `tools/rr/`, `p.bat`). Converted all 8 project files from YAML to flexible markdown. Updated README.md and qwen.md to reflect new workflow (natural language Qwen queries replace CLI). |
| 2026-04-14 | Qwen | Cleaned up Drive/Google tooling: deleted `find_cloud_refs.py`, `fix_drive_filenames.py`, `rebuild_drive_index.py`, `scan_drive_all_files.py`, `deploy_meta.py`. Only `copy_data.py` (backend for `rr c`) retained. |
| 2026-04-14 | Qwen | Clean uninstall of all Google Sheets/Drive workflow: deleted `sync_crm.py`, `sync_gsheet_to_local_csv.py`, `compare_apis.py`, `enrich_visual.py`, `re_enrich.py`, `Shared/google_auth.py`. Removed google-* packages from requirements.txt. Updated README.md and qwen.md references. |
| 2026-04-14 | Qwen | Deleted `pipeline/` (enrich_gdrive.py, process_folder.py) — obsolete Gemini enrichment workflow. Cleaned README.md and qwen.md references. |
| 2026-04-14 | Qwen | Major qwen.md cleanup: removed Google/Cloud references, fixed script names (`search_index_master.py`), updated AI agent to Qwen Code, removed redundant memories section, added documentation hygiene rule. Updated header, hybrid strategy, and AI directives sections. |
| 2026-03-31 | Manus | Added `rr find` command (`tools/rr/cmd_find.py`) — CLIP semantic search + EFU export to Everything Search. Supports text query, image query, `--top N`, `--stats`. Graceful fallback when index/packages not ready. |
| 2026-03-31 | Manus | Replaced Section 7 (G: Drive Asset Library) with Semantic Architecture 2026 — CLIP vector search, Parquet index, Pair Rule, Coffee Shop Mode. Deprecated CSV tagging and numerical prefixes. |
| 2026-03-31 | Manus | Improved all three TOML commands (safety gates, schema refs, path fixes, default args). Created `.gemini/commands/README.md` help reference. |
| 2026-03-31 | Manus | Created `.gemini/commands/` with `ingest.toml`, `audit.toml`, `clean.toml` Gemini CLI custom commands. Fixed stale `docs/` reference in `/clean` to point to `qwen.md`. |
| 2026-03-31 | Manus | Consolidated all rr CLI files into `tools/rr/` package (`cmd_p`, `cmd_dash`, `cmd_log`, `cmd_crm`, `cmd_open`, `cmd_c`, `cmd_help`, `utils`). Fixed `rr dash` and `rr log`. Archived old orphaned files: `lookup.py`, `rr_log.py`, `view_crm.py`, `help_commands.py`. `rr.py` is now a thin dispatcher. |
| 2026-03-31 | Manus | Cancelled `sync_brain.py`, `scripts/token.json`, `Shared/credentials.json` (Google Docs sync no longer needed). Deleted `docs/` folder — all content lives in `qwen.md`. |
| 2026-03-31 | Manus | Consolidated all `docs/*.md` into `qwen.md` as single brain. |
| 2026-03-31 | Manus | Full repo audit. Created `tools/rr.py` dispatcher + `tools/setup_bash.sh`. Fixed `rr_log.py`. Updated `lookup.py` to use `Shared/config.py`. Added `Shared/frontmatter.py`. Updated `System_Commands_Reference.md`, `Common_Commands.md`, `VS_Code_Setup_Guide.md`. Created `requirements.txt`. Archived stale scripts and docs. |
| 2026-03-30 | Gemini CLI | Cancelled `tasks` folder. Removed all multi-agent sync elements and task handoff protocols. |
| 2026-03-30 | Gemini CLI | Cancelled 3-way sync, Dashboard, and Cloud Brain. Shifted to text-only VSCode-centric workflow. |
| 2026-03-30 | Manus | Created `tools/audit_assets.py`. Cancelled `init_project.py` and `new_project.py`. |
| 2026-03-29 | Gemini CLI | Established and tested the `action_log.md` system. |
| 2026-03-28 | Gemini CLI | Established Three-Agent Handoff Protocol. |

## Qwen Added Memories
- Everything Search Column Assignment: URL=Project Code, Director=Room/Zone, Composer=Asset Type, Conductor=Status, Scale=Spare. Reserved: company, Track, Version, Length, Genre, Director, Composer, Conductor, Scale. Free for future use: Subject, Comment, From, To, Description, Keywords, link, owner. Rating scale: 99=5 stars, 79=4 stars, 59=3 stars, 39=2 stars, 19=1 star.
