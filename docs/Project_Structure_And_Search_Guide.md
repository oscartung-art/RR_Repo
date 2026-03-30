---
title: Project Structure & Search Guide
date: 2026-03-29
type: Guide
tags: [search, structure, workflow, google-drive, everything-search, nas]
status: Active
---

# Project Structure & Search Guide

This document is your **quick-reference map** for the studio's "Zero-Lock-In" architecture. If you ever forget where things live or how to find a specific piece of data, refer to this guide.

---

## 1. The Overview: Where Does Data Live?

Our system divides data by its *function* across different drives to avoid relying on proprietary 3rd-party apps (like Connecter or Obsidian).

*   **`D:\` (Google Drive Mirror) — "The Brain & Project Spine"**
    *   **What it is:** The `RR_Repo` folder, synced automatically via Google Drive for Desktop.
    *   **Contents:** Scripts (`pipeline/`, `tools/`), Knowledge Base (`docs/`), Quotes, SOPs, task handoffs (`tasks/`), and `gemini.md`.
*   **`F:\` (NAS) — "The Project Mass"**
    *   **What it is:** Heavy, active project working files.
    *   **Contents:** Folders named `[CODE]_[ProjectName]`. Inside, strict "Flat 3" structure: `01_Brief`, `02_Work`, `03_Shared`. Each project has a `CHANGELOG.md`.
*   **`G:\` (NAS) — "The Asset Mass"**
    *   **What it is:** The master 3D asset library.
    *   **Contents:** Heavy `.zip` files of 3D models, materials, and HDRIs, plus the master `_index.csv`.

---

## 2. The Search Guide: How to Find Anything

Because data is stored in standard formats (Markdown, CSV, JSON), you don't need a special app to find things. Use the right tool for the right data type:

### A. How to find Active Project Feedback & Status
*   **Tool:** `CHANGELOG.md` inside each project folder on `F:\`.
*   **How:** Navigate to `F:\[CODE]_[ProjectName]\` and open `CHANGELOG.md`.
*   **What you'll find:** The complete timeline of client instructions, links to delivered renders, and current project status.

### B. How to find Legacy/Archived Project Data (Contacts, Old Schedules)
*   **Tool:** Windows File Explorer or Everything Search.
*   **How:** Navigate to `F:\[CODE]_[ProjectName]\`. Open the `Project_Hub.md` or `README.md` file.
*   **What you'll find:** Historical data including client emails, architectural contacts, and asset schedules.

### C. How to find 3D Assets & Textures
*   **Tool:** "Everything Search" (by VoidTools).
*   **How:**
    1. Open Everything Search.
    2. Type your PascalCase keywords (e.g., `Furniture Sofa Leather`).
    3. Look at the thumbnail results pointing to your `D:\` (Google Drive) sync folder.
    4. Once you visually confirm the thumbnail you want, note its filename (e.g., `Furniture_3DSky_LeatherSofa_0042.jpg`).
    5. Go to your `G:\` drive and find the exact same filename ending in `.zip` to extract your 3D asset.

### D. How to find Scripts, SOPs, and Studio Knowledge
*   **Tool:** VS Code (Global Search).
*   **How:**
    1. Open the `D:\GoogleDrive\RR_Repo\` workspace in VS Code.
    2. Press `Ctrl + Shift + F`.
    3. Type your query (e.g., "how to name textures" or "unreal export").
    4. VS Code will instantly search across all Markdown files in `docs/` and all Python code.

### E. How to find Passwords & API Keys
*   **Web Logins (3dsky, forums, etc.):** Use **Google Password Manager**.
*   **API Keys (Gemini, etc.):** Look in the `.env` file at the root of `RR_Repo` in VS Code (Note: This file is never synced to any cloud service for security).

---

## 3. Emergency Maintenance

If the asset search stops working or the Google Drive thumbnails get out of sync with the NAS:
1. Open VS Code terminal in `D:\GoogleDrive\RR_Repo\`.
2. Run `python tools/sync_assets.py` (or `tools/rebuild_drive_index.py`).
3. This will rebuild the `_index.csv` map between `G:\` and `D:\`.
