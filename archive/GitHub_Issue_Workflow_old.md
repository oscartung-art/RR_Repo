---
title: GitHub Issue Hub Workflow
date: 2026-03-26
type: Strategy
tags: [workflow, github, issues, projects, logging]
status: Active
---

# GitHub Issue Hub Workflow

This document defines the transition from manual local `CHANGELOG.md` files to a **GitHub Issues-based** project tracking system. It combines the local "Flat 3" folder structure on `F:\` with the centralized, automated logging of GitHub.

## 1. The Core Strategy: GitHub as the "Brain"

Every new project is represented by a **GitHub Issue**. This issue acts as the single source of truth for the project's history, feedback, and delivery status.

- **GitHub Issue:** Stores metadata, communication, feedback, and small attachments (PDFs, low-res renders).
- **F:\ Drive:** Stores large project assets (.skp, .max, .jpg) in the "Flat 3" structure.

---

## 2. A Concrete Example: GLC_GoldCoast

### Step 1: Initialize (The Hub)
When a project starts, create a **GitHub Issue**:
- **Title:** `[CODE] Project Name` (e.g., `[GLC] Gold Coast Clubhouse`).
- **Label:** Use labels like `Active`, `3D Rendering`, `WaitingOnClient`.
- **Initial Comment:** Log the start date and any initial notes.

### Step 2: Ingesting the Brief
- **Local:** Save to `F:\GLC_GoldCoast\01_Brief\YYYY-MM-DD_Description.ext`.
- **GitHub:** Drag and drop the brief file into a comment on the GitHub Issue.
- **Result:** Easy cloud access to briefs without searching the NAS.

### Step 3: Logging Feedback
- **GitHub Action:** Paste client feedback (emails, messages) into a new comment.
- **Example:** `Feedback (2026-03-26): Client requested darker wood for the interior clubhouse render.`

### Step 4: Tracking Deliveries (The Receipt)
- **Local:** Save the render to `F:\GLC_GoldCoast\03_Shared\YYYY-MM-DD_CODE_Description_vXX.ext`.
- **GitHub Action:** Post a comment noting the delivery.
- **Example:** `Delivery: Sent v01 render to client. Filename: 2026-03-26_GLC_FinalRender_v01.jpg`.

---

## 3. Automation Integration

Future scripts (e.g., `new_project.py`) will automate:
1. Creating the GitHub Issue via API.
2. Generating a `.url` shortcut in the project folder root named `GH_ISSUE_#XX.url` to link directly to the issue.
3. Potentially updating the issue status upon file exports.

---

## 4. Key Benefits

- **Zero Manual Formatting:** No Markdown tables to maintain.
- **Global Search:** Find any project's feedback instantly using the project code.
- **Cloud/Mobile Access:** Check project status and briefs from anywhere.
- **Zero-Lock-In:** Project history can be exported from GitHub as Markdown/JSON if needed.
