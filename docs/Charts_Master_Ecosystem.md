# Studio Master Ecosystem & Workflows

This document is the consolidated visual map of the Real-HK "Zero-Lock-In" architecture. It maps the macro-level system layout, followed by the specific daily workflows for communications, projects, and 3D assets.

---

## 1. MACRO VIEW: System Architecture

How your hardware, cloud services, and production tools connect.

```text
┌────────────────────────────────────────────────────────┐
│ [ THE BRAIN ] (D:\GoogleDrive\RR_Repo - Google Drive)    │
│                                                        │
│ 📁 docs/ (SOPs, Guides)    📁 db/ (Project/Asset CSVs) │
│ 📁 quotes/ (Templates)     📁 tools/ (Python Scripts)  │
│ 📄 Active_Projects.md      📄 inbox.md                 │
└─────────┬───────────────────────────┬──────────────────┘
          │ (Scripts Manage)          │ (Cloud Sync)
          ▼                           ▼
┌───────────────────────┐   ┌────────────────────────────┐
│ [ THE MASS ] (NAS)    │   │ [ THE CLOUD & COMMS ]      │
│                       │   │                            │
│ 📁 F:\ Active Projects│   │ 📁 D:\ Google Drive (Brain)│
│    (Unreal, 3ds Max)  │   │ 📱 WhatsApp / Email        │
│                       │   │ 💸 Waveapps (Finance)      │
│ 📁 G:\ Asset Library  │──►│    (Thumbnails / Delivery) │
│    (High-Res Zips)    │   │                            │
└─────────┬─────────────┘   └────────────────────────────┘
          │ (Assets pulled into / Renders saved out)
          ▼
┌───────────────────────┐
│ [ THE ENGINE ROOM ]   │
│ - 3ds Max & Plugins   │
│ - Unreal Engine 5     │
│ - Fusion / Compositing│
│ - Quixel Bridge       │
└───────────────────────┘
```

---

## 2. MICRO VIEW: The Information Pipeline

How chaotic client communications are transformed into structured, actionable data.

```text
 [ CHAOS ]                                  [ STRUCTURE ]

 📱 WhatsApp ──────┐
                   │
 📧 Email ─────────┼──► [ 📄 inbox.md ] ──► [ 📄 Active_Projects.md ]
                   │      (Raw Text Dump)     (Actionable Dashboard)
 💬 Direct ────────┘                               │
                                                   ▼
 🗂️ Loose Files ──────► [ 📁 D:/Dump ] ───► [ 📁 F:/Project/01_Brief ]
```

---

## 3. MICRO VIEW: Project Lifecycle (F: Drive)

The step-by-step flow from awarding a job to final invoicing.

```text
 1. AWARDED
    ├──► Run 'new_project.py'
    ├──► Generates: F:\KIL112\ (01_Brief, 02_Work, 03_Shared)
    └──► Creates: CHANGELOG.md for logging & discussion

 2. EXECUTION & FEEDBACK
    ├──► Build scenes in '02_Work'
    ├──► Save drafts to '03_Shared'
    ├──► Client sends feedback ──► Paste into 'inbox.md'
    └──► Process 'inbox.md' ─────► Update 'Active_Projects.md' checklist

 3. DELIVERY & INVOICING
    ├──► Export final renders to '03_Shared'
    ├──► Generate Invoice in Waveapps
    └──► Paste Waveapps Link & Status into 'Active_Projects.md'
```

---

## 4. MICRO VIEW: Asset Library Lifecycle (G: Drive)

How messy 3D model downloads become a highly searchable "DIY-DAM".

```text
 1. INGESTION
    ├──► Download messy zip (e.g., from 3dsky) to Temp folder
    └──► Run 'ingest_asset.py'
           ├─► Renames to: [Category]_[Source]_[ID].zip
           ├─► Generates unique hash to prevent duplicates
           └─► Moves zip/jpg to G:\ Asset Library

 2. INDEXING & SYNC
    └──► Run 'sync_assets.py'
           ├─► Scans G:\ Drive
           ├─► Updates 'db/Asset_Index.csv' with all metadata
           └─► Mirrors all .jpg thumbnails to D:\ Google Drive

 3. SEARCH & REUSE
    ├──► Use 'Everything Search' ──► Search "Chair Leather 3dsky"
    └──► Pull .zip directly from G:\ into your 3D Scene
```
