---
title: Studio Architecture Improvement Plan
date: 2026-03-26
type: Strategy
tags: [architecture, workflow, nas, github, google-drive, automation]
status: Active
---

# Studio Architecture Improvement Plan

This document outlines the strategic shift for Real-HK's storage and workflow architecture. It transitions the studio from an organically grown, manual system to a robust, automated "Zero-Lock-In" environment.

## The Unifying Principle
> **Google Drive = Brain & Project Spine | NAS = File Mass**

The core objective is to eliminate reliance on proprietary third-party applications (like Connecter, Eagle, or Obsidian) by utilizing existing hardware and standardizing data formats (Markdown, CSV/JSON, Python).

---

## Core Infrastructure

| Component | Drive/Service | Responsibility |
| :--- | :--- | :--- |
| **The Brain** | `D:\` (Google Drive Mirror) | `RR_Repo`. Single source of truth for scripts, SOPs, plugin manifests, quotes, task handoffs, and project logs. |
| **The Project Mass** | `F:\` (NAS) | Large active project files (3ds Max, Unreal, Fusion). |
| **The Asset Mass** | `G:\` (NAS) | Centralized, long-term 3D asset storage (Textures, Models, HDRIs). |
| **The Sync Layer** | `D:\` & Google Drive | Local mirror of thumbnails (`.jpg`) for fast cloud browsing and AI metadata enrichment. |

---

## 1. Asset Library (The "DIY-DAM")

**The Problem:** Disconnected metadata (Excel) and manual thumbnail synchronization.
**The Solution:**
*   **The Index:** Replace Excel with a single `_index.csv` (or `.json`) maintained by a Python script. This index maps the `.zip` file on `G:\` to the `.jpg` thumbnail on `D:\`.
*   **Search Engine:** Continue using **Everything Search** by indexing the `_index.csv` (exported as `.efu`).
*   **Automation Goal:** `sync_assets.py` - Scans `G:\`, auto-generates the index, and automatically mirrors matching thumbnails to the Google Drive folder.

## 2. Asset Normalization (The Ingest Pipeline)

**The Problem:** Inconsistent naming conventions from various 3D marketplaces (3dsky, Dimensiva, etc.) and hidden duplicates.
**The Solution:**
*   **The Ingest Station:** New downloads never go directly to `G:\`. They land in a `temp` folder.
*   **Naming Standard:** `[Category]_[Source]_[Description]_[ID].zip` (e.g., `Furniture_3DSky_LeatherSofa_0042.zip`).
*   **Automation Goal:** `ingest_asset.py` - A script that takes a raw download, prompts the user for Category/Source, renames the zip and thumbnail, generates a file hash to detect duplicates, and finally moves it to `G:\`.

## 3. Project Progress Tracking (The "Spine")

**The Problem:** No single source of truth for project status or client feedback; "incoming" folders are messy.
**The Solution:**
*   **Repository-Driven:** Use GitHub to track project progress.
*   **The Log:** Every project folder on `F:\` must contain a `CHANGELOG.md`. This file records dates, delivered files, and client feedback.
*   **Version Control:** Commit client instruction zips/emails into the project repository history (if small enough) or log their receipt in the `CHANGELOG.md`.
*   **Automation Goal:** `new_project.py` - Automates the creation of standard folder structures (`01_Brief`, `02_Work`, `03_Shared`) and initializes the project's `CHANGELOG.md`.

## 4. Scattered Scripts, Notes, and Passwords

**The Problem:** Information is spread across multiple apps and text files.
**The Solution:**
*   **The Knowledge Base:** Centralize all scripts and SOPs in the `RR_Repo/docs/` directory.
*   **Convention:** Use `YYYY-MM-DD_Topic_Description.md` for notes. Use VS Code's global search (`Ctrl+Shift+F`) to find information instantly.
*   **Secrets:** Stick strictly to **Google Password Manager** for web logins. Use local `.env` files (added to `.gitignore`) for API keys.

## 5. 3ds Max Plugin Management

**The Problem:** Difficulty migrating environments or tracking installed plugins.
**The Solution:**
*   **The Manifest:** Maintain a single markdown file (`docs/3dsmax_plugins.md`).
*   **Structure:** A table tracking: `Plugin Name | Version | Source URL | License Key Location | Notes`.
*   **Execution:** Update this manifest immediately upon installing or updating any plugin.

## 6. Quotations and Invoicing

**The Problem:** Unstandardized text files for billing.
**The Solution:**
*   **Markdown Templates:** Create a `quotes/` folder within the repository.
*   **Workflow:** Generate quotes using a standard Markdown template based on `Quotation_Rules.md`.
*   **Export:** Use a VS Code extension or script (e.g., Pandoc) to convert the Markdown quote into a branded PDF for the client.

## 7. Legacy Database Migration Strategy

**The Problem:** Project metadata and schedules (Client Contacts, URLs, Asset Schedules) were trapped in a single `ProjectDB.csv`.
**The Solution:** The database has been split into JSON/CSV files per project using `tools/migrate_db.py`. Moving forward, we use a **Hybrid Approach** for this extracted data:
*   **Active Projects:** Bulk import to GitHub Issues via `gh cli`. The JSON metadata (contacts, links) will form the issue body, and CSV schedules will be attached or formatted as comments.
*   **Archived/Legacy Projects:** Convert the JSON/CSV data into a local `Project_Hub.md` (or `README.md`) file to live permanently in the project's root folder on the `F:\` drive.
*   **Automation Goal:** `deploy_meta.py` - Reads the `projects.json` mapping and deploys the metadata either to GitHub (if active) or NAS (if archived).
