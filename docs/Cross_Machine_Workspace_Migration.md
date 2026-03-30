---
title: Cross-Machine Workspace Migration Checklist
id: cross-machine-workspace-migration
date: 2026-03-29
type: Process Guide
tags: [setup, migration, google-drive, vscode, gemini]
status: Active
---

# Cross-Machine Workspace Migration Checklist

This guide outlines the steps required to seamlessly transition your `RR_Repo` workspace and AI terminal environment from one machine (e.g., your primary workstation) to another (e.g., a secondary laptop).

> **Architecture Note:** GitHub has been removed from this workflow. The repo lives on Google Drive and is automatically mirrored to `D:\GoogleDrive\RR_Repo\` on every machine via Google Drive for Desktop. No manual sync or `git push` is required.

---

## Phase 1: Pre-Departure (On Machine A)

Before leaving your current machine, ensure all AI context is up to date.

- [ ] **1. Save All Files:** Ensure all open files in VS Code are saved.
- [ ] **2. Sync AI Context:** If you've made significant decisions, ask Gemini or Manus to update `gemini.md` (e.g., *"Update gemini.md with our latest progress."*).
- [ ] **3. Wait for Drive Sync:** Confirm the Google Drive tray icon shows sync is complete before switching machines.
- [ ] **4. VS Code Settings Sync (Optional):** Verify that VS Code Settings Sync is enabled (Accounts > Settings Sync is On) to persist your UI layout and extensions.

---

## Phase 2: Initial Setup (On Machine B — First Time Only)

- [ ] **1. Install Core Prerequisites:**
  - Google Drive for Desktop (to mirror `D:\GoogleDrive\`)
  - Node.js (v18+)
  - Python 3.9+
  - VS Code
- [ ] **2. Sign in to Google Drive for Desktop** with `oscartung@real-hk.com`. Wait for `D:\GoogleDrive\RR_Repo\` to fully sync.
- [ ] **3. Run Automated Setup:**
  ```powershell
  D:\GoogleDrive\RR_Repo\tools\setup_notebook.ps1
  ```
- [ ] **4. Authenticate CLIs:**
  - Gemini CLI: Run `gemini` and enter your API key when prompted.
  - Google Workspace (gws): Run `gws auth login` for Manus integration.
- [ ] **5. VS Code Configuration:** Sign in to VS Code Settings Sync to restore your extensions and layout.
- [ ] **6. Open Workspace:** Open `D:\GoogleDrive\RR_Repo\` as your VS Code workspace folder.

---

## Phase 3: Daily Resumption (On Machine B)

Whenever you switch to the secondary machine, follow these steps to resume your workflow.

- [ ] **1. Confirm Drive Sync:** Check the Google Drive tray icon — ensure it shows sync is complete. The latest `gemini.md` will already be present at `D:\GoogleDrive\RR_Repo\gemini.md`.
- [ ] **2. Activate Python Environment (if required):**
  ```bash
  D:\GoogleDrive\RR_Repo\.venv\Scripts\activate
  ```
- [ ] **3. Launch Gemini CLI:**
  ```bash
  gemini
  ```
  Gemini will automatically load `gemini.md` and have the exact same project knowledge as Machine A.

---

## Troubleshooting

- **"Command not found: gemini"**: Ensure Node.js is installed and the npm global prefix is in your system PATH.
- **Files not syncing:** Check the Google Drive for Desktop tray icon. If paused, resume sync and wait for completion before starting work.
- **Gemini CLI has stale context mid-session:** Tell it: *"Re-read `gemini.md`."* No restart required.
